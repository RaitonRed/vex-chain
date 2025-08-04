import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict
from src.cli.commands import CommandExecutor
from src.cli.outputs import display_menu, print_error, print_success, print_info
from src.cli.style import CLITheme
from src.utils.logger import logging, logger
from src.blockchain.node import BlockchainNode
from src.cli.menu import MenuItem

class NodeMenu:
    def __init__(self, node):
        self.node = node
        self.executor = CommandExecutor(node)
        self.theme = CLITheme()
        self.commands = {
            # Information Section
            "1": MenuItem("📊 Node Status", self.executor.show_status),
            "2": MenuItem("⛓ Blockchain Info", self.executor.show_blockchain_info),
            "3": MenuItem("📝 Mempool Transactions", self.executor.show_mempool_info),
            "4": MenuItem("🌐 Network Peers", self.executor.show_peers),
            "5": MenuItem("🛡️ Validator Status", self.executor.show_validators),

            # wallet
            "6": MenuItem("Create Account", self.executor.create_account),
            
            # Transactions Section
            "10": MenuItem("💸 Send Transaction", self.executor.create_transaction),
            "11": MenuItem("📦 Contract Transaction", self.executor.create_contract_transaction),
            
            # Staking Section
            "20": MenuItem("💰 Stake Coins", self.executor.stake_coins),
            "21": MenuItem("💱 Unstake Coins", self.executor.unstake_coins),
            "22": MenuItem("🏆 Claim Stake Rewards", self.executor.claim_stake_rewards),
            
            # Smart Contracts Section
            "30": MenuItem("🛠️ Deploy Contract", self.executor.deploy_contract),
            "31": MenuItem("📞 Call Contract", self.executor.call_contract),
            "32": MenuItem("👀 View Contract", self.executor.view_contract),
            "33": MenuItem("🔍 View Contract Events", self.executor.view_contract_events),
            
            # Network Management
            "40": MenuItem("🔄 Sync Network", self.executor.sync_network),
            "41": MenuItem("🔗 Connect to Peer", self.executor.connect_to_peer),
            "42": MenuItem("🚫 Disconnect Peer", self.executor.disconnect_peer),
            
            # System Management (Admin)
            "90": MenuItem("⚙️ Node Settings", self.executor.node_settings, admin_only=True),
            "91": MenuItem("⛏ Manual Mining", self.executor.mine_block, admin_only=True),
            "92": MenuItem("🧹 Clear Mempool", self.executor.clear_mempool, admin_only=True),
            
            # Exit
            "99": MenuItem("🚪 Exit", self.executor.exit_node)
        }

    def show(self):
        while True:
            self._display_header()
            display_menu("Blockchain Node Manager", self.commands)
            choice = input(f"{self.theme.PROMPT}Select option: {self.theme.INPUT}").strip()
            
            if choice not in self.commands:
                print_error("Invalid option!")
                continue

            menu_item = self.commands[choice]
            
            if menu_item.requires_ready_node and not self.node.is_ready():
                print_error("Node services are not ready!")
                continue
                
            if menu_item.admin_only and not self._check_admin():
                print_error("Admin access required!")
                continue

            try:
                menu_item.handler()
                input("\n" + self.theme.INFO + "Press Enter to continue..." + self.theme.RESET)
            except Exception as e:
                print_error(f"Error: {str(e)}")

    def _display_header(self):
        last_block = self.node.blockchain.get_last_block()
        status = (
            f"{self.theme.SUCCESS}✓ Online{self.theme.RESET}" 
            if self.node.is_ready() 
            else f"{self.theme.ERROR}✗ Offline{self.theme.RESET}"
        )
        
        info = [
            f"{self.theme.LABEL}Status:{self.theme.RESET} {status}",
            f"{self.theme.LABEL}Block:{self.theme.RESET} {len(self.node.blockchain.chain)}",
            f"{self.theme.LABEL}Peers:{self.theme.RESET} {len(self.node.p2p_network.peers)}",
            f"{self.theme.LABEL}Tx Pending:{self.theme.RESET} {len(self.node.mempool.transactions)}"
        ]
        
        print(f"\n{' | '.join(info)}\n")

    def _check_admin(self):
        return True

def main():
    node = None

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting blockchain node...")
    
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument('--host', default='127.0.0.1', help="Host address")
    parser.add_argument('--p2p-port', type=int, default=2000, help="P2P port")
    parser.add_argument('--api-port', type=int, default=5000, help="API port")
    parser.add_argument('--no-menu', action='store_true', help="Run in headless mode")
    
    args = parser.parse_args()
    
    try:
        node = BlockchainNode(
            host=args.host,
            p2p_port=args.p2p_port,
            api_port=args.api_port
        )
        
        # فقط وضعیت راه‌اندازی را بررسی کنید
        if node.start():
            logger.info("Node started successfully")
            
            if not args.no_menu:
                print("\n" + "="*50)
                print("Blockchain Node CLI".center(50))
                print("="*50 + "\n")
                NodeMenu(node).show()
            else:
                logger.info("Running in headless mode")
                input("Press Enter to stop...")
        else:
            logger.error("Failed to start node. Exiting.")
            return
            
    except KeyboardInterrupt:
        logger.info("\nShutting down node...")
    except Exception as e:
        logger.error(f"Node failed: {e}")
    finally:
        if node is not None:
            node.stop()

if __name__ == '__main__':
    print("="*50)
    print("Starting Blockchain Node".center(50))
    print("="*50)
    
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
