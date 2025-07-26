from src.blockchain.stake_manager import StakeManager
from src.blockchain.validator_registry import ValidatorRegistry
from src.blockchain.contract.contract_manager import ContractManager
from src.cli.prompts import (
    prompt_address,
    prompt_amount,
    prompt_contract_code,
    prompt_contract_call,
    prompt_method_name,
    prompt_contract_address
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
    print_warning
)
from cryptography.hazmat.primitives.asymmetric import ec
import json

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

    def exit_node(self):
        """Handle node shutdown"""
        self.node.stop()
        print("\nGoodbye! 👋")
        exit(0)