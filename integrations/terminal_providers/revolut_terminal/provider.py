"""
Revolut Terminal provider for cloud-based card-present payments.

Uses the Revolut Merchant API to push payment requests to Revolut Terminal
and Revolut Reader devices. The terminal handles card presentation, and the
POS polls for payment status until completion.

Integration mode: cloud
- No frontend SDK required
- Backend creates an order via Revolut Merchant API
- Backend pushes a payment intent to a specific terminal
- Terminal receives and displays the payment request
- Customer taps/inserts card on the terminal
- POS polls order status until completed

Revolut Terminal API docs:
  https://developer.revolut.com/docs/guides/in-person-payments/revolut-terminal/push-payments
"""
import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

import requests

from pos_app.terminal_providers.base import TerminalProviderBase

logger = logging.getLogger(__name__)

# API base URLs
SANDBOX_BASE = 'https://sandbox-merchant.revolut.com/api'
PRODUCTION_BASE = 'https://merchant.revolut.com/api'

# Revolut API version
API_VERSION = '2024-09-01'


class RevolutTerminalProvider(TerminalProviderBase):
    """Revolut Terminal cloud-based payment provider."""

    provider_key = 'revolut_terminal'
    provider_name = 'Revolut Terminal'

    @property
    def integration_mode(self):
        return 'cloud'

    @property
    def credential_schema(self):
        return {
            'type': 'object',
            'properties': {
                'secret_key': {
                    'type': 'string',
                    'title': 'Revolut Secret Key',
                    'description': 'Your Revolut Merchant API secret key',
                    'required': True,
                    'secret': True,
                },
            },
        }

    def validate_credentials(self, credentials):
        secret_key = credentials.get('secret_key', '')
        if not secret_key:
            raise ValueError("Revolut secret key is required")

    # ── Internal Helpers ──────────────────────────────────────────

    def _get_base_url(self):
        env = self.config.get('environment', 'sandbox')
        if env == 'production':
            return PRODUCTION_BASE
        return SANDBOX_BASE

    def _get_location_id(self):
        return self.config.get('location_id', '')

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.credentials["secret_key"]}',
            'Revolut-Api-Version': API_VERSION,
        }

    def _amount_to_minor(self, amount, currency: str) -> int:
        """Convert amount to minor currency units (cents/pence)."""
        zero_decimal = ['BIF', 'CLP', 'DJF', 'GNF', 'JPY', 'KMF', 'KRW',
                        'MGA', 'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF',
                        'XOF', 'XPF']
        if currency.upper() in zero_decimal:
            return int(Decimal(str(amount)))
        return int(Decimal(str(amount)) * 100)

    # ── Connection ────────────────────────────────────────────────

    def test_connection(self):
        try:
            url = f"{self._get_base_url()}/orders"
            resp = requests.get(
                url, headers=self._get_headers(), params={'limit': 1}, timeout=15
            )
            if resp.status_code in (200, 201):
                return {
                    'success': True,
                    'message': f"Connected to Revolut ({self.config.get('environment', 'sandbox')})",
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid API key'}
            elif resp.status_code == 403:
                return {'success': False, 'message': 'API key does not have required permissions'}
            else:
                return {'success': False, 'message': f'Revolut API error: {resp.status_code}'}
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ── Reader Management ─────────────────────────────────────────

    def list_readers(self, location_id=None):
        """List terminals via Revolut Terminals API."""
        try:
            url = f"{self._get_base_url()}/terminals"
            params = {}
            loc = location_id or self._get_location_id()
            if loc:
                params['location_id'] = loc

            resp = requests.get(
                url, headers=self._get_headers(), params=params, timeout=15
            )

            if resp.status_code != 200:
                return {
                    'success': False,
                    'message': f'Failed to list terminals: {resp.status_code}',
                    'readers': [],
                }

            data = resp.json()
            terminals = data if isinstance(data, list) else data.get('terminals', data.get('items', []))

            readers = []
            for terminal in terminals:
                readers.append({
                    'id': terminal.get('id', ''),
                    'label': terminal.get('name', terminal.get('label', '')),
                    'type': terminal.get('type', terminal.get('device_type', '')),
                    'serial_number': terminal.get('serial_number', ''),
                    'status': 'online' if terminal.get('status', '').upper() in ('ONLINE', 'ACTIVE', 'PAY_AT_COUNTER') else 'offline',
                    'location': terminal.get('location_id', ''),
                })

            return {'success': True, 'readers': readers}
        except Exception as e:
            logger.error(f"Revolut list terminals error: {e}")
            return {'success': False, 'message': str(e), 'readers': []}

    # ── Cloud Payment Operations ──────────────────────────────────

    def initiate_cloud_payment(self, amount, currency, reader_id, metadata=None):
        """
        Create an order and push a payment intent to the specified terminal.

        Flow:
        1. Create order with location_id
        2. Create payment for the order, targeting the terminal
        3. Terminal receives and displays the payment request
        """
        metadata = metadata or {}
        location_id = self._get_location_id()

        # Step 1: Create order
        order_data = {
            'amount': self._amount_to_minor(amount, currency),
            'currency': currency.upper(),
            'capture_mode': 'AUTOMATIC',
        }
        if location_id:
            order_data['location_id'] = location_id
        if metadata.get('order_reference'):
            order_data['merchant_order_ext_ref'] = str(metadata['order_reference'])[:128]
        if metadata.get('description'):
            order_data['description'] = str(metadata['description'])[:256]

        try:
            order_url = f"{self._get_base_url()}/orders"
            order_resp = requests.post(
                order_url, headers=self._get_headers(), json=order_data, timeout=30
            )

            if order_resp.status_code not in (200, 201):
                error_data = order_resp.json() if order_resp.content else {}
                error_msg = error_data.get('message', f'Revolut API error: {order_resp.status_code}')
                return {
                    'success': False,
                    'error_code': 'ORDER_CREATION_FAILED',
                    'message': error_msg,
                }

            order = order_resp.json()
            order_id = order.get('id', '')

            # Step 2: Push payment to terminal
            payment_data = {
                'terminal_id': reader_id,
            }

            payment_url = f"{self._get_base_url()}/orders/{order_id}/payments"
            payment_resp = requests.post(
                payment_url, headers=self._get_headers(), json=payment_data, timeout=30
            )

            if payment_resp.status_code not in (200, 201):
                error_data = payment_resp.json() if payment_resp.content else {}
                error_msg = error_data.get('message', f'Push payment failed: {payment_resp.status_code}')
                # Try to cancel the order we just created
                try:
                    requests.post(
                        f"{self._get_base_url()}/orders/{order_id}/cancel",
                        headers=self._get_headers(), timeout=10
                    )
                except Exception:
                    pass
                return {
                    'success': False,
                    'error_code': 'PUSH_PAYMENT_FAILED',
                    'message': error_msg,
                }

            return {
                'success': True,
                'transaction_id': order_id,
                'status': 'pending',
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error_code': 'TIMEOUT',
                'message': 'Timed out initiating terminal payment',
            }
        except Exception as e:
            logger.error(f"Revolut cloud payment error: {e}")
            return {'success': False, 'message': str(e)}

    def check_payment_status(self, transaction_id):
        """
        Poll the order status.

        Revolut order states: PENDING → PROCESSING → AUTHORISED → COMPLETED
        Also: CANCELLED, FAILED
        """
        try:
            url = f"{self._get_base_url()}/orders/{transaction_id}"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return {
                    'success': False,
                    'status': 'failed',
                    'message': f'Failed to get order status: {resp.status_code}',
                }

            data = resp.json()
            state = data.get('state', '')

            status_map = {
                'PENDING': 'pending',
                'PROCESSING': 'pending',
                'AUTHORISED': 'pending',
                'COMPLETED': 'succeeded',
                'CANCELLED': 'canceled',
                'FAILED': 'failed',
            }

            result = {
                'success': True,
                'status': status_map.get(state, 'pending'),
            }

            if state == 'COMPLETED':
                # Extract payment details
                payments = data.get('payments', [])
                if payments:
                    latest = payments[-1]
                    pm = latest.get('payment_method', {})
                    card = pm.get('card', {})
                    if card:
                        result['card_brand'] = (card.get('card_brand', '') or '').lower()
                        result['last4'] = card.get('card_last_four', '')

                order_amount = data.get('order_amount', {})
                amount_val = order_amount.get('value', 0)
                currency = order_amount.get('currency', data.get('currency', 'GBP'))
                zero_decimal = ['JPY', 'KRW']
                if currency.upper() in zero_decimal:
                    result['amount'] = Decimal(str(amount_val))
                else:
                    result['amount'] = Decimal(str(amount_val)) / 100

            elif state in ('CANCELLED', 'FAILED'):
                result['message'] = data.get('reason', f'Payment {state.lower()}')

            return result
        except Exception as e:
            logger.error(f"Revolut check status error: {e}")
            return {'success': False, 'status': 'failed', 'message': str(e)}

    def cancel_cloud_payment(self, transaction_id):
        """Cancel a pending order/payment."""
        try:
            url = f"{self._get_base_url()}/orders/{transaction_id}/cancel"
            resp = requests.post(url, headers=self._get_headers(), json={}, timeout=15)

            if resp.status_code in (200, 201):
                return {'success': True}
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get('message', 'Cancel failed')
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"Revolut cancel error: {e}")
            return {'success': False, 'message': str(e)}

    def cancel_payment_intent(self, payment_intent_id):
        return self.cancel_cloud_payment(payment_intent_id)

    # ── Refunds ───────────────────────────────────────────────────

    def refund_payment(self, payment_intent_id, amount=None):
        """Refund a completed Revolut terminal payment."""
        try:
            refund_data = {}
            if amount is not None:
                # Get order to determine currency
                order_url = f"{self._get_base_url()}/orders/{payment_intent_id}"
                order_resp = requests.get(order_url, headers=self._get_headers(), timeout=15)
                if order_resp.status_code == 200:
                    order = order_resp.json()
                    currency = order.get('currency', 'GBP')
                    refund_data['amount'] = self._amount_to_minor(amount, currency)

            url = f"{self._get_base_url()}/orders/{payment_intent_id}/refund"
            resp = requests.post(
                url, headers=self._get_headers(), json=refund_data or None, timeout=30
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'refund_id': data.get('id', ''),
                    'status': 'refunded',
                }
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get('message', 'Refund failed')
                return {'success': False, 'message': error_msg}
        except Exception as e:
            logger.error(f"Revolut refund error: {e}")
            return {'success': False, 'message': str(e)}
