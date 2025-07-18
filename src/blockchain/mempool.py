from typing import List, Dict
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
from src.utils.database import db_connection
import json
import time

class Mempool:
    """مدیریت تراکنش‌های منتظر تایید"""
    
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}
        self.max_size = 1000
        self._load_from_db()  # بارگذاری تراکنش‌های موجود در دیتابیس هنگام راه‌اندازی

    def _load_from_db(self):
        """بارگذاری تراکنش‌های موجود در دیتابیس به حافظه"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM mempool')
            for row in cursor.fetchall():
                tx = Transaction(
                    sender=row[2],
                    recipient=row[3],
                    amount=row[4],
                    data=json.loads(row[5]),
                    timestamp=row[6],
                    signature=row[7]
                )
                tx.tx_hash = row[1]  # تنظیم هش تراکنش
                self.transactions[tx.tx_hash] = tx

    def add_transaction(self, tx: Transaction) -> bool:
        """اضافه کردن تراکنش جدید به mempool"""
        try:
            # اعتبارسنجی اولیه تراکنش
            if not tx.tx_hash or tx.tx_hash != tx.calculate_hash():
                logger.error("Invalid transaction hash")
                return False
            
            if tx.tx_hash in self.transactions:
                logger.warning(f"Transaction {tx.tx_hash[:8]} already in mempool")
                return False
            
            if len(self.transactions) >= self.max_size:
                logger.warning("Mempool is full, transaction rejected")
                return False
            
            # ذخیره در حافظه
            self.transactions[tx.tx_hash] = tx
            
            # ذخیره در دیتابیس
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT OR IGNORE INTO mempool (
                    tx_hash, sender, recipient, 
                    amount, data, timestamp, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx.tx_hash,
                    tx.sender,
                    tx.recipient,
                    tx.amount,
                    json.dumps(tx.data),
                    tx.timestamp,
                    tx.signature
                ))
                conn.commit()
            
            logger.info(f"Transaction added to mempool: {tx.tx_hash[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to add transaction: {e}")
            return False

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
        with db_connection() as conn:
            cursor = conn.cursor()
            for tx_hash in tx_hashes:
                # حذف از حافظه
                if tx_hash in self.transactions:
                    del self.transactions[tx_hash]
                
                # حذف از دیتابیس
                cursor.execute('DELETE FROM mempool WHERE tx_hash = ?', (tx_hash,))
            conn.commit()
        
        logger.info(f"Removed {len(tx_hashes)} transactions from mempool")

    def clear_expired(self, expiry_seconds: int = 3600):
        """پاک‌سازی تراکنش‌های منقضی شده"""
        now = time.time()
        expired = [
            tx_hash for tx_hash, tx in self.transactions.items()
            if now - tx.timestamp > expiry_seconds
        ]
        
        with db_connection() as conn:
            cursor = conn.cursor()
            for tx_hash in expired:
                # حذف از حافظه
                del self.transactions[tx_hash]
                
                # حذف از دیتابیس
                cursor.execute('DELETE FROM mempool WHERE tx_hash = ?', (tx_hash,))
            conn.commit()
        
        logger.info(f"Cleared {len(expired)} expired transactions")