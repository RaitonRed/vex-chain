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
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding
import time
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from src.blockchain.block import Block
from src.blockchain.consensus.validator_registry import ValidatorRegistry
from src.blockchain.consensus.stake_manager import StakeManager
from src.utils.database import db_connection
from src.utils.crypto import generate_ecc_key_pair, sign_message, verify_signature

from src.utils.database import db_connection


class Blockchain:
    def __init__(self, difficulty: int = 4):
        self.difficulty = difficulty
        self.chain = []
        self.p2p_network = None

        if not hasattr(self, '_db_initialized'):
            try:
                from src.utils.database import init_db
                init_db()
                self._db_initialized = True
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise

        self.chain = self.load_chain()
        if not self.chain:
            logger.info("No valid chain found, initializing new blockchain")
            self._initialize_new_chain()
        elif not Consensus.is_chain_valid(self.chain):
            logger.warning("Invalid chain detected, resetting database...")
            self._reset_blockchain()
            self._initialize_new_chain()

    def set_p2p_network(self, p2p_network):
        """Set P2P network reference after initialization"""
        self.p2p_network = p2p_network

    def _initialize_new_chain(self):
        """مقداردهی اولیه یک زنجیره جدید بدون ریست دیتابیس"""
        logger.info("Initializing new blockchain")
        try:
            # ایجاد بلاک جنسیس
            genesis_block = self._create_genesis_block()
            self.chain = [genesis_block]
            logger.info("New blockchain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize new chain: {e}")
            raise RuntimeError("Failed to initialize blockchain") from e


    def _create_genesis_block(self) -> Block:
        """
        این متد بلاک اولیه (Genesis Block) را تولید می‌کند.
        در این متد، کلید عمومی از کلید خصوصی استخراج شده و به فرمت
        PEM تبدیل می‌شود تا بتوانیم آدرس ولیدیتور را به صورت قطعی از آن بسازیم.
        """
        genesis_private_key = self._get_genesis_private_key()

        genesis_public_key = genesis_private_key.public_key()

        genesis_public_key_pem = genesis_public_key.public_bytes(
            Encoding.PEM,
            PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        validator_address = ValidatorRegistry.get_validator_address(genesis_public_key_pem)
        
        genesis_stake = StakeManager.get_validator_stake(validator_address)

        genesis_block = Block(
            index=0,
            timestamp=int(time.time()),
            transactions=[],
            previous_hash="0",
            validator=validator_address,
            stake_amount=genesis_stake,
            difficulty=self.difficulty
        )

        genesis_block.sign_block(genesis_private_key, genesis_stake)

        return genesis_block

    def load_chain(self) -> List[Block]:
        """بارگذاری زنجیره از دیتابیس"""
        chain = []
        block_count = BlockRepository.get_block_count()
        
        for index in range(block_count):
            block = BlockRepository.get_block_by_index(index)
            if not block:
                logger.error(f"Invalid block at index {index}")
                return []
                
            chain.append(block)
        
        # اعتبارسنجی زنجیره بارگذاری شده
        if not chain or not Consensus.is_chain_valid(chain):
            logger.error("Loaded chain is invalid")
            return []
            
        logger.info(f"Successfully loaded chain with {len(chain)} blocks")
        return chain
    
    def add_block(self, transactions: List[Transaction], 
             validator_private_key: ec.EllipticCurvePrivateKey = None,
             external_block: Block = None) -> Optional[Block]:
        """
        اضافه کردن بلاک جدید به زنجیره
        - اگر external_block ارائه شده باشد، بلاک از شبکه دریافت شده است
        - در غیر این صورت، بلاک محلی ایجاد می‌شود
        """
        # حالت 1: بلاک از شبکه دریافت شده است
        if external_block:
            return self._add_external_block(external_block)
        
        # حالت 2: ایجاد بلاک جدید محلی
        new_block = self._create_new_block(transactions, validator_private_key)
        if new_block:
            if hasattr(self, 'p2p_network') and self.p2p_network:
                self.p2p_network.broadcast_block(new_block)
    
        return new_block
            
    def _add_external_block(self, block: Block) -> Optional[Block]:
        """اضافه کردن بلاک دریافتی از شبکه"""
        last_block = self.get_last_block()
        if not last_block:
            logger.error("Cannot add external block: no last block")
            return None
            
        # اعتبارسنجی ساختار بلاک
        if not block.is_valid(last_block):
            logger.error(f"Invalid external block received: {block.hash}")
            return None
            
        # اعتبارسنجی امضای بلاک
        if not block.verify_signature():
            logger.error(f"Invalid signature for external block: {block.hash}")
            return None
            
        # اعتبارسنجی تراکنش‌ها
        for tx in block.transactions:
                sender_nonce = StateDB().get_nonce(tx.sender)
                if tx.nonce != sender_nonce + 1:
                    logger.error(f"Invalid nonce for tx {tx.tx_hash}")
                    return None
                
                if not tx.is_valid():
                    logger.error(f"Invalid transaction in external block: {tx.tx_hash}")
                    return None
                
                # بررسی اینکه فرستنده موجودی کافی دارد
                if tx.contract_type == "NORMAL":
                    sender_balance = StateDB().get_balance(tx.sender)
                    if sender_balance < tx.amount:
                        logger.error(f"Insufficient balance for {tx.sender}")
                        return None

        
        # اجرای قراردادهای هوشمند در بلاک دریافتی
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
                    # اما در اینجا فقط خطا را ثبت می‌کنیم
        
        # افزودن بلاک به زنجیره
        self.chain.append(block)
        
        # ذخیره در دیتابیس
        try:
            block_id = BlockRepository.save_block(block)
            TransactionRepository.save_transactions_bulk(block.transactions, block_id)
            logger.info(f"Block #{block.index} added from network: {block.hash[:10]}...")
            return block
        except Exception as e:
            logger.error(f"Failed to save external block: {e}")
            # حذف بلاک از زنجیره اگر ذخیره‌سازی ناموفق بود
            self.chain.pop()
            return None

    def _create_genesis_block(self) -> Block:
        """ایجاد بلاک جنسیس با مکانیزم PoS"""
        genesis_tx = Transaction(
            sender="0",
            recipient="0",
            amount=0,
            data={"type": "genesis", "message": "Initial block of the chain"}
        )
        
        # ایجاد یک کلید خصوصی برای ولیدیتور جنسیس
        genesis_private_key = ec.generate_private_key(ec.SECP256K1())  # تعریف متغیر
        validator_address = ValidatorRegistry.get_validator_address(genesis_private_key)
        
        # تولید کلید عمومی به فرمت PEM
        public_key_pem = genesis_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        # ثبت ولیدیتور جنسیس با سهام اولیه
        ValidatorRegistry.register_validator(
            address=validator_address,
            public_key_pem=public_key_pem,
            stake=1000000  # سهام اولیه بزرگ برای جنسیس
        )
        
        genesis_block = Block(
            index=0,
            timestamp=0,
            transactions=[genesis_tx],
            previous_hash="0",
            validator=validator_address,
            stake_amount=1000000,
            difficulty=self.difficulty,
            nonce=0  # Explicitly set nonce
        )
        
        # امضای بلاک جنسیس
        genesis_block.sign_block(genesis_private_key, 1000000)
        
        # ذخیره در دیتابیس
        try:
            block_id = BlockRepository.save_block(genesis_block)
            TransactionRepository.save_transaction(genesis_tx, block_id)
            logger.info(f"Genesis block created with hash: {genesis_block.hash}")
            return genesis_block
        except Exception as e:
            logger.error(f"Failed to save genesis block: {e}")
            raise
    
    
    def get_last_block(self) -> Optional[Block]:
        """دریافت آخرین بلاک زنجیره"""
        if not self.chain:
            return None
        return self.chain[-1]

    def is_chain_valid(self) -> bool:
        """اعتبارسنجی زنجیره فعلی"""
        return Consensus.is_chain_valid(self.chain)

    def resolve_conflicts(self, nodes: List[str]) -> bool:
        """حل تعارضات با نودهای دیگر (طولانی‌ترین زنجیره معتبر)"""
        logger.info("Resolving conflicts with network nodes...")
        
        new_chain = None
        max_cumulative_diff = Consensus.cumulative_difficulty(self.chain)
        
        # در اینجا معمولاً با نودهای دیگر ارتباط برقرار می‌کنیم
        # برای سادگی، فرض می‌کنیم زنجیره‌های دیگر را دریافت کرده‌ایم
        
        # اگر زنجیره جدیدی با سختی تجمعی بیشتر پیدا شد
        if new_chain and Consensus.is_chain_valid(new_chain):
            if Consensus.cumulative_difficulty(new_chain) > max_cumulative_diff:
                self.chain = new_chain
                logger.info("Chain replaced with longer valid chain")
                return True
                
        logger.info("Current chain remains authoritative")
        return False

    def get_blocks_paginated(self, page: int = 1, per_page: int = 10) -> List[Block]:
        """دریافت بلاک‌ها به صورت صفحه‌بندی شده"""
        return BlockRepository.get_blocks_paginated(page, per_page)
    
    def _save_pending_block(self, block):
        # ذخیره بلوک در صف انتظار برای انتشار مجدد
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pending_blocks (block_data)
                VALUES (?)
            ''', (json.dumps(block.to_dict()),))
            conn.commit()

    def _create_new_block(self, transactions: List[Transaction], 
                     validator_private_key: ec.EllipticCurvePrivateKey) -> Optional[Block]:
        """ایجاد و افزودن بلاک جدید محلی"""
        if not transactions:
            logger.warning("Cannot add empty block")
            return None

        last_block = self.get_last_block()
        if not last_block:
            logger.error("Chain not initialized")
            return None

        # اجرای قراردادهای هوشمند
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

        # دریافت اطلاعات ولیدیتور
        validator_address = ValidatorRegistry.get_validator_address(validator_private_key)
        stake = ValidatorRegistry.get_validator_stake(validator_address)
        
        if stake <= 0:
            logger.error(f"Validator {validator_address} has no stake or not registered in DB")
            return None

        # ایجاد بلاک جدید
        new_block = Block(
            index=last_block.index + 1,
            timestamp=int(time.time()),
            transactions=successful_txs,
            previous_hash=last_block.hash,
            validator=validator_address,
            stake_amount=stake,
            difficulty=self.difficulty
        )

        # امضای بلاک
        new_block.sign_block(validator_private_key, stake)

        # ذخیره در دیتابیس
        try:
            block_id = BlockRepository.save_block(new_block)
            TransactionRepository.save_transactions_bulk(successful_txs, block_id)
            self.chain.append(new_block)
            
            logger.info(f"Block #{new_block.index} added to chain: {new_block.hash[:10]}...")
            
            # انتشار بلاک در شبکه
            if hasattr(self, 'p2p_network') and self.p2p_network:
                try:
                    self.p2p_network.broadcast_block(new_block)
                except Exception as e:
                    logger.error(f"Block broadcast failed: {e}")
                    self._save_pending_block(new_block)
                    
            return new_block
            
        except Exception as e:
            logger.error(f"Failed to save block: {e}")
            # حذف بلاک از زنجیره اگر ذخیره‌سازی ناموفق بود
            if new_block in self.chain:
                self.chain.remove(new_block)
            return None

    def __repr__(self) -> str:
        return f"<Blockchain length={len(self.chain)}, last_block={self.get_last_block()}>"