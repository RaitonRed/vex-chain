import sqlite3
import json
from typing import List, Optional
from src.utils.database import db_connection
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

class BlockRepository:
    """ذخیره و بازیابی بلاک‌ها از دیتابیس"""
    
    @staticmethod
    def save_block(block: Block) -> int:
        """ذخیره بلاک در دیتابیس و بازگرداندن ID"""
        with db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO blocks ("index", timestamp, previous_hash, nonce, hash, difficulty)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    block.index,
                    block.timestamp,
                    block.previous_hash,
                    block.nonce,
                    block.hash,  # اینجا hash پس از محاسبه ذخیره می‌شود
                    block.difficulty
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: blocks.index" in str(e):
                    logger.warning(f"Block {block.index} already exists")
                raise

    @staticmethod
    def get_block_by_index(index: int) -> Optional[Block]:
        """بازیابی بلاک بر اساس شماره ایندکس"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blocks WHERE "index" = ?', (index,))
            row = cursor.fetchone()
        
            if not row:
                return None
            
            transactions = TransactionRepository.get_transactions_by_block_id(row[0])


            # ایجاد بلاک با استفاده از هش ذخیره شده در دیتابیس
            block = Block(
                index=row[1],
                timestamp=row[2],
                transactions=transactions,
                previous_hash=row[3],
                nonce=row[4],
                difficulty=row[6]
            )
        
            # استفاده از هش ذخیره شده به جای محاسبه مجدد
            block.hash = row[5]
            block.validator = row[7] if len(row) > 7 else ""
        
            return block
    
    @staticmethod
    def get_blocks_paginated(page: int = 1, per_page: int = 10) -> List[Block]:
        """بازیابی بلاک‌ها به صورت صفحه‌بندی شده"""
        offset = (page - 1) * per_page
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM blocks 
            ORDER BY "index" DESC 
            LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            blocks = []
            for row in cursor.fetchall():
                transactions = TransactionRepository.get_transactions_by_block_id(row[0])
                blocks.append(Block(
                    index=row[1],
                    timestamp=row[2],
                    transactions=transactions,
                    previous_hash=row[3],
                    nonce=row[4],
                    hash=row[5],
                    difficulty=row[6]
                ))
            return blocks
    
    @staticmethod
    def get_block_count() -> int:
        """تعداد بلاک‌های ذخیره شده"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM blocks')
            return cursor.fetchone()[0]

class TransactionRepository:
    """ذخیره و بازیابی تراکنش‌ها از دیتابیس"""
    
    @staticmethod
    def save_transaction(transaction: Transaction, block_id: int) -> int:
        """ذخیره تراکنش در دیتابیس"""
        with db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO transactions (
                    block_id, tx_hash, sender, recipient, 
                    amount, data, timestamp, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    block_id,
                    transaction.tx_hash,
                    transaction.sender,
                    transaction.recipient,
                    transaction.amount,
                    json.dumps(transaction.data),
                    transaction.timestamp,
                    transaction.signature
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: transactions.tx_hash" in str(e):
                    logger.warning(f"Transaction {transaction.tx_hash} already exists")
                raise

    @staticmethod
    def save_transactions_bulk(transactions: List[Transaction], block_id: int) -> None:
        """ذخیره دسته‌ای تراکنش‌ها"""
        with db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany('''
                INSERT OR IGNORE INTO transactions (
                    block_id, tx_hash, sender, recipient, 
                    amount, data, timestamp, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    (
                        block_id,
                        tx.tx_hash,
                        tx.sender,
                        tx.recipient,
                        tx.amount,
                        json.dumps(tx.data),
                        tx.timestamp,
                        tx.signature
                    ) for tx in transactions
                ])
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise

    @staticmethod
    def get_transactions_by_block_id(block_id: int) -> List[Transaction]:
        """بازیابی تمام تراکنش‌های یک بلاک"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transactions WHERE block_id = ?', (block_id,))
            
            transactions = []
            for row in cursor.fetchall():
                tx = Transaction(
                    sender=row[3],
                    recipient=row[4],
                    amount=row[5],
                    data=json.loads(row[6]),
                    timestamp=row[7],
                    signature=row[8]
                )
                # بررسی تطابق هش
                if tx.tx_hash != row[2]:
                    logger.warning(f"Transaction hash mismatch for tx {row[0]}")
                    continue
                transactions.append(tx)
            return transactions

    @staticmethod
    def get_transaction_by_hash(tx_hash: str) -> Optional[Transaction]:
        """بازیابی تراکنش بر اساس هش"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transactions WHERE tx_hash = ?', (tx_hash,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return Transaction(
                sender=row[3],
                recipient=row[4],
                amount=row[5],
                data=json.loads(row[6]),
                timestamp=row[7],
                signature=row[8],
                tx_hash=row[2]
            )