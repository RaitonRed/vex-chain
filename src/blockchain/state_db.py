import json
import time
from src.utils.database import db_connection

class StateDB:
    """پیاده‌سازی StateDB برای قراردادهای هوشمند"""
    
    def load_contract_code(self, contract_address):
        """بارگذاری کد قرارداد از دیتابیس"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM contracts WHERE address = ?', (contract_address,))
            row = cursor.fetchone()
            return row[0] if row else None

    def save_contract(self, address, code, creator):
        """ذخیره قرارداد جدید در دیتابیس"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contracts (address, code, creator, created_at)
                VALUES (?, ?, ?, ?)
            ''', (address, code, creator, time.time()))
            conn.commit()

    def load_storage(self, contract_address):
        """بارگذاری وضعیت ذخیره‌سازی قرارداد"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT storage FROM contract_state WHERE contract_address = ?', (contract_address,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else {}

    def save_storage(self, contract_address, storage):
        """ذخیره وضعیت ذخیره‌سازی قرارداد"""
        with db_connection() as conn:
            cursor = conn.cursor()
            storage_json = json.dumps(storage)
            cursor.execute('''
                INSERT OR REPLACE INTO contract_state (contract_address, storage)
                VALUES (?, ?)
            ''', (contract_address, storage_json))
            conn.commit()

    def get_balance(self, address):
        """دریافت موجودی حساب (پیاده‌سازی نمونه)"""
        return 1000000  # مقدار ثابت برای نمونه

    def update_balance(self, address, new_balance):
        """به‌روزرسانی موجودی حساب (پیاده‌سازی نمونه)"""
        pass

    def add_balance(self, address, amount):
        """افزایش موجودی حساب (پیاده‌سازی نمونه)"""
        pass