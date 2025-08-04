class Account:
    def __init__(self, address: str, public_key_pem: str, nonce: int = 0):
        self.address = address
        self.public_key_pem = public_key_pem
        self.nonce = nonce

    def to_dict(self):
        return {
            'address': self.address,
            'public_key_pem': self.public_key_pem,
            'nonce': self.nonce
        }