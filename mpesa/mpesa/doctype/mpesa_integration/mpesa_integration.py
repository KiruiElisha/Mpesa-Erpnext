import frappe
import requests
import base64
import codecs
from datetime import datetime
from frappe.model.document import Document

class MpesaIntegration(Document):
    def generate_access_token(self):
        credentials = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        headers = {"Authorization": f"Basic {credentials}"}

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            access_token = response.json()["access_token"]
            return access_token
        else:
            frappe.throw_exception(f"Failed to retrieve access token. Status code: {response.status_code}")

    def create_mpesa_transaction_document(self, transaction_number, amount, sales_invoice, transaction_status, payment_time):
        mpesa_transaction_doc = frappe.new_doc("Mpesa Transaction")
        mpesa_transaction_doc.transaction_number = transaction_number
        mpesa_transaction_doc.amount = amount
        mpesa_transaction_doc.sales_invoice = sales_invoice
        mpesa_transaction_doc.transaction_status = transaction_status
        mpesa_transaction_doc.payment_time = payment_time
        mpesa_transaction_doc.insert(ignore_permissions=True)

    def lipa_na_mpesa(self, phone, amount):
        access_token = self.generate_access_token()
        if access_token is None:
            return

        unformatted_time = datetime.now()
        formatted_time = unformatted_time.strftime("%Y%m%d%H%M%S")

        data_to_encode = self.shortcode + self.online_passkey + formatted_time
        encoded = base64.b64encode(data_to_encode.encode())
        decoded_password = encoded.decode("utf-8")

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {access_token}"}

        request_payload = {
            "BusinessShortCode": self.shortcode,
            "Password": decoded_password,
            "Timestamp": formatted_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": "https://mydomain.com/pat",
            "AccountReference": "Test",
            "TransactionDesc": "Test",
        }

        response = requests.post(api_url, json=request_payload, headers=headers)
        if response.status_code == 200:
            # Assuming the relevant information is available in the response
            transaction_number = response.json().get("TransactionNumber", "")
            amount = response.json().get("Amount", "")
            sales_invoice = response.json().get("SalesInvoice", "")
            transaction_status = response.json().get("TransactionStatus", "")
            payment_time = now()

            # Create the Mpesa Transaction document
            self.create_mpesa_transaction_document(transaction_number, amount, sales_invoice, transaction_status, payment_time)

        return response.json() if response.status_code == 200 else None

        return response.json() if response.status_code == 200 else None

    def verify_transaction(self, transaction_id):
        access_token = self.generate_access_token()
        if access_token is None:
            return None

        try:
            unformatted_time = datetime.now()
            formatted_time = unformatted_time.strftime("%Y%m%d%H%M%S")

            data_to_encode = self.shortcode + self.online_passkey + formatted_time
            encoded = base64.b64encode(data_to_encode.encode())
            decoded_password = encoded.decode("utf-8")

            api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/query"
            headers = {"Authorization": f"Bearer {access_token}"}

            request_payload = {
                "BusinessShortCode": self.shortcode,
                "Password": decoded_password,  # Use the same password as in the initiation
                "Timestamp": formatted_time,
                "TransactionID": transaction_id,
                "PartyA": self.shortcode,
                "IdentifierType": "4",  # Use the default value for PayBill
                "ResultURL": "https://mydomain.com/result",
                "QueueTimeOutURL": "https://mydomain.com/timeout",
                "Remarks": "Check transaction status",
                "Occasion": "Check status",
            }

            response = requests.post(api_url, json=request_payload, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def check_transaction_status(self, checkout_request_id):
        access_token = self.generate_access_token()
        if access_token is None:
            return None

        try:
            unformatted_time = datetime.now()
            formatted_time = unformatted_time.strftime("%Y%m%d%H%M%S")

            data_to_encode = self.shortcode + self.online_passkey + formatted_time
            encoded = base64.b64encode(data_to_encode.encode())
            decoded_password = encoded.decode("utf-8")

            api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/query"
            headers = {"Authorization": f"Bearer {access_token}"}

            request_payload = {
                "BusinessShortCode": self.shortcode,
                "Password": decoded_password,  # Use the same password as in the initiation
                "Timestamp": formatted_time,
                "TransactionID": checkout_request_id,
                "PartyA": self.shortcode,
                "IdentifierType": "4",  # Use the default value for PayBill
                "ResultURL": "https://mydomain.com/result",
                "QueueTimeOutURL": "https://mydomain.com/timeout",
                "Remarks": "Check transaction status",
                "Occasion": "Check status",
            }

            response = requests.post(api_url, json=request_payload, headers=headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses

            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

@frappe.whitelist()
def initiate_mpesa_payment(phone, amount):
    mpesa_integration = frappe.get_doc("Mpesa Integration")

    if not mpesa_integration.consumer_key or not mpesa_integration.consumer_secret \
            or not mpesa_integration.shortcode or not mpesa_integration.online_passkey:
        frappe.throw_exception("Please set the required fields in Mpesa Integration document.")

    return mpesa_integration.lipa_na_mpesa(phone, amount)

@frappe.whitelist()
def verify_mpesa_transaction(transaction_id):
    mpesa_integration = frappe.get_doc("Mpesa Integration")

    if not mpesa_integration.consumer_key or not mpesa_integration.consumer_secret \
            or not mpesa_integration.shortcode or not mpesa_integration.online_passkey:
        frappe.throw_exception("Please set the required fields in Mpesa Integration document.")

    return mpesa_integration.verify_transaction(transaction_id)

@frappe.whitelist()
def check_transaction_status(checkout_request_id):
    mpesa_integration = frappe.get_doc("Mpesa Integration")

    if not mpesa_integration.consumer_key or not mpesa_integration.consumer_secret \
            or not mpesa_integration.shortcode or not mpesa_integration.online_passkey:
        frappe.throw_exception("Please set the required fields in Mpesa Integration document.")

    return mpesa_integration.check_transaction_status(checkout_request_id)