import random
from typing import List
from src.utils.logger import logger

class Consensus:
    def __init__(self, blockchain, stake_manager):
        self.blockchain = blockchain
        self.stake_manager = stake_manager

    def select_validator(self):
        validators = self.stake_manager.get_active_validators()

        if not validators:
            logger.error("No active validators available")
            return None

        total_stake = sum(validators.values())
        if total_stake <= 0:
            logger.error("Total stake is zero or negative")
            return None

        selection_point = random.uniform(0, total_stake)
        current_sum = 0

        for address, stake in validators.items():
            current_sum += stake
            if current_sum >= selection_point:
                logger.info(f"Selected validator: {address} with stake {stake}")
                return address

        logger.error("Validator selection failed")
        return None

    @staticmethod
    def validate_block(block: 'Block', previous_block: 'Block') -> bool:
        return block.is_valid(previous_block)

    @staticmethod
    def is_chain_valid(chain: List['Block']) -> bool:
        if not chain:
            return False

        genesis = chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            logger.error("Invalid genesis block")
            return False

        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i-1]

            if not current.is_valid(previous):
                return False

        return True

    @staticmethod
    def cumulative_difficulty(chain: List['Block']) -> float:
        if not chain:
            return 0
        return sum(block.difficulty for block in chain)
