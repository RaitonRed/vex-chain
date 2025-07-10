from blockchain.chain import Blockchain

if __name__ == "__main__":
    bc = Blockchain()

    data = {
        "type": "log",
        "source": "main.py",
        "message": "start of project",
    }

    new_block = bc.add_block(data)
    print(f"new block added: index={new_block.index}, hash={new_block.hash}")
