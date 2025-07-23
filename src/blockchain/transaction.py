import json
import hashlib
import time
import binascii
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
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

    # Smart Contracts
    contract_type: str = "NORMAL"  # NORMAL, CREATE, CALL
    contract_code: Optional[str] = None
    contract_method: Optional[str] = None
    contract_args: Dict[str, Any] = field(default_factory=dict)
    gas_limit: int = 1000000
    gas_price: float = 0.001
    contract_address: Optional[str] = None


    def __post_init__(self):
        self.tx_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """محاسبه هش تراکنش"""
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'data': self.data,
            'timestamp': self.timestamp,
            'contract_type': self.contract_type,
            'contract_code': self.contract_code,
            'contract_method': self.contract_method,
            'contract_args': self.contract_args,
            'gas_limit': self.gas_limit,
            'gas_price': self.gas_price,
            'contract_address': self.contract_address
        }
        return hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode()
        ).hexdigest()

    def sign(self, private_key: ec.EllipticCurvePrivateKey) -> None:
        """امضای تراکنش با کلید خصوصی ECDSA"""
        try:
            signature = private_key.sign(
                self.tx_hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            self.signature = binascii.hexlify(signature).decode()
        except Exception as e:
            logger.error(f"Transaction signing failed: {e}")
            raise

    def verify_signature(self, public_key: ec.EllipticCurvePublicKey) -> bool:
        """اعتبارسنجی امضای تراکنش با کلید عمومی"""
        if not self.signature:
            return False
            
        try:
            signature_bytes = binascii.unhexlify(self.signature)
            public_key.verify(
                signature_bytes,
                self.tx_hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except (InvalidSignature, ValueError, TypeError) as e:
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