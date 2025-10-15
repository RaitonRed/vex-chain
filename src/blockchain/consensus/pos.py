from src.blockchain.block import Block
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

class VRF:
    def __init__(self, private_key):
        self.private_key = private_key

    def prove(self, seed):
        # Generate VRF proof
        signature = self.private_key.sign(
            seed,
            ec.ECDSA(hashes.SHA256()))

        return signature

    @staticmethod
    def verify(public_key, seed, signature):
        # Verify VRF proof
        try:
            public_key.verify(
                signature,
                seed,
                ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

class ProofOfStake:
    def __init__(self):
        self.validators = {}
        self.staking_contract = "0xStakingContract"

    def add_validator(self, address: str, stake: float):
        self.validators[address] = stake

    def select_validator(self, seed):

        # Calculate validator weights based on their stake
        total_stake = sum(self.validators.values())

        vrf = VRF(private_key=self.staking_contract)
        proof = vrf.prove(seed)
        random_value = int.from_bytes(proof, 'big') % total_stake

        # Select validator based on random value
        current_sum = 0
        for address, stake in self.validators.items():
            current_sum += stake
            if current_sum >= random_value:
                return address, proof

        return None

    def validate_block(self, block: Block, validator: str) -> bool:
        return block.validator == validator and Block.verify_signature(block.signature)
