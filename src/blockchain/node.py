import os
import json
import time
import threading
from src.blockchain.consensus.consensus import Consensus
from src.blockchain.chain import Blockchain
from src.blockchain.mempool import Mempool
from src.p2p.network import P2PNetwork
from src.api.api_server import app as flask_app
from src.utils.logger import logger
from src.wallet.wallet import Wallet
from src.utils.database import init_db
from src.blockchain.consensus.stake_manager import StakeManager

class BlockchainNode:
    def __init__(self, host='0.0.0.0', p2p_port=6000, api_port=5000):
        self.host = host
        self.p2p_port = p2p_port
        self.api_port = api_port

        # Initialize core modules first
        self.blockchain = Blockchain()
        self.mempool = Mempool()
        self.wallet = Wallet(self)
        self.consensus = Consensus(self.blockchain, stake_manager=StakeManager())
        self.p2p_network = P2PNetwork(host, p2p_port, self.blockchain)  # Use initialized blockchain

        modules = {
            'blockchain': self.blockchain,
            'mempool': self.mempool,
            'wallet': self.wallet,
            'consensus': self.consensus,
            'p2p_network': self.p2p_network
        }

        self.modules = modules

        # Inject dependencies Manualy (Automatic had error)
        self.mempool.blockchain = self.blockchain
        self.wallet.blockchain = self.blockchain
        self.consensus.blockchain = self.blockchain
        self.p2p_network.blockchain = self.blockchain
        self.blockchain.p2p_network = self.p2p_network

        # Additional setup
        self.mempool.p2p_network = self.p2p_network
        self.p2p_network.set_mempool(self.mempool)

        # Create Node-specific  data directory
        self.data_dir = f"data/node_{p2p_port}"
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize node wallet
        self.node_wallet_path = os.path.join(self.data_dir, 'wallet.json')
        self._init_node_wallet()

        # Register validator
        self._register_as_validator()

        self.p2p_thread = None
        self.api_thread = None
        self.health_thread = None
        self.api_server = flask_app
        # self.api_server.config['node'] = self  # Inject node into Flask app context
        self.monitor = None
        self._services_ready = threading.Event()
        self._running = False

    def _init_node_wallet(self):
        """Initialize node's wallet if it doesn't exist"""
        if not os.path.exists(self.node_wallet_path):
            password = 12345 # This is For test comment it
            # password = os.getenv("NODE_WALLET_PASSWORD", "default_password")
            address, private_key = self.wallet.create_account(
                f"node_{self.p2p_port}",
                password
            )

            node_wallet_data = {
                'address': address,
                'private_key': private_key,
                'password': password,
                'public_key': self.wallet.accounts[f"node_{self.p2p_port}"]['public_key']
            }

            with open(self.node_wallet_path, 'w') as f:
                json.dump(node_wallet_data, f, indent=2)

            logger.info(f"Created node wallet: {address}")
        else:
            # Load existing node wallet
            with open(self.node_wallet_path, 'r') as f:
                node_wallet_data = json.load(f)

            # Import into main wallet
            self.wallet.import_private_key(
                f"node_{self.p2p_port}",
                node_wallet_data['privare_key'],
                password=1234
            )
            logger.info(f"Loaded existing node wallet: {node_wallet_data['address']}")

    def _register_as_validator(self):
        """Register node as validator eith its stake"""
        node_account = self.wallet.accounts.get(f"node_{self.p2p_port}")
        if not node_account:
            logger.error("Node wallet not found")
            return

        address = node_account['address']
        public_key_pem = node_account['public_key']

        # Auto-stake a fixed amount (e.g., 1000 coins)
        stake_amount = 1000.0

        # Check if already registered
        existing_stake = StakeManager.get_validator_stake(address)
        if existing_stake > 0:
            logger.info(f"Node already registered as validator with stake: {existing_stake}")
            return

        # Register validator
        try:
            tx_id = StakeManager.stake(
                address,
                stake_amount,
                public_key_pem
            )
            if tx_id:
                logger.info(f"Node registered as validator with stake {stake_amount}. TX: {tx_id}")
            else:
                logger.error("Failed to register node as validator")
        except Exception as e:
            logger.error(f"Validator registration failed: {e}")

    def _start_api_service(self):
        try:
            # Setting up the node instance in the Flask application
            flask_app.config['node'] = self

            # Creating a thread for the API service
            self.api_thread = threading.Thread(
                target=self._run_api_service,
                daemon=True,
                name="API_Service"
            )
            self.api_thread.start()
            logger.info("API service thread started")
        except Exception as e:
            logger.error(f"Failed to start API thread: {e}")
            self.stop()

    def _run_api_service(self):
        try:
            logger.info(f"Starting API server on {self.host}:{self.api_port}")

            # Use Waitress server if installed
            try:
                from waitress import serve
                serve(flask_app, host=self.host, port=self.api_port)
                return
            except ImportError:
                logger.warning("Waitress not installed, using Flask development server")

            # Using the Flask development server
            flask_app.run(
                host=self.host,
                port=self.api_port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"API service runtime error: {e}")
            self.stop()

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

            logger.info("initializing database...")
            init_db()

            # Launching modules
            for name, module in self.modules.items():
                if hasattr(module, 'initialize'):
                    logger.info(f"Initializing {name} module...")
                    module.initialize()
                if hasattr(module, 'start'):
                    logger.info(f"Starting {name} module...")
                    module.start()

            self._start_p2p_service()
            self._start_api_service()

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
            # Checking for the existence of p2p_network before calling
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
        """wait to all services ready"""
        logger.info("Waiting for services to start...")
        return self._services_ready.wait(timeout=timeout)

    def is_ready(self):
        return self._services_ready.is_set()

    def stop(self):
        if not self._running:
            return

        self._running = False
        logger.info("Shutting down node...")

        # Stop P2P network first
        if self.p2p_network is not None:
            self.p2p_network.stop()
            logger.info("P2P network stopped")

        # Give services time to shut down
        time.sleep(1)

        logger.info("Node shutdown complete")
