from flask import Flask, request, jsonify
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.repositories import BlockRepository, TransactionRepository
from src.blockchain.mempool import Mempool
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from src.utils.logger import logger

app = Flask(__name__)
blockchain = Blockchain()

# Global references
blockchain = None
mempool = None
p2p_network = None

def create_app(blockchain_instance, mempool_instance, network_instance):
    global blockchain, mempool, p2p_network
    blockchain = blockchain_instance
    mempool = mempool_instance
    p2p_network = network_instance
    
    app = Flask(__name__)
    return app

app = create_app(blockchain, mempool, p2p_network)

@app.route('/mine', methods=['POST'])
def mine_block_post():
    transactions = mempool.get_transactions()
    
    if not transactions:
        return jsonify({'error': 'No transactions to mine'}), 400
    
    private_key_pem = request.headers.get('X-Private-Key')
    if not private_key_pem:
        return jsonify({'error': 'Private key required'}), 401
    
    try:
        validator_private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )

        new_block = blockchain.add_block(transactions, validator_private_key)
        
        if new_block:
            # Broadcast new block to network
            p2p_network.broadcast_block(new_block)
            
            # Clear mined transactions
            mempool.remove_transactions([tx.tx_hash for tx in transactions])
            
            return jsonify({
                'status': 'success',
                'block': {
                    'index': new_block.index,
                    'hash': new_block.hash,
                }
            }), 201
            
    except Exception as e:
        return jsonify({'error': 'Invalid private key'}), 401

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
        
        # اضافه کردن تراکنش به mempool
        mempool = Mempool()
        if mempool.add_transaction(tx):
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash
            }), 201
        else:
            return jsonify({'error': 'Failed to add transaction to mempool'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/mine', methods=['POST'])
def mine_block():
    
    # دریافت تراکنش‌ها از mempool
    mempool = Mempool()
    transactions = mempool.get_transactions()
    
    if not transactions:
        return jsonify({'error': 'No transactions to mine'}), 400
    
    try:
        # ساخت کلید خصوصی برای ولیدیتور (در محیط واقعی باید از کلید واقعی استفاده شود)
        validator_private_key = ec.generate_private_key(ec.SECP256K1())
        
        # اضافه کردن بلاک جدید
        new_block = blockchain.add_block(transactions, validator_private_key)
        if not new_block:
            return jsonify({'error': 'Failed to mine block'}), 500
        
        # حذف تراکنش‌های پردازش شده از mempool
        mempool.remove_transactions([tx.tx_hash for tx in transactions])
        
        return jsonify({
            'status': 'success',
            'block': {
                'index': new_block.index,
                'hash': new_block.hash,
                'transaction_count': len(new_block.transactions)
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Mining failed: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)