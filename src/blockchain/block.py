import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import List
from cryptography.fernet import Fernet
from src.utils.logger import logger

@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List['Transaction']
    previous_hash: str
    nonce: int = 0
    difficulty: int = 4
    hash: str = field(init=False)
    transactions_hash: str = field(init=False)

    def __post_init__(self):
        self.timestamp = self.timestamp or time.time()
        self.transactions_hash = self.calculate_transactions_hash()
        self.hash = self.calculate_hash()

    def calculate_transactions_hash(self) -> str:
        """محاسبه هش ترکیبی تمام تراکنش‌های بلاک"""
        if not self.transactions:
            return hashlib.sha256(b'').hexdigest()
        tx_hashes = [tx.tx_hash for tx in self.transactions]
        return hashlib.sha256(''.join(tx_hashes).encode()).hexdigest()

    def calculate_hash(self) -> str:
        """محاسبه هش بلاک با استفاده از تمام فیلدهای مهم"""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions_hash': self.transactions_hash,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
        return hashlib.sha256(
            json.dumps(block_data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def to_dict(self) -> dict:
        """تبدیل بلاک به دیکشنری برای ذخیره در دیتابیس"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash,
            'difficulty': self.difficulty
        }

    def __repr__(self) -> str:
        return (f"<Block index={self.index}, hash={self.hash[:10]}..., "
                f"txs={len(self.transactions)}, nonce={self.nonce}>")