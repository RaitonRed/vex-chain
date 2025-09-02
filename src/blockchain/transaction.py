# src/blockchain/transaction.py
import json
import time
from dataclasses import dataclass, field
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.db.state_db import StateDB
from src.utils.crypto import sign_data
from src.utils import logger

@dataclass
class Transaction:
    """Base transaction class"""
    # Required fields (no defaults)
    sender: str
    recipient: str
    amount: float
    
    # Fields with defaults come after
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: str = field(default="")
    tx_hash: Optional[str] = field(default=None)
    contract_type: str = field(default="NORMAL")

    # Add Gas fields
    gas_limit: int = 1000000
    gas_price: float = 0.0001

    fee: float = field(default=0.01)

    nonce: int = 0

    chain_id: int = field(default=1)

    def __post_init__(self):
        # حالت خاص برای تراکنش‌های سیستمی
        if self.sender == "0x0000000000000000000000000000000000000000":
            self.nonce = 0
        elif self.nonce is None:
            try:
                self.nonce = StateDB().get_nonce(self.sender) + 1
            except:
                self.nonce = 0
        
        # محاسبه هش باید بعد از تنظیم تمام فیلدها انجام شود
        self.tx_hash = self.calculate_hash()
        
        # بررسی تطابق هش
        if hasattr(self, 'tx_hash') and self.tx_hash:
            calculated_hash = self.calculate_hash()
            if self.tx_hash != calculated_hash:
                logger.error(f"Transaction hash mismatch: {self.tx_hash} != {calculated_hash}")
                self.tx_hash = calculated_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary"""
        return {
            "tx_hash": self.tx_hash,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "contract_type": self.contract_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create transaction from dictionary"""
        return cls(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            data=data.get('data', {}),
            timestamp=data['timestamp'],
            signature=data.get('signature', ''),
            tx_hash=data.get('tx_hash'),
            contract_type=data.get('contract_type', 'NORMAL')
        )

    def calculate_hash(self) -> str:
        """Calculate transaction hash"""
        import hashlib
        hash_data = (
            f"{self.sender}{self.recipient}{self.amount}"
            f"{self.nonce}{self.timestamp}{json.dumps(self.data, sort_keys=True)}"
        )

        return hashlib.blake2s(hash_data.encode(), digest_size=32).hexdigest()

    def sign(self, private_key) -> None:
        """Improved signing method"""
        from cryptography.hazmat.primitives import serialization
        
        if isinstance(private_key, str):
            private_key = serialization.load_pem_private_key(
                private_key.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        
        # اطمینان از محاسبه هش قبل از امضا
        if not hasattr(self, 'tx_hash') or not self.tx_hash:
            self.tx_hash = self.calculate_hash()
        
        signature = private_key.sign(
            self.tx_hash.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        self.signature = signature.hex()  # ذخیره به صورت hex string

    def is_valid(self) -> bool:
        """Enhanced validation with proper signature verification"""
        if not all([self.sender, self.recipient, self.tx_hash]):
            return False
            
        if self.amount < 0:
            return False
            
        if self.tx_hash != self.calculate_hash():
            return False
            
        # دریافت کلید عمومی از دیتابیس
        public_key_pem = ValidatorRegistry.get_public_key_pem(self.sender)
        if not public_key_pem:
            return False
        
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            public_key = load_pem_public_key(public_key_pem.encode())
            
            # تبدیل امضا از فرمت hex به bytes
            signature_bytes = bytes.fromhex(self.signature)
            
            # بررسی امضا
            public_key.verify(
                signature_bytes,
                self.tx_hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False