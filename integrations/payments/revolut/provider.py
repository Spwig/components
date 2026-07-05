"""
Revolut payment provider for online checkout payments.

Uses the Revolut Merchant API to process orders, capture payments,
issue refunds, and handle webhooks. Supports cards, Revolut Pay,
Apple Pay, Google Pay, and Pay by Bank.

Revolut Merchant API docs: https://developer.revolut.com/docs/merchant/merchant-api
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from payment_providers.providers.base import PaymentProviderBase

logger = logging.getLogger(__name__)

# API base URLs
SANDBOX_BASE = 'https://sandbox-merchant.revolut.com/api'
PRODUCTION_BASE = 'https://merchant.revolut.com/api'

# Revolut API version
API_VERSION = '2024-09-01'

# Status mapping: Revolut order states → normalized states
ORDER_STATUS_MAP = {
    'PENDING': 'created',
    'PROCESSING': 'processing',
    'AUTHORISED': 'authorized',
    'COMPLETED': 'succeeded',
    'CANCELLED': 'canceled',
    'FAILED': 'failed',
    'REFUNDED': 'refunded',
}

# Payment status mapping for webhook events
PAYMENT_STATUS_MAP = {
    'pending': 'pending',
    'authentication_challenge': 'requires_action',
    'authentication_verified': 'processing',
    'authorisation_started': 'processing',
    'authorisation_passed': 'authorized',
    'authorised': 'authorized',
    'capture_started': 'processing',
    'captured': 'succeeded',
    'completed': 'succeeded',
    'declined': 'failed',
    'soft_declined': 'failed',
    'cancelled': 'canceled',
    'failed': 'failed',
}


class RevolutProvider(PaymentProviderBase):
    """Revolut Merchant API payment provider."""

    provider_key = 'revolut'
    provider_name = 'Revolut'

    # ── Properties ────────────────────────────────────────────────

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'charge': True,
            'authorize': True,
            'capture': True,
            'void': True,
            'refund': True,
            'partial_refund': True,
            'recurring': False,
            'save_payment_method': False,
            'hosted_checkout': True,
            'integrated_checkout': True,
            'webhooks': True,
            'multi_currency': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'secret_key': {
                    'type': 'string',
                    'title': 'Secret API Key',
                    'description': 'Your Revolut Merchant API secret key',
                    'required': True,
                    'secret': True,
                },
                'public_key': {
                    'type': 'string',
                    'title': 'Public API Key',
                    'description': 'Your Revolut public key for the Checkout Widget',
                    'required': False,
                },
                'webhook_secret': {
                    'type': 'string',
                    'title': 'Webhook Signing Secret',
                    'description': 'Secret for verifying webhook signatures',
                    'required': False,
                    'secret': True,
                },
                'environment': {
                    'type': 'string',
                    'title': 'Environment',
                    'enum': ['sandbox', 'production'],
                    'default': 'sandbox',
                    'required': True,
                },
                'capture_mode': {
                    'type': 'string',
                    'title': 'Capture Mode',
                    'enum': ['AUTOMATIC', 'MANUAL'],
                    'default': 'AUTOMATIC',
                    'required': False,
                },
            },
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        return ['card', 'digital_wallet', 'revolut_pay', 'pay_by_bank']

    @property
    def supported_currencies(self) -> List[str]:
        return [
            'AUD', 'CAD', 'CHF', 'CZK', 'DKK', 'EUR', 'GBP', 'HKD', 'HUF',
            'ILS', 'JPY', 'MXN', 'NOK', 'NZD', 'PLN', 'RON', 'SEK', 'SGD',
            'TRY', 'USD', 'ZAR',
        ]

    @property
    def supported_countries(self) -> List[str]:
        return [
            'GB', 'IE', 'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE',
            'FI', 'FR', 'DE', 'GR', 'HU', 'IS', 'IT', 'LV', 'LT', 'LU',
            'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE',
            'CH', 'US', 'AU', 'CA', 'SG', 'JP', 'NZ', 'HK', 'MX', 'ZA',
        ]

    # ── Credential Validation ─────────────────────────────────────

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        secret_key = credentials.get('secret_key', '')
        if not secret_key:
            raise ValueError("Revolut secret key is required")
        if not secret_key.startswith(('sk_live_', 'sk_test_', 'sk_sandbox_', 'sk_')):
            raise ValueError(
                "Invalid Revolut secret key format. "
                "Key should start with 'sk_live_' (production) or 'sk_test_'/'sk_sandbox_' (sandbox)."
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive credential values."""
        redacted = dict(credentials)
        sensitive_substrings = ('secret_key', 'webhook_secret')
        for key, value in redacted.items():
            if isinstance(value, str) and any(s in key for s in sensitive_substrings):
                if len(value) > 12:
                    redacted[key] = f"{value[:8]}***{value[-4:]}"
                elif value:
                    redacted[key] = '***'
        return redacted

    # ── Internal Helpers ──────────────────────────────────────────

    def _get_base_url(self) -> str:
        env = self.credentials.get('environment', 'sandbox')
        if env == 'production':
            return PRODUCTION_BASE
        return SANDBOX_BASE

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.credentials["secret_key"]}',
            'Revolut-Api-Version': API_VERSION,
        }

    def _safe_json(self, resp):
        """Safely parse JSON response, returning empty dict on failure."""
        try:
            return resp.json() if resp.content else {}
        except (ValueError, requests.exceptions.JSONDecodeError):
            return {'message': f'Non-JSON response: {resp.status_code}'}

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30,
        idempotency_key: Optional[str] = None,
    ) -> requests.Response:
        url = f"{self._get_base_url()}{endpoint}"
        headers = self._get_headers()
        if idempotency_key:
            headers['Revolut-Request-Id'] = idempotency_key
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None,
                params=params,
                timeout=timeout,
            )
            return resp
        except requests.exceptions.Timeout:
            logger.error(f"Revolut API timeout: {method} {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Revolut API request error: {method} {endpoint} - {e}")
            raise

    def _amount_to_minor(self, amount, currency: str) -> int:
        """Convert amount to minor currency units (cents/pence)."""
        zero_decimal = ['BIF', 'CLP', 'DJF', 'GNF', 'JPY', 'KMF', 'KRW',
                        'MGA', 'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF',
                        'XOF', 'XPF']
        if currency.upper() in zero_decimal:
            return int(Decimal(str(amount)))
        return int(Decimal(str(amount)) * 100)

    def _amount_from_minor(self, minor_amount: int, currency: str) -> Decimal:
        """Convert minor currency units back to standard amount."""
        zero_decimal = ['BIF', 'CLP', 'DJF', 'GNF', 'JPY', 'KMF', 'KRW',
                        'MGA', 'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF',
                        'XOF', 'XPF']
        if currency.upper() in zero_decimal:
            return Decimal(str(minor_amount))
        return Decimal(str(minor_amount)) / 100

    def _map_order_status(self, revolut_state: str) -> str:
        return ORDER_STATUS_MAP.get(revolut_state, 'unknown')

    # ── Connection Test ───────────────────────────────────────────

    def test_connection(self) -> Dict[str, Any]:
        try:
            resp = self._make_request('GET', '/orders', params={'limit': 1})
            if resp.status_code in (200, 201):
                env = self.credentials.get('environment', 'sandbox')
                return {
                    'success': True,
                    'message': f'Connected to Revolut ({env})',
                    'details': {
                        'environment': env,
                        'api_base': self._get_base_url(),
                    },
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
            logger.error(f"Revolut test_connection error: {e}")
            return {'success': False, 'message': str(e)}

    # ── Payment Processing ────────────────────────────────────────

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        order_data = {
            'amount': self._amount_to_minor(amount, currency),
            'currency': currency.upper(),
            'capture_mode': 'AUTOMATIC',
        }

        if metadata.get('order_id'):
            order_data['merchant_order_ext_ref'] = str(metadata['order_id'])
        if metadata.get('customer_email'):
            order_data['email'] = metadata['customer_email']
        if metadata.get('description'):
            order_data['description'] = metadata['description']

        try:
            resp = self._make_request('POST', '/orders', data=order_data)
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'transaction_id': data.get('id', ''),
                    'provider_transaction_id': data.get('id', ''),
                    'status': self._map_order_status(data.get('state', '')),
                    'amount': amount,
                    'currency': currency.upper(),
                    'checkout_url': data.get('checkout_url', ''),
                    'message': 'Order created successfully',
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Revolut API error: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut charge error: {e}")
            return {'success': False, 'message': str(e)}

    def authorize(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        order_data = {
            'amount': self._amount_to_minor(amount, currency),
            'currency': currency.upper(),
            'capture_mode': 'MANUAL',
        }

        if metadata.get('order_id'):
            order_data['merchant_order_ext_ref'] = str(metadata['order_id'])
        if metadata.get('customer_email'):
            order_data['email'] = metadata['customer_email']
        if metadata.get('description'):
            order_data['description'] = metadata['description']

        try:
            resp = self._make_request('POST', '/orders', data=order_data)
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'authorization_id': data.get('id', ''),
                    'provider_authorization_id': data.get('id', ''),
                    'status': 'authorized',
                    'amount': amount,
                    'currency': currency.upper(),
                    'checkout_url': data.get('checkout_url', ''),
                    'message': 'Authorization created successfully',
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Revolut API error: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut authorize error: {e}")
            return {'success': False, 'message': str(e)}

    def capture(
        self,
        authorization_id: str,
        amount: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        capture_data = {}
        if amount is not None:
            # Retrieve order to get currency for conversion
            order_resp = self._make_request('GET', f'/orders/{authorization_id}')
            if order_resp.status_code != 200:
                return {
                    'success': False,
                    'message': f'Failed to retrieve order for partial capture: {order_resp.status_code}',
                }
            order = order_resp.json()
            currency = order.get('currency', 'GBP')
            capture_data['amount'] = self._amount_to_minor(amount, currency)

        try:
            resp = self._make_request(
                'POST', f'/orders/{authorization_id}/capture',
                data=capture_data or None,
                idempotency_key=f'capture-{authorization_id}',
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                captured_amount = amount
                if not captured_amount:
                    currency = data.get('currency', 'GBP')
                    captured_amount = self._amount_from_minor(
                        (data.get('order_amount') or {}).get('value', 0), currency
                    )
                return {
                    'success': True,
                    'transaction_id': data.get('id', authorization_id),
                    'provider_transaction_id': data.get('id', authorization_id),
                    'status': 'completed',
                    'amount': captured_amount,
                    'message': 'Payment captured successfully',
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Capture failed: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut capture error: {e}")
            return {'success': False, 'message': str(e)}

    def void(
        self,
        authorization_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            resp = self._make_request('POST', f'/orders/{authorization_id}/cancel')
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'authorization_id': authorization_id,
                    'status': 'voided',
                    'message': 'Authorization voided successfully',
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Void failed: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut void error: {e}")
            return {'success': False, 'message': str(e)}

    def refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        refund_data = {}
        if amount is not None:
            # Retrieve order to get currency
            order_resp = self._make_request('GET', f'/orders/{transaction_id}')
            if order_resp.status_code != 200:
                return {
                    'success': False,
                    'message': f'Failed to retrieve order for partial refund: {order_resp.status_code}',
                }
            order = order_resp.json()
            currency = order.get('currency', 'GBP')
            refund_data['amount'] = self._amount_to_minor(amount, currency)
        if reason:
            refund_data['description'] = reason

        try:
            resp = self._make_request(
                'POST', f'/orders/{transaction_id}/refund',
                data=refund_data or None,
                idempotency_key=f'refund-{transaction_id}-{uuid.uuid4().hex[:8]}',
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'refund_id': data.get('id', ''),
                    'provider_refund_id': data.get('id', ''),
                    'status': 'completed',
                    'amount': amount,
                    'message': 'Refund processed successfully',
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Refund failed: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut refund error: {e}")
            return {'success': False, 'message': str(e)}

    # ── Webhook Handling ──────────────────────────────────────────

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        webhook_secret = self.credentials.get('webhook_secret', '')
        if not webhook_secret:
            logger.error("Revolut webhook secret not configured - cannot verify webhook signature")
            return False

        try:
            # Revolut signature format: v1.{hmac}
            if not signature or '.' not in signature:
                logger.warning("Invalid Revolut webhook signature format")
                return False

            version, received_hmac = signature.split('.', 1)
            if version != 'v1':
                logger.warning(f"Unsupported Revolut signature version: {version}")
                return False

            timestamp = kwargs.get('timestamp', '')
            # Revolut signs: {version}.{timestamp}.{payload}
            payload_to_sign = f"v1.{timestamp}.{payload.decode('utf-8')}"
            computed_hmac = hmac.new(
                webhook_secret.encode('utf-8'),
                payload_to_sign.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(computed_hmac, received_hmac)
        except Exception as e:
            logger.error(f"Revolut webhook verification error: {e}")
            return False

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = payload.get('order_id', '')

        if event_type == 'ORDER_COMPLETED':
            return {
                'success': True,
                'handled': True,
                'action': 'payment_completed',
                'event_type': 'payment.succeeded',
                'transaction_id': order_id,
                'status': 'succeeded',
                'raw_event': payload,
            }
        elif event_type == 'ORDER_AUTHORISED':
            return {
                'success': True,
                'handled': True,
                'action': 'payment_authorized',
                'event_type': 'payment.authorized',
                'transaction_id': order_id,
                'status': 'authorized',
                'raw_event': payload,
            }
        elif event_type == 'ORDER_CANCELLED':
            return {
                'success': True,
                'handled': True,
                'action': 'payment_canceled',
                'event_type': 'payment.canceled',
                'transaction_id': order_id,
                'status': 'canceled',
                'raw_event': payload,
            }
        elif event_type in ('ORDER_FAILED', 'ORDER_PAYMENT_FAILED', 'ORDER_PAYMENT_DECLINED'):
            return {
                'success': True,
                'handled': True,
                'action': 'payment_failed',
                'event_type': 'payment.failed',
                'transaction_id': order_id,
                'status': 'failed',
                'error': payload.get('reason', ''),
                'raw_event': payload,
            }
        elif event_type == 'ORDER_PAYMENT_AUTHENTICATED':
            return {
                'success': True,
                'handled': True,
                'action': 'payment_authenticated',
                'event_type': 'payment.authenticated',
                'transaction_id': order_id,
                'status': 'processing',
                'raw_event': payload,
            }
        elif event_type == 'ORDER_REFUNDED':
            return {
                'success': True,
                'handled': True,
                'action': 'payment_refunded',
                'event_type': 'payment.refunded',
                'transaction_id': order_id,
                'status': 'refunded',
                'raw_event': payload,
            }
        else:
            logger.info(f"Unhandled Revolut webhook event: {event_type}")
            return {
                'success': True,
                'handled': False,
                'event_type': event_type,
                'raw_event': payload,
            }

    # ── Checkout Orchestration ────────────────────────────────────

    def create_payment_intent_for_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        capture_mode = self.credentials.get('capture_mode', 'AUTOMATIC')

        order_data = {
            'amount': self._amount_to_minor(amount, currency),
            'currency': currency.upper(),
            'capture_mode': capture_mode,
        }

        if metadata.get('order_id'):
            order_data['merchant_order_ext_ref'] = str(metadata['order_id'])
        if customer_email:
            order_data['email'] = customer_email
        if metadata.get('description'):
            order_data['description'] = metadata['description']

        try:
            resp = self._make_request('POST', '/orders', data=order_data)
            if resp.status_code in (200, 201):
                data = resp.json()
                order_id = data.get('id', '')
                token = data.get('token', '')
                checkout_url = data.get('checkout_url', '')
                state = data.get('state', 'PENDING')

                # Build handler_config for plugin architecture (v1.1.0)
                handler_config = {
                    'order_id': order_id,
                    'token': token,
                    'public_key': self.credentials.get('public_key', ''),
                    'environment': self.credentials.get('environment', 'sandbox'),
                    'currency': currency.upper(),
                    'amount': self._amount_to_minor(amount, currency),
                }

                return {
                    'success': True,
                    'provider_intent_id': order_id,
                    'client_secret': token,
                    'checkout_url': checkout_url,
                    'status': self._map_order_status(state),
                    'requires_action': False,
                    'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    'handler_config': handler_config,
                    'raw_response': data,
                }
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Revolut API error: {resp.status_code}'),
                    'error_code': error.get('code', ''),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut create_payment_intent error: {e}")
            return {'success': False, 'message': str(e)}

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        try:
            resp = self._make_request('GET', f'/orders/{intent_id}')
            if resp.status_code == 200:
                data = resp.json()
                state = data.get('state', '')
                normalized_status = self._map_order_status(state)
                requires_action = state == 'PENDING'

                result = {
                    'success': True,
                    'provider_intent_id': data.get('id', intent_id),
                    'status': normalized_status,
                    'provider_status': state,
                    'requires_action': requires_action,
                    'raw_response': data,
                }

                # Extract payment details if available
                payments = data.get('payments', [])
                if payments:
                    latest = payments[-1]
                    pm_details = latest.get('payment_method', {})
                    result['payment_method_type'] = pm_details.get('type', '')
                    card = pm_details.get('card', {})
                    if card:
                        result['payment_method_last4'] = card.get('card_last_four', '')
                        result['payment_method_brand'] = card.get('card_brand', '')

                if normalized_status == 'failed':
                    result['error'] = {
                        'code': data.get('reason_code', ''),
                        'message': data.get('reason', 'Payment failed'),
                    }

                return result
            else:
                error = self._safe_json(resp)
                return {
                    'success': False,
                    'message': error.get('message', f'Failed to retrieve order: {resp.status_code}'),
                    'raw_response': error,
                }
        except Exception as e:
            logger.error(f"Revolut retrieve_payment_intent error: {e}")
            return {'success': False, 'message': str(e)}

    def confirm_payment_intent(
        self,
        intent_id: str,
        confirmation_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Revolut handles confirmation via their checkout widget/page.
        # After customer completes, we just retrieve the order status.
        return self.retrieve_payment_intent(intent_id)

    def cancel_payment_intent(
        self,
        intent_id: str,
        cancellation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.void(intent_id)

    # ── Hosted Checkout ───────────────────────────────────────────

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = self.create_payment_intent_for_checkout(
            amount=amount,
            currency=currency,
            return_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )
        if result.get('success'):
            return {
                'success': True,
                'session_id': result.get('provider_intent_id', ''),
                'checkout_url': result.get('checkout_url', ''),
                'message': 'Checkout session created',
                'raw_response': result.get('raw_response', {}),
            }
        return result
