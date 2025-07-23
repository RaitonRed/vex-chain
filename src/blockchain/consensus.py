import random
from typing import List, Dict
from src.blockchain.block import Block
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
    def validate_block(block: Block, previous_block: Block) -> bool:
        """اعتبارسنجی کامل یک بلاک در PoS"""
        if not block.verify_signature():
            logger.error(f"Invalid block signature for block {block.index}")
            return False
            
        if block.hash != block.calculate_hash():
            logger.error(f"Invalid block hash for block {block.index}")
            return False
            
        if block.previous_hash != previous_block.hash:
            logger.error(f"Previous hash mismatch in block {block.index}")
            return False
            
        if not all(tx.tx_hash == tx.calculate_hash() for tx in block.transactions):
            logger.error(f"Invalid transaction hash in block {block.index}")
            return False
            
        return True

    @staticmethod
    def is_chain_valid(chain: List[Block]) -> bool:
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
            
            if not Consensus.validate_block(current, previous):
                return False
                
        return True