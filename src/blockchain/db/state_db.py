import json
import time
from trie import MerklePatriciaTrie
from src.utils.database import db_connection

class StateDB:
    """پیاده‌سازی StateDB برای قراردادهای هوشمند"""
    
    def __init__(self):
        self.trie = MerklePatriciaTrie(db={})
        self.cache = {}
        self.nonce_prefix = b"nonce_"

    def create_account(self, address: str, public_key_pem: str = "", nonce: int = 0):
        """Create a new account in the database"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO accounts (address, public_key_pem, nonce)
                VALUES (?, ?, ?)
            ''', (address, public_key_pem, nonce))
            conn.commit()

    def get_account(self, address: str) -> dict:
        """دریافت حساب با کش و درخواست به Trie"""
        if address in self.cache:
            return self.cache[address]
        
        encoded = self.trie.get(address.encode())
        if not encoded:
            return None
            
        account = json.loads(encoded.decode())
        self.cache[address] = account
        return account
    
    def update_account(self, address: str, account_data: dict):
        """به‌روزرسانی حساب در Trie و کش"""
        encoded = json.dumps(account_data).encode()
        self.trie.update(address.encode(), encoded)
        self.cache[address] = account_data

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
        """Get account balance"""

        # Check cache first
        if address in self.cache:
            return self.cache[address]

        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM balances WHERE address = ?', (address,))
            row = cursor.fetchone()
            return row[0] if row else 0

        value = self.trie.get(address.encode())
        return float(value.decode()) if value else 0.0

    def update_balance(self, address, new_balance):
        """Update account balance"""

        # Update trie
        key = address.encode()
        value = str(new_balance).encode()
        self.trie.set(key, value)

        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO balances (address, balance)
                VALUES (?, ?)
            ''', (address, new_balance))
            conn.commit()

    def add_balance(self, address, amount):
        """Add to account balance"""
        current = self.get_balance(address)
        self.update_balance(address, current + amount)

    def get_nonce(self, address: str) -> int:
        """Get the current nonce for an address

        Args:
            address (str): wallet address

        Returns:
            int: nonce
        """
        
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT nonce FROM accounts WHERE address = ?', 
                (address,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    def increment_nonce(self, address: str) -> int:
        """Increment and return the new nonce for an address"""
        with db_connection() as conn:
            cursor = conn.cursor()

            # FIX: Changed 'none' to 'nonce'
            cursor.execute(
                'SELECT nonce FROM accounts WHERE address = ?', 
                (address,)
            )
            row = cursor.fetchone()
            current_nonce = row[0] if row else 0

            # Update nonce
            new_nonce = current_nonce + 1
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (address, public_key_pem, nonce)
                VALUES (?, ?, ?)
            ''', (address, None, new_nonce))
            conn.commit()  # FIX: Changed cursor.commit() to conn.commit()
            return new_nonce