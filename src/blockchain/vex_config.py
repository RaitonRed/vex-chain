VEX_CONFIG = {
    "name": "VEX",
    "symbol": "VEX",
    "decimals": 18,
    "total_supply": int(90_000_000 * 10**18), # 90 million tokens with 18 decimals
    "initial_distribution": {
        "foundation": 0.2,
        "ecosystem": 0.3,
        "public_sale": 0.5
    },
    "metadata": {
        "website": "https://vexcoin.github.io",
        "description": "VEX Coin is a decentralized cryptocurrency powering the VEX blockchain.",
        "algorithm": "Proof of Stake",
        "network": "mainnet"
    }
}

foundation_address = "0x0000000000000000000000000000000000000001"
ecosystem_address = "0x0000000000000000000000000000000000000002"
public_sale_address = "0x0000000000000000000000000000000000000003"

foundation_amount = int(VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["foundation"])
ecosystem_amount = int(VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["ecosystem"])
public_sale_amount = int(VEX_CONFIG["total_supply"] * VEX_CONFIG["initial_distribution"]["public_sale"])
