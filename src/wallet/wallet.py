import hashlib
import os
import json
import binascii
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from src.utils.database import db_connection
from src.utils.logger import logger

class Wallet:
    def __init__(self, node):
        self.node = node
        self.accounts = {}
        self.load_accounts()
        self.check_permissions()

    def create_account(self, account_name):
        """Create new cryptographic account"""
        private_key = ec.generate_private_key(
            ec.SECP256K1(),
            default_backend()
        )
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Generate address
        address = '0x' + hashlib.sha256(public_pem.encode()).hexdigest()[:40]
        
        self.accounts[account_name] = {
            'name': account_name,
            'address': address,
            'private_key': private_pem,
            'public_key': public_pem
        }
        
        self.save_to_db(address, public_pem)
        self.save_wallet()
        return address

    def check_permissions(self):
        wallet_path = os.path.join('data', 'wallet.json')
        if os.path.exists(wallet_path):
            if not os.access(wallet_path, os.W_OK | os.R_OK):
                logger.error("Wallet file is not writable. Please check permissions.")
                raise PermissionError("Wallet file is not writable.")

    def get_account(self, account_name):
        """Get account details"""
        return self.accounts.get(account_name)

    def get_account_by_address(self, address):
        """Get account details by address"""
        return self.accounts.get(address)

    def get_private_key(self, account_name):
        """Get private key for signing"""
        account = self.get_account(account_name)
        return account['private_key'] if account else None

    def save_to_db(self, address, public_pem):
        """Save account to database"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (address, public_key_pem)
                VALUES (?, ?)
            ''', (address, public_pem))
            conn.commit()

    def save_wallet(self):
        """Save wallet data with proper error handling"""
        wallet_path = os.path.join('data', 'wallet.json')
        try:
            wallet_data = {}
            for name, acc in self.accounts.items():
                if 'private_key' in acc:
                    wallet_data[name] = {
                        'address': acc['address'],
                        'private_key': acc['private_key'],
                        'public_key': acc.get('public_key', '')
                    }

            with open(wallet_path, 'w') as f:
                json.dump(wallet_data, f, indent=2)
                
            logger.info("Wallet saved successfully")
        except Exception as e:
            logger.error(f"Failed to save wallet: {e}")

    def load_accounts(self):
        """Load accounts with enhanced error handling"""
        # Create data directory if not exists
        os.makedirs('data', exist_ok=True)
        
        wallet_path = os.path.join('data', 'wallet.json')
        wallet_path = os.path.abspath(wallet_path)

        # Check if wallet exists
        if not os.path.exists(wallet_path):
            logger.warning("Wallet file not found, creating new one")
            with open(wallet_path, 'w') as f:
                json.dump({}, f)
            return

        try:
            # Load wallet file
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
                logger.debug(f"Loaded wallet data: {wallet_data}")

            # Load from database
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT address, public_key_pem FROM accounts')
                for address, public_pem in cursor.fetchall():
                    self.accounts[address] = {
                        'address': address,
                        'public_key': public_pem
                    }
                    logger.debug(f"Loaded account from DB: {address}")

            # Merge private keys
            for name, data in wallet_data.items():
                if isinstance(data, dict) and 'address' in data:
                    if data['address'] in self.accounts:
                        self.accounts[data['address']].update({
                            'name': name,
                            'private_key': data.get('private_key')
                        })
                        logger.debug(f"Merged private key for {data['address']}")
                    else:
                        logger.warning(f"Address {data['address']} not found in DB")

            # Warn if any account is missing a private key
            for addr, acc in self.accounts.items():
                if 'private_key' not in acc:
                    logger.warning(f"Account {addr} is missing a private key. It may be watch-only.")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in wallet file: {e}")
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")