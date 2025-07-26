from tabulate import tabulate
from src.cli.style import CLITheme

theme = CLITheme()

def display_menu(title, commands):
    """Display a formatted menu with title and command options"""
    print(f"\n{theme.HEADER}{'=' * 50}")
    print(f"{title.center(50)}")
    print(f"{'=' * 50}{theme.RESET}")
    
    menu_items = []
    for key, item in commands.items():
        menu_items.append([f"{theme.KEY}{key}{theme.RESET}", item.label])
    
    print(tabulate(menu_items, tablefmt="plain"))

def display_status(data):
    """Display node status information"""
    print(f"\n{theme.SUBHEADER}Node Status:{theme.RESET}")
    for key, value in data.items():
        print(f"{theme.LABEL}{key}:{theme.RESET} {theme.VALUE}{value}{theme.RESET}")

def display_blockchain_info(block):
    """Display blockchain summary"""
    if not block:
        print(f"{theme.WARNING}No blocks in chain{theme.RESET}")
        return
    
    print(f"\n{theme.SUBHEADER}Blockchain Info:{theme.RESET}")
    info = [
        ["Block Index", block.index],
        ["Block Hash", f"{block.hash[:20]}..."],
        ["Validator", f"{block.validator[:10]}..."],
        ["Timestamp", block.timestamp]
    ]
    print(tabulate(info, tablefmt="grid"))

def display_mempool(transactions):
    """Display mempool transactions"""
    print(f"\n{theme.SUBHEADER}Mempool Transactions:{theme.RESET}")
    
    if not transactions:
        print(f"{theme.INFO}Mempool is empty{theme.RESET}")
        return
    
    table_data = []
    for i, tx in enumerate(transactions, 1):
        table_data.append([
            i,
            f"{tx.tx_hash[:8]}...",
            f"{tx.sender[:6]}...",
            f"{tx.recipient[:6]}...",
            tx.amount
        ])
    
    headers = [
        f"{theme.HEADER}#{theme.RESET}",
        f"{theme.HEADER}Hash{theme.RESET}",
        f"{theme.HEADER}From{theme.RESET}",
        f"{theme.HEADER}To{theme.RESET}",
        f"{theme.HEADER}Amount{theme.RESET}"
    ]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def display_peers(peers):
    """Display connected peers"""
    print(f"\n{theme.SUBHEADER}Network Peers:{theme.RESET}")
    
    if not peers:
        print(f"{theme.INFO}No connected peers{theme.RESET}")
        return
    
    for i, peer in enumerate(peers, 1):
        print(f"{theme.LABEL}{i}.{theme.RESET} {peer[0]}:{peer[1]}")

def display_validators(validators):
    """Display active validators"""
    print(f"\n{theme.SUBHEADER}Active Validators:{theme.RESET}")
    
    if not validators:
        print(f"{theme.WARNING}No active validators{theme.RESET}")
        return
    
    table_data = []
    for address, stake in validators.items():
        table_data.append([
            f"{address[:10]}...",
            stake
        ])
    
    headers = [
        f"{theme.HEADER}Address{theme.RESET}",
        f"{theme.HEADER}Stake{theme.RESET}"
    ]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def display_contract_state(contract_address, state):
    """Display contract state"""
    print(f"\n{theme.SUBHEADER}Contract State ({contract_address[:10]}...):{theme.RESET}")
    
    if not state:
        print(f"{theme.INFO}No state available{theme.RESET}")
        return
    
    for key, value in state.items():
        print(f"{theme.LABEL}{key}:{theme.RESET} {theme.VALUE}{value}{theme.RESET}")

def print_success(message):
    """Print success message"""
    print(f"{theme.SUCCESS}✅ {message}{theme.RESET}")

def print_error(message):
    """Print error message"""
    print(f"{theme.ERROR}❌ {message}{theme.RESET}")

def print_warning(message):
    """Print warning message"""
    print(f"{theme.WARNING}⚠️ {message}{theme.RESET}")

def print_info(message):
    """Print info message"""
    print(f"{theme.INFO}ℹ️ {message}{theme.RESET}")