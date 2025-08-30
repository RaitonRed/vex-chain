import hashlib
import os
import json
import base64
import getpass
import sys
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


class Wallet:
    def __init__(self, node):
        self.node = node
        self.accounts = {}
        self.encryption_key = None
        self.load_accounts()
        self.check_permissions()

    def _get_user_password(self):
        """Get password securely from user"""
        try:
            password = os.getenv("WALLET_PASSWORD")
            if not password:
                if sys.stdin.isatty():
                    password = getpass.getpass("Enter wallet password: ")
                else:
                    logger.error("WALLET_PASSWORD environment variable not set")
                    raise ValueError("Wallet password required")
            return password
        except Exception as e:
            logger.error(f"Failed to get password: {e}")
            raise

    def _derive_key_from_password(self, password, salt=None):
        """Derive encryption key from password"""
        if salt is None:
            salt = os.urandom(16)  # Generate random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        raw_key = kdf.derive(password.encode('utf-8'))
        return base64.urlsafe_b64encode(raw_key), salt

    def _encrypt_data(self, data, password):
        """Encrypt data with password-derived key"""
        key, salt = self._derive_key_from_password(password)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt + encrypted).decode()

    def _decrypt_data(self, encrypted_data, password):
        """Decrypt data with password-derived key"""
        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            salt = data[:16]
            encrypted = data[16:]
            key, _ = self._derive_key_from_password(password, salt)
            fernet = Fernet(key)
            return fernet.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def create_account(self, account_name, password):
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
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Generate address
        address = 'VCX' + hashlib.blake2b(public_bytes, digest_size=20).hexdigest()
        
        # Encrypt private key with user password
        encrypted_private = self._encrypt_data(private_pem, password)
        
        self.accounts[account_name] = {
            'name': account_name,
            'address': address,
            'public_key': public_pem,
            'private_key': encrypted_private  # Store encrypted private key
        }
        
        # Return private key to user (should be saved securely)
        self.save_to_db(address, public_pem)
        self.save_wallet()
        
        return address, private_pem  # Return both address and private key

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

    def save_wallet(self):
        """Save wallet data without private keys"""
        wallet_path = os.path.join('data', 'wallet.json')
        try:
            wallet_data = {}
            for name, acc in self.accounts.items():
                wallet_data[name] = {
                    'address': acc['address'],
                    'public_key': acc.get('public_key', ''),
                    'private_key': acc.get('private_key', '')  # Save encrypted private key
                }

            with open(wallet_path, 'w') as f:
                json.dump(wallet_data, f, indent=2)
                
            logger.info("Wallet saved successfully (with encrypted private keys)")
        except Exception as e:
            logger.error(f"Failed to save wallet: {e}")

    def load_accounts(self):
        """Load accounts and decrypt private keys"""
        os.makedirs('data', exist_ok=True)
        wallet_path = os.path.join('data', 'wallet.json')

        if not os.path.exists(wallet_path):
            logger.warning("Wallet file not found, creating new one")
            with open(wallet_path, 'w') as f:
                json.dump({}, f)
            return

        try:
            with open(wallet_path, 'r') as f:
                wallet_data = json.load(f)

            self.accounts = {}
            for name, data in wallet_data.items():
                self.accounts[name] = {
                    'name': name,
                    'address': data['address'],
                    'public_key': data.get('public_key', ''),
                    'private_key': data.get('private_key', '')  # Load encrypted private key
                }
                
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")

    def import_private_key(self, account_name, private_key_pem, password):
        """Import and encrypt a private key"""
        try:
            # Validate private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            address = 'VcX' + hashlib.blake2b(public_bytes, digest_size=20).hexdigest()
            
            # Encrypt private key with user password
            encrypted_private = self._encrypt_data(private_key_pem, password)
            
            self.accounts[account_name] = {
                'name': account_name,
                'address': address,
                'public_key': public_pem,
                'private_key': encrypted_private  # Store encrypted private key
            }
            
            self.save_to_db(address, public_pem)
            self.save_wallet()
            
            return address
            
        except Exception as e:
            logger.error(f"Failed to import private key: {e}")
            raise

    def get_private_key(self, account_name, password):
        """Retrieve private key temporarily (should not be stored)"""
        account = self.get_account(account_name)
        if not account or 'private_key' not in account:
            logger.error(f"Account {account_name} not found or private key missing.")
            return None

        encrypted_private_key = account['private_key']
        try:
            private_key_pem = self._decrypt_data(encrypted_private_key, password)
            return private_key_pem
        except Exception as e:
            logger.error(f"Failed to decrypt private key for {account_name}: {e}")
            return None

    def create_transaction(self, recipient, amount, data=None, account_name=None, password=None):
        if not account_name:
            # Default to the first account if none is specified
            if not self.accounts:
                raise ValueError("No accounts available. Create or import an account first.")
            account_name = next(iter(self.accounts))

        account = self.get_account(account_name)
        if not account:
            raise ValueError(f"Account '{account_name}' not found.")

        private_key_pem = self.get_private_key(account_name, password)
        if not private_key_pem:
            raise ValueError("Private key not available for signing.")

        nonce = StateDB().get_nonce(account['address']) + 1
            
        tx = Transaction(
            sender=account['address'],
            recipient=recipient,
            amount=amount,
            data=data or {},
            nonce=nonce
        )
        
        tx.sign(private_key_pem)
        return tx

    def save_to_db(self, address, public_pem):
        """Save account to database"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO accounts (address, public_key_pem)
                VALUES (?, ?)
            ''', (address, public_pem))
            conn.commit()