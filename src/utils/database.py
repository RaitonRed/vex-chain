import sqlite3
import json
import os
import contextlib
from typing import List, Optional
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

DB_FILE = "data/blockchain.db"

@contextlib.contextmanager
def db_connection():
    """مدیریت اتصال به دیتابیس با context manager"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        
def init_db():
    """مقداردهی اولیه دیتابیس و ایجاد جداول"""
    os.makedirs("data", exist_ok=True)
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # ایجاد جداول و ایندکس‌ها
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "index" INTEGER NOT NULL UNIQUE,
            timestamp REAL NOT NULL,
            previous_hash TEXT NOT NULL,
            nonce INTEGER NOT NULL,
            hash TEXT NOT NULL UNIQUE,
            difficulty INTEGER NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL,
            tx_hash TEXT NOT NULL UNIQUE,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            amount REAL NOT NULL,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            signature TEXT,
            FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS nodes (
            address TEXT PRIMARY KEY,
            last_seen REAL DEFAULT (strftime('%s', 'now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks ("index");
        CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks (hash);
        CREATE INDEX IF NOT EXISTS idx_tx_hash ON transactions (tx_hash);
        CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions (sender);
        CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions (recipient);
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")