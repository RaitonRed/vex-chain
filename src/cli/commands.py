from src.blockchain.contract_transaction import ContractTransaction
from src.blockchain.transaction import Transaction
from src.blockchain.stake_manager import StakeManager
from src.blockchain.validator_registry import ValidatorRegistry
from src.blockchain.contract.contract_manager import ContractManager
from src.blockchain.consensus import Consensus
from src.blockchain.transaction import Transaction
from src.cli.prompts import (
    prompt_address,
    prompt_amount,
    prompt_contract_code,
    prompt_contract_call,
    prompt_method_name,
    prompt_contract_address,
    prompt_json_data
)
from src.cli.outputs import (
    display_status,
    display_blockchain_info,
    display_mempool,
    display_peers,
    display_validators,
    display_contract_state,
    print_success,
    print_error,
    print_warning,
    print_info
)
from cryptography.hazmat.primitives.asymmetric import ec

class CommandExecutor:
    def __init__(self, node):
        self.node = node

    def show_status(self):
        """Display node status information"""
        status_data = {
            "Running": "Yes" if self.node._running else "No",
            "Host": self.node.host,
            "P2P Port": self.node.p2p_port,
            "API Port": self.node.api_port,
            "Block Height": len(self.node.blockchain.chain),
            "Mempool Size": len(self.node.mempool.transactions),
            "Connected Peers": len(list(self.node.p2p_network.peers))
        }
        display_status(status_data)

    def show_blockchain_info(self):
        """Display blockchain summary"""
        last_block = self.node.blockchain.get_last_block()
        display_blockchain_info(last_block)

    def show_mempool_info(self):
        """Display mempool transactions"""
        transactions = list(self.node.mempool.transactions.values())[:10]  # Limit to 10 txs
        display_mempool(transactions)

    def show_peers(self):
        """Display connected peers"""
        peers = list(self.node.p2p_network.peers)
        display_peers(peers)

    def stake_coins(self):
        """Handle staking operation"""
        try:
            address = prompt_address("Your address")
            amount = prompt_amount("Amount to stake")
            
            StakeManager.stake(address, amount, len(self.node.blockchain.chain))
            print_success(f"Successfully staked {amount} coins")
            
        except Exception as e:
            print_error(f"Staking failed: {str(e)}")

    def unstake_coins(self):
        """Handle unstaking operation"""
        try:
            address = prompt_address("Your address")
            amount = prompt_amount("Amount to unstake")
            
            if StakeManager.unstake(address, amount):
                print_success(f"Successfully unstaked {amount} coins")
            else:
                print_error("Unstaking failed (insufficient stake?)")
                
        except Exception as e:
            print_error(f"Unstaking failed: {str(e)}")

    def show_validators(self):
        """Display active validators"""
        validators = ValidatorRegistry.get_active_validators()
        display_validators(validators)

    def mine_block(self):
        """Handle manual block mining"""
        if not self.node.blockchain.chain:
            print_error("Blockchain not initialized")
            return

        validators = ValidatorRegistry.get_active_validators()
        if not validators:
            print_error("No active validators available")
            return

        transactions = list(self.node.mempool.transactions.values())
        if not transactions:
            print_warning("No transactions in mempool")
            return

        try:
            # In production, use actual validator key
            validator_key = ec.generate_private_key(ec.SECP256K1())
            
            new_block = self.node.blockchain.add_block(transactions, validator_key)
            if new_block:
                print_success(f"Block #{new_block.index} mined successfully!")
                self.node.mempool.remove_transactions([tx.tx_hash for tx in transactions])
                StakeManager.distribute_rewards(new_block)
            else:
                print_error("Block mining failed")
                
        except Exception as e:
            print_error(f"Mining failed: {str(e)}")

    def deploy_contract(self):
        """Handle contract deployment"""
        try:
            sender = prompt_address("Sender address")
            print("\nEnter contract code (type 'END' on new line to finish):")
            code = prompt_contract_code()
            
            contract_address = ContractManager.deploy_contract(sender, code)
            print_success(f"Contract deployed at: {contract_address}")
            
        except Exception as e:
            print_error(f"Contract deployment failed: {str(e)}")

    def call_contract(self):
        """Handle contract calls"""
        try:
            sender = prompt_address("Sender address")
            contract_address = prompt_contract_address()
            method = prompt_method_name()
            args = prompt_contract_call()
            amount = prompt_amount("Amount to send (0 for none)")
            
            tx = ContractManager.call_contract(
                sender,
                contract_address,
                method,
                args,
                amount
            )
            
            if self.node.mempool.add_transaction(tx):
                print_success(f"Contract call transaction added: {tx.tx_hash[:10]}...")
            else:
                print_error("Failed to add transaction to mempool")
                
        except Exception as e:
            print_error(f"Contract call failed: {str(e)}")

    def view_contract(self):
        """Display contract state"""
        try:
            contract_address = prompt_contract_address()
            state = ContractManager.get_contract_state(contract_address)
            display_contract_state(contract_address, state)
            
        except Exception as e:
            print_error(f"Failed to view contract: {str(e)}")

    def sync_network(self):
        """Handle network synchronization"""
        try:
            print("\nSyncing with network...")
            self.node.p2p_network.sync_blockchain()
            self.node.p2p_network.sync_mempool()
            print_success("Synchronization completed")
            
        except Exception as e:
            print_error(f"Synchronization failed: {str(e)}")

    def create_transaction(self):
        """Create new transaction"""
        sender = prompt_address("Sender address")
        recipient = prompt_address("Recipient address")
        amount = prompt_amount("Amount")
        data = prompt_json_data("Additional data (JSON)")
        
        tx = Transaction(
            sender=sender,
            recipient=recipient,
            amount=amount,
            data=data
        ).sign(self.node.wallet.get_private_key())
        
        if self.node.mempool.add_transaction(tx):
            print_success(f"Transaction added successfully! Hash: {tx.tx_hash[:10]}...")
        else:
            print_error("Failed to add transaction")

    def create_contract_transaction(self):
        """Create smart contract transaction"""
        sender = prompt_address("Sender address")
        contract_address = prompt_contract_address()
        method = prompt_method_name()
        args = prompt_contract_call()
        amount = prompt_amount("Amount to send")
        
        tx = ContractTransaction(
            sender=sender,
            contract_address=contract_address,
            method=method,
            args=args,
            amount=amount
        ).sign(self.node.wallet.get_private_key())
        
        if self.node.mempool.add_transaction(tx):
            print_success(f"Contract transaction added! Hash: {tx.tx_hash[:10]}...")
        else:
            print_error("Failed to add contract transaction")

    def claim_stake_rewards(self):
        """Claim staking rewards"""
        validator = prompt_address("Validator address")
        try:
            rewards = StakeManager.claim_rewards(validator)
            print_success(f"Successfully claimed rewards: {rewards} coins")
        except Exception as e:
            print_error(f"Error claiming rewards: {str(e)}")

    def connect_to_peer(self):
        """Manually connect to peer"""
        host = input("Peer IP address: ").strip()
        port = int(input("Peer port: ").strip())
        self.node.p2p_network.connect_to_peer(host, port)
        print_success(f"Connection request sent to {host}:{port}")

    def disconnect_peer(self):
        """Disconnect from peer"""
        peers = list(self.node.p2p_network.peers)
        if not peers:
            print_warning("No peers to disconnect")
            return
            
        print("Connected peers:")
        for i, (host, port) in enumerate(peers, 1):
            print(f"{i}. {host}:{port}")
            
        choice = int(input("Select peer to disconnect: ")) - 1
        peer = peers[choice]
        self.node.p2p_network.peers.remove(peer)
        print_success(f"Disconnected from {peer[0]}:{peer[1]}")

    def view_contract_events(self):
        """View contract events"""
        contract_address = prompt_contract_address()
        events = ContractManager.get_contract_events(contract_address)
        
        if not events:
            print_info("No events found for this contract")
            return
            
        print(f"\nEvents for contract {contract_address[:10]}...:\n")
        for event in events:
            print(f"📢 {event['event_name']}")
            print(f"   Block: #{event['block_number']}")
            print(f"   Data: {event['event_data']}\n")

    def node_settings(self):
        """Advanced node settings"""
        settings = {
            "1": ("Mempool size limit", self._set_mempool_limit),
            "2": ("Minimum stake amount", self._set_min_stake),
            "3": ("Block interval", self._set_block_interval)
        }
        
        while True:
            print("\nAdvanced Node Settings:")
            for key, (label, _) in settings.items():
                print(f"{key}. {label}")
            print("0. Back")
            
            choice = input("Select: ").strip()
            if choice == "0":
                break
            if choice in settings:
                settings[choice][1]()
            else:
                print_error("Invalid option!")

    def _set_mempool_limit(self):
        new_limit = int(input("Max transactions in mempool: "))
        self.node.mempool.max_size = new_limit
        print_success(f"Mempool limit set to {new_limit}")

    def _set_min_stake(self):
        amount = float(input("Minimum stake for validation: "))
        ValidatorRegistry.MIN_STAKE = amount
        print_success(f"Minimum stake set to {amount}")

    def _set_block_interval(self):
        seconds = int(input("Time between blocks (seconds): "))
        Consensus.BLOCK_INTERVAL = seconds
        print_success(f"Block interval set to {seconds} seconds")
    
    def deploy_contract(self):
        """Handle contract deployment"""
        try:
            sender = prompt_address("Sender address")
            print("\nEnter contract code (type 'END' on new line to finish):")
            code = prompt_contract_code()
        
            contract_address = ContractManager.deploy_contract(sender, code)
            print_success(f"Contract deployed at: {contract_address}")
        
        except Exception as e:
            print_error(f"Contract deployment failed: {str(e)}")

    def call_contract(self):
        """Handle contract calls"""
        try:
            sender = prompt_address("Sender address")
            contract_address = prompt_contract_address()
            method = prompt_method_name()
            args = prompt_contract_call()
            amount = prompt_amount("Amount to send (0 for none)")
        
            # Create contract transaction
            tx = ContractTransaction(
                sender=sender,
                recipient=contract_address,  # Using recipient field for consistency
                amount=amount,
                data={},  # Additional data if needed
                contract_address=contract_address,
                method=method,
                args=args
            ).sign(self.node.wallet.get_private_key())
        
            if self.node.mempool.add_transaction(tx):
                print_success(f"Contract call transaction added: {tx.tx_hash[:10]}...")
            else:
                print_error("Failed to add transaction to mempool")
            
        except Exception as e:
            print_error(f"Contract call failed: {str(e)}")

    def clear_mempool(self):
        """Clear all transactions from mempool"""
        try:
            count = len(self.node.mempool.transactions)
            self.node.mempool.transactions.clear()
            print_success(f"Cleared {count} transactions from mempool")
        except Exception as e:
            print_error(f"Failed to clear mempool: {str(e)}")
    
    def exit_node(self):
        """Handle node shutdown"""
        self.node.stop()
        print("\nGoodbye! 👋")
        exit(0)