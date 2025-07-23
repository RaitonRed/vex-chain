import pytest
import os
from src.utils.database import init_db, db_connection

@pytest.fixture(scope="function")
def clean_db():
    """فیکسچر برای ایجاد دیتابیس جدید قبل از هر تست"""
    if os.path.exists("data/blockchain.db"):
        os.remove("data/blockchain.db")
    init_db()
    yield
    if os.path.exists("data/blockchain.db"):
        os.remove("data/blockchain.db")

@pytest.fixture
def sample_transaction():
    """تراکنش نمونه برای تست"""
    return {
        "sender": "Alice",
        "recipient": "Bob",
        "amount": 10.0,
        "data": {"note": "Test transaction"}
    }

@pytest.fixture
def sample_block(sample_transaction):
    """بلاک نمونه برای تست"""
    return {
        "index": 0,
        "timestamp": 1633024800.0,
        "transactions": [sample_transaction],
        "previous_hash": "0",
        "nonce": 12345
    }