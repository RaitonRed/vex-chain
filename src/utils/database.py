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
        -- جدول بلاک‌ها
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "index" INTEGER NOT NULL UNIQUE,
            timestamp REAL NOT NULL,
            previous_hash TEXT NOT NULL,
            nonce INTEGER NOT NULL,
            hash TEXT NOT NULL UNIQUE,
            difficulty INTEGER NOT NULL,
            validator TEXT
        );
        
        -- جدول تراکنش‌ها
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
        
        -- جدول نودهای شبکه
        CREATE TABLE IF NOT EXISTS nodes (
            address TEXT PRIMARY KEY,
            last_seen REAL DEFAULT (strftime('%s', 'now'))
        );
        
        -- جدول جدید: ولیدیتورها (اضافه شد)
        CREATE TABLE IF NOT EXISTS validators (
            address TEXT PRIMARY KEY,
            public_key_pem TEXT NOT NULL,
            last_updated REAL DEFAULT (strftime('%s', 'now'))
        );
        
        -- جدول جدید: حافظه موقت تراکنش‌ها (Mempool)
        CREATE TABLE IF NOT EXISTS mempool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT NOT NULL UNIQUE,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            amount REAL NOT NULL,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            signature TEXT,
            fee REAL DEFAULT 0
        );
        
        -- ایندکس‌های جدول بلاک‌ها
        CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks ("index");
        CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks (hash);
        CREATE INDEX IF NOT EXISTS idx_blocks_validator ON blocks (validator);
        
        -- ایندکس‌های جدول تراکنش‌ها
        CREATE INDEX IF NOT EXISTS idx_tx_hash ON transactions (tx_hash);
        CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions (sender);
        CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions (recipient);
        CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions (block_id);
        
        -- ایندکس‌های جدول نودها
        CREATE INDEX IF NOT EXISTS idx_nodes_address ON nodes (address);
        
        -- ایندکس‌های جدول ولیدیتورها
        CREATE INDEX IF NOT EXISTS idx_validators_address ON validators (address);
        
        -- ایندکس‌های جدول Mempool
        CREATE INDEX IF NOT EXISTS idx_mempool_tx_hash ON mempool (tx_hash);
        CREATE INDEX IF NOT EXISTS idx_mempool_sender ON mempool (sender);
        CREATE INDEX IF NOT EXISTS idx_mempool_recipient ON mempool (recipient);
        CREATE INDEX IF NOT EXISTS idx_mempool_timestamp ON mempool (timestamp);
        ''')
        
        # ایجاد جدول وضعیت زنجیره (برای ذخیره آخرین حالت)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chain_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_blocks INTEGER DEFAULT 0,
            total_transactions INTEGER DEFAULT 0,
            last_block_hash TEXT,
            last_block_timestamp REAL,
            last_updated REAL DEFAULT (strftime('%s', 'now'))
        )
        ''') 
        
        # ایجاد رکورد اولیه برای وضعیت زنجیره
        cursor.execute('''
        INSERT OR IGNORE INTO chain_state (id, total_blocks, total_transactions)
        VALUES (1, 0, 0)
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully with all tables and indexes")