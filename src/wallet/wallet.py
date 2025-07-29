import os
import json
from src.utils.crypto import generate_key_pair, private_key_to_pem, public_key_to_pem, address_from_public_key
from src.utils.database import db_connection
from src.utils.logger import logger

class Wallet:
    def __init__(self, node):
        self.node = node
        self.accounts = {}
        self.load_accounts()

    def create_account(self, account_name):
        """Create new cryptographic account"""
        private_key, public_key = generate_key_pair()
        private_pem = private_key_to_pem(private_key)
        public_pem = public_key_to_pem(public_key)
        address = address_from_public_key(public_pem)
        
        self.accounts[account_name] = {
            'address': address,
            'private_key': private_pem,
            'public_key': public_pem
        }
        
        # Save to database
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (address, public_key_pem)
                VALUES (?, ?)
            ''', (address, public_pem))
            conn.commit()
        
        self.save_wallet()
        return address

    def get_account(self, account_name):
        """Get account details"""
        return self.accounts.get(account_name)

    def get_private_key(self, account_name):
        """Get private key for signing"""
        account = self.get_account(account_name)
        return account['private_key'] if account else None

    def save_wallet(self):
        """Save wallet to secure file"""
        wallet_path = os.path.join('data', 'wallet.json')
        with open(wallet_path, 'w') as f:
            json.dump(self.accounts, f, indent=2)

    def load_accounts(self):
        """Load accounts from database and wallet file"""
        # Load from database
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT address, public_key_pem FROM accounts')
            for address, public_key_pem in cursor.fetchall():
                self.accounts[address] = {
                    'address': address,
                    'public_key': public_key_pem
                }
        
        # Load private keys from secure file
        wallet_path = os.path.join('data', 'wallet.json')
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
                for name, data in wallet_data.items():
                    if name in self.accounts:
                        self.accounts[name]['private_key'] = data.get('private_key')