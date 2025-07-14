import os
import json
import requests
import time
from src.blockchain.block import Block
from urllib.parse import urlparse
from src.utils.database import (
    init_db, save_block, get_block, 
    get_last_block, get_full_chain, get_chain_length,
    add_node, get_nodes, replace_chain
)

CHAIN_FILE = "data/chain.json"

class Blockchain:
    def __init__(self):
        self.chain = []
        self.nodes = set()
        self.load_chain()

        # Gensis Block
        if not self.chain:
            self.create_genesis_block()
            self.chain = get_full_chain()

    def create_genesis_block(self):
        genesis_data = {
            "type": "genesis",
            "message": "Initial block of StorageChain",
            "timestamp": time.time()
        }
        genesis = Block(0, genesis_data, "0")
        save_block(genesis)

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

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def chain_validate(self, chain=None):
        chain = chain or self.chain
        previous_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if previous_block != previous_block.hash:
                return False
            
            if not block.hash.startswith('0' * 3):
                return False
            
            if block.hash != block.calculate_hash():
                return False
            
            previous_block = block
            current_index += 1

        return True
    
    def resolve_conflicts(self):
        new_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            try:
                response = requests.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain_data = response.json()['chain']
                    
                    if length > max_length:
                        chain = [Block.from_dict(block) for block in chain_data]
                        
                        if self.is_chain_valid(chain):
                            max_length = length
                            new_chain = chain
            except requests.exceptions.RequestException:
                continue
        
        if new_chain:
            self.chain = new_chain
            self.save_chain()
            return True
            
        return False