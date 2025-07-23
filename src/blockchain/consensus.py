from typing import List, Optional
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
import random
import time

class Consensus:
    """پیاده‌سازی الگوریتم اجماع"""
    
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
    def proof_of_work(block: Block, max_nonce: int = 2**32) -> Optional[Block]:
        """الگوریتم PoW با محدودیت و بهینه‌سازی"""
        logger.info(f"Mining block #{block.index} [difficulty: {block.difficulty}]")
        
        start_time = time.time()
        target = '0' * block.difficulty
        
        for nonce in range(max_nonce):
            block.nonce = nonce
            block.hash = block.calculate_hash()
            
            if block.hash.startswith(target):
                elapsed = time.time() - start_time
                logger.info(f"Block mined in {elapsed:.2f}s | Nonce: {nonce} | Hash: {block.hash[:16]}...")
                return block
            
            # بهینه‌سازی: افزایش nonce به صورت تصادفی برای جلوگیری از الگوهای قابل پیش‌بینی
            if nonce % 100000 == 0:
                block.nonce = random.randint(0, max_nonce)
        
        logger.warning(f"PoW failed after {max_nonce} attempts")
        return None

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