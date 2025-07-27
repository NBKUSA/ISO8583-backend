# iso8583_crypto.py — Blockchain Payout Processor (ERC20 / TRC20)

import os
from decimal import Decimal
from web3 import Web3
from tronpy import Tron
from tronpy.providers import HTTPProvider
from tronpy.keys import PrivateKey

def process_crypto_payout(wallet: str, amount, currency: str, network: str):
    """Route payout to the correct blockchain"""
    amount = Decimal(str(amount))
    network = network.upper()

    if network == "TRC20":
        return send_tron(wallet, amount)
    elif network == "ERC20":
        return send_erc20(wallet, amount)
    else:
        raise Exception("Unsupported payout network")

def send_erc20(to_address: str, amount: Decimal):
    infura_url = os.getenv("INFURA_URL")
    private_key = os.getenv("ERC20_PRIVATE_KEY")
    token_address = os.getenv("ERC20_CONTRACT_ADDRESS")

    if not all([infura_url, private_key, token_address]):
        raise Exception("Missing ERC20 configuration")

    web3 = Web3(Web3.HTTPProvider(infura_url))
    if not Web3.is_address(to_address):
        raise Exception("Invalid Ethereum wallet address")

    account = web3.eth.account.from_key(private_key)
    token_address = web3.to_checksum_address(token_address)
    to_address = web3.to_checksum_address(to_address)

    contract = web3.eth.contract(address=token_address, abi=erc20_abi())
    decimals = contract.functions.decimals().call()
    amt = int(amount * Decimal(10 ** decimals))
    nonce = web3.eth.get_transaction_count(account.address)

    tx = contract.functions.transfer(to_address, amt).build_transaction({
        'chainId': web3.eth.chain_id,
        'gas': 0,  # placeholder, will be overwritten
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
    })

    # Estimate gas
    gas_estimate = web3.eth.estimate_gas({
        'from': account.address,
        'to': token_address,
        'data': tx['data']
    })
    tx['gas'] = gas_estimate

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return web3.to_hex(tx_hash)

def send_tron(to_address: str, amount: Decimal):
    tron_private_key = os.getenv("TRC20_PRIVATE_KEY")
    token_contract = os.getenv("TRC20_CONTRACT_ADDRESS")
    tron_api_key = os.getenv("TRON_API_KEY")

    if not all([tron_private_key, token_contract, tron_api_key]):
        raise Exception("Missing TRC20 configuration")

    client = Tron(provider=HTTPProvider(api_key=tron_api_key), network="mainnet")
    pk = PrivateKey(bytes.fromhex(tron_private_key))
    contract = client.get_contract(token_contract)

    decimals = contract.functions.decimals()
    amt = int(amount * Decimal(10 ** decimals))

    txn = (
        contract.functions.transfer(to_address, amt)
        .with_owner(pk.public_key.to_base58check_address())
        .fee_limit(1_000_000)
        .build()
        .sign(pk)
    )

    result = txn.broadcast()
    if "txid" not in result:
        raise Exception("TRON broadcast failed")

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
