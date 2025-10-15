import heapq
from typing import List
from src.blockchain.contracts.contract_repository import ContractRepository
from src.blockchain.db.state_db import StateDB
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
from src.utils.database import db_connection
from src.p2p.network import P2PNetwork
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

        # Load only if mempool table exists
        try:
            self._load_from_db()
        except sqlite3.OperationalError:
            logger.warning("Mempool table not found, starting with empty mempool")

    def _load_from_db(self):
        """load transactions from database"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mempool'")
            if not cursor.fetchone():
                return

            cursor.execute('SELECT * FROM mempool')

    def add_transaction(self, transaction):
        """Add a transaction to the mempool with better error handling"""
        try:
            # Validate transaction
            if not transaction.is_valid():
                logger.error("Invalid transaction")
                return False

            # Check if transaction already exists
            if transaction.tx_hash in self.transactions:
                logger.warning("Transaction already in mempool")
                return False

            # Add to mempool
            self.transactions[transaction.tx_hash] = transaction
            logger.info(f"Transaction added to mempool: {transaction.tx_hash[:8]}...")

            # Broadcast to network
            if self.p2p_network:
                try:
                    self.p2p_network.broadcast_transaction(transaction)
                except Exception as e:
                    logger.error(f"Failed to broadcast transaction: {e}")

            return True
        except Exception as e:
            logger.error(f"Error adding transaction to mempool: {e}")
            return False

    def get_transactions(self, max_count: int = 10) -> List[Transaction]:
        """fetch transactions for creating new block"""
        sorted_txs = sorted(
            self.transactions.values(),
            key=lambda tx: tx.timestamp
        )
        return sorted_txs[:max_count]

    def remove_transactions(self, tx_hashes: List[str]):
        """remove validated transactions"""
        with db_connection() as conn:
            cursor = conn.cursor()
            for tx_hash in tx_hashes:
                if tx_hash in self.transactions:
                    del self.transactions[tx_hash]

                cursor.execute('DELETE FROM mempool WHERE tx_hash = ?', (tx_hash,))
            conn.commit()

        logger.info(f"Removed {len(tx_hashes)} transactions from mempool")

    def clear_expired(self, expiry_seconds: int = 3600):
        """clear expired transactions"""
        now = time.time()
        while self.expiration and self.expiration_queue[0][0] < now:
            _, tx = heapq.heappop(self.expiration_queue)
            if tx.tx_hash in self.transactions:
                del self.transactions[tx.tx_hash]
                logger.info(f"Removed expired transaction: {tx.tx_hash[:8]}")


    def _validate_transaction(self, tx):

        last_nonce = StateDB().get_nonce(tx.sender)

        # Check nonce
        if tx.nonce <= last_nonce:
            logger.error(f"Invalid nonce for {tx.sender}: {tx.nonce} <= {last_nonce}")
            return False

        if not tx.is_valid():
            logger.error(f"Invalid signature for tx: {tx.tx_hash[:8]}")
            return False

        state_db = StateDB()
        sender_balance = state_db.get_balance(tx.sender)
        required_amount = tx.amount + getattr(tx, 'fee', 0)

        if sender_balance < required_amount:
            logger.error(f"Insufficient balance for {tx.sender}")
            return False

        if tx.tx_hash in self.transactions:
            logger.warning(f"Duplicate transaction: {tx.tx_hash[:8]}")
            return False

        if hasattr(tx, 'contract_address') and tx.contract_address:
            if not ContractRepository.contract_exists(tx.contract_address):
                logger.error(f"Invalid contract: {tx.contract_address[:8]}")
                return False

        return True
