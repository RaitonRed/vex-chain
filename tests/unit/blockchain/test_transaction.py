import pytest
from src.blockchain.transaction import Transaction
from cryptography.hazmat.primitives.asymmetric import ec

def test_transaction_initialization(sample_transaction):
    tx = Transaction(**sample_transaction)
    assert tx.sender == "Alice"
    assert tx.recipient == "Bob"
    assert tx.amount == 10.0

def test_transaction_hash_uniqueness(sample_transaction):
    tx1 = Transaction(**sample_transaction)
    tx2 = Transaction(**sample_transaction)
    tx2.timestamp = tx1.timestamp + 1  # تغییر جزئی
    
    assert tx1.tx_hash != tx2.tx_hash

def test_transaction_signature_verification(sample_transaction):
    tx = Transaction(**sample_transaction)
    private_key = ec.generate_private_key(ec.SECP256K1())
    public_key = private_key.public_key()
    
    tx.sign(private_key)
    assert tx.verify_signature(public_key) is True
    
    # دستکاری داده‌ها بعد از امضا
    tx.amount = 20.0
    assert tx.verify_signature(public_key) is False