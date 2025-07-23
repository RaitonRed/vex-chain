import hashlib
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from src.utils.database import db_connection
from typing import Dict

class ValidatorRegistry:
    """مدیریت ثبت و احراز هویت ولیدیتورها"""
    
    @staticmethod
    def register_validator(address: str, public_key_pem: str, stake: float):
        """ثبت ولیدیتور جدید با کلید عمومی و مقدار سهام"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO validators 
                (address, public_key_pem, stake, last_active)
                VALUES (?, ?, ?, datetime('now'))
            ''', (address, public_key_pem, stake))
            conn.commit()

    @staticmethod
    def get_validator_stake(address: str) -> float:
        """دریافت مقدار سهام یک ولیدیتور"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT stake FROM validators WHERE address = ?', (address,))
            row = cursor.fetchone()
            return row[0] if row else 0

    @staticmethod
    def get_active_validators() -> Dict[str, float]:
        """دریافت لیست ولیدیتورهای فعال و سهام آنها"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT address, stake FROM validators 
                WHERE last_active > datetime('now', '-1 day')
            ''')
            return {row[0]: row[1] for row in cursor.fetchall()}

    @staticmethod
    def get_validator_address(private_key: ec.EllipticCurvePrivateKey) -> str:
        """استخراج آدرس از کلید خصوصی"""
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            Encoding.PEM,
            PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(public_bytes).hexdigest()[:40]