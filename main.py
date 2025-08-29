import argparse
from src.utils.logger import logging, logger
from src.blockchain.node import BlockchainNode

def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting blockchain node...")
    
    parser = argparse.ArgumentParser(description="Blockchain Node")
    parser.add_argument('--host', default='127.0.0.1', help="Host address")
    parser.add_argument('--p2p-port', type=int, default=2000, help="P2P port")
    parser.add_argument('--api-port', type=int, default=5000, help="API port")
    
    args = parser.parse_args()
    
    node = None
    try:
        node = BlockchainNode(
            host=args.host,
            p2p_port=args.p2p_port,
            api_port=args.api_port
        )
        
        if node.start():
            logger.info("Node started successfully")
            # Keep the node running until interrupted
            try:
                node.wait_for_services(timeout=30)
                logger.info("Node services are ready. Running indefinitely...")
                import time
                while True:
                    time.sleep(1)  # Keep the main thread alive
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
        else:
            logger.error("Failed to start node. Exiting.")
            return
            
    except Exception as e:
        logger.error(f"Node failed: {e}")
    finally:
        if node is not None:
            node.stop()
            logger.info("Node stopped")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")