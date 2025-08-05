class GasTracker:
    """سیستم ردیابی و مدیریت مصرف گاز در اجرای قراردادهای هوشمند"""
    
    def __init__(self):
        self.remaining_gas = 0
        self.total_used = 0
        self.gas_costs = {
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
    
    def initialize(self, gas_limit: int):
        """مقدار اولیه گاز را تنظیم می‌کند"""
        self.remaining_gas = gas_limit
        self.total_used = 0
    
    def consume(self, opcode: str) -> bool:
        """مصرف گاز برای یک عملیات خاص"""
        cost = self.gas_costs.get(opcode, 10)  # مقدار پیش‌فرض 10
        
        if self.remaining_gas < cost:
            return False  # گاز کافی نیست
        
        self.remaining_gas -= cost
        self.total_used += cost
        return True
    
    def refund(self, amount: int):
        """بازگرداندن گاز استفاده شده"""
        self.remaining_gas += amount
        self.total_used -= amount
    
    def get_remaining(self) -> int:
        """دریافت مقدار گاز باقیمانده"""
        return self.remaining_gas
    
    def get_used(self) -> int:
        """دریافت مقدار گاز مصرف شده"""
        return self.total_used