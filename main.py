from src.blockchain.chain import Blockchain
import argparse

if __name__ == "__main__":
    bc = Blockchain()

    parser = argparse.ArgumentParser()
    parser.add_argument('--content', type=str, required=True, help='Text Content')
    args = parser.parse_args()


    data = {
        "type": "log",
        "source": "main.py",
        "message": args.content,
    }

    new_block = bc.add_block(data)
    print(f"new block added: index={new_block.index}, hash={new_block.hash}")
