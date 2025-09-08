import time
import threading
from src.utils.logger import logger
from src.blockchain.consensus.hybrid_consensus import HybridConsensus

class Miner:
    def __init__(self, node, consensus, mining_enabled=True):
        self.node = node
        self.consensus = consensus
        self.mining_enabled = mining_enabled
        self.mining_thread = None
        self.is_mining = False
        
    def start_mining(self):
        """شروع فرآیند ماینینگ در یک thread جداگانه"""
        if not self.mining_enabled:
            logger.info("Mining is disabled for this node")
            return
            
        if self.is_mining:
            logger.warning("Mining is already in progress")
            return
            
        self.is_mining = True
        self.mining_thread = threading.Thread(
            target=self._mining_loop,
            daemon=True,
            name="MiningThread"
        )
        self.mining_thread.start()
        logger.info("Mining started")
        
    def stop_mining(self):
        """توقف فرآیند ماینینگ"""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        logger.info("Mining stopped")
        
    def _mining_loop(self):
        """حلقه اصلی ماینینگ"""
        while self.is_mining and self.mining_enabled:
            try:
                # دریافت تراکنش‌ها از mempool
                transactions = self.node.mempool.get_transactions(10)
                
                if not transactions:
                    time.sleep(1)
                    continue
                    
                # انتخاب ولیدیتور برای این بلوک
                validator_address = self.consensus.select_validator()
                if not validator_address:
                    logger.error("No validator available for mining")
                    time.sleep(1)
                    continue
                    
                # ایجاد بلوک جدید
                new_block = self.consensus.create_block(
                    transactions, 
                    self.node.node_wallet, 
                    validator_address
                )
                
                if new_block and self.consensus.validate_block(new_block):
                    # افزودن بلوک به زنجیره
                    if self.node.blockchain.add_block(new_block):
                        logger.info(f"Mined new block #{new_block.index}")
                        # حذف تراکنش‌های پردازش شده از mempool
                        self.node.mempool.remove_transactions(
                            [tx.tx_hash for tx in transactions]
                        )
                        
                        # انتشار بلوک در شبکه
                        if hasattr(self.node, 'p2p_network') and self.node.p2p_network:
                            self.node.p2p_network.broadcast_block(new_block)
                
                time.sleep(0.1)  # جلوگیری از مصرف CPU بالا
                
            except Exception as e:
                logger.error(f"Mining error: {e}")
                time.sleep(1)
                
    def set_mining_enabled(self, enabled):
        """فعال یا غیرفعال کردن ماینینگ"""
        if self.mining_enabled != enabled:
            self.mining_enabled = enabled
            if enabled:
                self.start_mining()
            else:
                self.stop_mining()
                
    def get_mining_status(self):
        """دریافت وضعیت ماینینگ"""
        return {
            'mining_enabled': self.mining_enabled,
            'is_mining': self.is_mining,
            'miner_address': self.node.node_wallet.address if hasattr(self.node, 'node_wallet') else None
        }