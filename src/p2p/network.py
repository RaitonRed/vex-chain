import socket
import threading
import json
import time
from src.p2p.message_handler import MessageHandler
from src.p2p.peer_discovery import PeerDiscovery
from src.blockchain.chain import Blockchain
from src.utils.logger import logger


class P2PNetwork:
    def __init__(self, host, port, blockchain: Blockchain):
        self.host = host
        self.port = port
        self.blockchain = blockchain
        self.mempool = None
        self.peers = set()
        self.peer_discovery = PeerDiscovery(self)
        self.message_handler = MessageHandler(self, blockchain, self.mempool)
        
        # Start listening socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(5)
        
        logger.info(f"P2P node listening on {host}:{port}")
        
        # Start threads
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.peer_discovery.start, daemon=True).start()
    
    def is_listening(self):
        """Check if the node is listening for connections"""
        return hasattr(self, 'socket') and self.socket is not None

    def set_blockchain(self, blockchain):
        """Set blockchain reference after initialization"""
        self.blockchain = blockchain
        self.message_handler.blockchain = blockchain

    def set_mempool(self, mempool):
        """Set MemPool reference after initialization"""
        self.mempool = mempool
        if self.message_handler:
            self.message_handler.mempool = mempool

    def listen_for_peers(self):
        """Listen for incoming peer connections"""
        while True:
            try:
                conn, addr = self.socket.accept()
                logger.info(f"New connection from {addr}")
                threading.Thread(
                    target=self.handle_peer_connection, 
                    args=(conn, addr),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
    
    def handle_peer_connection(self, conn, addr):
        """Handle messages from a peer connection"""
        with conn:
            while True:
                try:
                    # Receive message length (first 10 bytes)
                    raw_length = conn.recv(10)
                    if not raw_length:
                        break
                    
                    # Receive actual message
                    length = int(raw_length.decode().strip())
                    data = conn.recv(length)
                    if not data:
                        break
                    
                    # Process message
                    message = json.loads(data.decode())
                    self.message_handler.handle_message(message, addr)
                except Exception as e:
                    logger.error(f"Error handling peer connection: {e}")
                    break
    
    def connect_to_peer(self, host, port):
        """Connect to a new peer"""
        if (host, port) == (self.host, self.port):
            return  # Don't connect to self
        
        if (host, port) in self.peers:
            return  # Already connected
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            self.peers.add((host, port))
            logger.info(f"Connected to peer {host}:{port}")
            
            # Start thread to listen to this peer
            threading.Thread(
                target=self.handle_peer_connection, 
                args=(sock, (host, port)),
                daemon=True
            ).start()
            
            # Request blockchain and mempool
            self.send_message({"type": "get_blockchain"}, (host, port))
            self.send_message({"type": "get_mempool"}, (host, port))
            
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
    
    def broadcast_message(self, message):
        """Broadcast a message to all peers"""
        for peer in list(self.peers):
            try:
                self.send_message(message, peer)
            except Exception as e:
                logger.error(f"Error broadcasting to {peer}: {e}")
                self.peers.discard(peer)
    
    def send_message(self, message, peer):
        """Send a message to a specific peer"""
        host, port = peer
        try:
            data = json.dumps(message).encode()
            length = f"{len(data):<10}".encode()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.sendall(length + data)
            sock.close()
        except Exception as e:
            logger.error(f"Error sending message to {peer}: {e}")
            self.peers.discard(peer)
    
    def broadcast_block(self, block):
        """Broadcast a new block to the network"""
        self.broadcast_message({
            "type": "new_block",
            "data": block.to_dict()
        })
    
    def broadcast_transaction(self, transaction):
        """Broadcast a new transaction to the network"""
        self.broadcast_message({
            "type": "new_transaction",
            "data": transaction.to_dict()
        })
    
    def sync_blockchain(self):
        """Sync blockchain with a random peer"""
        if not self.peers:
            return
        
        peer = list(self.peers)[0]
        self.send_message({
            "type": "get_blockchain"
        }, peer)
    
    def sync_mempool(self):
        """Sync mempool with a random peer"""
        if not self.peers:
            return
        
        peer = list(self.peers)[0]
        self.send_message({
            "type": "get_mempool"
        }, peer)