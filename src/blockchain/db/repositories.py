import sqlite3
import json
from typing import List, Optional
from src.utils.database import db_connection
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

class BlockRepository:
    @staticmethod
    def save_block(block: Block) -> int:
        with db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO blocks (
                    "index", timestamp, previous_hash,
                    hash, nonce, difficulty,
                    validator, stake_amount, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    block.index,
                    block.timestamp,
                    block.previous_hash,
                    block.hash,
                    block.nonce,
                    block.difficulty,
                    block.validator,
                    block.stake_amount,
                    block.signature
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError as e:
                # ... error handling ...
                print(f"Error while saving block: {e}")

    @staticmethod
    def get_block_by_index(index: int) -> Optional[Block]:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM blocks WHERE "index" = ?', (index,))
            row = cursor.fetchone()

            if not row:
                return None

            # Get column names to handle schema changes
            cursor.execute("PRAGMA table_info(blocks)")
            columns = [col[1] for col in cursor.fetchall()]

            # Map columns to values
            row_dict = dict(zip(columns, row))

            transactions = TransactionRepository.get_transactions_by_block_id(row_dict['id'])

            block = Block(
                index=row_dict['index'],
                timestamp=row_dict['timestamp'],
                transactions=transactions,
                previous_hash=row_dict['previous_hash'],
                nonce=row_dict['nonce'],
                difficulty=row_dict['difficulty'],
                validator=row_dict.get('validator', ''),
                stake_amount=row_dict.get('stake_amount', 0),
                signature=row_dict.get('signature', '')
            )
            block.hash = row_dict['hash']
            return block

    @staticmethod
    def get_blocks_paginated(page: int = 1, per_page: int = 10) -> List[Block]:
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
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM blocks')
            return cursor.fetchone()[0]

class TransactionRepository:

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
                if tx.tx_hash != row[2]:
                    logger.warning(f"Transaction hash mismatch for tx {row[0]}")
                    continue
                transactions.append(tx)
            return transactions

    @staticmethod
    def get_transaction_by_hash(tx_hash: str) -> Optional[Transaction]:
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
