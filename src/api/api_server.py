from flask import Flask, request, jsonify, current_app
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.db.repositories import BlockRepository
from src.utils.logger import logger

# Create Flask app instance
app = Flask(__name__)

# Remove global variables and create_app function
# Instead, we'll use app context to access node

@app.route('/mine', methods=['POST'])
def mine_block_post():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
    blockchain = node.blockchain
    mempool = node.mempool
    p2p_network = node.p2p_network
    
    transactions = mempool.get_transactions()
    
    if not transactions:
        return jsonify({'error': 'No transactions to mine'}), 400
    
    private_key_pem = request.headers.get('X-Private-Key')
    if not private_key_pem:
        return jsonify({'error': 'Private key required'}), 401
    
    try:
        from cryptography.hazmat.primitives import serialization
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
        logger.error(f"Mining error: {str(e)}")
        return jsonify({'error': 'Invalid private key or mining error'}), 401

@app.route('/')
def home():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
    blockchain = node.blockchain
    return jsonify({
        'status': 'running',
        'chain_length': len(blockchain.chain),
        'last_block': blockchain.get_last_block().index if blockchain.chain else None,
        'difficulty': blockchain.difficulty
    })

@app.route('/blocks', methods=['GET'])
def get_blocks():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
    blockchain = node.blockchain
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
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
    blockchain = node.blockchain
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
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
    mempool = node.mempool
    p2p_network = node.p2p_network
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    try:
        # ایجاد تراکنش با استفاده از تابع سازنده صحیح
        tx = Transaction(
            sender=data.get('sender'),
            recipient=data.get('recipient'),
            amount=data.get('amount'),
            data=data.get('data', {})
        )
        
        # اضافه کردن تراکنش به mempool
        if mempool.add_transaction(tx):
            # Broadcast transaction to network
            if p2p_network:
                p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash
            }), 201
        else:
            return jsonify({'error': 'Failed to add transaction to mempool'}), 400
            
    except Exception as e:
        logger.error(f"Transaction error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health_check():
    node = current_app.config.get('node')
    if not node:
        return jsonify({"status": "NOT READY"}), 503
    
    # Simple health check
    status = "READY" if node.is_ready() else "NOT READY"
    return jsonify({
        "status": status,
        "services": {
            "blockchain": node._check_blockchain(),
            "p2p": node._check_p2p(),
            "api": node._check_api()
        }
    }), 200 if status == "READY" else 503

# Remove if __name__ == '__main__' block