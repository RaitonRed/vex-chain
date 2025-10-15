from flask import Flask, request, jsonify, current_app
from src.blockchain.consensus.consensus import Consensus
from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.db.repositories import BlockRepository
from src.utils.logger import logger
from src.blockchain.vex_config import *
from src.blockchain.consensus.stake_manager import StakeManager
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.db.state_db import StateDB
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

    # Calculate block reward (VEX minted in this block)
    block_reward = VEX_CONFIG["block_reward"]
    transaction_fees = sum(getattr(tx, 'fee', 0) for tx in block.transactions)
    total_reward = block_reward + transaction_fees

    return jsonify({
        'index': block.index,
        'hash': block.hash,
        'previous_hash': block.previous_hash,
        'timestamp': block.timestamp,
        'nonce': block.nonce,
        'difficulty': block.difficulty,
        'validator': block.validator,
        'block_reward': block_reward,
        'transaction_fees': transaction_fees,
        'total_reward': total_reward,
        'reward_currency': VEX_CONFIG["symbol"],
        'transactions': [{
            'tx_hash': tx.tx_hash,
            'sender': tx.sender,
            'recipient': tx.recipient,
            'amount': tx.amount,
            'currency': VEX_CONFIG["symbol"],
            'fee': getattr(tx, 'fee', 0),
            'fee_currency': VEX_CONFIG["symbol"]
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

    tx_data = data.get('transaction')
    if not tx_data:
        return jsonify({'error': 'No transaction provided'}), 400

    try:
        tx = Transaction(
            sender=tx_data.get('sender'),
            recipient=tx_data.get('recipient'),
            amount=tx_data.get('amount'),
            data=tx_data.get('data', {}),
            signature=tx_data.get('signature'),
            nonce=tx_data.get('nonce')
        )

        if not tx.is_valid():
            return jsonify({'error': 'Invalid transaction signature'}), 400

        if node.mempool.add_transaction(tx):
            if node.p2p_network:
                node.p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash
            }), 201
        else:
            return jsonify({'error': 'Failed to add staking transaction'}), 400

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

    tx_data = data.get('transaction')
    if not tx_data:
        return jsonify({'error': 'No transaction provided'}), 400

    try:
        tx = Transaction(
            sender=tx_data.get('sender'),
            recipient=tx_data.get('recipient'),
            amount=tx_data.get('amount'),
            data={
                'type': 'unstake',
                'amount': tx_data.get('amount'),
                **tx_data.get('data', {})
            },
            signature=tx_data.get('signature'),
            nonce=tx_data.get('nonce')
        )

        if not tx.is_valid():
            return jsonify({'error': 'Invalid transaction signature'}), 400

        if tx.data.get('type') != 'unstake':
            return jsonify({'error': 'Transaction is not an unstake operation'}), 400

        stake_amount = StakeManager.get_stake_amount(tx.sender)
        if stake_amount < tx.amount:
            return jsonify({'error': f'Insufficient stake balance: {stake_amount}'}), 400

        if node.mempool.add_transaction(tx):
            if node.p2p_network:
                node.p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash,
                'message': f'Unstake transaction submitted. {tx.amount} coins will be unstaked.'
            }), 200
        else:
            return jsonify({'error': 'Failed to add unstake transaction to mempool'}), 400

    except Exception as e:
        logger.error(f"Unstake error: {str(e)}")
        return jsonify({'error': f'Unstake failed: {str(e)}'}), 500

@app.route('/stake/<address>', methods=['GET'])
def get_stake_info(address):
    node = current_app.config.get('node')

    if not node:
        return jsonify(
            {
                'error': 'Node Not initialized'
            }
        ), 500

    try:
        stake_amount = StakeManager.get_stake_amount(address)
        is_validator = ValidatorRegistry.is_validator(address)
        validator_info = ValidatorRegistry.get_validator_info(address) if is_validator else None

        return jsonify({
            'status': 'success',
            'address': address,
            'stake_amount': stake_amount,
            'is_validator': is_validator,
            'validator_info': validator_info
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get stake info: {str(e)}'}), 500

@app.route('/stake/<address>/transactions', methods=['GET'])
def get_stake_transactions(address):
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        staking_txs = StakeManager.get_staking_transactions(address)
        unstaking_txs = StakeManager.get_unstaking_transactions(address)

        return jsonify({
            'status': 'success',
            'address': address,
            'staking_transactions': staking_txs,
            'unstaking_transactions': unstaking_txs
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get stake transactions: {str(e)}'}), 500

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

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    private_key_pem = data.get('private_key')
    if not private_key_pem:
        return jsonify({'error': 'Private key is required for mining'}), 400

    try:
        validator_private_key = load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )

        validator_address = ValidatorRegistry.get_validator_address(validator_private_key)

        stake = ValidatorRegistry.get_validator_stake(validator_address)
        if stake <= 0:
            return jsonify({'error': 'Validator has no stake or not registered'}), 400

        transactions = list(node.mempool.transactions.values())
        if not transactions:
            return jsonify({'error': 'No transactions in the mempool'}), 400

        new_block = node.blockchain._create_new_block(
            transactions,
            validator_private_key,
            validator_address
        )

        if new_block:
            node.p2p_network.broadcast_block(new_block)
            node.mempool.remove_transactions([tx.tx_hash for tx in transactions])
            return jsonify({
                'status': 'success',
                'block': {
                    'index': new_block.index,
                    'hash': new_block.hash,
                    'validator': validator_address
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to create new block'}), 400

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
        tx_data = {
            'sender': data.get('sender'),
            'recipient': data.get('recipient'),
            'amount': data.get('amount'),
            'data': data.get('data', {}),
            'signature': data.get('signature'),
            'nonce': data.get('nonce')
        }

        # Add VEX info to transaction data if not already present
        if 'type' not in tx_data['data']:
            tx_data['data']['type'] = 'vex_transfer'
            tx_data['data']['symbol'] = VEX_CONFIG["symbol"]

        tx = Transaction(**tx_data)

        # Validate transaction
        if not tx.is_valid():
            return jsonify({'error': 'Invalid transaction signature'}), 400

        # Check if sender has enough VEX for regular transfers
        if tx.data.get('type') == 'vex_transfer':
            sender_balance = StateDB().get_balance(tx.sender)
            total_cost = tx.amount + getattr(tx, 'fee', 0)

            if sender_balance < total_cost:
                return jsonify({
                    'error': f'Insufficient VEX balance. Available: {sender_balance}, Required: {total_cost}'
                }), 400

        if node.mempool.add_transaction(tx):
            if node.p2p_network:
                node.p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash,
                'currency': VEX_CONFIG["symbol"]
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

    tx_data = data.get('transaction')
    if not tx_data:
        return jsonify({'error': 'No transaction provided'}), 400

    try:
        tx = ContractTransaction(
            sender=tx_data.get('sender'),
            recipient=tx_data.get('recipient'),
            amount=tx_data.get('amount', 0),
            data=tx_data.get('data', {}),
            contract_address=tx_data.get('contract_address'),
            method=tx_data.get('method'),
            args=tx_data.get('args', {}),
            signature=tx_data.get('signature'),
            nonce=tx_data.get('nonce')
        )

        if not tx.is_valid():
            return jsonify({'error': 'Invalid transaction signature'}), 400

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
    password = data.get('password')

    if not account_name or not password:
        return jsonify({'error': 'Missing account_name or password'}), 400

    try:
        address, private_key = node.wallet.create_account(account_name, password)
        return jsonify({
            'status': 'success',
            'address': address,
            'private_key': private_key
        }), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create account: {str(e)}'}), 500

@app.route('/accounts/import', methods=['POST'])
def import_account():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    account_name = data.get('account_name')
    private_key = data.get('private_key')
    password = data.get('password')

    if not all([account_name, private_key, password]):
        return jsonify({'error': 'Missing account_name, private_key or password'}), 400

    try:
        address = node.wallet.import_private_key(account_name, private_key, password)
        return jsonify({
            'status': 'success',
            'address': address,
            'message': 'Account imported successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': f'Failed to import account: {str(e)}'}), 500

@app.route('/node/stake', methods=['POST'])
def node_stake():
    """Endpoint for nodes to stake and become validators"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    amount = data.get('amount', 1000.0)  # Default stake amount

    try:
        # Get node's wallet
        node_account = node.wallet.accounts.get(f"node_{node.p2p_port}")
        if not node_account:
            return jsonify({'error': 'Node wallet not found'}), 400

        address = node_account['address']
        public_key_pem = node_account['public_key']

        # Perform staking
        tx_id = StakeManager.stake(address, amount, public_key_pem)
        if tx_id:
            return jsonify({
                'status': 'success',
                'message': f'Node staked {amount} coins successfully',
                'tx_id': tx_id,
                'validator_address': address
            }), 200
        else:
            return jsonify({'error': 'Staking failed'}), 400

    except Exception as e:
        return jsonify({'error': f'Staking failed: {str(e)}'}), 500

@app.route('/node/validator-info', methods=['GET'])
def get_node_validator_info():
    """Get validator information for this node"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        node_account = node.wallet.accounts.get(f"node_{node.p2p_port}")
        if not node_account:
            return jsonify({'error': 'Node wallet not found'}), 400

        address = node_account['address']
        stake = StakeManager.get_validator_stake(address)
        is_active = address in StakeManager.get_active_validators()

        return jsonify({
            'status': 'success',
            'validator_address': address,
            'stake_amount': stake,
            'is_active': is_active,
            'node_port': node.p2p_port
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get validator info: {str(e)}'}), 500

@app.route('/accounts/<address>/nonce', methods=['GET'])
def get_account_nonce(address):
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        nonce = StateDB().get_nonce(address)
        return jsonify({
            'status': 'success',
            'address': address,
            'nonce': nonce
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get nonce: {str(e)}'}), 500

@app.route('/accounts/<address>', methods=['GET'])
def get_account_info(address):
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        balance = StateDB().get_balance(address)
        nonce = StateDB().get_nonce(address)
        stake_amount = StakeManager.get_stake_amount(address)
        is_validator = ValidatorRegistry.is_validator(address)

        return jsonify({
            'status': 'success',
            'address': address,
            'balance': balance,
            'currency': VEX_CONFIG["symbol"],
            'nonce': nonce,
            'stake_amount': stake_amount,
            'stake_currency': VEX_CONFIG["symbol"],
            'is_validator': is_validator
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get account info: {str(e)}'}), 500

@app.route('/accounts', methods=['GET'])
def get_accounts():
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        accounts = []
        for name, acc in node.wallet.accounts.items():
            address = acc.get('address')
            balance = StateDB().get_balance(address) if address else 0
            accounts.append({
                'name': name,
                'address': address,
                'balance': balance,
                'currency': VEX_CONFIG["symbol"]
            })

        return jsonify({
            'status': 'success',
            'accounts': accounts
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get accounts: {str(e)}'}), 500

# Check later
# @app.route('/accounts/export/<account_name>', methods=['POST'])
# def export_account(account_name):
#     node = current_app.config.get('node')
#     if not node:
#         return jsonify({'error': 'Node not initialized'}), 500
#
#     data = request.json
#     if not data:
#         return jsonify({'error': 'No data provided'}), 400
#
#     password = data.get('password')
#     if not password:
#        return jsonify({'error': 'Password is required'}), 400
#
#     try:
#         private_key = node.wallet.export_private_key(account_name, password)
#         if private_key:
#             return jsonify({
#                 'status': 'success',
#                 'account_name': account_name,
#                 'private_key': private_key
#             }), 200
#         else:
#            return jsonify({'error': 'Failed to export private key'}), 400
#     except Exception as e:
#         return jsonify({'error': f'Failed to export account: {str(e)}'}), 500

# Security Issue
# @app.route('/shutdown', methods=['POST'])
# def shutdown_node():
#    node = current_app.config.get('node')
#    if not node:
#        return jsonify({'error': 'Node not initialized'}), 500
#
#    try:
#        node.stop()
#        return jsonify({'status': 'success', 'message': 'Node shutting down'}), 200
#    except Exception as e:
#        return jsonify({'error': f'Failed to shutdown node: {str(e)}'}), 500

@app.route('/vex/supply', methods=['GET'])
def get_vex_supply():
    """Get current VEX circulating supply"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    # Calculate circulating supply (total supply minus unclaimed rewards)
    total_supply = VEX_CONFIG["total_supply"]
    # In a real implementation, you'd subtract unclaimed rewards from total supply

    return jsonify({
        'total_supply': total_supply,
        'circulating_supply': total_supply,  # Simplified for now
        'symbol': VEX_CONFIG["symbol"]
    }), 200

@app.route('/vex/balance/<address>', methods=['GET'])
def get_vex_balance(address):
    """Get VEX balance for a specific address"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        balance = StateDB().get_balance(address)
        return jsonify({
            'status': 'success',
            'address': address,
            'balance': balance,
            'symbol': VEX_CONFIG["symbol"]
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get VEX balance: {str(e)}'}), 500

@app.route('/vex/transfer', methods=['POST'])
def transfer_vex():
    """Transfer VEX coins between accounts"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Create VEX transfer transaction
        tx = Transaction(
            sender=data.get('sender'),
            recipient=data.get('recipient'),
            amount=data.get('amount'),
            data={
                'type': 'vex_transfer',
                'symbol': VEX_CONFIG["symbol"],
                **data.get('data', {})
            },
            signature=data.get('signature'),
            nonce=data.get('nonce')
        )

        # Validate transaction
        if not tx.is_valid():
            return jsonify({'error': 'Invalid transaction signature'}), 400

        # Check if sender has enough VEX
        sender_balance = StateDB().get_balance(tx.sender)
        total_cost = tx.amount + getattr(tx, 'fee', 0)

        if sender_balance < total_cost:
            return jsonify({
                'error': f'Insufficient VEX balance. Available: {sender_balance}, Required: {total_cost}'
            }), 400

        # Add to mempool
        if node.mempool.add_transaction(tx):
            if node.p2p_network:
                node.p2p_network.broadcast_transaction(tx)
            return jsonify({
                'status': 'success',
                'tx_hash': tx.tx_hash,
                'message': f'Transferring {tx.amount} {VEX_CONFIG["symbol"]} to {tx.recipient}'
            }), 201
        else:
            return jsonify({'error': 'Failed to add transaction to mempool'}), 400

    except Exception as e:
        logger.error(f"VEX transfer error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/vex/rewards/<validator_address>', methods=['GET'])
def get_vex_rewards(validator_address):
    """Get VEX rewards for a validator"""
    node = current_app.config.get('node')
    if not node:
        return jsonify({'error': 'Node not initialized'}), 500

    try:
        # Calculate total rewards earned by validator
        total_rewards = 0
        last_block = node.blockchain.get_last_block()

        if last_block:
            # In a real implementation, you'd sum up all block rewards for this validator
            # This is a simplified version
            validator_blocks = [b for b in node.blockchain.chain if b.validator == validator_address]
            total_rewards = len(validator_blocks) * VEX_CONFIG["block_reward"]

            # Add transaction fees from validated blocks
            for block in validator_blocks:
                total_rewards += sum(getattr(tx, 'fee', 0) for tx in block.transactions)

        return jsonify({
            'status': 'success',
            'validator': validator_address,
            'total_rewards': total_rewards,
            'symbol': VEX_CONFIG["symbol"]
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get VEX rewards: {str(e)}'}), 500
