"""
SumUp Terminal provider for cloud-based card-present payments.

Uses the SumUp Cloud API (Readers API) to push payment requests to SumUp
Solo card readers. The reader handles card presentation, and the POS polls
for checkout status until completion.

Integration mode: cloud
- No frontend SDK required
- Backend creates a checkout via SumUp Readers API
- SumUp cloud pushes the checkout to the Solo reader
- Reader handles card interaction
- POS polls GET /v0.1/checkouts/{id} for status

SumUp Cloud API docs: https://developer.sumup.com/terminal-payments/cloud-api
"""
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional

import requests

from pos_app.terminal_providers.base import TerminalProviderBase

logger = logging.getLogger(__name__)

# SumUp API base URL (same for test and live; environment controlled by API key type)
BASE_URL = 'https://api.sumup.com'


class SumUpTerminalProvider(TerminalProviderBase):
    provider_key = 'sumup_terminal'
    provider_name = 'SumUp Terminal'

    @property
    def integration_mode(self):
        return 'cloud'

    @property
    def credential_schema(self):
        return {
            'type': 'object',
            'properties': {
                'api_key': {
                    'type': 'string',
                    'title': 'API Key',
                    'description': 'SumUp API key (sup_sk_... for live, or test key)',
                    'required': True,
                    'secret': True,
                },
                'merchant_code': {
                    'type': 'string',
                    'title': 'Merchant Code',
                    'description': 'Your SumUp merchant code',
                    'required': True,
                },
            },
        }

    def validate_credentials(self, credentials):
        api_key = credentials.get('api_key', '')
        if not api_key:
            raise ValueError("SumUp API key is required")
        merchant_code = credentials.get('merchant_code', '')
        if not merchant_code:
            raise ValueError("SumUp merchant code is required")

    def _get_merchant_code(self):
        return self.credentials.get('merchant_code', '')

    def _get_affiliate_app_id(self):
        return self.config.get('affiliate_app_id', '')

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.credentials["api_key"]}',
        }

    # ── Connection ─────────────────────────────────────────────────

    def test_connection(self):
        """Test connection by listing readers."""
        try:
            merchant_code = self._get_merchant_code()
            url = f"{BASE_URL}/v0.1/merchants/{merchant_code}/readers"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                readers = data if isinstance(data, list) else data.get('items', [])
                return {
                    'success': True,
                    'message': f"Connected to SumUp. {len(readers)} reader(s) found.",
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid API key'}
            elif resp.status_code == 403:
                return {'success': False, 'message': 'API key does not have required permissions'}
            else:
                return {'success': False, 'message': f'SumUp API error: {resp.status_code}'}
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ── Reader Management ──────────────────────────────────────────

    def list_readers(self, location_id=None):
        """List readers via SumUp Readers API."""
        try:
            merchant_code = self._get_merchant_code()
            url = f"{BASE_URL}/v0.1/merchants/{merchant_code}/readers"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return {'success': False, 'message': f'Failed to list readers: {resp.status_code}', 'readers': []}

            data = resp.json()
            reader_list = data if isinstance(data, list) else data.get('items', [])
            readers = []
            for reader in reader_list:
                device = reader.get('device', {})
                readers.append({
                    'id': reader.get('id', ''),
                    'label': reader.get('name', device.get('identifier', '')),
                    'type': device.get('model', 'solo'),
                    'serial_number': device.get('identifier', ''),
                    'status': 'online' if reader.get('status') == 'paired' else 'offline',
                })

            return {'success': True, 'readers': readers}
        except Exception as e:
            logger.error(f"SumUp list readers error: {e}")
            return {'success': False, 'message': str(e), 'readers': []}

    # ── Cloud Payment Operations ───────────────────────────────────

    def initiate_cloud_payment(self, amount, currency, reader_id, metadata=None):
        """
        Create a checkout on a SumUp reader via Cloud API.

        SumUp amounts use a minor_unit system (e.g. 1500 with minor_unit=2 = 15.00).
        """
        merchant_code = self._get_merchant_code()

        # Convert amount to minor units
        amount_minor = int(Decimal(str(amount)) * 100)

        checkout_body = {
            'total_amount': {
                'currency': currency.upper(),
                'minor_unit': 2,
                'value': amount_minor,
            },
        }

        # Add affiliate key (required for Cloud API)
        affiliate_app_id = self._get_affiliate_app_id()
        if affiliate_app_id:
            checkout_body['affiliate'] = {'app_id': affiliate_app_id}

        # Add optional description
        if metadata and metadata.get('order_reference'):
            checkout_body['description'] = f"Order {metadata['order_reference']}"

        try:
            url = f"{BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}/checkout"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=checkout_body,
                timeout=30,
            )

            if resp.status_code not in (200, 201):
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get('message', f'SumUp API error: {resp.status_code}')
                return {
                    'success': False,
                    'error_code': 'CLOUD_PAYMENT_FAILED',
                    'message': error_msg,
                }

            data = resp.json()
            checkout_id = data.get('id', '')

            return {
                'success': True,
                'transaction_id': checkout_id,
                'status': 'pending',
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error_code': 'TIMEOUT',
                'message': 'Timed out creating reader checkout',
            }
        except Exception as e:
            logger.error(f"SumUp cloud payment error: {e}")
            return {'success': False, 'message': str(e)}

    def check_payment_status(self, transaction_id):
        """
        Poll the checkout status via SumUp Checkouts API.

        Statuses: PENDING -> PAID or FAILED or EXPIRED
        """
        try:
            url = f"{BASE_URL}/v0.1/checkouts/{transaction_id}"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return {
                    'success': False,
                    'status': 'failed',
                    'message': f'Failed to get checkout status: {resp.status_code}',
                }

            data = resp.json()
            status = data.get('status', '')

            status_map = {
                'PENDING': 'pending',
                'PAID': 'succeeded',
                'FAILED': 'failed',
                'EXPIRED': 'canceled',
            }

            result = {
                'success': True,
                'status': status_map.get(status, 'pending'),
            }

            if status == 'PAID':
                # Extract card details from transactions
                transactions = data.get('transactions', [])
                if transactions:
                    txn = transactions[0]
                    result['payment_id'] = txn.get('id', '')
                    result['transaction_code'] = txn.get('transaction_code', '')
                    result['amount'] = Decimal(str(txn.get('amount', 0)))
                    # SumUp doesn't always return card details in checkout response
                    result['card_brand'] = ''
                    result['last4'] = ''
                    result['entry_mode'] = txn.get('entry_mode', '')

            return result
        except Exception as e:
            logger.error(f"SumUp check status error: {e}")
            return {'success': False, 'status': 'failed', 'message': str(e)}

    def cancel_cloud_payment(self, transaction_id):
        """Terminate a pending checkout on the reader."""
        try:
            merchant_code = self._get_merchant_code()
            # SumUp terminate requires the reader_id, but we may not have it.
            # The transaction_id here is the checkout_id.
            # We need to use a stored reader_id from the provider account.
            reader_id = self.config.get('default_reader_id', '')
            if not reader_id:
                return {'success': False, 'message': 'Reader ID required for cancellation'}

            url = f"{BASE_URL}/v0.1/merchants/{merchant_code}/readers/{reader_id}/terminate"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                timeout=15,
            )

            if resp.status_code in (200, 204):
                return {'success': True}
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get('message', 'Terminate failed')
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"SumUp cancel error: {e}")
            return {'success': False, 'message': str(e)}

    def cancel_payment_intent(self, payment_intent_id):
        return self.cancel_cloud_payment(payment_intent_id)

    # ── Refunds ────────────────────────────────────────────────────

    def refund_payment(self, payment_intent_id, amount=None):
        """
        Refund a completed SumUp transaction.

        Full refund: POST /v0.1/me/refund/{transaction_id} with empty body.
        Partial refund: POST /v0.1/me/refund/{transaction_id} with amount.
        """
        try:
            url = f"{BASE_URL}/v0.1/me/refund/{payment_intent_id}"
            body = {}
            if amount is not None:
                body['amount'] = float(amount)

            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=body if body else None,
                timeout=30,
            )

            if resp.status_code in (200, 204):
                return {
                    'success': True,
                    'refund_id': payment_intent_id,
                    'status': 'refunded',
                }
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get('message', f'Refund failed: {resp.status_code}')
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"SumUp refund error: {e}")
            return {'success': False, 'message': str(e)}
