from flask import Flask, request, jsonify, current_app
from src.blockchain.consensus.consensus import Consensus
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.db.repositories import BlockRepository
from src.utils.logger import logger
from src.blockchain.consensus.stake_manager import StakeManager
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.contracts.contract_manager import ContractManager
from src.blockchain.contracts.contract_transaction import ContractTransaction
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import ec
import time
import random

# Create Flask app instance
app = Flask(__name__)

@app.route('/', methods=['GET'])
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

@app.route('/health', methods=['GET'])
def health_check():
    node = current_app.config.get('node')
    if not node:
        return jsonify({"status": "NOT READY"}), 503
    
    status = "READY" if node.is_ready() else "NOT READY"
    return jsonify({
        "status": status,
        "services": {
            "blockchain": node._check_blockchain(),
            "p2p": node._check_p2p(),
            "api": node._check_api()
        }
    }), 200 if status == "READY" else 503

@app.route('/status', methods=['GET'])
def get_status():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    status_data = {
        "running": "Yes" if node._running else "No",
        "host": node.host,
        "p2p_port": node.p2p_port,
        "api_port": node.api_port,
        "block_height": len(node.blockchain.chain),
        "mempool_size": len(node.mempool.transactions),
        "connected_peers": len(list(node.p2p_network.peers))
    }
    return jsonify(status_data), 200

@app.route('/blockchain/info', methods=['GET'])
def get_blockchain_info():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    last_block = node.blockchain.get_last_block()
    if not last_block:
        return jsonify({'error': 'No blockchain info available'}), 404

    return jsonify({
        'index': last_block.index,
        'hash': last_block.hash,
        'previous_hash': last_block.previous_hash,
        'timestamp': last_block.timestamp,
        'transaction_count': len(last_block.transactions),
        'validator': last_block.validator,
        'stake_amount': last_block.stake_amount
    }), 200

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
    }), 200

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
    }), 200

@app.route('/mempool', methods=['GET'])
def get_mempool_info():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    transactions = list(node.mempool.transactions.values())[:10]
    return jsonify({
        'transactions': [{
            'tx_hash': tx.tx_hash,
            'sender': tx.sender,
            'recipient': tx.recipient,
            'amount': tx.amount,
            'timestamp': tx.timestamp
        } for tx in transactions]
    }), 200

@app.route('/peers', methods=['GET'])
def get_peers():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    peers = list(node.p2p_network.peers)
    return jsonify({'peers': [f"{host}:{port}" for host, port in peers]}), 200

@app.route('/peers/connect', methods=['POST'])
def connect_to_peer():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    host = data.get('host')
    port = data.get('port')

    if not all([host, port]):
        return jsonify({'error': 'Missing host or port'}), 400

    try:
        node.p2p_network.connect_to_peer(host, port)
        return jsonify({'status': 'success', 'message': f'Connection request sent to {host}:{port}'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to connect to peer: {str(e)}'}), 500

@app.route('/peers/disconnect', methods=['POST'])
def disconnect_peer():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    host = data.get('host')
    port = data.get('port')

    if not all([host, port]):
        return jsonify({'error': 'Missing host or port'}), 400

    peer = (host, port)
    if peer in node.p2p_network.peers:
        node.p2p_network.peers.remove(peer)
        return jsonify({'status': 'success', 'message': f'Disconnected from {host}:{port}'}), 200
    else:
        return jsonify({'error': 'Peer not connected'}), 404

@app.route('/stake', methods=['POST'])
def stake_coins():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    account_name = data.get('account_name')
    amount = data.get('amount')

    if not all([account_name, amount]):
        return jsonify({'error': 'Missing account_name or amount'}), 400

    try:
        accounts = node.wallet.accounts
        if not accounts:
            return jsonify({'error': 'No accounts available'}), 400

        if account_name not in accounts:
            return jsonify({'error': 'Invalid account name'}), 400

        account = accounts[account_name]
        private_key = account.get('private_key')
        public_key = account.get('public_key')
        address = account.get('address')

        if not private_key or not public_key:
            return jsonify({'error': 'Private key or public key not available for this account'}), 400

        tx_hash = StakeManager.stake(
            address=address,
            amount=amount,
            public_key_pem=public_key,
        )

        if tx_hash:
            return jsonify({
                'status': 'success',
                'tx_hash': tx_hash,
                'validator_address': address
            }), 201
        else:
            return jsonify({'error': 'Staking failed'}), 400
    except Exception as e:
        return jsonify({'error': f'Staking failed: {str(e)}'}), 500

@app.route('/unstake', methods=['POST'])
def unstake_coins():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    address = data.get('address')
    amount = data.get('amount')

    if not all([address, amount]):
        return jsonify({'error': 'Missing address or amount'}), 400

    try:
        if StakeManager.unstake(address, amount):
            return jsonify({'status': 'success', 'message': f'Successfully unstaked {amount} coins'}), 200
        else:
            return jsonify({'error': 'Unstaking failed (insufficient stake?)'}), 400
    except Exception as e:
        return jsonify({'error': f'Unstaking failed: {str(e)}'}), 500

@app.route('/validators', methods=['GET'])
def get_validators():
    validators = StakeManager.get_active_validators()
    return jsonify({'validators': validators}), 200

@app.route('/mine', methods=['POST'])
def mine_block_post():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    if not node.blockchain.chain:
        return jsonify({'error': 'Blockchain is not initialized'}), 400

    try:
        accounts = node.wallet.accounts
        my_validators = []
        for account_name, account in accounts.items():
            address = account.get('address')
            stake = ValidatorRegistry.get_validator_stake(address) if address else 0
            if stake > 0:
                my_validators.append({
                    'address': address,
                    'stake': stake,
                    'private_key': account.get('private_key'),
                    'name': account_name
                })

        if not my_validators:
            return jsonify({'error': 'No validators found in your wallet with stake'}), 400

        transactions = list(node.mempool.transactions.values())
        if not transactions:
            return jsonify({'error': 'No transactions in the mempool'}), 400

        total_stake = sum(v['stake'] for v in my_validators)
        if total_stake <= 0:
            return jsonify({'error': 'Total stake is zero or negative'}), 400

        selection_point = random.uniform(0, total_stake)
        current_sum = 0
        selected_validator = None

        for validator in my_validators:
            current_sum += validator['stake']
            if current_sum >= selection_point:
                selected_validator = validator
                break

        if not selected_validator:
            return jsonify({'error': 'Validator selection failed'}), 400

        private_key_pem = selected_validator['private_key']
        if not private_key_pem:
            return jsonify({'error': f'Private Key not found for validator: {selected_validator["address"]}'}), 400

        try:
            validator_private_key = load_pem_private_key(
                private_key_pem.encode(),
                password=None,
            )

            new_block = node.blockchain.add_block(transactions, validator_private_key, selected_validator['address'])

            if new_block:
                node.p2p_network.broadcast_block(new_block)
                node.mempool.remove_transactions([tx.tx_hash for tx in transactions])
                return jsonify({
                    'status': 'success',
                    'block': {
                        'index': new_block.index,
                        'hash': new_block.hash,
                        'validator': selected_validator['address']
                    }
                }), 201
            else:
                return jsonify({'error': 'Failed to create new block'}), 400

        except Exception as e:
            logger.error(f"Mining error: {str(e)}")
            return jsonify({'error': 'Invalid private key or mining error'}), 401

    except Exception as e:
        logger.error(f"Mining error: {str(e)}")
        return jsonify({'error': f'Mining failed: {str(e)}'}), 500

@app.route('/transactions', methods=['POST'])
def add_transaction():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500
        
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
        
        private_key_pem = data.get('private_key_pem')
        if private_key_pem:
            private_key = load_pem_private_key(
                private_key_pem.encode(),
                password=None,
            )
            tx.sign(private_key)
        
        if node.mempool.add_transaction(tx):
            if node.p2p_network:
                node.p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash
            }), 201
        else:
            return jsonify({'error': 'Failed to add transaction to mempool'}), 400
            
    except Exception as e:
        logger.error(f"Transaction error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/contracts/deploy', methods=['POST'])
def deploy_contract():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    sender = data.get('sender')
    code = data.get('code')

    if not all([sender, code]):
        return jsonify({'error': 'Missing sender or code'}), 400

    try:
        contract_address = ContractManager.deploy_contract(sender, code)
        return jsonify({'status': 'success', 'contract_address': contract_address}), 201
    except Exception as e:
        return jsonify({'error': f'Contract deployment failed: {str(e)}'}), 500

@app.route('/contracts/call', methods=['POST'])
def call_contract():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    sender = data.get('sender')
    contract_address = data.get('contract_address')
    method = data.get('method')
    args = data.get('args', {})
    amount = data.get('amount', 0)
    private_key_pem = data.get('private_key_pem')

    if not all([sender, contract_address, method, private_key_pem]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        private_key = load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )

        tx = ContractTransaction(
            sender=sender,
            recipient=contract_address,
            amount=amount,
            data={},
            contract_address=contract_address,
            method=method,
            args=args
        ).sign(private_key)

        if node.mempool.add_transaction(tx):
            return jsonify({'status': 'success', 'tx_hash': tx.tx_hash}), 201
        else:
            return jsonify({'error': 'Failed to add transaction to mempool'}), 400
    except Exception as e:
        return jsonify({'error': f'Contract call failed: {str(e)}'}), 500

@app.route('/contracts/<contract_address>/events', methods=['GET'])
def view_contract_events(contract_address):
    events = ContractManager.get_contract_events(contract_address)
    if not events:
        return jsonify({'message': 'No events found for this contract'}), 404
    return jsonify({'events': events}), 200

@app.route('/mempool/clear', methods=['POST'])
def clear_mempool():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        count = len(node.mempool.transactions)
        node.mempool.transactions.clear()
        return jsonify({'status': 'success', 'message': f'Cleared {count} transactions from mempool'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to clear mempool: {str(e)}'}), 500

@app.route('/accounts/create', methods=['POST'])
def create_account():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    account_name = data.get('account_name')

    if not account_name:
        return jsonify({'error': 'Missing account_name'}), 400

    try:
        address = node.wallet.create_account(account_name)
        return jsonify({'status': 'success', 'address': address}), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create account: {str(e)}'}), 500

@app.route('/settings/mempool_limit', methods=['POST'])
def set_mempool_limit():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    new_limit = data.get('new_limit')

    if not new_limit:
        return jsonify({'error': 'Missing new_limit'}), 400

    try:
        node.mempool.max_size = new_limit
        return jsonify({'status': 'success', 'message': f'Mempool limit set to {new_limit}'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to set mempool limit: {str(e)}'}), 500

@app.route('/settings/min_stake', methods=['POST'])
def set_min_stake():
    data = request.json
    amount = data.get('amount')

    if not amount:
        return jsonify({'error': 'Missing amount'}), 400

    try:
        ValidatorRegistry.MIN_STAKE = amount
        return jsonify({'status': 'success', 'message': f'Minimum stake set to {amount}'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to set minimum stake: {str(e)}'}), 500

@app.route('/settings/block_interval', methods=['POST'])
def set_block_interval():
    data = request.json
    seconds = data.get('seconds')

    if not seconds:
        return jsonify({'error': 'Missing seconds'}), 400

    try:
        Consensus.BLOCK_INTERVAL = seconds
        return jsonify({'status': 'success', 'message': f'Block interval set to {seconds} seconds'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to set block interval: {str(e)}'}), 500

@app.route('/test/validator', methods=['POST'])
def create_test_validator():
    try:
        from cryptography.hazmat.primitives import serialization
        
        validator_key = ec.generate_private_key(ec.SECP256K1())
        public_key_pem = validator_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        validator_address = ValidatorRegistry.get_validator_address(validator_key)
        
        ValidatorRegistry.register_validator(
            address=validator_address,
            public_key_pem=public_key_pem,
            stake=10000
        )
        return jsonify({'status': 'success', 'validator_address': validator_address}), 201
    
    except Exception as e:
        return jsonify({'error': f'Failed to create test validator: {str(e)}'}), 500

@app.route('/test/transaction', methods=['POST'])
def create_test_transaction():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        test_tx = Transaction(
            sender="0x1234567890123456789012345678901234567890",
            recipient="0x0987654321098765432109876543210987654321",
            amount=10.0,
            data={"type": "test", "message": "Test transaction for mining"}
        )
        
        node.mempool.add_transaction(test_tx)
        return jsonify({'status': 'success', 'tx_hash': test_tx.tx_hash}), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create test transaction: {str(e)}'}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown_node():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        node.stop()
        return jsonify({'status': 'success', 'message': 'Node shutting down'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to shutdown node: {str(e)}'}), 500