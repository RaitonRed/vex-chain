import json
from dataclasses import dataclass, field
from typing import Dict, Any
from src.blockchain.transaction import Transaction

@dataclass
class ContractTransaction(Transaction):
    contract_address: str = ""
    method: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    contract_type: str = "CONTRACT"
    
    # Then fields with defaults
    contract_type: str = field(default="CONTRACT")
    
    def __post_init__(self):
        # Call parent's __post_init__ if it exists
        if hasattr(super(), '__post_init__'):
            super().__post_init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for serialization"""
        base_dict = super().to_dict()
        return {
            **base_dict,
            "contract_address": self.contract_address,
            "method": self.method,
            "args": self.args,
            "contract_type": self.contract_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContractTransaction':
        """Create transaction from dictionary"""
        return cls(
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            data=data.get('data', {}),
            timestamp=data['timestamp'],
            signature=data.get('signature', ''),
            tx_hash=data.get('tx_hash'),
            contract_address=data['contract_address'],
            method=data['method'],
            args=data['args']
        )

    def calculate_hash(self) -> str:
        """Calculate transaction hash including contract-specific fields"""
        hash_data = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
            "contract_address": self.contract_address,
            "method": self.method,
            "args": self.args,
            "contract_type": self.contract_type
        }
        return super()._calculate_hash(hash_data)