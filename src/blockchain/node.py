import time
import threading
from src.blockchain.chain import Blockchain
from src.blockchain.mempool import Mempool
from src.p2p.network import P2PNetwork
from src.api.server import app as flask_app
from src.utils.service_monitor import ServiceMonitor
from src.utils.logger import logger

class BlockchainNode:
    def __init__(self, host='0.0.0.0', p2p_port=6000, api_port=5000):
        """Initialize blockchain node with all core components"""
        self.host = host
        self.p2p_port = p2p_port
        self.api_port = api_port
        
        # Core components
        self.blockchain = Blockchain()
        self.mempool = Mempool()
        self.p2p_network = P2PNetwork(
            host=host,
            port=p2p_port,
            blockchain=self.blockchain
        )
        
        # Service monitoring
        self.monitor = ServiceMonitor()
        self._services_ready = threading.Event()
        self._running = False

        # Set cross-references
        self._setup_dependencies()

    def _setup_dependencies(self):
        """Establish cross-references between components"""
        self.mempool.p2p_network = self.p2p_network
        self.p2p_network.set_mempool(self.mempool)
        self.blockchain.set_p2p_network(self.p2p_network)

    def start(self):
        """Start all node services"""
        if self._running:
            logger.warning("Node is already running!")
            return

        self._running = True
        logger.info("Starting node services...")

        # Start services in separate threads
        self._start_p2p_service()
        self._start_api_service()
        self._start_monitoring()

        logger.info(f"Node services started on {self.host}")

    def _start_p2p_service(self):
        """Start P2P network service"""
        self.p2p_thread = threading.Thread(
            target=self._run_p2p_service,
            daemon=True
        )
        self.p2p_thread.start()

    def _run_p2p_service(self):
        """P2P service execution with error handling"""
        try:
            self.p2p_network.listen_for_peers()
            logger.info("P2P service started successfully")
        except Exception as e:
            logger.error(f"P2P service failed: {e}")
            self.stop()

    def _start_api_service(self):
        """Start API server"""
        self.api_thread = threading.Thread(
            target=self._run_api_service,
            daemon=True
        )
        self.api_thread.start()

    def _run_api_service(self):
        """API service execution with error handling"""
        try:
            flask_app.config['node'] = self  # Make node accessible to API
            flask_app.run(
                host=self.host,
                port=self.api_port,
                debug=False,
                use_reloader=False
            )
            logger.info("API service started successfully")
        except Exception as e:
            logger.error(f"API service failed: {e}")
            self.stop()

    def _start_monitoring(self):
        """Start health monitoring service"""
        self.health_thread = threading.Thread(
            target=self._monitor_services,
            daemon=True
        )
        self.health_thread.start()

    def _monitor_services(self):
        """Continuously check service health"""
        while self._running:
            try:
                services_ready = all([
                    self._check_blockchain(),
                    self._check_p2p(),
                    self._check_api()
                ])
                
                if services_ready:
                    self._services_ready.set()
                else:
                    self._services_ready.clear()
                    
                time.sleep(1)
            except Exception as e:
                logger.error(f"Monitoring failed: {e}")
                break

    def _check_blockchain(self):
        """Check blockchain service health"""
        return (
            hasattr(self, 'blockchain') and 
            self.blockchain is not None and
            len(self.blockchain.chain) > 0
        )

    def _check_p2p(self):
        """Check P2P network health"""
        return (
            hasattr(self, 'p2p_network') and
            self.p2p_network is not None and
            hasattr(self.p2p_network.socket, 'fileno')
        )

    def _check_api(self):
        """Check API service health"""
        return (
            hasattr(self, 'api_thread') and
            self.api_thread.is_alive()
        )

    def wait_for_services(self, timeout=30):
        """Wait for essential services to become ready"""
        logger.info("Waiting for services to start...")
        return self._services_ready.wait(timeout=timeout)

    def is_ready(self):
        """Check if all services are operational"""
        return self._services_ready.is_set()

    def stop(self):
        """Gracefully shutdown the node"""
        if not self._running:
            return

        self._running = False
        logger.info("Shutting down node...")
        
        # Additional cleanup can be added here
        if hasattr(self, 'p2p_network') and self.p2p_network:
            self.p2p_network.socket.close()
        
        logger.info("Node shutdown complete")