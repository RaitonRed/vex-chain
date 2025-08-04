from dataclasses import dataclass
from typing import Callable, Dict
from src.cli.commands import CommandExecutor
from src.cli.outputs import display_menu, print_error, print_success
from src.cli.style import CLITheme

@dataclass
class MenuItem:
    label: str
    handler: Callable
    requires_ready_node: bool = True
    admin_only: bool = False

class NodeMenu:
    def __init__(self, node):
        self.node = node
        self.executor = CommandExecutor(node)
        self.theme = CLITheme()
        self.commands = {
            "1": MenuItem("Node Status", self.executor.show_status),
            "2": MenuItem("Blockchain Info", self.executor.show_blockchain_info),
            "3": MenuItem("Mempool Info", self.executor.show_mempool_info),
            "4": MenuItem("Network Peers", self.executor.show_peers),
            "5": MenuItem("Stake coins", self.executor.stake_coins, False),
            "6": MenuItem("Unstake coins", self.executor.unstake_coins, False),
            "7": MenuItem("Validator Status", self.executor.show_validators),
            "8": MenuItem("Mine Block", self.executor.mine_block),
            "9": MenuItem("Deploy Contract", self.executor.deploy_contract),
            "10": MenuItem("Call Contract", self.executor.call_contract),
            "11": MenuItem("View Contract", self.executor.view_contract),
            "12": MenuItem("Sync Network", self.executor.sync_network),
            "13": MenuItem("Create Account", self.executor.create_account),
            "14": MenuItem("Send Transaction", self.executor.create_transaction),
            "15": MenuItem("Exit", self.executor.exit_node),
        }

    def show(self):
        while True:
            display_menu("Blockchain Node Manager", self.commands)
            choice = input(f"{self.theme.PROMPT} Select an option: ")
            
            if choice not in self.commands:
                print_error("Invalid option, try again")
                continue

            menu_item = self.commands[choice]
            if menu_item.requires_ready_node and not self.node.is_ready():
                print_error("Node services are not ready yet")
                continue

            try:
                menu_item.handler()
            except Exception as e:
                print_error(f"Operation failed: {str(e)}")