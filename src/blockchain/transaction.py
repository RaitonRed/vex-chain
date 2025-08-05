# src/blockchain/transaction.py
import json
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.blockchain.db.state_db import StateDB
from src.utils.crypto import sign_data, verify_signature
from src.utils.database import db_connection
from src.utils import logger
from src.utils.crypto import generate_secure_nonce

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

    fee: int = 0.01

    nonce: int = 0

    chain_id: int = field(default=1)

    def __post_init__(self):
        if self.tx_hash is None:
            self.tx_hash = self.calculate_hash()

        if self.signature is None:
            self.sign()

            # اعتبارسنجی هش
        calculated_hash = self.calculate_hash()
        if self.tx_hash != calculated_hash:
            logger.warning(f"Transaction hash mismatch! Stored: {self.tx_hash}, Calculated: {calculated_hash}")
            self.tx_hash = calculated_hash  # اصلاح هش نادرست

        # Set nonce automatically if not provided
        if self.nonce is None:
            try:
                # Special case for system accounts
                if self.sender == "0x0000000000000000000000000000000000000000":
                    self.nonce = 0
                else:
                    self.nonce = generate_secure_nonce(self.sender)
            except Exception as e:
                logger.error(f"Error getting nonce: {e}")
                self.nonce = 0

        # Set nonce automatically if not provided
        if self.nonce is None:
            # Special case for genesis transaction
            if self.sender == "0":
                self.nonce = 0
            else:
                try:
                    self.nonce = StateDB().get_nonce(self.sender) + 1
                except:
                    # If account doesn't exist, start at 0
                    self.nonce = 0

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
        return hashlib.blake2s(
            f"{self.sender}{self.recipient}{self.amount}{self.chain_id}{self.nonce}{self.timestamp}{self.tx_hash}{self.gas_limit}{self.gas_price}{self.fee}".encode(),
            digest_size=32
        ).hexdigest()

    def sign(self, private_key) -> None:
        """Improved signing method"""
        from cryptography.hazmat.primitives import serialization
        
        if isinstance(private_key, str):
            private_key = serialization.load_pem_private_key(
                private_key.encode('utf-8'),
                password=None
            )
        
        self.signature = sign_data(private_key, self.tx_hash)

    def is_valid(self) -> bool:
        """Enhanced validation"""
        if not all([self.sender, self.recipient, self.tx_hash]):
            return False
            
        if self.amount < 0:
            return False
            
        if self.tx_hash != self.calculate_hash():
            return False
            
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT public_key_pem FROM accounts WHERE address = ?', (self.sender,))
            row = cursor.fetchone()
            
        if not row:
            return False
            
        return verify_signature(row[0], self.signature, self.tx_hash)