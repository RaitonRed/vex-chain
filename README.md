# Blockchain Node - Proof of Stake Implementation

A Python-based blockchain implementation with Proof of Stake consensus, smart contracts, P2P networking, and a comprehensive CLI interface.


## Features
- ✅ Proof of Stake Consensus - Energy-efficient validation mechanism
- 🤖 Smart Contract Support - Custom VM with gas accounting
- 🌐 P2P Networking - Peer discovery and blockchain synchronization
- 💻 Interactive CLI - User-friendly node management interface
- 📊 REST API - Programmatic access to blockchain functions
- 🔒 Cryptographic Security - ECDSA signatures for blocks and transactions
- 📦 SQLite Database - Persistent storage for blockchain data

---
## Key Components
### Blockchain Core
- **PoS Consensus**: Validator selection based on stake weight
- **Smart Contracts**: Custom VM with gas accounting
- **Mempool Management**: Transaction pooling with expiration
- **State Management**: Persistent storage for accounts and contracts

### Networking
- Peer discovery and connection management
- Blockchain synchronization
- Transaction and block broadcasting

### Interfaces
- **CLI**: Interactive node management
- **REST API**: HTTP endpoints for integration
- **Service Monitoring**: Health checks and diagnostics


## Getting Started

### Prerequisites

- Python 3.9+
- SQLite 3.x
- Required packages: `pip install -r requirements.txt`

### Installation

```bash
git clone https://github.com/RaitonRed/StorageNet.git
cd StorageNet
pip install -r requirements.txt
```

### Running a Node
```bash
# Start node with interactive CLI
python main.py

# Start in headless mode
python main.py --no-menu

# Start with custom ports
python main.py --host 0.0.0.0 --p2p-port 6000 --api-port 5000
```

## CLI Usage
The interactive CLI provides full node management capabilities:

```bash
==================== Blockchain Node CLI ====================

1.  📊 Node Status
2.  ⛓ Blockchain Info
3.  📝 Mempool Transactions
4.  🌐 Network Peers
5.  🛡️ Validator Status
10. 💸 Send Transaction
20. 💰 Stake Coins
30. 🛠️ Deploy Contract
40. 🔄 Sync Network
99. 🚪 Exit

Select option: 
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Node status |
| `/blocks` | GET | List blocks (paginated) |
| `/blocks/{index}` | GET | Get block details |
| `/transactions` | POST | Submit new transaction |
| `/mine` | POST | Mine a new block |
| `/health` | GET | Node health status |

## Project Structure
```bash
blockchain-node/
├── src/
│   ├── blockchain/          # Core blockchain implementation
│   │   ├── consensus/       # Proof of Stake consensus
│   │   ├── contracts/       # Smart contract system
│   │   ├── db/              # Database repositories
│   │   └── ...              # Core components
│   ├── cli/                 # Command line interface
│   ├── p2p/                 # P2P networking
│   ├── api/                 # REST API server
│   └── utils/               # Utility modules
├── tests/                   # Unit and integration tests
├── data/                    # Database storage
├── requirements.txt         # Python dependencies
└── main.py                  # Entry point
```

## Contributing
Contributions are welcome! Please follow these steps:

1. Fork the repository

2. Create a new branch (`git checkout -b feature/your-feature`)

3. Commit your changes (`git commit -am 'Add some feature'`)

4. Push to the branch (`git push origin feature/your-feature`)

5. Create a new Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Future Roadmap
Implement cross-shard transactions

Add privacy features (zk-SNARKs)

Develop browser-based wallet

Create testnet deployment scripts

Add Docker support for easy deployment

---

**Note**: This is a simplified implementation for educational purposes. Not recommended for production use without extensive security audits.
