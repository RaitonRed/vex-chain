import hashlib
import os
import json
import binascii
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
from src.blockchain.db.state_db import StateDB
from src.blockchain.transaction import Transaction
from src.utils.database import db_connection
from src.utils.logger import logger

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from src.utils.crypto import generate_secure_nonce

class Wallet:
    def __init__(self, node):
        self.node = node
        self.accounts = {}
        # self.encryption_key = self._get_encryption_key()
        self.encryption_key = self._drive_encryption_key()
        self.load_accounts()
        self.check_permissions()

    def _drive_encryption_key(self):
        """Safely get or generate encryption key"""
        password = os.getenv("WALLET_PASSWORD", "default_password")
        salt = b"a1b2c3d4e5f6g7h8i9j0"  # Use a secure random salt in production
    
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        return kdf.derive(password.encode('utf-8'))

    def _get_encryption_key(self):
        """Safely get or generate encryption key"""
        key_path = "data/wallet_key.key"
        os.makedirs("data", exist_ok=True)
        
        try:
            # Try to read existing key
            if os.path.exists(key_path):
                with open(key_path, "rb") as key_file:
                    return key_file.read()
            
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            os.chmod(key_path, 0o600)
            return key
        except Exception as e:
            logger.error(f"Failed to get encryption key: {e}")
            raise
    
    def _encrypt_data(self, data):
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data):
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_data.encode()).decode()

    def create_account(self, account_name):
        """Create new cryptographic account"""
        private_key = ec.generate_private_key(
            ec.SECP521R1(),
            default_backend()
        )
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key = private_key.public_key()

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Generate address
        address = 'VcX' + hashlib.blake2b(public_bytes, digest_size=20).hexdigest()
        
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
                        'private_key': self._encrypt_data(acc['private_key']),
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
            try:
                with open(wallet_path, 'w') as f:
                    json.dump({}, f)
                return
            except Exception as e:
                logger.error(f"Failed to create wallet file: {e}")
                raise

        try:
            # ADDED: Log file path
            logger.debug(f"Loading wallet from {wallet_path}")
            
            # Load wallet file
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)
                logger.debug(f"Loaded wallet data: {wallet_data}")

            # Initialize accounts dictionary
            self.accounts = {}
            
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
                    decrypted_pk = None
                    if 'private_key' in data:
                        try:
                            decrypted_pk = self._decrypt_data(data['private_key'])
                        except Exception as e:
                            logger.error(f"Decryption failed for {data['address']}: {e}")

                    if data['address'] in self.accounts:
                        self.accounts[data['address']].update({
                            'name': name,
                            'private_key': decrypted_pk
                        })
                        logger.debug(f"Merged private key for {data['address']}")
                    else:
                        logger.warning(f"Address {data['address']} not found in DB. Creating new entry.")
                        self.accounts[data['address']] = {
                            'name': name,
                            'address': data['address'],
                            'public_key': data.get('public_key', ''),
                            'private_key': decrypted_pk
                        }

            # Warn if any account is missing a private key
            for addr, acc in self.accounts.items():
                if 'private_key' not in acc:
                    logger.warning(f"Account {addr} is missing a private key. It may be watch-only.")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in wallet file: {e}")
            logger.error(f"Wallet file content: {open(wallet_path).read()}")
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")
            logger.exception(e)  # ADDED: Full exception traceback

    def create_transaction(self, recipient, amount, data=None):
        account = self.get_account()
        nonce = StateDB().get_nonce(account['address']) + 1
            
        tx = Transaction(
            sender=account['address'],
            recipient=recipient,
            amount=amount,
            data=data or {},
            nonce=nonce
        )
            
        tx.sign(self.get_private_key())
        return tx
    
    def _validate_encryption_key(self, key):
        try:
            Fernet(key)  # Test if key is valid
            return True
        except:
            return False

    def _get_encryption_key(self):
        key_path = "data/wallet_key.key"
        os.makedirs("data", exist_ok=True)
        
        try:
            # Try to read existing key
            if os.path.exists(key_path):
                with open(key_path, "rb") as key_file:
                    key = key_file.read()
                    if self._validate_encryption_key(key):
                        return key
                    else:
                        logger.warning("Invalid encryption key found, generating new one")
            
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            os.chmod(key_path, 0o600)
            return key
        except Exception as e:
            logger.error(f"Failed to get encryption key: {e}")
            raise

    def rotate_encryption_key(self):
        """Generate a new encryption key and re-encrypt all private keys"""
        # Backup old key
        old_key = self.encryption_key
        
        # Generate new key
        self.encryption_key = Fernet.generate_key()
        
        # Re-encrypt all private keys
        for acc in self.accounts.values():
            if 'private_key' in acc:
                plaintext = self._decrypt_data(acc['private_key'], old_key)
                acc['private_key'] = self._encrypt_data(plaintext)
        
        # Save updated wallet
        self.save_wallet()
        
        # Save new key to file
        with open("data/wallet_key.key", "wb") as key_file:
            key_file.write(self.encryption_key)
        
        logger.info("Encryption key rotated successfully")

    def _decrypt_data(self, encrypted_data, key=None):
        """Decrypt data with optional key override"""
        key = key or self.encryption_key
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data.encode()).decode()