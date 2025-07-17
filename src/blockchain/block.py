import json
import hashlib
import time
import binascii
from dataclasses import dataclass, field
from typing import List
from src.blockchain.consensus import ValidatorRegistery
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import deocde_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature
from src.blockchain.consensus import ValidatorRegistry
from src.utils.logger import logger

@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List['Transaction']
    previous_hash: str
    nonce: int = 0
    difficulty: int = 4
    hash: str = field(init=False)
    transactions_hash: str = field(init=False)
    validator: str = ""
    signature: str = ""
    
    def __post_init__(self):
        self.timestamp = self.timestamp or time.time()
        self.transactions_hash = self.calculate_transactions_hash()
        self.hash = self.calculate_hash()

    def sign_block(self, private_key: ec.EllipticCurvePrivateKey):
        signature = private_key.sign(
                self.hash.encode(),
                ec.ECDSA(hashes.SHA256())
        )
        self.signature = binascii.hexlify(signature).decode()

    def verify_signature(self) -> bool:
        if not self.signature or not self.validator:
            return False

        try:
            public_key = self.get_validator_public_key()

            signature_bytes = binascii.unhexlify(self.signature)

            public_key.verify(
                signature_bytes,
                self.hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )

            return True
        except (InvalidSignature, ValueError, TypeError) as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def calculate_transactions_hash(self) -> str:
        if not self.transactions:
            return hashlib.sha256(b'').hexdigest()
        tx_hashes = [tx.tx_hash for tx in self.transactions]
        return hashlib.sha256(''.join(tx_hashes).encode()).hexdigest()

    def calculate_hash(self) -> str:
        """محاسبه هش بلاک با استفاده از تمام فیلدهای مهم"""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions_hash': self.transactions_hash,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
        return hashlib.sha256(
            json.dumps(block_data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def to_dict(self) -> dict:
        """تبدیل بلاک به دیکشنری برای ذخیره در دیتابیس"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash,
            'difficulty': self.difficulty
        }
    
    def __repr__(self) -> str:
        return (f"<Block index={self.index}, hash={self.hash[:10]}..., "
                f"txs={len(self.transactions)}, nonce={self.nonce}>")
    
    def get_validator_public_key(self) -> ec.EllipticCurvePublicKey:
        return ValidatorRegistry.get_public_key(self.validator)
