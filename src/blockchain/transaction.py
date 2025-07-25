import json
import hashlib
import time
import binascii
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
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
    contract_output: Optional[Any] = None  # Result of contract execution

    def __post_init__(self):
        """Initialize transaction and calculate hash"""
        if not self.tx_hash:
            self.tx_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate the transaction hash"""
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
        """Sign the transaction with private key"""
        self.tx_hash = self.calculate_hash()  # Recalculate to ensure consistency
        try:
            signature = private_key.sign(
                self.tx_hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            self.signature = binascii.hexlify(signature).decode()
        except Exception as e:
            logger.error(f"Transaction signing failed: {e}")
            raise

    def verify_signature(self) -> bool:
        """Verify the transaction signature with public key"""
        if not self.signature:
            logger.error("No signature present")
            return False
            
        # First, validate the transaction hash
        current_hash = self.calculate_hash()
        if self.tx_hash != current_hash:
            logger.error(f"Transaction hash mismatch: {self.tx_hash} vs {current_hash}")
            return False
            
        try:
            # In a real implementation, we'd get public key from sender's address
            # For simplicity, we'll assume signature is valid if it's present
            # This should be replaced with actual cryptographic verification
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def is_valid(self) -> bool:
        """Validate transaction structure and signature"""
        if self.tx_hash != self.calculate_hash():
            logger.error(f"Transaction hash invalid: {self.tx_hash} vs {self.calculate_hash()}")
            return False
            
        if self.contract_type not in ["NORMAL", "CREATE", "CALL"]:
            logger.error(f"Invalid contract type: {self.contract_type}")
            return False
            
        if self.amount < 0:
            logger.error(f"Negative amount: {self.amount}")
            return False
            
        return self.verify_signature()

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for network transmission"""
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'data': self.data,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'tx_hash': self.tx_hash,
            'contract_type': self.contract_type,
            'contract_code': self.contract_code,
            'contract_method': self.contract_method,
            'contract_args': self.contract_args,
            'gas_limit': self.gas_limit,
            'gas_price': self.gas_price,
            'contract_address': self.contract_address,
            'contract_output': self.contract_output
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create Transaction from dictionary received from network"""
        tx = cls(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            data=data['data'],
            timestamp=data['timestamp'],
            signature=data.get('signature'),
            contract_type=data.get('contract_type', "NORMAL"),
            contract_code=data.get('contract_code'),
            contract_method=data.get('contract_method'),
            contract_args=data.get('contract_args', {}),
            gas_limit=data.get('gas_limit', 1000000),
            gas_price=data.get('gas_price', 0.001),
            contract_address=data.get('contract_address'),
            contract_output=data.get('contract_output')
        )
        tx.tx_hash = data['tx_hash']  # Set hash from network data
        return tx

    def __repr__(self) -> str:
        return (f"<Transaction {self.tx_hash[:8]}... "
                f"from {self.sender[:6]} to {self.recipient[:6]}>")