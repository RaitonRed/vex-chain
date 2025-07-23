import hashlib
import json
import time
from typing import Optional
from src.blockchain.transaction import Transaction
from src.utils.database import db_connection
from src.utils.logger import logger

class ContractManager:
    """مدیریت چرخه حیات قراردادهای هوشمند"""
    
    @staticmethod
    def deploy_contract(sender: str, code: str) -> str:
        """استقرار قرارداد جدید و بازگرداندن آدرس آن"""
        # ایجاد آدرس منحصر به فرد
        tx_hash = hashlib.sha256(f"{sender}{time.time_ns()}".encode()).hexdigest()
        contract_address = f"0x{tx_hash[:40]}"
        
        # ذخیره در دیتابیس
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contracts (address, code, creator, created_at)
                VALUES (?, ?, ?, ?)
            ''', (contract_address, code, sender, time.time()))
            conn.commit()
        
        logger.info(f"Contract deployed at {contract_address}")
        return contract_address

    @staticmethod
    def call_contract(sender: str, contract_address: str, method: str, args: dict, amount: float = 0) -> Transaction:
        """ایجاد تراکنش برای فراخوانی قرارداد"""
        tx = Transaction(
            sender=sender,
            recipient=contract_address,
            amount=amount,
            contract_type="CALL",
            contract_method=method,
            contract_args=args
        )
        return tx

    @staticmethod
    def get_contract_code(contract_address: str) -> Optional[str]:
        """دریافت کد قرارداد"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM contracts WHERE address = ?', (contract_address,))
            row = cursor.fetchone()
            return row[0] if row else None

    @staticmethod
    def get_contract_state(contract_address: str) -> dict:
        """دریافت وضعیت ذخیره‌سازی قرارداد"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT storage FROM contract_state WHERE contract_address = ?', (contract_address,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else {}