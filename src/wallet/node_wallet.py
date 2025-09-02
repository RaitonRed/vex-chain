import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from src.utils.crypto import public_key_to_pem, sign_data

class NodeWallet:
    def __init__(self, node_id):
        self.private_key = ec.generate_private_key(ec.SECP256K1())
        self.public_key = self.private_key.public_key()
        self.address = self.generate_address()
        self.stake_amount = 0
        self.node_id = node_id
        
    def generate_address(self):
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        return 'NODE' + hashlib.blake2b(public_bytes, digest_size=20).hexdigest()
    
    def sign_data(self, data):
        return sign_data(self.private_key, data)
    
    def add_stake(self, amount):
        self.stake_amount += amount
        
    def to_dict(self):
        return {
            'address': self.address,
            'public_key': public_key_to_pem(self.public_key),
            'stake_amount': self.stake_amount,
            'node_id': self.node_id
        }