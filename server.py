# server.py — ISO8583 Server for Card + Crypto Gateway

from flask import Flask, request, jsonify
import random, logging
import uuid
from iso8583_crypto import process_crypto_payout

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
                return jsonify({"status": "rejected", "message": f"Missing field: {f}", "field39": "99"})

        # Accept Visa, MasterCard, and Amex (starts with 4, 5, or 3)
        if data['pan'].startswith(('4', '5', '3')):
            transaction_id = str(uuid.uuid4())
            arn = f"ARN{random.randint(10**11, 10**12)}"

            try:
                tx_hash = process_crypto_payout(
                    wallet=data['wallet'],
                    amount=data['amount'],
                    currency=data['currency'],
                    network=data['payout_type']
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

        return jsonify({
            "status": "rejected",
            "message": "Card not supported (not Visa/MasterCard/Amex)",
            "field39": "05"
        })

    except Exception as ex:
        logging.exception("Error processing payment")
        return jsonify({"status": "rejected", "message": str(ex), "field39": "99"})


if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
