from flask import Flask, request, jsonify
from blockchain.chain import Blockchain

app = Flask(__name__)
blockchain = Blockchain()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "ChainNet API is running"})

@app.route("/add", methods=["POST"])
def add_data():
    data = request.json
    if not data:
        return jsonify({"error": "No Data sent"}), 400

    block = blockchain.add_block(data)
    return jsonify({
        "message": "✅ Data saved!",
        "index": block.index,
        "hash": block.hash
    }), 201

@app.route("/chain", methods=["GET"])
def get_chain():
    return jsonify({
        "length": len(blockchain.chain),
        "chain": [b.to_dict() for b in blockchain.chain]
    })

@app.route("/block/<int:index>", methods=["GET"])
def get_block(index):
    if index >= len(blockchain.chain):
        return jsonify({"error": "block not found"}), 404

    block = blockchain.chain[index]
    return jsonify(block.to_dict())

if __name__ == "__main__":
    app.run(port=5000, debug=True)