"""
Square Terminal provider for cloud-based card-present payments.

Uses the Square Terminal Checkouts API to push payment requests to Square
card readers. The reader handles card presentation, and the POS polls for
the checkout status until completion.

Integration mode: cloud
- No frontend SDK required
- Backend creates a Terminal Checkout via Square API
- Square cloud pushes the checkout to the reader
- Reader handles card interaction
- POS polls GET /v2/terminals/checkouts/{id} for status

Square Terminal API docs: https://developer.squareup.com/docs/terminal-api/overview
"""
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional

import requests

from pos_app.terminal_providers.base import TerminalProviderBase

logger = logging.getLogger(__name__)

# Square API base URLs
BASE_URLS = {
    'sandbox': 'https://connect.squareupsandbox.com/v2',
    'production': 'https://connect.squareup.com/v2',
}

# Square API version header
SQUARE_VERSION = '2025-10-16'

# Default timeout for checkout (5 minutes max)
DEFAULT_DEADLINE = 'PT5M'


class SquareTerminalProvider(TerminalProviderBase):
    provider_key = 'square_terminal'
    provider_name = 'Square Terminal'

    @property
    def integration_mode(self):
        return 'cloud'

    @property
    def credential_schema(self):
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'title': 'Access Token',
                    'description': 'Square access token with PAYMENTS_WRITE and DEVICES_READ permissions',
                    'required': True,
                    'secret': True,
                },
            },
        }

    def validate_credentials(self, credentials):
        access_token = credentials.get('access_token', '')
        if not access_token:
            raise ValueError("Square access token is required")

    def _get_base_url(self):
        env = self.config.get('environment', 'sandbox')
        return BASE_URLS.get(env, BASE_URLS['sandbox'])

    def _get_location_id(self):
        return self.config.get('location_id', '')

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.credentials["access_token"]}',
            'Square-Version': SQUARE_VERSION,
        }

    # ── Connection ─────────────────────────────────────────────────

    def test_connection(self):
        """Test connection by listing devices."""
        try:
            url = f"{self._get_base_url()}/devices"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                devices = data.get('devices', [])
                return {
                    'success': True,
                    'message': f"Connected to Square. {len(devices)} device(s) found.",
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid access token'}
            elif resp.status_code == 403:
                return {'success': False, 'message': 'Access token does not have required permissions'}
            else:
                return {'success': False, 'message': f'Square API error: {resp.status_code}'}
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ── Reader Management ──────────────────────────────────────────

    def list_readers(self, location_id=None):
        """List devices via Square Devices API."""
        try:
            url = f"{self._get_base_url()}/devices"
            params = {}
            loc = location_id or self._get_location_id()
            if loc:
                params['location_id'] = loc

            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=15)

            if resp.status_code != 200:
                return {'success': False, 'message': f'Failed to list devices: {resp.status_code}', 'readers': []}

            data = resp.json()
            readers = []
            for device in data.get('devices', []):
                attrs = device.get('attributes', {})
                status_info = device.get('status', {})
                readers.append({
                    'id': device.get('id', ''),
                    'label': attrs.get('name', attrs.get('manufacturers_id', '')),
                    'type': attrs.get('model', ''),
                    'serial_number': attrs.get('manufacturers_id', ''),
                    'status': 'online' if status_info.get('category') == 'AVAILABLE' else 'offline',
                })

            return {'success': True, 'readers': readers}
        except Exception as e:
            logger.error(f"Square list devices error: {e}")
            return {'success': False, 'message': str(e), 'readers': []}

    # ── Cloud Payment Operations ───────────────────────────────────

    def initiate_cloud_payment(self, amount, currency, reader_id, metadata=None):
        """
        Create a Terminal Checkout on Square and push it to the reader.

        Square amounts are in the smallest denomination (cents for USD).
        """
        idempotency_key = str(uuid.uuid4())

        # Convert amount to smallest unit (cents)
        amount_cents = int(Decimal(str(amount)) * 100)

        checkout_body = {
            'idempotency_key': idempotency_key,
            'checkout': {
                'amount_money': {
                    'amount': amount_cents,
                    'currency': currency.upper(),
                },
                'device_options': {
                    'device_id': reader_id,
                    'skip_receipt_screen': False,
                    'collect_signature': False,
                },
                'payment_type': 'CARD_PRESENT',
                'deadline_duration': DEFAULT_DEADLINE,
            },
        }

        # Add optional reference
        if metadata:
            if metadata.get('order_reference'):
                checkout_body['checkout']['reference_id'] = str(metadata['order_reference'])[:40]
            if metadata.get('note'):
                checkout_body['checkout']['note'] = str(metadata['note'])[:500]

        try:
            url = f"{self._get_base_url()}/terminals/checkouts"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=checkout_body,
                timeout=30,
            )

            if resp.status_code not in (200, 201):
                error_data = resp.json() if resp.content else {}
                errors = error_data.get('errors', [{}])
                error_msg = errors[0].get('detail', f'Square API error: {resp.status_code}') if errors else f'Square API error: {resp.status_code}'
                return {
                    'success': False,
                    'error_code': 'CLOUD_PAYMENT_FAILED',
                    'message': error_msg,
                }

            data = resp.json()
            checkout = data.get('checkout', {})
            checkout_id = checkout.get('id', '')

            return {
                'success': True,
                'transaction_id': checkout_id,
                'status': 'pending',
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error_code': 'TIMEOUT',
                'message': 'Timed out creating terminal checkout',
            }
        except Exception as e:
            logger.error(f"Square cloud payment error: {e}")
            return {'success': False, 'message': str(e)}

    def check_payment_status(self, transaction_id):
        """
        Poll the Terminal Checkout status.

        Statuses: PENDING -> IN_PROGRESS -> COMPLETED or CANCELED
        """
        try:
            url = f"{self._get_base_url()}/terminals/checkouts/{transaction_id}"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return {
                    'success': False,
                    'status': 'failed',
                    'message': f'Failed to get checkout status: {resp.status_code}',
                }

            data = resp.json()
            checkout = data.get('checkout', {})
            status = checkout.get('status', '')

            status_map = {
                'PENDING': 'pending',
                'IN_PROGRESS': 'pending',
                'CANCEL_REQUESTED': 'pending',
                'COMPLETED': 'succeeded',
                'CANCELED': 'canceled',
            }

            result = {
                'success': True,
                'status': status_map.get(status, 'pending'),
            }

            if status == 'COMPLETED':
                # Get payment details
                payment_ids = checkout.get('payment_ids', [])
                if payment_ids:
                    result['payment_id'] = payment_ids[0]
                    # Fetch payment details for card info
                    card_info = self._get_payment_card_info(payment_ids[0])
                    if card_info:
                        result['card_brand'] = card_info.get('card_brand', '')
                        result['last4'] = card_info.get('last4', '')

                amount_money = checkout.get('amount_money', {})
                result['amount'] = Decimal(str(amount_money.get('amount', 0))) / 100

            elif status == 'CANCELED':
                result['cancel_reason'] = checkout.get('cancel_reason', '')

            return result
        except Exception as e:
            logger.error(f"Square check status error: {e}")
            return {'success': False, 'status': 'failed', 'message': str(e)}

    def cancel_cloud_payment(self, transaction_id):
        """Cancel a pending or in-progress checkout."""
        try:
            url = f"{self._get_base_url()}/terminals/checkouts/{transaction_id}/cancel"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json={},
                timeout=15,
            )

            if resp.status_code == 200:
                return {'success': True}
            else:
                error_data = resp.json() if resp.content else {}
                errors = error_data.get('errors', [{}])
                error_msg = errors[0].get('detail', 'Cancel failed') if errors else 'Cancel failed'
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"Square cancel error: {e}")
            return {'success': False, 'message': str(e)}

    def cancel_payment_intent(self, payment_intent_id):
        return self.cancel_cloud_payment(payment_intent_id)

    # ── Refunds ────────────────────────────────────────────────────

    def refund_payment(self, payment_intent_id, amount=None):
        """Refund a completed Square payment."""
        try:
            # First get the payment to know the amount
            payment_url = f"{self._get_base_url()}/payments/{payment_intent_id}"
            payment_resp = requests.get(payment_url, headers=self._get_headers(), timeout=15)

            if payment_resp.status_code != 200:
                return {'success': False, 'message': f'Failed to fetch payment: {payment_resp.status_code}'}

            payment_data = payment_resp.json().get('payment', {})
            amount_money = payment_data.get('amount_money', {})

            refund_amount = int(Decimal(str(amount)) * 100) if amount else amount_money.get('amount')
            currency = amount_money.get('currency', 'USD')

            refund_body = {
                'idempotency_key': str(uuid.uuid4()),
                'payment_id': payment_intent_id,
                'amount_money': {
                    'amount': refund_amount,
                    'currency': currency,
                },
            }

            url = f"{self._get_base_url()}/refunds"
            resp = requests.post(url, headers=self._get_headers(), json=refund_body, timeout=30)

            if resp.status_code in (200, 201):
                refund = resp.json().get('refund', {})
                return {
                    'success': True,
                    'refund_id': refund.get('id', ''),
                    'status': 'refunded',
                }
            else:
                error_data = resp.json() if resp.content else {}
                errors = error_data.get('errors', [{}])
                error_msg = errors[0].get('detail', 'Refund failed') if errors else 'Refund failed'
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"Square refund error: {e}")
            return {'success': False, 'message': str(e)}

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_payment_card_info(self, payment_id):
        """Fetch card details from a completed payment."""
        try:
            url = f"{self._get_base_url()}/payments/{payment_id}"
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                payment = resp.json().get('payment', {})
                card_details = payment.get('card_details', {})
                card = card_details.get('card', {})
                return {
                    'card_brand': (card.get('card_brand', '') or '').lower(),
                    'last4': card.get('last_4', ''),
                }
        except Exception:
            pass
        return None
