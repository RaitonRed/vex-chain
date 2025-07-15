from flask import Flask, request, jsonify
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.repositories import BlockRepository, TransactionRepository
from src.utils.logger import logger

app = Flask(__name__)
blockchain = Blockchain()

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'chain_length': len(blockchain.chain),
        'last_block': blockchain.get_last_block().index if blockchain.chain else None,
        'difficulty': blockchain.difficulty
    })

@app.route('/blocks', methods=['GET'])
def get_blocks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    blocks = blockchain.get_blocks_paginated(page, per_page)
    return jsonify({
        'blocks': [{
            'index': block.index,
            'hash': block.hash,
            'previous_hash': block.previous_hash,
            'timestamp': block.timestamp,
            'transaction_count': len(block.transactions)
        } for block in blocks]
    })

@app.route('/blocks/<int:index>', methods=['GET'])
def get_block(index: int):
    block = BlockRepository.get_block_by_index(index)
    if not block:
        return jsonify({'error': 'Block not found'}), 404
        
    return jsonify({
        'index': block.index,
        'hash': block.hash,
        'previous_hash': block.previous_hash,
        'timestamp': block.timestamp,
        'nonce': block.nonce,
        'difficulty': block.difficulty,
        'transactions': [{
            'tx_hash': tx.tx_hash,
            'sender': tx.sender,
            'recipient': tx.recipient,
            'amount': tx.amount
        } for tx in block.transactions]
    })

@app.route('/transactions', methods=['POST'])
def add_transaction():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    try:
        tx = Transaction(
            sender=data.get('sender'),
            recipient=data.get('recipient'),
            amount=data.get('amount'),
            data=data.get('data', {})
        )
        
        # در یک پیاده‌سازی واقعی، اینجا تراکنش به mempool اضافه می‌شود
        # و بعداً در بلاک جدید قرار می‌گیرد
        
        return jsonify({
            'status': 'success',
            'tx_hash': tx.tx_hash
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/mine', methods=['POST'])
def mine_block():
    # در یک پیاده‌سازی واقعی، تراکنش‌ها از mempool گرفته می‌شوند
    dummy_tx = Transaction(
        sender="network",
        recipient="miner",
        amount=1.0,
        data={"type": "reward", "message": "Block mining reward"}
    )
    
    new_block = blockchain.add_block([dummy_tx])
    if not new_block:
        return jsonify({'error': 'Failed to mine block'}), 500
        
    return jsonify({
        'status': 'success',
        'block': {
            'index': new_block.index,
            'hash': new_block.hash
        }
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)