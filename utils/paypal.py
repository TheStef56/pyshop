import os
import base64
import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

# Configura logging per tenacity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PAYPAL_CLIENT = os.getenv('PAYPAL_CLIENT')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET')
PAYPAL_URL = os.getenv('PAYPAL_URL')

class PaypalCheckout():
    def __init__(self, cache):
        self.cache = cache
        self.base_url = PAYPAL_URL
        self.token = None
        self.token_expiration = 0
        self.billing = None
        self.shipping = None

    @retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _fetch_new_token(self):
        auth = base64.b64encode(f"{PAYPAL_CLIENT}:{PAYPAL_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        response = requests.post(f"{self.base_url}/v1/oauth2/token", headers=headers, data=data)
        response.raise_for_status()  # Solleva eccezione su 4xx/5xx

        return response.json()

    def get_valid_token(self):
        token_data = self.cache.get("paypal_token")
        if token_data:
            return token_data["access_token"]

        try:
            token_data = self._fetch_new_token()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Errore durante il recupero del token PayPal: {e}")

        access_token = token_data["access_token"]
        expires_in = token_data["expires_in"] - 60  # margine

        self.cache.set("paypal_token", {"access_token": access_token}, timeout=expires_in)
        return access_token

    def add_billing_data(self, name: str, surname: str, street: str, city: str, province: str, postal_code: str, country_code: str):
        self.billing = {    
                            "name": {
                                "full_name": f"{name} {surname}"
                            },
                            "address": {
                                "address_line_1": street,      # VIa G. Rossini 26
                                "admin_area_2":   city,        # San Pancrazio
                                "admin_area_1":   province,    # BR
                                "postal_code":    postal_code, # 72026
                                "country_code":   country_code # IT
                            }
                        }

    def add_shipping_data(self, name: str, surname: str, street: str, city: str, province: str, postal_code: str, country_code: str):
        self.shipping = {
                            "payer": {
                                "name": {
                                    "given_name": name,
                                    "surname": surname
                                },
                                "address": {
                                    "address_line_1": street,      # VIa G. Rossini 26
                                    "admin_area_2":   city,        # San Pancrazio
                                    "admin_area_1":   province,    # BR
                                    "postal_code":    postal_code, # 72026
                                    "country_code":   country_code # IT
                                }
                            }
                        }


    @retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def create_order(self, amount: float, currency: str):
        load_dotenv()
        token = self.get_valid_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": str(round(amount, 2))
                }
            }],
            "application_context": {
                "return_url": f"{os.environ.get('DOMAIN')}/payment/paypal/success",
                "cancel_url": f"{os.environ.get('DOMAIN')}/payment/paypal/cancel"
            }
        }

        if self.billing:
            payload["purchase_units"][0].update({"shipping": self.billing})
        
        if self.shipping:
            payload.update(self.shipping)

        response = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers=headers,
            json=payload,
            timeout=10
        )
        logger.info(f"Create order response: {response.status_code}")
        response.raise_for_status()
        return response.json()

    @retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def capture_order(self, order_id):
        token = self.get_valid_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers=headers,
            timeout=10
        )
        logger.info(f"Capture order response: {response.status_code}")
        response.raise_for_status()
        return response.json()
