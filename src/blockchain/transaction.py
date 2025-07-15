import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from src.utils.logger import logger

@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None
    tx_hash: str = field(default="", init=False)

    def __post_init__(self):
        self.tx_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """محاسبه هش تراکنش"""
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'data': self.data,
            'timestamp': self.timestamp
        }
        return hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode()
        ).hexdigest()

    def sign(self, private_key: str) -> None:
        """امضای تراکنش با کلید خصوصی"""
        cipher_suite = Fernet(private_key)
        self.signature = cipher_suite.encrypt(self.tx_hash.encode()).decode()

    def verify_signature(self, public_key: str) -> bool:
        """اعتبارسنجی امضای تراکنش"""
        if not self.signature:
            return False
            
        try:
            cipher_suite = Fernet(public_key)
            decrypted = cipher_suite.decrypt(self.signature.encode()).decode()
            return decrypted == self.tx_hash
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def to_dict(self) -> dict:
        """تبدیل تراکنش به دیکشنری"""
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'data': self.data,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'tx_hash': self.tx_hash
        }

    def __repr__(self) -> str:
        return (f"<Transaction {self.tx_hash[:8]}... "
                f"from {self.sender[:6]} to {self.recipient[:6]}>")