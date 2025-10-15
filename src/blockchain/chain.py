import json
import time
from typing import List, Optional
from src.blockchain.consensus.stake_manager import StakeManager
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.blockchain.consensus.consensus import Consensus
from src.blockchain.db.repositories import BlockRepository, TransactionRepository
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.contracts.vm import SmartContractVM
from src.blockchain.db.state_db import StateDB
from src.utils.logger import logger
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from src.blockchain.block import Block
from src.utils.database import db_connection
from src.utils.cache import LRUCache

VEX_CONFIG = {
    "name": "VEX",
    "symbol": "VEX",
    "decimals": 18,
    "total_supply": 2_000_000_000 * 10**0, # 20 million tokens with 18 decimals
    "initial_distribution": {
        "foundation": 0.2, # 20% to foundation (4,000,000 VEX)
        "ecosystem": 0.3, # 30% to ecosystem development (6,000,000 VEX)
        "public_sale": 0.5 # 50% to public sale (10,000,000 VEX)
    }
}

foundation_address = "0x0000000000000000000000000000000000000001"
ecosystem_address = "0x0000000000000000000000000000000000000002"
public_sale_address = "0x0000000000000000000000000000000000000003"

foundation_amount = VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["foundation"]
ecosystem_amount = VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["ecosystem"]
public_sale_amount = VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["public_sale"]

class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.difficulty = difficulty

        self.chain = []
        self.block_cache = LRUCache(capacity=100)  # Cache for blocks
        self.last_block = self.load_last_block()  # Load last block from cache or DB
        self._db_initialized = False  # Track if DB has been initialized
        self.p2p_network = None

        try:
            from src.utils.database import init_db
            logger.info("Initializing database...")
            init_db()
            self._db_initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise RuntimeError("Failed to initialize database") from e

        # Load existing chain or create new one
        try:
            logger.info("Loading blockchain from database...")
            self.chain = self.load_chain()

            if not self.chain:
                logger.info("No existing chain found, creating new blockchain")
                self._reset_blockchain()  # Clean slate
                self._initialize_new_chain()
            elif not Consensus.is_chain_valid(self.chain):
                logger.warning("Existing chain is invalid, resetting...")
                self._reset_blockchain()
                self._initialize_new_chain()
            else:
                logger.info(f"Successfully loaded blockchain with {len(self.chain)} blocks")

        except Exception as e:
            logger.error(f"Blockchain initialization failed: {e}")
            # Last resort: try to create completely fresh blockchain
            try:
                logger.info("Attempting complete blockchain reset...")
                self._reset_blockchain()
                self._initialize_new_chain()
                logger.info("Fresh blockchain created successfully")
            except Exception as reset_error:
                logger.error(f"Failed to create fresh blockchain: {reset_error}")
                raise RuntimeError("Complete blockchain initialization failure") from reset_error

    def load_last_block(self) -> Optional[Block]:
        """Load the last block from cache or database"""
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX("index") FROM blocks')
            max_index = cursor.fetchone()[0]
            if max_index is None:
                return None
            return BlockRepository.get_block_by_index(max_index)


    def _reset_blockchain(self):
        """Reset blockchain database to initial state"""
        logger.info("Resetting blockchain database...")
        try:
            # Clear in-memory chain
            self.chain = []

            # Reset SQL database tables
            with db_connection() as conn:
                cursor = conn.cursor()
                # Delete all transactions first (foreign key constraint)
                cursor.execute("DELETE FROM transactions")
                cursor.execute("DELETE FROM blocks")
                # Reset autoincrement counters
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='blocks'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
                conn.commit()

            # Reset StateDB if implemented
            if hasattr(StateDB, 'reset'):
                StateDB().reset()
                logger.info("StateDB reset complete")
            else:
                logger.warning("StateDB reset not implemented")

            logger.info("Blockchain reset successfully")
        except Exception as e:
            logger.error(f"Blockchain reset failed: {e}")
            raise RuntimeError("Blockchain reset failed") from e


    def set_p2p_network(self, p2p_network):
        """Set P2P network reference after initialization"""
        self.p2p_network = p2p_network

    def _initialize_new_chain(self):
        logger.info("Initializing new blockchain")
        try:
            self._initialize_special_accounts()
            genesis_block = self._create_genesis_block()
            self.chain = [genesis_block]
            logger.info("New blockchain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize new chain: {e}")
            raise RuntimeError("Failed to initialize blockchain") from e

    def _initialize_special_accounts(self):
        """Create system accounts if they don't exist"""
        state_db = StateDB()

        # Create coinbase account
        coinbase_address = "0x0000000000000000000000000000000000000000"
        if not state_db.get_account(coinbase_address):
            state_db.create_account(coinbase_address, "", 0)

        # Create genesis account
        genesis_address = "0x0000000000000000000000000000000000000001"
        if not state_db.get_account(genesis_address):
            state_db.create_account(genesis_address, "", 0)

        # Set initial balance for genesis account
        state_db.update_balance(genesis_address, 1000000)

        logger.info("System accounts initialized")

    def _create_genesis_block(self) -> Block:
        """Create genesis block with PoS mechanism"""
        try:
            # Create private key for genesis validator
            genesis_private_key = ec.generate_private_key(ec.SECP256K1())

            # Generate validator address
            validator_address = ValidatorRegistry.get_validator_address(genesis_private_key)

            # Generate public key PEM
            public_key_pem = genesis_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()

            # Register genesis validator first
            ValidatorRegistry.register_validator(
                address=validator_address,
                public_key_pem=public_key_pem,
                stake=1000000  # Genesis validator stake
            )

            # Create genesis transaction
            genesis_tx = Transaction(
                sender="0x0000000000000000000000000000000000000000",
                recipient="0x0000000000000000000000000000000000000001",
                amount=1000000,  # Initial supply
                data={"type": "genesis", "message": "Initial block of the chain"},
                nonce=0,  # Explicitly set nonce to 0
                timestamp=0
            )

            genesis_tx.tx_hash = genesis_tx.calculate_hash()

            # Create genesis block
            genesis_block = Block(
                index=0,
                timestamp=0,
                transactions=[genesis_tx],
                previous_hash="0",
                validator=validator_address,
                stake_amount=1000000,
                difficulty=self.difficulty,
                nonce=0
            )

            vex_transactions = [
                Transaction(
                    sender="0x0",
                    recipient=foundation_address,
                    amount=foundation_amount,
                    data={
                        "type": "vex_genesis",
                        "distribution": "foundation",
                    }
                ),
                Transaction(
                    sender="0x0",
                    recipient=ecosystem_address,
                    amount=ecosystem_amount,
                    data={
                        "type": "vex_genesis",
                        "distribution": "ecosystem",
                    }
                ),
                Transaction(
                    sender="0x0",
                    recipient=public_sale_address,
                    amount=public_sale_amount,
                    data={
                        "type": "vex_genesis",
                        "distribution": "public_sale",
                    }
                )
            ]

            genesis_block.transactions.extend(vex_transactions)

            # Sign genesis block
            genesis_block.sign_block(genesis_private_key, 1000000)

            # Save to database with proper error handling
            try:
                logger.info("Saving genesis block to database...")
                block_id = BlockRepository.save_block(genesis_block)

                if block_id is None:
                    raise RuntimeError("Failed to save genesis block: block_id is None")

                logger.info(f"Genesis block saved with ID: {block_id}")

                # Save genesis transaction
                logger.info("Saving genesis transaction...")
                tx_id = TransactionRepository.save_transaction(genesis_tx, block_id)

                if tx_id is None:
                    raise RuntimeError("Failed to save genesis transaction: tx_id is None")

                logger.info(f"Genesis transaction saved with ID: {tx_id}")
                logger.info(f"Genesis block created successfully with hash: {genesis_block.hash}")

                return genesis_block

            except Exception as db_error:
                logger.error(f"Database error while saving genesis block: {db_error}")

                # Try to clean up any partial data
                try:
                    with db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM blocks WHERE index = 0')
                        cursor.execute('DELETE FROM transactions WHERE sender = ? AND recipient = ?',
                                    (genesis_tx.sender, genesis_tx.recipient))
                        conn.commit()
                        logger.info("Cleaned up partial genesis data")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup genesis data: {cleanup_error}")

                raise RuntimeError(f"Failed to save genesis block to database: {db_error}") from db_error

        except Exception as e:
            logger.error(f"Failed to create genesis block: {e}")
            raise RuntimeError(f"Genesis block creation failed: {e}") from e

    def load_chain(self) -> List[Block]:
        chain = []
        block_count = BlockRepository.get_block_count()

        for index in range(block_count):
            block = BlockRepository.get_block_by_index(index)
            if not block:
                logger.error(f"Invalid block at index {index}")
                return []

            chain.append(block)

        if not chain or not Consensus.is_chain_valid(chain):
            logger.error("Loaded chain is invalid")
            return []

        logger.info(f"Successfully loaded chain with {len(chain)} blocks")
        return chain

    def add_block(self, block: Block, transactions: List[Transaction] = None,
              validator_private_key: ec.EllipticCurvePrivateKey = None,
              external_block: Block = None,
              selected_validator_address: str = None) -> Optional[Block]:
        """
        Add a new block to the blockchain
        """
        if external_block:
            block_to_add = external_block
        else:
            block_to_add = block

        # Get the last block
        last_block = self.get_last_block()
        if not last_block:
            logger.error("Cannot add block: no last block found.")
            return None

        # Validate block structure
        if not block_to_add.is_valid(last_block):
            logger.error(f"Invalid block structure: {block_to_add.hash}")
            return None

        # Verify block signature
        if not block_to_add.verify_signature():
            logger.error(f"Invalid signature for block: {block_to_add.hash}")
            return None

        # Initialize state database and VM
        state_db = StateDB()
        vm = SmartContractVM(state_db)

        # Process transactions
        for tx in block_to_add.transactions:
            # Validate transaction
            if not tx.is_valid():
                logger.error(f"Invalid transaction in block: {tx.tx_hash}")
                return None

            # Check nonce
            sender_nonce = state_db.get_nonce(tx.sender)
            if tx.nonce != sender_nonce + 1:
                logger.error(f"Invalid nonce for tx {tx.tx_hash}")
                return None

            # Handle different transaction types
            if tx.contract_type == "NORMAL":
                # Regular VEX coin transfer
                sender_balance = state_db.get_balance(tx.sender)
                total_deduct = tx.amount + getattr(tx, 'fee', 0)

                if sender_balance < total_deduct:
                    logger.error(f"Insufficient VEX balance for {tx.sender}")
                    return None

                # Deduct amount + fee from sender
                state_db.update_balance(tx.sender, sender_balance - total_deduct)

                # Add amount to recipient
                recipient_balance = state_db.get_balance(tx.recipient)
                state_db.update_balance(tx.recipient, recipient_balance + tx.amount)

                # Increment sender's nonce
                state_db.increment_nonce(tx.sender)

            elif tx.contract_type == "CONTRACT":
                # Smart contract execution
                logger.info(f"Executing smart contract tx: {tx.tx_hash[:8]}")
                success, result = vm.execute(
                    tx,
                    block_to_add.index,
                    block_to_add.timestamp
                )

                if success:
                    logger.info(f"Contract executed successfully. Result: {result}")
                    tx.contract_output = result
                else:
                    logger.error(f"Contract execution failed: {result}")
                    return None

            elif tx.contract_type == "VEX_REWARD":
                # VEX block reward transaction (mint new VEX)
                recipient_balance = state_db.get_balance(tx.recipient)
                state_db.update_balance(tx.recipient, recipient_balance + tx.amount)

            elif tx.contract_type == "VEX_STAKE":
                # VEX staking transaction
                sender_balance = state_db.get_balance(tx.sender)
                if sender_balance < tx.amount:
                    logger.error(f"Insufficient VEX balance for staking: {tx.sender}")
                    return None

                # Move VEX to staking contract
                state_db.update_balance(tx.sender, sender_balance - tx.amount)
                staking_balance = state_db.get_balance(tx.recipient)
                state_db.update_balance(tx.recipient, staking_balance + tx.amount)

                # Update validator stake
                StakeManager.stake(tx.sender, tx.amount, ValidatorRegistry.get_public_key_pem(tx.sender))

            else:
                logger.error(f"Unknown transaction type: {tx.contract_type}")
                return None

        # Save block to database
        try:
            block_id = BlockRepository.save_block(block_to_add)
            TransactionRepository.save_transactions_bulk(block_to_add.transactions, block_id)

            # Update in-memory chain and cache
            self.chain.append(block_to_add)
            self.last_block = block_to_add
            self.block_cache.put(block_to_add.index, block_to_add)

            logger.info(f"Block #{block_to_add.index} added: {block_to_add.hash[:10]}...")

            # Distribute VEX rewards to validator
            self._distribute_vex_rewards(block_to_add)

            # Broadcast the block if it's a local block
            if not external_block and hasattr(self, 'p2p_network') and self.p2p_network:
                try:
                    self.p2p_network.broadcast_block(block_to_add)
                except Exception as e:
                    logger.error(f"Block broadcast failed: {e}")
                    self._save_pending_block(block_to_add)

            return block_to_add
        except Exception as e:
            logger.error(f"Failed to save block: {e}")
            # Clean up if save failed
            if block_to_add in self.chain:
                self.chain.remove(block_to_add)
            return None

    def _distribute_vex_rewards(self, block: Block):
        """Distribute VEX rewards to the block validator"""
        # Calculate reward (example: fixed 10 VEX per block)
        base_reward = 50 # fixed block reward of 50 VEX
        total_fees = sum(getattr(tx, 'fee', 0) for tx in block.transactions if hasattr(tx, 'fee'))
        total_reward = base_reward + total_fees

        reward_tx = Transaction(
            sender="0x0000000000000000000000000000000000000000", # System address
            recipient=block.validator,
            amount=total_reward,
            contract_type="VEX_REWARD",
            data={
                "type": "block_reward",
                "block_index": block.index,
            }
        )

        logger.info(f"Distributing {total_reward} VEX to validator {block.validator} for block #{block.index}")

        # Update Validator balance
        state_db = StateDB()
        validator_balance = state_db.get_balance(block.validator)
        balance = validator_balance + total_reward
        state_db.update_balance(block.validator, balance)

    def _add_external_block(self, block: Block) -> Optional[Block]:
        last_block = self.get_last_block()
        if not last_block:
            logger.error("Cannot add external block: no last block")
            return None

        if not block.is_valid(last_block):
            logger.error(f"Invalid external block received: {block.hash}")
            return None

        if not block.verify_signature():
            logger.error(f"Invalid signature for external block: {block.hash}")
            return None

        for tx in block.transactions:
                sender_nonce = StateDB().get_nonce(tx.sender)
                if tx.nonce != sender_nonce + 1:
                    logger.error(f"Invalid nonce for tx {tx.tx_hash}")
                    return None

                if not tx.is_valid():
                    logger.error(f"Invalid transaction in external block: {tx.tx_hash}")
                    return None

                if tx.contract_type == "NORMAL":
                    sender_balance = StateDB().get_balance(tx.sender)
                    if sender_balance < tx.amount:
                        logger.error(f"Insufficient balance for {tx.sender}")
                        return None


        vm = SmartContractVM(StateDB())
        for tx in block.transactions:
            sender_nonce = StateDB().get_nonce(tx.sender)
            if tx.nonce != sender_nonce + 1:
                logger.error(f"Invalid nonce for tx {tx.tx_hash}")
                return None

            if tx.contract_type != "NORMAL":
                logger.info(f"Executing smart contract tx from external block: {tx.tx_hash[:8]}")

                success, result = vm.execute(
                    tx,
                    block.index,
                    block.timestamp
                )

                if success:
                    logger.info(f"Contract executed successfully. Result: {result}")
                    tx.contract_output = result
                else:
                    logger.error(f"Contract execution failed: {result}")
                    # در یک پیاده‌سازی واقعی، ممکن است بخواهید بلاک را رد کنید

        self.chain.append(block)

        try:
            block_id = BlockRepository.save_block(block)
            TransactionRepository.save_transactions_bulk(block.transactions, block_id)
            logger.info(f"Block #{block.index} added from network: {block.hash[:10]}...")
            return block
        except Exception as e:
            logger.error(f"Failed to save external block: {e}")
            self.chain.pop()
            return None

    def get_last_block(self) -> Optional[Block]:
        if not self.chain:
            return None
        return self.chain[-1]

    def is_chain_valid(self) -> bool:
        return Consensus.is_chain_valid(self.chain)

    def resolve_conflicts(self, nodes: List[str]) -> bool:
        logger.info("Resolving conflicts with network nodes...")

        new_chain = None
        max_cumulative_diff = Consensus.cumulative_difficulty(self.chain)

        if new_chain and Consensus.is_chain_valid(new_chain):
            if Consensus.cumulative_difficulty(new_chain) > max_cumulative_diff:
                self.chain = new_chain
                logger.info("Chain replaced with longer valid chain")
                return True

        logger.info("Current chain remains authoritative")
        return False

    def get_blocks_paginated(self, page: int = 1, per_page: int = 10) -> List[Block]:
        return BlockRepository.get_blocks_paginated(page, per_page)

    def _save_pending_block(self, block):
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pending_blocks (block_data)
                VALUES (?)
            ''', (json.dumps(block.to_dict()),))
            conn.commit()

    def _create_new_block(self, transactions: List[Transaction],
                 validator_private_key: ec.EllipticCurvePrivateKey,
                 selected_validator_address: str = None) -> Optional[Block]:

        # Get Our Node's Address
        our_address = ValidatorRegistry.get_validator_address(validator_private_key)

        # Only proceed if we are the selected validator
        if our_address != selected_validator_address:
            logger.error(f"Not the selected validator. Expected: {selected_validator_address}, Our: {our_address}")
            return None

        if not transactions:
            logger.warning("Cannot add empty block")
            return None

        last_block = self.get_last_block()
        if not last_block:
            logger.error("Chain not initialized")
            return None

        vm = SmartContractVM(StateDB())
        successful_txs = []
        for tx in transactions:
            if tx.contract_type != "NORMAL":
                logger.info(f"Executing smart contract tx: {tx.tx_hash[:8]}")
                success, result = vm.execute(
                    tx,
                    last_block.index + 1,
                    time.time()
                )
                if success:
                    logger.info(f"Contract executed successfully. Result: {result}")
                    tx.contract_output = result
                    successful_txs.append(tx)
                else:
                    logger.error(f"Contract execution failed: {result}")
            else:
                successful_txs.append(tx)

        if not successful_txs:
            logger.warning("No valid transactions to include in block")
            return None

        if selected_validator_address:
            validator_address = selected_validator_address
            stake = ValidatorRegistry.get_validator_stake(validator_address)
        else:
            validator_address = ValidatorRegistry.get_validator_address(validator_private_key)
            stake = ValidatorRegistry.get_validator_stake(validator_address)

        if stake <= 0:
            logger.error(f"Validator {validator_address} has no stake or not registered in DB")
            return None

        new_block = Block(
            index=last_block.index + 1,
            timestamp=int(time.time()),
            transactions=successful_txs,
            previous_hash=last_block.hash,
            validator=validator_address,
            stake_amount=stake,
            difficulty=self.difficulty
        )

        new_block.sign_block(validator_private_key, stake)

        try:
            block_id = BlockRepository.save_block(new_block)
            TransactionRepository.save_transactions_bulk(successful_txs, block_id)
            self.chain.append(new_block)

            logger.info(f"Block #{new_block.index} added to chain: {new_block.hash[:10]}...")

            if hasattr(self, 'p2p_network') and self.p2p_network:
                try:
                    self.p2p_network.broadcast_block(new_block)
                except Exception as e:
                    logger.error(f"Block broadcast failed: {e}")
                    self._save_pending_block(new_block)

            return new_block

        except Exception as e:
            logger.error(f"Failed to save block: {e}")
            if new_block in self.chain:
                self.chain.remove(new_block)
            return None
