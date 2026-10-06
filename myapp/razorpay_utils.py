from typing import Any, cast
 
import razorpay
from django.conf import settings
 
 
client = cast(
    Any,
    razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    ),
)
 
def create_razorpay_order(amount, receipt):
    amount_in_paise = int(float(amount) * 100)
    order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": str(receipt),
    })
    return order
 
def verify_payment(payment_id, order_id, signature):
 
    data = {
        "razorpay_payment_id": payment_id,
        "razorpay_order_id": order_id,
        "razorpay_signature": signature,
    }
 
    try:
        client.utility.verify_payment_signature(data)
        return True
 
    except razorpay.errors.SignatureVerificationError:
        return False
 