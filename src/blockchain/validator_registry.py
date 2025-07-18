from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import ec
from src.utils.database import db_connection
from src.utils.logger import logger

class ValidatorRegistry:
    """رجیستری برای مدیریت کلیدهای عمومی ولیدیتورها"""
    _validators = {}
    
    @classmethod
    def add_validator(cls, address: str, public_key_pem: str):
        # ذخیره در حافظه
        cls._validators[address] = public_key_pem
        
        # ذخیره در دیتابیس
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO validators (address, public_key_pem)
            VALUES (?, ?)
            ''', (address, public_key_pem))
            conn.commit()

    @classmethod
    def get_public_key(cls, address: str) -> ec.EllipticCurvePublicKey:
        # اول از حافظه بازیابی کند
        public_key_pem = cls._validators.get(address)
        
        # اگر در حافظه نبود، از دیتابیس بخواند
        if not public_key_pem:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT public_key_pem FROM validators WHERE address = ?', (address,))
                row = cursor.fetchone()
                if row:
                    public_key_pem = row[0]
                    cls._validators[address] = public_key_pem  # کش در حافظه
        
        if not public_key_pem:
            raise ValueError(f"Validator {address} not registered")
            
        return load_pem_public_key(public_key_pem.encode())