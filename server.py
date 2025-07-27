# server.py — ISO8583 Crypto Gateway Server (Render Deployment Ready)

from flask import Flask, request, jsonify
from decimal import Decimal, InvalidOperation
from iso8583_crypto import process_crypto_payout
import logging, random, uuid, os

app = Flask(__name__)

# Setup production-grade logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

@app.route('/')
def home():
    return "ISO8583 Crypto Gateway Running"

@app.route('/process_payment', methods=['POST'])
def process_payment():
    data = request.get_json(silent=True)
    required = ['pan', 'expiry', 'cvv', 'amount', 'currency', 'wallet', 'payout_type']

    # Check required fields
    for field in required:
        if field not in data:
            return iso8583_response("99", f"Missing field: {field}", status="rejected")

    # Accept Visa (4), MasterCard (5), Amex (3)
    if not data['pan'].startswith(('3', '4', '5')):
        return iso8583_response("05", "Unsupported card type", status="rejected")

    # Validate amount
    try:
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return iso8583_response("13", "Invalid amount", status="rejected")

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

@app.errorhandler(500)
def internal_error(e):
    logging.exception("Server error")
    return iso8583_response("96", "System error", status="rejected")

def iso8583_response(field39, message, status="rejected"):
    return jsonify({
        "status": status,
        "message": message,
        "field39": field39
    }), 400

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
