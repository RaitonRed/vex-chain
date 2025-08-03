import heapq
from typing import List, Dict
from src.blockchain.contracts.contract_repository import ContractRepository
from src.blockchain.db.state_db import StateDB
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
from src.utils.database import db_connection
from src.p2p.network import P2PNetwork
import json
import time
import sqlite3

EXPIRY_SECONDS = 3600  # 1 hour

class Mempool:
    def __init__(self):
        self.transactions = {}
        self.priority_queue = []
        self.expiration_queue = []
        self.max_size = 1000
        self.p2p_network = P2PNetwork

        # بارگذاری فقط در صورتی که جدول mempool وجود دارد
        try:
            self._load_from_db()
        except sqlite3.OperationalError:
            logger.warning("Mempool table not found, starting with empty mempool")

    def _load_from_db(self):
        """بارگذاری تراکنش‌ها فقط اگر جدول وجود دارد"""
        with db_connection() as conn:
            cursor = conn.cursor()
            # بررسی وجود جدول mempool
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mempool'")
            if not cursor.fetchone():
                return
                
            cursor.execute('SELECT * FROM mempool')

    def add_transaction(self, tx: Transaction) -> bool:
        """اضافه کردن تراکنش جدید به mempool"""

        heapq.heappush(self.priority_queue, (-tx.fee, tx.timestamp, tx))
        heapq.heappush(self.expiration_queue, (tx.timestamp + EXPIRY_SECONDS, tx.tx_hash))

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
            
            if tx.tx_hash not in self.transactions:
                if hasattr(self, 'p2p_network'):
                    self.p2p_network.broadcast_transaction(tx)

            if not self._validate_transaction(tx):
                return False
            
            # ذخیره در حافظه
            self.transactions[tx.tx_hash] = tx
            
            # ذخیره در دیتابیس
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO mempool (
                        tx_hash, sender, recipient, amount, data, timestamp, signature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tx.tx_hash, tx.sender, tx.recipient, tx.amount, json.dumps(tx.data), tx.timestamp, tx.signature
                ))
                conn.commit()
                logger.info(f"Transaction {tx.tx_hash[:8]} added to mempool database")
                
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
        while self.expiration and self.expiration_queue[0][0] < now:
            _, tx = heapq.heappop(self.expiration_queue)
            if tx.tx_hash in self.transactions:
                del self.transactions[tx.tx_hash]
                logger.info(f"Removed expired transaction: {tx.tx_hash[:8]}")


    def _validate_transaction(self, tx):
        # 1. بررسی امضا
        if not tx.is_valid():
            logger.error(f"Invalid signature for tx: {tx.tx_hash[:8]}")
            return False
            
        # 2. بررسی موجودی
        state_db = StateDB()
        sender_balance = state_db.get_balance(tx.sender)
        required_amount = tx.amount + getattr(tx, 'fee', 0)
        
        if sender_balance < required_amount:
            logger.error(f"Insufficient balance for {tx.sender}")
            return False
            
        # 3. بررسی تکراری نبودن
        if tx.tx_hash in self.transactions:
            logger.warning(f"Duplicate transaction: {tx.tx_hash[:8]}")
            return False
            
        # 4. اعتبارسنجی قرارداد (اگر وجود دارد)
        if hasattr(tx, 'contract_address') and tx.contract_address:
            if not ContractRepository.contract_exists(tx.contract_address):
                logger.error(f"Invalid contract: {tx.contract_address[:8]}")
                return False
                
        return True