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
        if not last_block:
            raise Exception("Blockchain not initialized")
        
        new_block = Block(
            index=last_block.index + 1,
            data=data,
            previous_hash=last_block.hash
        )

        new_block = self.proof_of_work(new_block)

        save_block(new_block)
        self.chain.append(new_block)

        return new_block

    def proof_of_work(self, block, difficulty=3):
        start_time = time.time()
        print(f"Mining block #{block.index}...")
        
        while not block.hash.startswith('0' * difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()
        
        mining_time = time.time() - start_time
        print(f"Block mined in {mining_time:.2f}s | Hash: {block.hash}")
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
        if not parsed_url.netloc:
            raise ValueError("Invalid node address")
        add_node(parsed_url.netloc)

    def chain_validate(self, chain=None):
        chain = chain or self.chain
        if not chain:
            return False
            
        genesis = chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            return False
            
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i-1]
            
            if current.index != previous.index + 1:
                return False
                
            if current.previous_hash != previous.hash:
                return False
                
            if current.hash != current.calculate_hash():
                return False
                
            if not current.hash.startswith('0' * 3):
                return False
                
        return True
    
    def resolve_conflicts(self):
        nodes = get_nodes()
        if not nodes:
            return False
            
        new_chain = None
        max_length = len(self.chain)

        for node in nodes:
            try:
                response = requests.get(f'http://{node}/chain', timeout=3)
                if response.status_code == 200:
                    chain_data = response.json().get('chain', [])
                    if len(chain_data) > max_length:
                        chain = []
                        for block_data in chain_data:
                            chain.append(Block(
                                index=block_data['index'],
                                timestamp=block_data['timestamp'],
                                data=block_data['data'],
                                previous_hash=block_data['previous_hash'],
                                nonce=block_data['nonce'],
                                hash=block_data['hash']
                            ))
                        
                        if self.is_chain_valid(chain):
                            new_chain = chain
                            max_length = len(chain)
            except (requests.RequestException, ValueError, KeyError):
                continue
        
        if new_chain:
            replace_chain(new_chain)
            self.chain = new_chain
            return True
            
        return False