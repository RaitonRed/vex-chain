import os
import json
from blockchain.block import Block

CHAIN_FILE = "data/chain.json"

class Blockchain:
    def __init__(self):
        self.chain = []
        self.load_chain()

    def create_genesis_block(self):
        genesis = Block(0, {"type": "genesis"}, "0")
        self.chain.append(genesis)
        self.save_chain()

    def get_last_block(self):
        return self.chain[-1]

    def add_block(self, data):
        last_block = self.get_last_block()
        new_block = Block(
            index=last_block.index + 1,
            data=data,
            previous_hash=last_block.hash
        )
        new_block = self.proof_of_work(new_block)
        self.chain.append(new_block)
        self.save_chain()
        return new_block

    def proof_of_work(self, block, difficulty=3):
        while not block.hash.startswith('0' * difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block

    def save_chain(self):
        os.makedirs("data", exist_ok=True)
        with open(CHAIN_FILE, "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def load_chain(self):
        if not os.path.exists(CHAIN_FILE):
            self.create_genesis_block()
            return
        with open(CHAIN_FILE, "r") as f:
            data = json.load(f)
            self.chain = [Block.from_dict(b) for b in data]