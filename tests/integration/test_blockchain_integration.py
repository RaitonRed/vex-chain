import pytest
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction

def test_blockchain_initialization(clean_db):
    blockchain = Blockchain()
    assert len(blockchain.chain) == 1  # باید بلاک جنسیس وجود داشته باشد
    
    genesis = blockchain.chain[0]
    assert genesis.index == 0
    assert genesis.previous_hash == "0"

def test_block_addition(clean_db):
    blockchain = Blockchain()
    tx = Transaction(sender="Alice", recipient="Bob", amount=10.0)
    
    # افزودن بلاک جدید (در تست واقعی باید ولیدیتور معتبر باشد)
    new_block = blockchain.add_block([tx], validator_private_key=None)
    
    assert new_block is not None
    assert new_block.index == 1
    assert len(blockchain.chain) == 2
    assert new_block.transactions[0].tx_hash == tx.tx_hash

def test_chain_validation(clean_db):
    blockchain = Blockchain()
    tx = Transaction(sender="Alice", recipient="Bob", amount=10.0)
    blockchain.add_block([tx], validator_private_key=None)
    
    assert blockchain.is_chain_valid() is True
    
    # دستکاری زنجیره
    blockchain.chain[1].transactions[0].amount = 100.0
    assert blockchain.is_chain_valid() is False