# iso8583_crypto.py — Real Blockchain Payouts

import os
from web3 import Web3
from tronpy import Tron
from tronpy.providers import HTTPProvider
from tronpy.keys import PrivateKey


def process_crypto_payout(wallet, amount, currency, network):
    if network.upper() == "TRC20":
        return send_tron(wallet, amount)
    elif network.upper() == "ERC20":
        return send_erc20(wallet, amount)
    else:
        raise Exception("Unsupported payout type")


def send_erc20(to_address, amount):
    infura_url = os.getenv("INFURA_URL")
    private_key = os.getenv("ERC20_PRIVATE_KEY")
    token_address = os.getenv("ERC20_CONTRACT_ADDRESS")

    if not all([infura_url, private_key, token_address]):
        raise Exception("Missing ERC20 environment variables.")

    web3 = Web3(Web3.HTTPProvider(infura_url))
    account = web3.eth.account.from_key(private_key)

    # Convert to checksum addresses
    to_address = web3.to_checksum_address(to_address)
    token_address = web3.to_checksum_address(token_address)

    contract = web3.eth.contract(address=token_address, abi=erc20_abi())

    decimals = contract.functions.decimals().call()
    amt = int(float(amount) * (10 ** decimals))
    nonce = web3.eth.get_transaction_count(account.address)

    tx = contract.functions.transfer(to_address, amt).build_transaction({
        'chainId': 1 if "mainnet" in infura_url else 5,
        'gas': 60000,
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return web3.to_hex(tx_hash)


def send_tron(to_address, amount):
    tron_private_key = os.getenv("TRC20_PRIVATE_KEY")
    token_contract = os.getenv("TRC20_CONTRACT_ADDRESS")

    if not all([tron_private_key, token_contract]):
        raise Exception("Missing TRC20 environment variables.")

    client = Tron(
        provider=HTTPProvider(api_key="90556144-eb12-4d28-be5f-24368bb813ff"),
        network="mainnet"
    )

    pk = PrivateKey(bytes.fromhex(tron_private_key))
    contract = client.get_contract(token_contract)

    decimals = contract.functions.decimals()  # FIXED HERE
    amt = int(float(amount) * (10 ** decimals))

    txn = (
        contract.functions.transfer(to_address, amt)
        .with_owner(pk.public_key.to_base58check_address())
        .fee_limit(1_000_000)
        .build()
        .sign(pk)
    )

    result = txn.broadcast()
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
