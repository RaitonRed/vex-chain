import os
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
        self.host = host
        self.p2p_port = p2p_port
        self.api_port = api_port
        
        self.blockchain = None
        self.mempool = None
        self.p2p_network = None
        
        self.monitor = None
        self._services_ready = threading.Event()
        self._running = False

    def _setup_dependencies(self):
        if self.mempool and self.p2p_network:
            self.mempool.p2p_network = self.p2p_network
        if self.p2p_network and self.mempool:
            self.p2p_network.set_mempool(self.mempool)
        if self.blockchain and self.p2p_network:
            self.blockchain.set_p2p_network(self.p2p_network)

    def start(self):
        if self._running:
            print("⚠️ Node is already running!")
            return False

        try:
            if self.p2p_port < 1024 and os.geteuid() != 0:
                raise PermissionError(f"Port {self.p2p_port} requires root privileges")
            
            print("🟢 Initializing blockchain...")
            self.blockchain = Blockchain()
            
            print("🟢 Initializing mempool...")
            self.mempool = Mempool()
            
            print("🟢 Starting P2P network...")
            self.p2p_network = P2PNetwork(
                host=self.host,
                port=self.p2p_port,
                blockchain=self.blockchain
            )
            
            self._setup_dependencies()
            
            print("🟢 Starting network services...")
            self._start_p2p_service()
            time.sleep(1)
            self._start_api_service()
            time.sleep(1)
            
            self._start_monitoring()
            
            self._running = True
            print("🟢 Node services started successfully")
            return True
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"❌ Port {self.p2p_port} is already in use!")
                print("   Please stop other nodes or use a different port")
            logger.error(f"Startup failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            return False

    def _start_p2p_service(self):
        if self.p2p_network is None:
            logger.error("Cannot start P2P service: p2p_network is None")
            return
            
        self.p2p_thread = threading.Thread(
            target=self._run_p2p_service,
            daemon=True
        )
        self.p2p_thread.start()

    def _run_p2p_service(self):
        try:
            # بررسی وجود p2p_network قبل از فراخوانی
            if self.p2p_network:
                self.p2p_network.listen_for_peers()
                logger.info("P2P service started successfully")
            else:
                logger.error("P2P network is not initialized")
        except Exception as e:
            logger.error(f"P2P service failed: {e}")
            self.stop()

    def _start_api_service(self):
        self.api_thread = threading.Thread(
            target=self._run_api_service,
            daemon=True
        )
        self.api_thread.start()

    def _run_api_service(self):
        try:
            flask_app.config['node'] = self
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
        self.health_thread = threading.Thread(
            target=self._monitor_services,
            daemon=True
        )
        self.health_thread.start()

    def _monitor_services(self):
        logger.info("Starting service monitoring...")
        while self._running:
            try:
                time.sleep(2)
                
                blockchain_ok = self._check_blockchain()
                p2p_ok = self._check_p2p()
                api_ok = self._check_api()
                
                services_ready = all([blockchain_ok, p2p_ok, api_ok])
                
                if services_ready:
                    self._services_ready.set()
                    # logger.info("✅ All services are ready")
                else:
                    self._services_ready.clear()
                    logger.warning("⚠️ Services not ready: "
                                  f"Blockchain: {blockchain_ok}, "
                                  f"P2P: {p2p_ok}, "
                                  f"API: {api_ok}")
                    
                time.sleep(3)
            except Exception as e:
                logger.error(f"Monitoring failed: {e}")
                break

    def _check_blockchain(self):
        return self.blockchain is not None and len(self.blockchain.chain) > 0

    def _check_p2p(self):
        return self.p2p_network is not None and self.p2p_network.is_listening()

    def _check_api(self):
        return self.api_thread is not None and self.api_thread.is_alive()

    def wait_for_services(self, timeout=30):
        """منتظر ماندن برای آماده‌سازی سرویس‌ها"""
        logger.info("Waiting for services to start...")
        return self._services_ready.wait(timeout=timeout)

    def is_ready(self):
        return self._services_ready.is_set()

    def stop(self):
        if not self._running:
            return

        self._running = False
        logger.info("Shutting down node...")
        
        if self.p2p_network is not None:
            self.p2p_network.socket.close()
            logger.info("P2P network stopped")
        
        logger.info("Node shutdown complete")