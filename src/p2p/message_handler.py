import json
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

class MessageHandler:
    def __init__(self, network, blockchain, mempool):
        self.network = network
        self.blockchain = blockchain
        self.mempool = mempool
    
    def handle_message(self, message, addr, block_data):
        """Handle incoming messages from peers"""
        try:
            msg_type = message["type"]

                    # Validate and add block
            last_block = self.blockchain.get_last_block()
            if Block.index > last_block.index:
                if self.blockchain.add_block([], validator_private_key=None, external_block=Block):
                    logger.info(f"Added new block #{Block.index} from network")
                
                    # Broadcast to other peers
                    self.network.broadcast_message({
                        "type": "new_block",
                        "data": block_data
                    })
            
                if msg_type == "get_blockchain":
                    self.handle_get_blockchain(addr)
                elif msg_type == "blockchain":
                    self.handle_blockchain(message["data"])
                elif msg_type == "get_mempool":
                    self.handle_get_mempool(addr)
                elif msg_type == "mempool":
                    self.handle_mempool(message["data"])
                elif msg_type == "new_block":
                    self.handle_new_block(message["data"])
                elif msg_type == "new_transaction":
                    self.handle_new_transaction(message["data"])
                elif msg_type == "get_peers":
                    self.handle_get_peers(addr)
                elif msg_type == "peers":
                    self.network.peer_discovery.handle_peers_response(message["data"])
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
        except Exception as e:
            logger.error(f"Error handling message from {addr}: {e}")
    
    def handle_get_blockchain(self, addr):
        """Send blockchain to requesting peer"""
        chain_data = [block.to_dict() for block in self.blockchain.chain]
        self.network.send_message({
            "type": "blockchain",
            "data": chain_data
        }, addr)
    
    def handle_blockchain(self, chain_data):
        """Process received blockchain"""
        try:
            # Convert to Block objects
            from src.blockchain.block import Block
            received_chain = [Block.from_dict(block) for block in chain_data]
            
            # Validate and replace if longer and valid
            if self.blockchain.is_chain_valid(received_chain) and len(received_chain) > len(self.blockchain.chain):
                self.blockchain.chain = received_chain
                logger.info("Blockchain replaced with longer valid chain")
        except Exception as e:
            logger.error(f"Error processing blockchain: {e}")
    
    def handle_get_mempool(self, addr):
        """Send mempool to requesting peer"""
        mempool_data = [tx.to_dict() for tx in self.mempool.transactions.values()]
        self.network.send_message({
            "type": "mempool",
            "data": mempool_data
        }, addr)
    
    def handle_mempool(self, mempool_data):
        """Process received mempool"""
        try:
            # Convert to Transaction objects
            for tx_data in mempool_data:
                tx = Transaction.from_dict(tx_data)
                if tx.tx_hash not in self.mempool.transactions:
                    self.mempool.add_transaction(tx)
        except Exception as e:
            logger.error(f"Error processing mempool: {e}")
    
    def handle_new_block(self, block_data):
        """Process new block from network"""
        try:
            from src.blockchain.block import Block
            block = Block.from_dict(block_data)
            
            # Validate block
            last_block = self.blockchain.get_last_block()
            if block.index > last_block.index:
                # Add to blockchain if valid
                if self.blockchain.add_block([], validator_private_key=None, external_block=block):
                    logger.info(f"Added new block #{block.index} from network")
                    
                    # Remove transactions from mempool
                    tx_hashes = [tx.tx_hash for tx in block.transactions]
                    self.mempool.remove_transactions(tx_hashes)
        except Exception as e:
            logger.error(f"Error processing new block: {e}")
    
    def handle_new_transaction(self, tx_data):
        """Process new transaction from network"""
        try:
            tx = Transaction.from_dict(tx_data)
            if tx.tx_hash not in self.mempool.transactions:
                self.mempool.add_transaction(tx)
                logger.info(f"Added new transaction from network: {tx.tx_hash[:8]}")
        except Exception as e:
            logger.error(f"Error processing new transaction: {e}")
    
    def handle_get_peers(self, addr):
        """Send peer list to requesting peer"""
        self.network.send_message({
            "type": "peers",
            "data": list(self.network.peers)
        }, addr)