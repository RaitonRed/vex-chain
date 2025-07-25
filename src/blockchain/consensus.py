# consensus.py
import random
from typing import List, Dict
from src.utils.logger import logger
from src.blockchain.validator_registry import ValidatorRegistry

class Consensus:
    """پیاده‌سازی الگوریتم اجماع Proof of Stake"""
    
    @staticmethod
    def select_validator(validators: Dict[str, float]) -> str:
        """انتخاب تصادفی ولیدیتور با وزن سهام"""
        total_stake = sum(validators.values())
        selection_point = random.uniform(0, total_stake)
        current_sum = 0
        
        for address, stake in validators.items():
            current_sum += stake
            if current_sum >= selection_point:
                return address
        return list(validators.keys())[0]

    @staticmethod
    def validate_block(block: 'Block', previous_block: 'Block') -> bool:
        """اعتبارسنجی کامل یک بلاک در PoS (با استفاده از متد is_valid خود بلاک)"""
        return block.is_valid(previous_block)

    @staticmethod
    def is_chain_valid(chain: List['Block']) -> bool:
        """اعتبارسنجی کامل یک زنجیره در PoS"""
        if not chain:
            return False
            
        # بررسی بلاک جنسیس
        genesis = chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            logger.error("Invalid genesis block")
            return False
            
        # بررسی تک تک بلاک‌ها
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i-1]
            
            if not current.is_valid(previous):
                return False
                
        return True