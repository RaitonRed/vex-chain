from typing import List, Dict
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
import time

class Mempool:
    """مدیریت تراکنش‌های منتظر تایید"""
    
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}
        self.max_size = 1000

    def add_transaction(self, tx: Transaction) -> bool:
        """اضافه کردن تراکنش جدید به mempool"""
        if tx.tx_hash in self.transactions:
            logger.warning(f"Transaction {tx.tx_hash[:8]} already in mempool")
            return False
            
        if len(self.transactions) >= self.max_size:
            logger.warning("Mempool is full, transaction rejected")
            return False
            
        self.transactions[tx.tx_hash] = tx
        logger.info(f"Transaction added to mempool: {tx.tx_hash[:8]}")
        return True

    def get_transactions(self, max_count: int = 10) -> List[Transaction]:
        """دریافت تراکنش‌ها برای ساخت بلاک جدید"""
        # اولویت‌بندی بر اساس کارمزد یا timestamp
        sorted_txs = sorted(
            self.transactions.values(),
            key=lambda tx: tx.timestamp
        )
        return sorted_txs[:max_count]

    def remove_transactions(self, tx_hashes: List[str]):
        """حذف تراکنش‌های تایید شده از mempool"""
        for tx_hash in tx_hashes:
            if tx_hash in self.transactions:
                del self.transactions[tx_hash]
        logger.info(f"Removed {len(tx_hashes)} transactions from mempool")

    def clear_expired(self, expiry_seconds: int = 3600):
        """پاک‌سازی تراکنش‌های منقضی شده"""
        now = time.time()
        expired = [
            tx_hash for tx_hash, tx in self.transactions.items()
            if now - tx.timestamp > expiry_seconds
        ]
        for tx_hash in expired:
            del self.transactions[tx_hash]
        logger.info(f"Cleared {len(expired)} expired transactions")