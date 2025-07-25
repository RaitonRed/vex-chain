import json
import hashlib
import binascii
from dataclasses import dataclass, field
from typing import List, Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
from src.utils.logger import logger
from src.blockchain.validator_registry import ValidatorRegistry

@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List['Transaction']
    previous_hash: str
    validator: str = ""  # Address of the validator
    signature: str = ""  # Digital signature of the block
    stake_amount: float = 0  # Stake amount used for validation
    difficulty: int = 4 
    nonce: int = 0
    hash: str = field(init=False)  # Will be set by calculate_hash
    transactions_hash: str = field(init=False)  # Hash of transactions

    def __post_init__(self):
        """Initialize block and calculate hashes"""
        self.transactions_hash = self.calculate_transactions_hash()
        if not hasattr(self, 'hash') or not self.hash:
            self.hash = self.calculate_hash()

    def sign_block(self, private_key: ec.EllipticCurvePrivateKey, stake: float):
        """Sign the block with the validator's private key"""
        self.validator = ValidatorRegistry.get_validator_address(private_key)
        self.stake_amount = stake
        signature = private_key.sign(
            self.hash.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        self.signature = binascii.hexlify(signature).decode()

    def verify_signature(self) -> bool:
        """Verify the block signature with the validator's public key"""
        if not self.signature or not self.validator:
            logger.error("Missing signature or validator")
            return False

        try:
            public_key_pem = ValidatorRegistry.get_public_key_pem(self.validator)
            if not public_key_pem:
                logger.error(f"No public key found for validator: {self.validator}")
                return False
                
            public_key = load_pem_public_key(public_key_pem.encode())
            signature_bytes = binascii.unhexlify(self.signature)
            
            public_key.verify(
                signature_bytes,
                self.hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except Exception as e:
            logger.error(f"Block signature verification failed: {e}")
            return False
        
    def calculate_transactions_hash(self) -> str:
        """Calculate hash of all transactions in the block"""
        if not self.transactions:
            return hashlib.sha256(b'').hexdigest()
        
        tx_hashes = [tx.tx_hash for tx in self.transactions]
        return hashlib.sha256(''.join(tx_hashes).encode()).hexdigest()

    def calculate_hash(self) -> str:
        """Calculate the block hash including PoS fields"""
        block_data = {
            'index': self.index,
            'timestamp': int(self.timestamp),
            'transactions_hash': self.transactions_hash,
            'previous_hash': self.previous_hash,
            'validator': self.validator,
            'stake_amount': self.stake_amount
        }
        return hashlib.sha256(
            json.dumps(block_data, sort_keys=True).encode()
        ).hexdigest()

    def is_valid(self, previous_block: 'Block') -> bool:
        """Validate block structure and content"""
        if self.index != previous_block.index + 1:
            logger.error(f"Block index mismatch: {self.index} vs {previous_block.index + 1}")
            return False
            
        if self.previous_hash != previous_block.hash:
            logger.error(f"Previous hash mismatch: {self.previous_hash} vs {previous_block.hash}")
            return False
            
        if self.hash != self.calculate_hash():
            logger.error(f"Block hash invalid: {self.hash} vs {self.calculate_hash()}")
            return False
            
        if not self.verify_signature():
            logger.error(f"Invalid block signature for block {self.index}")
            return False
            
        # اعتبارسنجی تراکنش‌ها
        for tx in self.transactions:
            if not tx.is_valid():
                logger.error(f"Invalid transaction in block: {tx.tx_hash}")
                return False
                
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for network transmission"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'validator': self.validator,
            'stake_amount': self.stake_amount,
            'signature': self.signature
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create Block from dictionary received from network"""
        from src.blockchain.transaction import Transaction
        transactions = [Transaction.from_dict(tx) for tx in data['transactions']]
        
        block = cls(
            index=data['index'],
            timestamp=data['timestamp'],
            transactions=transactions,
            previous_hash=data['previous_hash'],
            validator=data['validator'],
            stake_amount=data['stake_amount'],
            signature=data['signature']
        )
        
        # Set hash from network data
        block.hash = data['hash']
        block.transactions_hash = block.calculate_transactions_hash()
        
        return block

    def __repr__(self) -> str:
        return (f"<Block index={self.index}, hash={self.hash[:10]}..., "
                f"txs={len(self.transactions)}, validator={self.validator[:6]}>")