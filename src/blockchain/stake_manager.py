from src.blockchain.transaction import Transaction
from src.blockchain.block import Block
from src.utils.database import db_connection

class StakeManager:
    """مدیریت سهام‌گذاری و پاداش‌ها"""
    
    @staticmethod
    def stake(address: str, amount: float, block_number: int):
        """ثبت سهام جدید"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE validators 
                SET stake = stake + ?, last_active = datetime('now')
                WHERE address = ?
            ''', (amount, address))
            conn.commit()

    @staticmethod
    def unstake(address: str, amount: float):
        """برداشت سهام"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE validators 
                SET stake = stake - ?, last_active = datetime('now')
                WHERE address = ? AND stake >= ?
            ''', (amount, address, amount))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def distribute_rewards(block: Block):
        """توزیع پاداش به ولیدیتور"""
        reward = block.transaction_fees * 0.8  # 80% کارمزدها به عنوان پاداش
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE validators 
                SET stake = stake + ?, last_active = datetime('now')
                WHERE address = ?
            ''', (reward, block.validator))
            conn.commit()