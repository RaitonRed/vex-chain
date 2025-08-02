import json
import hashlib
import time
from typing import Dict, Any, Tuple
from src.utils.logger import logger
from src.utils.database import db_connection

class SmartContractVM:
    """ماشین مجازی برای اجرای قراردادهای هوشمند"""
    
    GAS_COSTS = {
        'ADD': 3,
        'SUB': 3,
        'MUL': 5,
        'DIV': 5,
        'STORE': 100,
        'LOAD': 50,
        'CALL': 500,
        'CREATE': 2000,
        'JUMP': 10,
        'JUMPI': 10,
        'SSTORE': 200,
        'SLOAD': 100,
        'BALANCE': 100,
        'TRANSFER': 500,
        'EQ': 3,
        'LT': 3,
        'GT': 3,
        'AND': 3,
        'OR': 3,
        'NOT': 3,
        'SHA3': 30,
        'REVERT': 0
    }
    
    def __init__(self, state_db):
        self.state_db = state_db
        self.gas_used = 0
        self.output = None
        self.error = None
        self.logs = []
        
    def execute(self, tx: 'Transaction', block_number: int, timestamp: float) -> Tuple[bool, Any]:
        """اجرای یک تراکنش قرارداد هوشمند"""
        self.gas_used = 0
        self.output = None
        self.error = None
        self.logs = []
        
        try:
            context = {
                'sender': tx.sender,
                'value': tx.amount,
                'block_number': block_number,
                'timestamp': timestamp,
                'input': tx.contract_args,
                'storage': {},
                'memory': {},  # حافظه موقت برای اجرای قرارداد
                'balance': self._get_balance(tx.sender),
                'code': tx.contract_code if tx.contract_type == "CREATE" else self._load_contract_code(tx.contract_address)
            }
            
            # بارگذاری وضعیت ذخیره‌سازی
            if tx.contract_type == "CALL":
                context['storage'] = self._load_storage(tx.contract_address)
            
            # اجرای دستورات
            instructions = context['code'].split(';') if context['code'] else []
            for instruction in instructions:
                parts = instruction.strip().split()
                if not parts:
                    continue
                    
                opcode = parts[0].upper()
                params = parts[1:]
                
                # بررسی هزینه گاز
                gas_cost = self.GAS_COSTS.get(opcode, 10)
                if self.gas_used + gas_cost > tx.gas_limit:
                    raise RuntimeError(f"Out of gas (used: {self.gas_used}, limit: {tx.gas_limit})")
                
                # اجرای دستور
                if opcode == 'ADD':
                    self._op_add(context, params)
                elif opcode == 'SUB':
                    self._op_sub(context, params)
                elif opcode == 'MUL':
                    self._op_mul(context, params)
                elif opcode == 'DIV':
                    self._op_div(context, params)
                elif opcode == 'STORE':
                    self._op_store(context, params)
                elif opcode == 'LOAD':
                    self._op_load(context, params)
                elif opcode == 'CALL':
                    self._op_call(context, params)
                elif opcode == 'JUMP':
                    self._op_jump(context, params)
                elif opcode == 'JUMPI':
                    self._op_jumpi(context, params)
                elif opcode == 'SSTORE':
                    self._op_sstore(context, params)
                elif opcode == 'SLOAD':
                    self._op_sload(context, params)
                elif opcode == 'BALANCE':
                    self._op_balance(context, params)
                elif opcode == 'TRANSFER':
                    self._op_transfer(context, params)
                elif opcode == 'EQ':
                    self._op_eq(context, params)
                elif opcode == 'LT':
                    self._op_lt(context, params)
                elif opcode == 'GT':
                    self._op_gt(context, params)
                elif opcode == 'AND':
                    self._op_and(context, params)
                elif opcode == 'OR':
                    self._op_or(context, params)
                elif opcode == 'NOT':
                    self._op_not(context, params)
                elif opcode == 'SHA3':
                    self._op_sha3(context, params)
                elif opcode == 'REVERT':
                    self._op_revert(context, params)
                elif opcode == 'RETURN':
                    self._op_return(context, params)
                elif opcode == 'LOG':
                    self._op_log(context, params)
                else:
                    raise RuntimeError(f"Unknown opcode: {opcode}")
                
                self.gas_used += gas_cost
            
            # ذخیره وضعیت برای قراردادهای جدید
            if tx.contract_type == "CREATE":
                contract_address = self._create_contract_address(tx)
                self._save_contract(contract_address, context['code'], tx.sender)
                self.output = contract_address
            
            # ذخیره وضعیت ذخیره‌سازی
            if tx.contract_type == "CALL":
                self._save_storage(tx.contract_address, context['storage'])
            
            return True, self.output
        
        except Exception as e:
            self.error = str(e)
            logger.error(f"Contract execution failed: {self.error}")
            return False, self.error

    # دستورات ماشین مجازی
    def _op_add(self, context, params):
        if len(params) < 3:
            raise RuntimeError("ADD requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = a + b

    def _op_sub(self, context, params):
        if len(params) < 3:
            raise RuntimeError("SUB requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = a - b

    def _op_mul(self, context, params):
        if len(params) < 3:
            raise RuntimeError("MUL requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = a * b

    def _op_div(self, context, params):
        if len(params) < 3:
            raise RuntimeError("DIV requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        if b == 0:
            raise RuntimeError("Division by zero")
        context['storage'][var_name] = a // b

    def _op_store(self, context, params):
        if len(params) < 2:
            raise RuntimeError("STORE requires 2 parameters")
        key = params[0]
        value = self._get_value(context, params[1])
        context['memory'][key] = value

    def _op_load(self, context, params):
        if len(params) < 2:
            raise RuntimeError("LOAD requires 2 parameters")
        dest = params[0]
        src = params[1]
        context['memory'][dest] = context['memory'].get(src, 0)

    def _op_call(self, context, params):
        if len(params) < 1:
            raise RuntimeError("CALL requires at least contract address")
        contract_address = params[0]
        logger.info(f"Contract call to {contract_address}")

    def _op_jump(self, context, params):
        if len(params) < 1:
            raise RuntimeError("JUMP requires line number")
        # در این پیاده‌سازی ساده، پرش انجام نمی‌شود
        logger.warning("JUMP opcode not implemented")

    def _op_jumpi(self, context, params):
        if len(params) < 2:
            raise RuntimeError("JUMPI requires line number and condition")
        condition = self._get_value(context, params[1])
        if condition:
            # در این پیاده‌سازی ساده، پرش انجام نمی‌شود
            logger.warning("JUMPI opcode not implemented")

    def _op_sstore(self, context, params):
        if len(params) < 2:
            raise RuntimeError("SSTORE requires 2 parameters")
        key = params[0]
        value = self._get_value(context, params[1])
        context['storage'][key] = value

    def _op_sload(self, context, params):
        if len(params) < 2:
            raise RuntimeError("SLOAD requires 2 parameters")
        dest = params[0]
        key = params[1]
        context['memory'][dest] = context['storage'].get(key, 0)

    def _op_balance(self, context, params):
        if len(params) < 2:
            raise RuntimeError("BALANCE requires 2 parameters")
        dest = params[0]
        address = params[1]
        balance = self._get_balance(address)
        context['memory'][dest] = balance

    def _op_transfer(self, context, params):
        if len(params) < 2:
            raise RuntimeError("TRANSFER requires 2 parameters")
        recipient = params[0]
        amount = self._get_value(context, params[1])
        
        if context['balance'] < amount:
            raise RuntimeError("Insufficient balance")
        
        context['balance'] -= amount
        self._update_balance(context['sender'], context['balance'])
        self._add_balance(recipient, amount)
    
    def _op_eq(self, context, params):
        if len(params) < 3:
            raise RuntimeError("EQ requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = 1 if a == b else 0

    def _op_lt(self, context, params):
        if len(params) < 3:
            raise RuntimeError("LT requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = 1 if a < b else 0

    def _op_gt(self, context, params):
        if len(params) < 3:
            raise RuntimeError("GT requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = 1 if a > b else 0

    def _op_and(self, context, params):
        if len(params) < 3:
            raise RuntimeError("AND requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = a & b

    def _op_or(self, context, params):
        if len(params) < 3:
            raise RuntimeError("OR requires 3 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        b = self._get_value(context, params[2])
        context['storage'][var_name] = a | b

    def _op_not(self, context, params):
        if len(params) < 2:
            raise RuntimeError("NOT requires 2 parameters")
        var_name = params[0]
        a = self._get_value(context, params[1])
        context['storage'][var_name] = ~a

    def _op_sha3(self, context, params):
        if len(params) < 2:
            raise RuntimeError("SHA3 requires 2 parameters")
        var_name = params[0]
        data = str(self._get_value(context, params[1]))
        hash_val = hashlib.sha3_256(data.encode()).hexdigest()
        context['storage'][var_name] = hash_val

    def _op_revert(self, context, params):
        message = " ".join(params) if params else "Execution reverted"
        raise RuntimeError(f"REVERT: {message}")

    def _op_return(self, context, params):
        if params:
            self.output = self._get_value(context, params[0])

    def _op_log(self, context, params):
        message = " ".join(params)
        self.logs.append({
            'sender': context['sender'],
            'message': message,
            'timestamp': context['timestamp']
        })

    def _op_jump(self, context, params):
        if len(params) < 1:
            raise RuntimeError("JUMP requires line number")
        line_num = int(params[0])
        context['pc'] = line_num  # تنظیم شمارنده برنامه

    def _op_jumpi(self, context, params):
        if len(params) < 2:
            raise RuntimeError("JUMPI requires line number and condition")
        condition = self._get_value(context, params[1])
        if condition:
            line_num = int(params[0])
            context['pc'] = line_num

    # توابع کمکی
    def _get_value(self, context, value_str):
        """ارزش را از ذخیره‌سازی یا به صورت مستقیم برمی‌گرداند"""
        # ابتدا بررسی می‌کنیم آیا مقدار یک عدد است
        if value_str.isdigit() or (value_str[0] == '-' and value_str[1:].isdigit()):
            return int(value_str)
        
        # سپس بررسی می‌کنیم آیا در حافظه موقت وجود دارد
        if value_str in context['memory']:
            return context['memory'][value_str]
        
        # سپس بررسی می‌کنیم آیا در ذخیره‌سازی وجود دارد
        if value_str in context['storage']:
            return context['storage'][value_str]
        
        # در نهایت، اگر متغیر تعریف نشده بود خطا می‌دهیم
        raise RuntimeError(f"Undefined variable: {value_str}")

    def _create_contract_address(self, tx):
        """ایجاد آدرس قرارداد از هش تراکنش"""
        return hashlib.sha256(f"{tx.sender}{tx.tx_hash}".encode()).hexdigest()[:40]

    def _load_contract_code(self, contract_address):
        return self.state_db.load_contract_code(contract_address)
    
    def _save_contract(self, address, code, creator):
        self.state_db.save_contract(address, code, creator)
    
    def _load_storage(self, contract_address):
        return self.state_db.load_storage(contract_address)
    
    def _save_storage(self, contract_address, storage):
        self.state_db.save_storage(contract_address, storage)
    
    def _get_balance(self, address):
        return self.state_db.get_balance(address)
    
    def _update_balance(self, address, new_balance):
        self.state_db.update_balance(address, new_balance)
    
    def _add_balance(self, address, amount):
        self.state_db.add_balance(address, amount)