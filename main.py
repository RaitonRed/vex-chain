from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.utils.logger import logger
import json

def print_block(block):
    print(f"\nBlock #{block.index}")
    print(f"Hash: {block.hash}")
    print(f"Previous: {block.previous_hash}")
    print(f"Nonce: {block.nonce}")
    print(f"Transactions: {len(block.transactions)}")
    for tx in block.transactions:
        print(f"  - {tx.sender} -> {tx.recipient}: {tx.amount}")

def main():
    logger.info("Starting blockchain node...")
    
    try:
        bc = Blockchain(difficulty=3)
        print(f"Blockchain initialized with {len(bc.chain)} blocks")
        
        if bc.chain:
            print_block(bc.chain[0])
    
        while True:
            print("\nMenu:")
            print("1. Add transaction")
            print("2. Mine block")
            print("3. View last block")
            print("4. View chain info")
            print("5. Validate chain")
            print("6. Exit")
            
            choice = input("> Select an option: ").strip()
            
            if choice == "1":
                try:
                    sender = input("Sender: ")
                    recipient = input("Recipient: ")
                    amount = float(input("Amount: "))
                    data_str = input("Data (JSON): ") or "{}"
                    data = json.loads(data_str)
                    
                    tx = Transaction(
                        sender=sender,
                        recipient=recipient,
                        amount=amount,
                        data=data
                    )
                    
                    # در یک پیاده‌سازی کامل، اینجا تراکنش به mempool اضافه می‌شود
                    print(f"Transaction created: {tx.tx_hash}")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    
            elif choice == "2":
                # در یک پیاده‌سازی کامل، تراکنش‌ها از mempool گرفته می‌شوند
                dummy_tx = Transaction(
                    sender="network",
                    recipient="miner",
                    amount=1.0,
                    data={"type": "reward", "message": "Block mining reward"}
                )
                
                new_block = bc.add_block([dummy_tx])
                if new_block:
                    print_block(new_block)
                else:
                    print("Failed to mine block")
                    
            elif choice == "3":
                last_block = bc.get_last_block()
                if last_block:
                    print_block(last_block)
                else:
                    print("No blocks in chain")
                    
            elif choice == "4":
                print(f"Chain length: {len(bc.chain)} blocks")
                print(f"Difficulty: {bc.difficulty}")
                print(f"Last block index: {bc.get_last_block().index if bc.chain else 'N/A'}")
                
            elif choice == "5":
                if bc.is_chain_valid():
                    print("✅ Chain is valid")
                else:
                    print("❌ Chain is invalid")
                    
            elif choice == "6":
                print("Exiting...")
                break
                
            else:
                print("Invalid option")

    except Exception as e:
        print(f"❌ Failed to initialize blockchain: {e}")
        return

if __name__ == '__main__':
    main()