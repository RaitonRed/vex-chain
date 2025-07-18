from typing import List
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

class Consensus:
    """پیاده‌سازی الگوریتم اجماع Proof of Work"""
    
    @staticmethod
    def validate_block(block: Block, previous_block: Block) -> bool:
        """اعتبارسنجی کامل یک بلاک"""
        if block.hash != block.calculate_hash():
            logger.error(f"Invalid block hash for block {block.index}")
            return False
            
        if not block.hash.startswith('0' * block.difficulty):
            logger.error(f"PoW validation failed for block {block.index}")
            return False
            
        if block.previous_hash != previous_block.hash:
            logger.error(f"Previous hash mismatch in block {block.index}")
            return False
            
        if not all(tx.tx_hash == tx.calculate_hash() for tx in block.transactions):
            logger.error(f"Invalid transaction hash in block {block.index}")
            return False
            
        # تاخیر در بررسی امضا تا زمان نیاز
        return True

    @staticmethod
    def proof_of_work(block: Block) -> Block:
        """انجام اثبات کار برای یک بلاک"""
        logger.info(f"Mining block #{block.index} with difficulty {block.difficulty}...")
        
        while not block.hash.startswith('0' * block.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()
            
        logger.info(f"Block mined: {block.hash}")
        return block

    @staticmethod
    def cumulative_difficulty(chain: List[Block]) -> int:
        """محاسبه سختی تجمعی زنجیره"""
        return sum(2 ** block.difficulty for block in chain)

    @staticmethod
    def is_chain_valid(chain: List[Block]) -> bool:
        """اعتبارسنجی کامل یک زنجیره"""
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