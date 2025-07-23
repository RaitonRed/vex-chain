import pytest
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from cryptography.hazmat.primitives.asymmetric import ec

def test_block_initialization(sample_block):
    block = Block(**sample_block)
    assert block.index == 0
    assert block.previous_hash == "0"
    assert len(block.transactions) == 1

def test_block_hash_calculation(sample_block):
    block = Block(**sample_block)
    original_hash = block.hash
    
    # تغییر جزئی در داده‌ها
    block.nonce = 54321
    new_hash = block.calculate_hash()
    
    assert original_hash != new_hash
    assert len(original_hash) == 64  # طول هش SHA-256

def test_block_signature_verification(sample_block):
    block = Block(**sample_block)
    private_key = ec.generate_private_key(ec.SECP256K1())
    
    block.sign_block(private_key)
    assert block.verify_signature() is True
    
    # دستکاری امضا
    block.signature = "a" * 128
    assert block.verify_signature() is False