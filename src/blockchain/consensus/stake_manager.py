from typing import Dict
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.utils.database import db_connection
from src.utils.logger import logger
from src.blockchain.db.state_db import StateDB
import time

class StakeManager:

    REWARD_RATE = 0.8  # 80% of fees as reward
    SLASH_RATE = 0.05  # 5% penalty for malicious validators

    @staticmethod
    def stake(address: str, amount: float, public_key_pem: str) -> str:
        try:
            # Check if validator already exists
            existing_stake = StakeManager.get_validator_stake(address)
            if existing_stake > 0:
                logger.info(f"Validator {address} already exists with stake {existing_stake}")
                return f"stake_update_{address}_{int(time.time())}"

            # Deduct stake amount from balance
            state_db = StateDB()
            current_balance = state_db.get_balance(address)
            if current_balance < amount:
                logger.error(f"Insufficient balance for staking: {address}")
                return None

            state_db.update_balance(address, current_balance - amount)

            # Register validator
            ValidatorRegistry.register_validator(
                address=address,
                public_key_pem=public_key_pem,
                stake=amount
            )

            return f"stake_tx_{address}_{int(time.time())}"
        except Exception as e:
            logger.error(f"Staking failed: {e}")
            return None

    @staticmethod
    def unstake(address: str, amount: float):
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
    def claim_reward(validator_address: str) -> float:
        return 10.0

    @staticmethod
    def distribute_rewards(block):
        try:
            total_fees = sum(tx.fee for tx in block.transactions if hasattr(tx, 'fee'))
            base_reward = total_fees * StakeManager.REWARD_RATE

            validator_stake = ValidatorRegistry.get_validator_stake(block.validator)
            total_stake = sum(StakeManager.get_active_validators().values())
            stake_ratio = validator_stake / total_stake if total_stake > 0 else 0

            final_reward = base_reward * (1 + stake_ratio)

            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE validators
                    SET stake = stake + ?
                    WHERE address = ?
                ''', (final_reward, block.validator))
                conn.commit()

        except Exception as e:
            logger.error(f"Reward distribution failed: {e}")

    @staticmethod
    def slash_validator(validator_address, block_hash):
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT stake FROM validators WHERE address = ?', (validator_address,))
                stake = cursor.fetchone()[0]

                penalty = stake * StakeManager.SLASH_RATE
                new_stake = stake - penalty

                cursor.execute('''
                    UPDATE validators
                    SET stake = ?
                    WHERE address = ?
                ''', (new_stake, validator_address))
                conn.commit()

                logger.warning(f"Validator {validator_address} slashed {penalty} for block {block_hash}")

        except Exception as e:
            logger.error(f"Slashing failed: {e}")

    @staticmethod
    def get_validator_stake(address: str) -> float:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT stake FROM validators WHERE address = ?', (address,))
            row = cursor.fetchone()
            return row[0] if row else 0

    @staticmethod
    def get_active_validators() -> Dict[str, float]:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT address, stake FROM validators
                WHERE last_active > datetime('now', '-1 day')
            ''')
            return {row[0]: row[1] for row in cursor.fetchall()}
