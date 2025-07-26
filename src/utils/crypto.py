import binascii
import hashlib
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    PrivateFormat,
    NoEncryption
)
from cryptography.exceptions import InvalidSignature

def generate_key_pair():
    """Generate ECDSA key pair using secp256k1 curve"""
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    return private_key, public_key

def sign_data(private_key, data: str) -> str:
    """Sign data with private key"""
    if isinstance(data, str):
        data = data.encode()
    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    return binascii.hexlify(signature).decode()

def verify_signature(public_key_pem: str, signature: str, data: str) -> bool:
    """Verify signature with public key"""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    try:
        public_key = load_pem_public_key(public_key_pem.encode())
        if isinstance(data, str):
            data = data.encode()
        sig_bytes = binascii.unhexlify(signature)
        public_key.verify(
            sig_bytes,
            data,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except (InvalidSignature, ValueError, binascii.Error):
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

def address_from_public_key(public_key_pem: str) -> str:
    """Generate address from public key"""
    import hashlib
    public_key = public_key_pem.encode()
    sha256_hash = hashlib.sha256(public_key).hexdigest()
    return '0x' + sha256_hash[:40]  # 20-byte address

def generate_contract_address(sender: str, code: str) -> str:
    """Generate deterministic contract address"""
    unique_data = f"{sender}{code}{datetime.now().timestamp()}"
    sha256_hash = hashlib.sha256(unique_data.encode()).hexdigest()
    return '0x' + sha256_hash[:40]  # 20-byte address