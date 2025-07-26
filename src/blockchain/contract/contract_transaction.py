import json
from typing import Dict, Optional
from src.utils.database import db_connection
from src.utils.logger import logger

class ContractRepository:
    """Repository for managing smart contract storage and retrieval"""
    
    @staticmethod
    def save_contract(address: str, code: str, creator: str) -> bool:
        """Save a new contract to the database"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO contracts (
                    address, code, creator, created_at
                ) VALUES (?, ?, ?, datetime('now'))
                ''', (address, code, creator))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save contract: {e}")
            return False

    @staticmethod
    def get_contract(address: str) -> Optional[Dict]:
        """Retrieve a contract by its address"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT address, code, creator, created_at 
                FROM contracts WHERE address = ?
                ''', (address,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        "address": row[0],
                        "code": row[1],
                        "creator": row[2],
                        "created_at": row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get contract: {e}")
            return None

    @staticmethod
    def save_contract_state(address: str, state: Dict) -> bool:
        """Save contract state to database"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT OR REPLACE INTO contract_state (
                    contract_address, storage
                ) VALUES (?, ?)
                ''', (address, json.dumps(state)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save contract state: {e}")
            return False

    @staticmethod
    def get_contract_state(address: str) -> Optional[Dict]:
        """Retrieve contract state"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT storage FROM contract_state 
                WHERE contract_address = ?
                ''', (address,))
                row = cursor.fetchone()
                return json.loads(row[0]) if row else {}
        except Exception as e:
            logger.error(f"Failed to get contract state: {e}")
            return {}

    @staticmethod
    def save_contract_event(
        address: str,
        event_name: str,
        event_data: Dict,
        block_number: int,
        tx_hash: str
    ) -> bool:
        """Save a contract event to the database"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO contract_events (
                    contract_address, event_name, event_data,
                    block_number, tx_hash, timestamp
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    address,
                    event_name,
                    json.dumps(event_data),
                    block_number,
                    tx_hash
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save contract event: {e}")
            return False

    @staticmethod
    def get_contract_events(address: str, limit: int = 100) -> list:
        """Retrieve contract events"""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT event_name, event_data, block_number, tx_hash, timestamp
                FROM contract_events 
                WHERE contract_address = ?
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (address, limit))
                return [{
                    "event_name": row[0],
                    "event_data": json.loads(row[1]),
                    "block_number": row[2],
                    "tx_hash": row[3],
                    "timestamp": row[4]
                } for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get contract events: {e}")
            return []