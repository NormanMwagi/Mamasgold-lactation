# payments/services.py
import os, base64, requests, logging
from datetime import datetime
from dotenv import load_dotenv
from django.conf import settings

load_dotenv()
logger = logging.getLogger(__name__)

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL')


def generate_access_token():
    """Generate M-Pesa API access token"""
    try:
        credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        response = requests.get(
            f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"Access token error: {e}")
        return None


def initiate_mpesa_stk_push(phone_number, amount, order_number, callback_url):
    """Send STK Push to Safaricom API"""
    try:
        access_token = generate_access_token()
        if not access_token:
            return {'success': False, 'message': 'Failed to get access token'}

        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number

        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        stk_password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": stk_password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": order_number,
            "TransactionDesc": f"Payment for order {order_number}"
        }

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        return {'success': True, 'data': response.json()}

    except requests.exceptions.RequestException as e:
        logger.error(f"STK Push error: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"M-Pesa Error Response: {e.response.text}")
            print("Response status:", e.response.status_code)
            print("Response body:", e.response.text) 
        return {'success': False, 'message': 'Payment initiation failed'}
