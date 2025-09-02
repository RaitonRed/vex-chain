import random
import binascii
import time

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from src.blockchain.block import Block

class HybridConsensus:
    def __init__(self, blockchain, difficulty=4):
        self.blockchain = blockchain
        self.difficulty = difficulty
        self.validators = {}
        self.miners = {}
        
    def register_node(self, node_wallet, role):
        if role == 'validator':
            self.validators[node_wallet.address] = node_wallet
        elif role == 'miner':
            self.miners[node_wallet.address] = node_wallet
            
    def select_validator(self):
        total_stake = sum([v.stake_amount for v in self.validators.values()])
        if total_stake == 0:
            return random.choice(list(self.validators.keys()))
            
        selection_point = random.uniform(0, total_stake)
        current_sum = 0
        
        for address, wallet in self.validators.items():
            current_sum += wallet.stake_amount
            if current_sum >= selection_point:
                return address
        return list(self.validators.keys())[0]
    
    def validate_pow(self, block):
        target = '0' * self.difficulty
        return block.hash.startswith(target)
    
    def validate_pos(self, block):
        if block.validator not in self.validators:
            return False
            
        validator_wallet = self.validators[block.validator]
        try:
            public_key = load_pem_public_key(validator_wallet.public_key.encode())
            signature_bytes = binascii.unhexlify(block.signature)
            public_key.verify(
                signature_bytes,
                block.hash.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except:
            return False
            
    def create_block(self, transactions, miner_wallet, validator_address):
        last_block = self.blockchain.get_last_block()
        
        new_block = Block(
            index=last_block.index + 1,
            timestamp=time.time(),
            transactions=transactions,
            previous_hash=last_block.hash,
            miner=miner_wallet.address,
            validator=validator_address,
            stake_amount=self.validators[validator_address].stake_amount
        )
        
        # اثبات کار
        while not self.validate_pow(new_block):
            new_block.pow_nonce += 1
            new_block.hash = new_block.calculate_hash()
            
        # امضای ولیدیتور
        validator_wallet = self.validators[validator_address]
        new_block.sign_block(validator_wallet.private_key, validator_wallet.stake_amount)
        
        return new_block