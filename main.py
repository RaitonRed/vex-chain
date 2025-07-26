import argparse
from src.cli.outputs import (
    display_menu,
    print_error,
    print_success,
    print_warning
)
from src.blockchain.node import BlockchainNode

def main():
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument('--host', default='0.0.0.0', help="Host address")
    parser.add_argument('--p2p-port', type=int, default=6000, help="P2P port")
    parser.add_argument('--api-port', type=int, default=5000, help="API port")
    parser.add_argument('--no-menu', action='store_true', help="Run in headless mode")
    
    args = parser.parse_args()
    
    node = BlockchainNode(
        host=args.host,
        p2p_port=args.p2p_port,
        api_port=args.api_port
    )
    
    try:
        node.start()
        if not args.no_menu:
            display_menu(node).show()
        else:
            input("Press Enter to stop...")  # یا مدیریت headless mode
    except KeyboardInterrupt:
        print("\nShutting down node...")
    finally:
        node.stop()

if __name__ == '__main__':
    main()