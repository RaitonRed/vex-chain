import os
import sys
import time
import threading
import argparse
import json
from src.utils.logger import logger
from src.blockchain.chain import Blockchain
from src.blockchain.mempool import Mempool
from src.p2p.network import P2PNetwork
from src.api.server import app as flask_app
from src.blockchain.stake_manager import StakeManager
from src.blockchain.validator_registry import ValidatorRegistry
from src.blockchain.consensus import Consensus
from src.blockchain.contract.contract_manager import ContractManager
from src.utils.service_monitor import ServiceMonitor
from cryptography.hazmat.primitives.asymmetric import ec

class BlockchainNode:
    def __init__(self, host='0.0.0.0', p2p_port=6000, api_port=5000):
        self.host = host
        self.p2p_port = p2p_port
        self.api_port = api_port
        
        self.monitor = ServiceMonitor()
        self._service_ready = threading.Event()

        # Initialize core components
        self.blockchain = Blockchain()
        self.mempool = Mempool()
        self.p2p_network = P2PNetwork(
            host=host,
            port=p2p_port,
            blockchain=self.blockchain,
        )

        # Service Status
        self.services_ready = {
            'p2p': False,
            'api': False
        }
        
        # Set cross-references
        self.mempool.p2p_network = self.p2p_network
        self.p2p_network.set_mempool(self.mempool)
        self.blockchain.set_p2p_network(self.p2p_network)
        
        # Thread flags
        self._running = False

    def start(self):
        """Start all node services"""
        if self._running:
            logger.warning("Node is already running!")
            return

        self._running = True
        
        # Start P2P network
        self.p2p_thread = threading.Thread(
            target=self.p2p_network.listen_for_peers,
            daemon=True
        )
        self.p2p_thread.start()

        # Start API server
        self.api_thread = threading.Thread(
            target=lambda: flask_app.run(
                host=self.host,
                port=self.api_port,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        self.api_thread.start()

        # Start health monitoring
        self.health_thread = threading.Thread(
            target=self._monitor_services,
            daemon=True
        )
        self.health_thread.start()

        logger.info(f"Node started on {self.host}")
        logger.info(f"P2P Port: {self.p2p_port} | API Port: {self.api_port}")

    def _start_p2p_with_monitoring(self):
        try:
            self.p2p_network.listen_for_peers()
            logger.info("P2P service started successfully")
        except Exception as e:
            logger.error(f"P2P service failed: {e}")
            self.stop()
    
    def _start_api_with_monitoring(self):
        try:
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

    def _monitor_services(self):
        while self._running:
            if self.monitor.check_all_services(self):
                self._service_ready.set()
            else:
                self._service_ready.clear()
            time.sleep(1)

    def wait_for_services(self, timeout=30):
        """Wait for all services to become ready"""
        return self._service_ready.wait(timeout=timeout)

    def is_ready(self):
        """Check if all services are ready"""
        return self._service_ready.is_set()

    def stop(self):
        """Gracefully stop the node"""
        self._running = False
        logger.info("Shutting down node...")
        # Additional cleanup can be added here
        sys.exit(0)

def show_menu(node):
    """Display interactive menu with all features"""
    while True:
        print("\n" + "="*50)
        print("Blockchain Node Manager".center(50))
        print("="*50)
        print("1. Node Status")
        print("2. Blockchain Info")
        print("3. Mempool Info")
        print("4. Network Peers")
        print("5. Stake coins")
        print("6. Unstake coins")
        print("7. View validator status")
        print("8. Manually Mine Block (Validator only)")
        print("9. Deploy smart contract")
        print("10. Call smart contract")
        print("11. View contract state")
        print("12. Sync with Network")
        print("13. Exit")
        
        choice = input("\nSelect an option: ")
        
        if choice == "1":
            print(f"\nNode Status:")
            print(f"- Running: {'Yes' if node._running else 'No'}")
            print(f"- Host: {node.host}")
            print(f"- P2P Port: {node.p2p_port}")
            print(f"- API Port: {node.api_port}")
            print(f"- Blockchain Height: {len(node.blockchain.chain)}")
            print(f"- Mempool Size: {len(node.mempool.transactions)}")
            
        elif choice == "2":
            last_block = node.blockchain.get_last_block()
            print("\nBlockchain Info:")
            print(f"- Total Blocks: {len(node.blockchain.chain)}")
            print(f"- Last Block: #{last_block.index if last_block else 'N/A'}")
            print(f"- Last Block Hash: {last_block.hash[:20] + '...' if last_block else 'N/A'}")
            
        elif choice == "3":
            print("\nMempool Info:")
            print(f"- Transactions: {len(node.mempool.transactions)}")
            for i, tx in enumerate(list(node.mempool.transactions.values())[:5]):
                print(f"  {i+1}. {tx.tx_hash[:10]}... ({tx.amount} coins)")
            
        elif choice == "4":
            print("\nNetwork Peers:")
            peers = list(node.p2p_network.peers)
            if not peers:
                print("No connected peers")
            for i, peer in enumerate(peers):
                print(f"  {i+1}. {peer[0]}:{peer[1]}")
                
        elif choice == "5":  # Stake coins
            address = input("Your address: ")
            amount = float(input("Amount to stake: "))
            StakeManager.stake(address, amount, len(node.blockchain.chain))
            print(f"✅ Staked {amount} coins")
                
        elif choice == "6":  # Unstake coins
            address = input("Your address: ")
            amount = float(input("Amount to unstake: "))
            if StakeManager.unstake(address, amount):
                print(f"✅ Unstaked {amount} coins")
            else:
                print("❌ Failed to unstake (insufficient stake?)")
                
        elif choice == "7":  # View validator status
            validators = ValidatorRegistry.get_active_validators()
            print("\nActive Validators:")
            if not validators:
                print("No active validators")
            for i, (address, stake) in enumerate(validators.items()):
                print(f"  {i+1}. {address[:10]}...: {stake} staked")
                
        elif choice == "8":  # Manually mine block
            if not node.blockchain.chain:
                print("Chain not initialized")
                continue
            
            # Select validator
            validators = ValidatorRegistry.get_active_validators()
            if not validators:
                print("No active validators")
                continue
            
            # In real implementation, use actual validator key
            validator_key = ec.generate_private_key(ec.SECP256K1())
            
            transactions = list(node.mempool.transactions.values())
            if not transactions:
                print("No transactions in mempool to mine")
                continue
            
            new_block = node.blockchain.add_block(transactions, validator_key)
            if new_block:
                print(f"Block #{new_block.index} mined successfully!")
                # Remove mined transactions from mempool
                node.mempool.remove_transactions([tx.tx_hash for tx in transactions])
                # Distribute rewards
                StakeManager.distribute_rewards(new_block)
            else:
                print("Failed to mine block")
                
        elif choice == "9":  # Deploy smart contract
            try:
                sender = input("Sender address: ")
                print("Enter contract code (end with 'END' on a new line):")
                code_lines = []
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    code_lines.append(line)
                code = "\n".join(code_lines)
            
                contract_address = ContractManager.deploy_contract(sender, code)
                print(f"✅ Contract deployed at: {contract_address}")
            
            except Exception as e:
                print(f"Error: {e}")
                
        elif choice == "10":  # Call smart contract
            try:
                sender = input("Sender address: ")
                contract_address = input("Contract address: ")
                method = input("Method to call: ")
                args_str = input("Arguments (JSON): ") or "{}"
                args = json.loads(args_str)
                amount = float(input("Amount to send (0 for none): "))
            
                tx = ContractManager.call_contract(sender, contract_address, method, args, amount)
            
                # Add transaction to mempool
                if node.mempool.add_transaction(tx):
                    print(f"✅ Contract call transaction added: {tx.tx_hash}")
                else:
                    print("❌ Failed to add transaction to mempool")
            
            except Exception as e:
                print(f"Error: {e}")
                
        elif choice == "11":  # View contract state
            try:
                contract_address = input("Contract address: ")
                state = ContractManager.get_contract_state(contract_address)
                print(f"Contract state for {contract_address}:")
                for key, value in state.items():
                    print(f"  {key}: {value}")
                
            except Exception as e:
                print(f"Error: {e}")
                
        elif choice == "12":  # Sync with Network
            print("\nSyncing with network...")
            node.p2p_network.sync_blockchain()
            node.p2p_network.sync_mempool()
            print("Sync completed")
            
        elif choice == "13":  # Exit
            node.stop()
            break
            
        else:
            print("Invalid option, try again")

# تغییرات در بخش main()
def main():
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument('--host', default='0.0.0.0', help="Host address")
    parser.add_argument('--p2p-port', type=int, default=6000, help="P2P port")
    parser.add_argument('--api-port', type=int, default=5000, help="API port")
    parser.add_argument('--no-menu', action='store_true', help="Run in headless mode")
    
    args = parser.parse_args()
    
    # Initialize node
    node = BlockchainNode(
        host=args.host,
        p2p_port=args.p2p_port,
        api_port=args.api_port
    )
    
    # Start services
    node.start()
    
    # ایجاد مکانیزم انتظار برای اطمینان از اجرای کامل کدها
    startup_timeout = 10  # ثانیه
    startup_checks = 0
    max_startup_checks = 10
    
    if not node.wait_for_services(timeout=startup_timeout):
        logger.error("Some Services failed to start within timeout period")

        node.stop()
        sys.exit(1)

    # نمایش پیوند پیشرونده
    print("Initializing blockchain node...")
    if not args.no_menu:
        show_menu(node)
    else:
        logger.info("Running in headless mode...")
        try:
            while True:
                if int(time.time()) % 10 == 0:
                    logger.info(node.monitor.get_status_report())
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt! Killing Node...")
            node.stop()
    
    # اگر سرویس‌ها آماده نشدند
    if startup_checks >= max_startup_checks:
        logger.error("Failed to start all services within timeout")
        node.stop()
        sys.exit(1)
    
    # پاک کردن خطوط پیشرونده
    sys.stdout.write("\033[F" * (max_startup_checks + 2))  # برگشت به ابتدا
    sys.stdout.write("\033[K")  # پاک کردن خط
    
    # Show menu or run in background
    if not args.no_menu:
        show_menu(node)
    else:
        logger.info("Running in headless mode...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            node.stop()

if __name__ == '__main__':
    main()