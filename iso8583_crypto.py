# iso8583_crypto.py — Blockchain Payout Processor (ERC20 / TRC20)

import os
from decimal import Decimal

def process_crypto_payout(wallet: str, amount: Decimal, currency: str, network: str) -> str:
    network = network.upper()
    
    # Validate necessary environment variables before processing
    if network == "TRC20":
        for var in ["TRC20_PRIVATE_KEY", "TRC20_CONTRACT_ADDRESS", "TRON_API_KEY"]:
            if not os.getenv(var):
                raise Exception(f"Missing environment variable: {var}")
        return send_tron(wallet, amount)
    
    elif network == "ERC20":
        for var in ["INFURA_URL", "ERC20_PRIVATE_KEY", "ERC20_CONTRACT_ADDRESS"]:
            if not os.getenv(var):
                raise Exception(f"Missing environment variable: {var}")
        return send_erc20(wallet, amount)

    else:
        raise Exception("Unsupported payout network")


def send_erc20(to_address: str, amount: Decimal) -> str:
    from web3 import Web3  # Delay import for performance and memory
    infura_url = os.getenv("INFURA_URL")
    private_key = os.getenv("ERC20_PRIVATE_KEY")
    token_address = os.getenv("ERC20_CONTRACT_ADDRESS")

    web3 = Web3(Web3.HTTPProvider(infura_url))
    if not web3.is_connected():
        raise Exception("Failed to connect to Ethereum node")

    account = web3.eth.account.from_key(private_key)
    to_address = web3.to_checksum_address(to_address)
    token_address = web3.to_checksum_address(token_address)

    contract = web3.eth.contract(address=token_address, abi=erc20_abi())
    decimals = contract.functions.decimals().call()
    amt = int(amount * (10 ** decimals))

    nonce = web3.eth.get_transaction_count(account.address)
    tx = contract.functions.transfer(to_address, amt).build_transaction({
        'chainId': web3.eth.chain_id,
        'gas': 100_000,
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    return web3.to_hex(tx_hash)


def send_tron(to_address: str, amount: Decimal) -> str:
    from tronpy import Tron
    from tronpy.providers import HTTPProvider
    from tronpy.keys import PrivateKey

    tron_private_key = os.getenv("TRC20_PRIVATE_KEY")
    token_contract = os.getenv("TRC20_CONTRACT_ADDRESS")
    tron_api_key = os.getenv("TRON_API_KEY")

    client = Tron(provider=HTTPProvider(api_key=tron_api_key), network="mainnet")
    pk = PrivateKey(bytes.fromhex(tron_private_key))
    contract = client.get_contract(token_contract)

    decimals = contract.functions.decimals().call()
    amt = int(amount * (10 ** decimals))

    txn = (
        contract.functions.transfer(to_address, amt)
        .with_owner(pk.public_key.to_base58check_address())
        .fee_limit(1_000_000)
        .build()
        .sign(pk)
    )

    result = txn.broadcast()
    if "txid" not in result:
        raise Exception(f"TRON broadcast failed: {result}")

    return result["txid"]


def erc20_abi():
    return [
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]
