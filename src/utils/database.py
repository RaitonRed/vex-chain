import sqlite3
import json
import os
import hashlib
from blockchain.block import Block

DB_FILE = "data/blockchain.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index INTEGER NOT NULL UNIQUE,
        timestamp REAL NOT NULL,
        data TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        nonce INTEGER NOT NULL,
        hash TEXT NOT NULL UNIQUE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        address TEXT PRIMARY KEY,
        last_seen REAL DEFAULT (strftime('%s', 'now'))
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks (index)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks (hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_prev_hash ON blocks (previous_hash)')
    
    conn.commit()
    conn.close()

def save_block(block):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO blocks (index, timestamp, data, previous_hash, nonce, hash)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block.index,
            block.timestamp,
            json.dumps(block.data),
            block.previous_hash,
            block.nonce,
            block.hash
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: blocks.index" in str(e):
            cursor.execute('''
            UPDATE blocks SET
                timestamp = ?,
                data = ?,
                previous_hash = ?,
                nonce = ?,
                hash = ?
            WHERE index = ?
            ''', (
                block.timestamp,
                json.dumps(block.data),
                block.previous_hash,
                block.nonce,
                block.hash,
                block.index
            ))
            conn.commit()
        else:
            raise
    finally:
        conn.close()

def get_block(index):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM blocks WHERE index = ?', (index,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Block(
            index=row[1],
            timestamp=row[2],
            data=json.loads(row[3]),
            previous_hash=row[4],
            nonce=row[5],
            hash=row[6]
        )
    return None

def get_last_block():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM blocks ORDER BY index DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Block(
            index=row[1],
            timestamp=row[2],
            data=json.loads(row[3]),
            previous_hash=row[4],
            nonce=row[5],
            hash=row[6]
        )
    return None

def get_chain_length():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM blocks')
    length = cursor.fetchone()[0]
    conn.close()
    return length

def get_full_chain():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM blocks ORDER BY index ASC')
    rows = cursor.fetchall()
    conn.close()
    
    chain = []
    for row in rows:
        chain.append(Block(
            index=row[1],
            timestamp=row[2],
            data=json.loads(row[3]),
            previous_hash=row[4],
            nonce=row[5],
            hash=row[6]
        ))
    return chain

def add_node(address):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO nodes (address, last_seen)
        VALUES (?, strftime('%s', 'now'))
        ''', (address,))
        conn.commit()
    finally:
        conn.close()

def get_nodes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT address FROM nodes')
    nodes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return nodes

def replace_chain(new_chain):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('DELETE FROM blocks')
        
        for block in new_chain:
            cursor.execute('''
            INSERT INTO blocks (index, timestamp, data, previous_hash, nonce, hash)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                block.index,
                block.timestamp,
                json.dumps(block.data),
                block.previous_hash,
                block.nonce,
                block.hash
            ))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()