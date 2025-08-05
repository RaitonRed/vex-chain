import threading
import time
from src.utils.logger import logger

class PeerDiscovery:
    def __init__(self, network):
        self.network = network
        self.known_peers = set()
        self.bootstrap_nodes = [
            ("localhost", 6000),
            # ("127.0.0.1", 6001)
        ]
        self.min_peers = 1
    
    def start(self):
        """Start peer discovery process"""
        threading.Thread(target=self.discover_peers, daemon=True).start()
    
    def discover_peers(self):
        """Discover new peers periodically"""
        while True:
            try:
                # Connect to bootstrap nodes
                for node in self.bootstrap_nodes:
                    if node not in self.network.peers:
                        self.network.connect_to_peer(*node)
                
                # Ask known peers for their peer lists
                for peer in list(self.network.peers):
                    self.network.send_message({
                        "type": "get_peers"
                    }, peer)
                
                # Sleep for 5 minutes
                time.sleep(300)
            except Exception as e:
                logger.error(f"Error in peer discovery: {e}")
                time.sleep(60)
    
    def handle_peers_response(self, peers):
        """Handle list of peers from another node"""
        for host, port in peers:
            if (host, port) not in self.network.peers and (host, port) != (self.network.host, self.network.port):
                self.network.connect_to_peer(host, port)