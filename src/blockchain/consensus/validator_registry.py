import hashlib
from typing import Optional
import cryptography.hazmat.primitives.serialization as serialization
from src.utils.database import db_connection
from typing import Dict
from src.utils.crypto import address_from_public_key
from src.utils.logger import logger

class ValidatorRegistry:
    @staticmethod
    def register_validator(address: str, public_key_pem: str, stake: float):
        """Unified validator registration"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO validators
                (address, public_key_pem, stake, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (address, public_key_pem, stake))
            conn.commit()

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
                WHERE stake > 0 AND last_active > datetime('now', '-1 day')
            ''')
            validators = {row[0]: row[1] for row in cursor.fetchall()}

            if not validators:
                logger.warning("No active validators found in database")

            return validators

    @staticmethod
    def get_validator_address(private_key: str) -> str:
        """Generating validator address from public key

        Args:
            private_key (str): validator private key

        Returns:
            str: validator address
        """

        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        return address_from_public_key(public_key_pem)

    @staticmethod
    def get_public_key_pem(address: str) -> Optional[str]:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT public_key_pem FROM accounts WHERE address = ?', (address,))
            row = cursor.fetchone()
            if row:
                return row[0]

            cursor.execute('SELECT public_key_pem FROM validators WHERE address = ?', (address,))
            row = cursor.fetchone()
            return row[0] if row else None

#    @staticmethod
#    def select_validator():
#        from src.blockchain.consensus.stake_manager import StakeManager
#        validators = StakeManager.get_active_validators()
#
#        if not validators:
#            logger.error("No active validators available")
#            return None
#
#        total_stake = sum(validators.values())
#        if total_stake <= 0:
#            logger.error("Total stake is zero or negative")
#            return None
#
#        selection_point = random.uniform(0, total_stake)
#        current_sum = 0
#
#        for address, stake in validators.items():
#            current_sum += stake
#            if current_sum >= selection_point:
#                logger.info(f"Selected validator: {address} with stake {stake}")
#                return address
#
#        logger.error("Validator selection failed")
#        return None

    @staticmethod
    def calculate_address(public_key_pem: str) -> str:
        return hashlib.sha256(public_key_pem.encode()).hexdigest()[:40]
