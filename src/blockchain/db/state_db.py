import json
import time
from trie import HexaryTrie
from src.utils.database import db_connection

class StateDB:
    """پیاده‌سازی StateDB برای قراردادهای هوشمند"""
    
    def __init__(self):
        self.trie = HexaryTrie(db={})
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
        """Get account information"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT address, public_key_pem, nonce FROM accounts WHERE address = ?', 
                (address,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'address': row[0],
                    'public_key_pem': row[1],
                    'nonce': row[2]
                }
            return None
    
    def update_account(self, address: str, public_key_pem: str = None, nonce: int = None):
        """Update account information without overwriting public key"""
        account = self.get_account(address) or {}
        
        # Use existing values if not provided
        if public_key_pem is None:
            public_key_pem = account.get('public_key_pem', "")
        if nonce is None:
            nonce = account.get('nonce', 0)
        
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (address, public_key_pem, nonce)
                VALUES (?, ?, ?)
            ''', (address, public_key_pem, nonce))
            conn.commit()

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

    def reset(self):
        """Reset state database to initial state"""
        self.trie = HexaryTrie(db={})
        self.cache = {}

        with db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM accounts WHERE address != '0x0000000000000000000000000000000000000000'")
            cursor.execute("DELETE FROM balances")
            cursor.execute("UPDATE accounts SET nonce = 0 WHERE address = '0x0000000000000000000000000000000000000000'")
        
            conn.commit()

    def get_vex_balance(self, address: str) -> float:
        """Get VEX balance for an address"""
        return self.get_balance(address)
    
    def update_vex_balance(self, address: str, amount: float):
        """Update VEX balance for an address"""
        self.update_balance(address, amount)

    def transfer_vex(self, sender: str, recipient: str, amount: float) -> bool:
        """Transfer VEX from sender to recipient"""
        sender_balance = self.get_vex_balance(sender)
        if sender_balance < amount:
            raise ValueError("Insufficient balance")
            return False

        self.update_vex_balance(sender, sender_balance - amount)
        recipient_balance = self.get_vex_balance(recipient)
        self.update_vex_balance(recipient, recipient_balance + amount)