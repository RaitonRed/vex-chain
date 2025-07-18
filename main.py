from src.blockchain.chain import Blockchain
from src.blockchain.transaction import Transaction
from src.blockchain.mempool import Mempool
from cryptography.hazmat.primitives.asymmetric import ec
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
        mempool = Mempool()  # ایجاد یک نمونه از Mempool
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
                    
                    # اضافه کردن تراکنش به Mempool
                    if mempool.add_transaction(tx):
                        print(f"✅ Transaction added to mempool: {tx.tx_hash}")
                    else:
                        print("❌ Failed to add transaction to mempool")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    
            elif choice == "2":
                # دریافت تراکنش‌ها از Mempool
                transactions = mempool.get_transactions()
                
                if not transactions:
                    print("No transactions in mempool to mine")
                    continue
                
                # ایجاد کلید خصوصی برای ولیدیتور
                validator_private_key = ec.generate_private_key(ec.SECP256K1())
                
                # اضافه کردن بلاک جدید با تراکنش‌های Mempool
                new_block = bc.add_block(transactions, validator_private_key)
                if new_block:
                    print_block(new_block)
                    # حذف تراکنش‌های ماین شده از Mempool
                    mempool.remove_transactions([tx.tx_hash for tx in transactions])
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