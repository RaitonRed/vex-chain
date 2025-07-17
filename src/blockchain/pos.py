import random
from src.blockchain.block import Block
from src.blockchain.t

class ProofOfStake:
    def __init__(self):
        self.validators = {}
        self.staking_contract = "0xStakingContract"
    
    def add_validator(self, address: str, stake: float):
        """ثبت ولیدیتور جدید با مقدار سهام"""
        self.validators[address] = stake
    
    def select_validator(self) -> str:
        """انتخاب تصادفی ولیدیتور با وزن سهام"""
        total_stake = sum(self.validators.values())
        selection_point = random.uniform(0, total_stake)
        current_sum = 0
        
        for address, stake in self.validators.items():
            current_sum += stake
            if current_sum >= selection_point:
                return address
        return list(self.validators.keys())[0]
    
    def validate_block(self, block: Block, validator: str) -> bool:
        """اعتبارسنجی بلاک توسط ولیدیتور"""
        return block.validator == validator and verify_signature(block.signature)