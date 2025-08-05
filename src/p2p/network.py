import socket
import threading
import json
from src.p2p.message_handler import MessageHandler
from src.p2p.peer_discovery import PeerDiscovery
from src.blockchain.chain import Blockchain
from src.utils.logger import logger
from src.utils.crypto import sign_data, verify_signature

class P2PNetwork:
    def __init__(self, host, port, blockchain: Blockchain):
        self.host = host
        self.port = port
        self.blockchain = blockchain
        self.mempool = None
        self.peers = set()
        self.running = True
        self.peer_discovery = PeerDiscovery(self)
        self.message_handler = MessageHandler(self, blockchain, self.mempool)
        
        # Start listening socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(5)
        self.socket.settimeout(1.0)  # Set timeout to prevent blocking indefinitely
        
        logger.info(f"P2P node listening on {host}:{port}")
        
        # Start threads
        threading.Thread(target=self.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.peer_discovery.start, daemon=True).start()
    
    def is_listening(self):
        """Check if the node is listening for connections"""
        return self.running

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
        while self.running:
            try:
                conn, addr = self.socket.accept()
                logger.info(f"New connection from {addr}")
                conn.settimeout(10.0)  # Set connection timeout
                threading.Thread(
                    target=self.handle_peer_connection, 
                    args=(conn, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue  # Normal timeout, continue listening
            except OSError as e:
                if self.running:
                    logger.error(f"Socket error: {e}")
                break
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
    
    def handle_peer_connection(self, conn, addr):
        """Handle messages from a peer connection"""
        try:

            MAX_MSG_SIZE = 10 * 1024 * 1024  # 10 MB

            with conn:
                peer_id = f"{addr[0]}:{addr[1]}"
                logger.info(f"Handling connection from {peer_id}")
                
                while self.running:
                    try:
                        # Receive message length (first 10 bytes)
                        raw_length = conn.recv(10)
                        if not raw_length:
                            return
                        
                        # Receive actual message
                        length = int(raw_length.decode().strip())
                        data = conn.recv(length)
                        if not data:
                            break

                        if length > MAX_MSG_SIZE:
                            logger.warning(f"Message from {peer_id} exceeds max size: {length} bytes")
                            continue

                        # Parse message
                        message = json.loads(data.decode())
                        
                        # Verify message signature
                        if not self.verify_message(message):
                            logger.warning(f"Invalid message signature from {peer_id}")
                            continue
                        
                        # Process message
                        self.message_handler.handle_message(message, addr)
                    except socket.timeout:
                        # Send keep-alive
                        try:
                            conn.send(b'PING')
                        except:
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from {peer_id}")
                    except Exception as e:
                        logger.error(f"Error handling message from {peer_id}: {e}")
                        break
        except Exception as e:
            logger.error(f"Connection error with {peer_id}: {e}")
        finally:
            logger.info(f"Connection closed with {peer_id}")
            if addr in self.peers:
                self.peers.remove(addr)

    def connect_to_peer(self, host, port):
        """Connect to a new peer"""
        peer = (host, port)
        
        if peer == (self.host, self.port):
            return  # Don't connect to self
        
        if peer in self.peers:
            return  # Already connected
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(peer)
            self.peers.add(peer)
            logger.info(f"Connected to peer {host}:{port}")
            
            # Start thread to listen to this peer
            threading.Thread(
                target=self.handle_peer_connection, 
                args=(sock, peer),
                daemon=True
            ).start()
            
            # Request blockchain and mempool
            self.send_message({"type": "get_blockchain"}, peer)
            self.send_message({"type": "get_mempool"}, peer)
            
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
    
    def broadcast_message(self, message):
        """Broadcast a message to all peers"""
        if not self.peers:
            return
            
        for peer in list(self.peers):
            try:
                self.send_message(message, peer)
            except Exception as e:
                logger.error(f"Error broadcasting to {peer}: {e}")
                # Remove disconnected peer
                if peer in self.peers:
                    self.peers.remove(peer)

    def send_message(self, message, peer):
        """Send a message to a specific peer"""
        host, port = peer
        try:
            # Sign message
            signature = self.sign_message(message)
            message['signature'] = signature
            message['public_key'] = self.public_key_pem

            data = json.dumps(message).encode()
            length = f"{len(data):<10}".encode()
            
            # Create a new socket for each message
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((host, port))
                sock.sendall(length + data)
        except Exception as e:
            logger.error(f"Error sending message to {host}:{port}: {e}")
            # Remove disconnected peer
            if peer in self.peers:
                self.peers.remove(peer)

    def sign_message(self, message):
        data = json.dumps(message, sort_keys=True).encode()
        return sign_data(data, self.blockchain.wallet.private_key)
    
    def verify_message(self, message):
        signature = message.pop('signature')
        public_key_pem = message.pop('public_key')
        data = json.dumps(message, sort_keys=True).encode()
        return verify_signature(data, signature, public_key_pem)
    
    def broadcast_block(self, block):
        """Broadcast a new block to the network"""
        if len(block.transactions) > 10:
            self.broadcast_message({
                "type": "compact_block",
                "data": block.to_compact()
            })
        else:
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
    
    def stop(self):
        """Stop the P2P network"""
        self.running = False
        try:
            if self.socket:
                self.socket.close()
        except:
            pass
        logger.info("P2P network stopped")