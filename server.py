# server.py — ISO8583 Server for Card + Crypto Gateway

from flask import Flask, request, jsonify
import random, logging
import uuid
from iso8583_crypto import process_crypto_payout
from web3 import Web3
from tronpy.keys import is_base58check_address

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "ISO8583 Crypto Gateway Running"

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        required = ['pan', 'expiry', 'cvv', 'amount', 'currency', 'wallet', 'payout_type']
        for f in required:
            if f not in data:
                return jsonify({
                    "status": "rejected",
                    "message": f"Missing field: {f}",
                    "field39": "99"
                })

        # Card type check — Visa, MasterCard, Amex
        if not data['pan'].startswith(('4', '5', '3')):
            return jsonify({
                "status": "rejected",
                "message": "Card not supported (not Visa/MasterCard/Amex)",
                "field39": "05"
            })

        transaction_id = str(uuid.uuid4())
        arn = f"ARN{random.randint(10**11, 10**12)}"
        wallet = data['wallet']
        payout_type = data['payout_type'].upper()

        # ✅ Validate wallet format
        if payout_type == 'ERC20':
            if not Web3.is_address(wallet):
                return jsonify({
                    "status": "rejected",
                    "message": "Invalid Ethereum wallet address",
                    "field39": "99"
                })
        elif payout_type == 'TRC20':
            if not is_base58check_address(wallet):
                return jsonify({
                    "status": "rejected",
                    "message": "Invalid TRON wallet address",
                    "field39": "99"
                })
        else:
            return jsonify({
                "status": "rejected",
                "message": "Unsupported payout network",
                "field39": "12"
            })

        # ✅ Attempt crypto payout
        try:
            tx_hash = process_crypto_payout(
                wallet=wallet,
                amount=data['amount'],
                currency=data['currency'],
                network=payout_type
            )
            return jsonify({
                "status": "approved",
                "message": "Transaction Approved",
                "transaction_id": transaction_id,
                "arn": arn,
                "payout_tx_hash": tx_hash,
                "field39": "00"
            })
        except Exception as e:
            logging.warning(f"Payout error: {e}")
            return jsonify({
                "status": "pending_payout_failed",
                "message": f"Card accepted, but payout failed: {str(e)}",
                "transaction_id": transaction_id,
                "arn": arn,
                "payout_tx_hash": None,
                "field39": "91"
            })

    except Exception as ex:
        logging.exception("Unexpected server error")
        return jsonify({
            "status": "rejected",
            "message": f"Unexpected error: {str(ex)}",
            "field39": "99"
        })

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
