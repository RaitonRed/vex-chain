from dataclasses import dataclass
from src.blockchain.transaction import Transaction

@dataclass
class VexTransaction:
    vex_amount: float = 0
    transaction_type: str = "VEX_TRANSFER"

    def __post_init__(self):
        super().__post_init__()
        self.amount = self.vex_amount
    
    def to_dict(self):
        base_dict = super().to_dict()
        return {
            **base_dict,
            "vex_amount": self.vex_amount,
            "transaction_type": self.transaction_type
        }