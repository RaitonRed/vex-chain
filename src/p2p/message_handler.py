import json
from src.blockchain.block import Block
from src.blockchain.transaction import Transaction
from src.utils.logger import logger

class MessageHandler:
    def __init__(self, network, blockchain, mempool):
        self.network = network
        self.blockchain = blockchain
        self.mempool = mempool
    
    def handle_message(self, message, addr):
        """Handle incoming messages from peers"""
        try:
            msg_type = message.get("type")
            if not msg_type:
                logger.error("Received message without type")
                return

            if msg_type == "get_blockchain":
                self.handle_get_blockchain(addr)
            elif msg_type == "blockchain":
                self.handle_blockchain(message.get("data", []))
            elif msg_type == "get_mempool":
                self.handle_get_mempool(addr)
            elif msg_type == "mempool":
                self.handle_mempool(message.get("data", []))
            elif msg_type == "new_block":
                self.handle_new_block(message.get("data", {}))
            elif msg_type == "new_transaction":
                self.handle_new_transaction(message.get("data", {}))
            elif msg_type == "get_peers":
                self.handle_get_peers(addr)
            elif msg_type == "peers":
                peers = message.get("data", [])
                if peers:
                    self.network.peer_discovery.handle_peers_response(peers)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling message from {addr}: {e}")

    def handle_get_blockchain(self, addr):
        """Send blockchain to requesting peer"""
        try:
            chain_data = [block.to_dict() for block in self.blockchain.chain]
            self.network.send_message({
                "type": "blockchain",
                "data": chain_data
            }, addr)
        except Exception as e:
            logger.error(f"Error sending blockchain to {addr}: {e}")

    def handle_blockchain(self, chain_data):
        """Process received blockchain"""
        if not chain_data:
            logger.error("Empty blockchain received")
            return

        try:
            received_chain = [Block.from_dict(block) for block in chain_data]
            
            if (self.blockchain.is_chain_valid(received_chain) and 
                len(received_chain) > len(self.blockchain.chain)):
                self.blockchain.chain = received_chain
                logger.info("Blockchain replaced with longer valid chain")
        except Exception as e:
            logger.error(f"Error processing blockchain: {e}")

    def handle_get_mempool(self, addr):
        """Send mempool to requesting peer"""
        try:
            mempool_data = [tx.to_dict() for tx in self.mempool.transactions.values()]
            self.network.send_message({
                "type": "mempool",
                "data": mempool_data
            }, addr)
        except Exception as e:
            logger.error(f"Error sending mempool to {addr}: {e}")

    def handle_mempool(self, mempool_data):
        """Process received mempool"""
        if not mempool_data:
            logger.warning("Empty mempool received")
            return

        try:
            for tx_data in mempool_data:
                tx = Transaction.from_dict(tx_data)
                if tx.tx_hash not in self.mempool.transactions:
                    self.mempool.add_transaction(tx)
        except Exception as e:
            logger.error(f"Error processing mempool: {e}")

    def handle_new_block(self, block_data):
        """Process new block from network"""
        if not block_data:
            logger.error("Empty block data received")
            return

        try:
            block = Block.from_dict(block_data)
            last_block = self.blockchain.get_last_block()
            
            if block.index > last_block.index and block.is_valid(last_block):
                if self.blockchain.add_block([], validator_private_key=None, external_block=block):
                    logger.info(f"Added new block #{block.index} from network")
                    
                    # Remove transactions from mempool
                    tx_hashes = [tx.tx_hash for tx in block.transactions]
                    self.mempool.remove_transactions(tx_hashes)
        except Exception as e:
            logger.error(f"Error processing new block: {e}")

    def handle_new_transaction(self, tx_data):
        """Process new transaction from network"""
        if not tx_data:
            logger.error("Empty transaction data received")
            return

        try:
            tx = Transaction.from_dict(tx_data)
            if tx.tx_hash not in self.mempool.transactions:
                self.mempool.add_transaction(tx)
                logger.info(f"Added new transaction from network: {tx.tx_hash[:8]}")
        except Exception as e:
            logger.error(f"Error processing new transaction: {e}")

    def handle_get_peers(self, addr):
        """Send peer list to requesting peer"""
        try:
            self.network.send_message({
                "type": "peers",
                "data": list(self.network.peers)
            }, addr)
        except Exception as e:
            logger.error(f"Error sending peers to {addr}: {e}")