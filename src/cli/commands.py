# Deprecated

import time
import random
from src.blockchain.block import Block
from src.blockchain.contracts.contract_transaction import ContractTransaction
from src.blockchain.transaction import Transaction
from src.blockchain.consensus.stake_manager import StakeManager
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.contracts.contract_manager import ContractManager
from src.blockchain.consensus.consensus import Consensus
from src.blockchain.transaction import Transaction
from src.cli.style import CLITheme
from cryptography.hazmat.primitives.asymmetric import ec
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

class CommandExecutor:
    def __init__(self, node):
        self.node = node

        self.theme = CLITheme()

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
        try:
            # Get account selection
            accounts = self.node.wallet.accounts
            if not accounts:
                print("❌ No accounts available")
                return

            print("Available accounts:")
            for i, (name, acc) in enumerate(accounts.items(), 1):
                print(f"{i}. {name} ({acc['address'][:12]}...)")

            choice = input("Select account: ")
            if not choice.isdigit() or int(choice) > len(accounts):
                print("❌ Invalid selection")
                return

            account_name = list(accounts.keys())[int(choice)-1]
            account = accounts[account_name]

            # Get staking amount
            amount = float(input("Amount to stake: "))

            # Get private key and public key
            private_key = account.get('private_key')
            public_key = account.get('public_key')
            address = account.get('address')

            if not private_key or not public_key:
                print("❌ Private key or public key not available for this account")
                return

            # Stake coins - call static method directly
            tx_hash = StakeManager.stake(
                address=address,
                amount=amount,
                public_key_pem=public_key,
            )

            if tx_hash:
                print(f"✅ Staked {amount} coins. TX Hash: {tx_hash[:10]}...")
                print(f"   Validator address: {address}")
            else:
                print("❌ Staking failed")
        except Exception as e:
            print(f"❌ Staking failed: {e}")

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
        validators = StakeManager.get_active_validators()
        display_validators(validators)

    def mine_block(self):
        """Manual block mining - Only mine if we are the selected validator"""
        if not self.node.blockchain.chain:
            print_error("Blockchain is not initialized")
            return

        # Get validators from our wallet that have stake
        my_validators = self._get_validators_in_wallet()
        for account_name, account in self.node.wallet.accounts.items():
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
            print_error("No validators found in your wallet with stake")
            print_info("Please stake coins with one of your accounts first")
            return

        transactions = list(self.node.mempool.transactions.values())
        if not transactions:
            print_warning("No transactions in the mempool")
            return

        try:
            # Select a validator from our wallet (weighted by stake)
            total_stake = sum(v['stake'] for v in my_validators)
            if total_stake <= 0:
                print_error("Total stake is zero or negative")
                return

            selection_point = random.uniform(0, total_stake)
            current_sum = 0
            selected_validator = None

            for validator in my_validators:
                current_sum += validator['stake']
                if current_sum >= selection_point:
                    selected_validator = validator
                    break

            if not selected_validator:
                print_error("Validator selection failed")
                return

            print_info(f"Selected validator: {selected_validator['name']} ({selected_validator['address'][:10]}...)")

            # Load private key
            private_key_pem = selected_validator['private_key']
            if not private_key_pem:
                print_error(f"Private Key not found for validator: {selected_validator['address']}")
                return

            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            private_key = load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )

            # Create new block
            last_block = self.node.blockchain.get_last_block()

            new_block = Block(
                index=last_block.index + 1,
                timestamp=int(time.time()),
                transactions=transactions,
                previous_hash=last_block.hash,
                validator=selected_validator['address'],
                stake_amount=selected_validator['stake'],
                difficulty=self.node.blockchain.difficulty
            )

            # Sign the block
            new_block.sign_block(private_key, new_block.stake_amount)

            # Add block to blockchain
            added_block = self.node.blockchain.add_block(
                block=new_block,
                external_block=None,
                selected_validator_address=selected_validator['address']
            )

            if added_block:
                print_success(f"✅ Block #{added_block.index} mined successfully!")
                print_info(f"   Validator: {added_block.validator}")
                print_info(f"   Transactions: {len(added_block.transactions)}")
                print_info(f"   Hash: {added_block.hash[:16]}...")

                # Remove mined transactions from mempool
                tx_hashes = [tx.tx_hash for tx in transactions]
                self.node.mempool.remove_transactions(tx_hashes)

                # Distribute rewards
                StakeManager.distribute_rewards(added_block)
                print_info(f"   Rewards distributed to validator")
            else:
                print_error("Block mining failed")

        except Exception as e:
            print_error(f"Mining error: {str(e)}")
            import traceback
            traceback.print_exc()

    def _is_address_in_wallet(self, address):
        """Check if an address exists in our wallet"""
        return any(acc['address'] == address for acc in self.node.wallet.accounts.values())

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
        """Create and sign transaction properly"""
        try:
            # Account selection
            accounts = list(self.node.wallet.accounts.items())
            if not accounts:
                print(f"{self.theme.ERROR}❌ No accounts available{self.theme.RESET}")
                return

            print(f"{self.theme.INFO}Available accounts:{self.theme.RESET}")
            for i, (name, acc) in enumerate(accounts, 1):
                print(f"{i}. {name} ({acc['address'][:12]}...)")

            # Get account
            choice = int(input(f"{self.theme.PROMPT}Select account: {self.theme.INPUT}")) - 1
            account = accounts[choice][1]

            # Get transaction details
            recipient = prompt_address("Recipient address")
            amount = prompt_amount("Amount")
            data = prompt_json_data("Additional data (JSON)")

            # Create transaction
            tx = Transaction(
                sender=account['address'],
                recipient=recipient,
                amount=amount,
                data=data
            )

            # Sign transaction
            private_key_pem = account['private_key']
            if private_key_pem:
                from cryptography.hazmat.primitives.serialization import load_pem_private_key
                private_key = load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None
                )
                tx.sign(private_key)

                if self.node.mempool.add_transaction(tx):
                    print(f"{self.theme.SUCCESS}✅ Transaction added! Hash: {tx.tx_hash[:10]}...{self.theme.RESET}")
                else:
                    print(f"{self.theme.ERROR}❌ Failed to add transaction{self.theme.RESET}")
            else:
                print(f"{self.theme.ERROR}❌ No private key available{self.theme.RESET}")

        except Exception as e:
            print(f"{self.theme.ERROR}❌ Error: {str(e)}{self.theme.RESET}")

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

    def create_account(self):
        """Create new cryptographic account"""
        account_name = input(f"{self.theme.PROMPT}Account name: {self.theme.INPUT}").strip()
        if not account_name:
            print_error("Account name cannot be empty")
            return

        address = self.node.wallet.create_account(account_name)
        print_success(f"Account created successfully! Address: {address}")

    def _create_test_validator(self):
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
            print_success(f"Test validator created: {validator_address}")

        except Exception as e:
            print_error(f"Failed to create test validator: {e}")

    def _create_test_transaction(self):
        try:
            from src.blockchain.transaction import Transaction

            test_tx = Transaction(
                sender="0x1234567890123456789012345678901234567890",
                recipient="0x0987654321098765432109876543210987654321",
                amount=10.0,
                data={"type": "test", "message": "Test transaction for mining"}
            )

            self.node.mempool.add_transaction(test_tx)
            print_success("Test transaction created")

        except Exception as e:
            print_error(f"Failed to create test transaction: {e}")

    def _get_validators_in_wallet(self):
        """Get all validators that are in our wallet and have stake"""
        validators = []
        for account_name, account in self.node.wallet.accounts.items():
            address = account.get('address')
            if address:
                stake = ValidatorRegistry.get_validator_stake(address)
                if stake > 0:
                    validators.append({
                        'address': address,
                        'stake': stake,
                        'private_key': account.get('private_key'),
                        'name': account_name
                    })
        return validators

    def exit_node(self):
        """Handle node shutdown"""
        self.node.stop()
        print("\nGoodbye! 👋")
        exit(0)
