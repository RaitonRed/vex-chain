import pytest
from src.blockchain.mempool import Mempool
from src.blockchain.transaction import Transaction

def test_mempool_add_transaction(sample_transaction):
    mempool = Mempool()
    tx = Transaction(**sample_transaction)
    
    assert mempool.add_transaction(tx) is True
    assert tx.tx_hash in mempool.transactions
    
    # اضافه کردن تراکنش تکراری
    assert mempool.add_transaction(tx) is False

def test_mempool_transaction_limit(sample_transaction):
    mempool = Mempool()
    mempool.max_size = 2
    
    tx1 = Transaction(sender="A", recipient="B", amount=1)
    tx2 = Transaction(sender="B", recipient="C", amount=2)
    tx3 = Transaction(sender="C", recipient="D", amount=3)
    
    assert mempool.add_transaction(tx1) is True
    assert mempool.add_transaction(tx2) is True
    assert mempool.add_transaction(tx3) is False  # ظرفیت پر شده

def test_mempool_clear_expired(sample_transaction):
    mempool = Mempool()
    tx = Transaction(**sample_transaction)
    tx.timestamp = 0  # زمان قدیمی
    
    mempool.add_transaction(tx)
    mempool.clear_expired(expiry_seconds=1)
    
    assert tx.tx_hash not in mempool.transactions