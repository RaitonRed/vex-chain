import binascii
import hashlib
import time
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.backends import default_backend
from src.utils.logger import logger

def generate_ecc_key_pair():
    """Generate ECDSA key pair using secp256k1 curve"""
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    return private_key, public_key

def sign_message(private_key, message: str) -> str:
    """Sign a message with private key"""
    if isinstance(message, str):
        message = message.encode('utf-8')
    signature = private_key.sign(
        message,
        ec.ECDSA(hashes.SHA256())
    )
    return binascii.hexlify(signature).decode('utf-8')

def generate_key_pair():
    """Generate ECDSA key pair using ed25519 curve"""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def sign_data(private_key, data: str) -> str:
    """Sign data with private key"""
    if isinstance(data, str):
        data = data.encode('utf-8')

    return private_key.sign(data)

def verify_signature(public_key: str, signature: str, message: str) -> bool:
    """Verify signature with public key"""
    try:
        if isinstance(public_key, str):
            public_key = public_key.encode('utf-8')
        public_key.verify(signature, message)
        return True
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False

def private_key_to_pem(private_key) -> str:
    """Convert private key to PEM format"""
    return private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    ).decode()

def public_key_to_pem(public_key) -> str:
    """Convert public key to PEM format"""
    return public_key.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo
    ).decode()

def address_from_public_key(public_key_pem):
    """Generate address from public key PEM string"""
    if isinstance(public_key_pem, str):
        public_key_bytes = public_key_pem.encode('utf-8')
    else:
        public_key_bytes = public_key_pem
        
    # Hash the public key
    public_key_hash = hashlib.sha256(public_key_bytes).hexdigest()
    # Take first 40 characters (20 bytes) and prepend 0x
    return '0x' + public_key_hash[:40]

def generate_contract_address(sender: str, code: str) -> str:
    """Generate deterministic contract address"""
    unique_data = f"{sender}{code}{datetime.now().timestamp()}"
    sha256_hash = hashlib.sha256(unique_data.encode()).hexdigest()
    return '0x' + sha256_hash[:40]  # 20-byte address

def generate_secure_nonce(sender: str) -> int:
    """Generate a secure nonce for transaction"""
    timestamp = int(time.time() * 1000)  # Current time in milliseconds
    hash_base = f"{sender}{timestamp}".encode()

    return int.from_bytes(
        hashlib.shake_128(hash_base).digest(4),  # Use first 8 bytes for nonce
        byteorder='big'
    )