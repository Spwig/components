"""
Square Subscription Provider
Fallback mode - uses internal billing engine.
"""
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.utils import timezone
import logging
import uuid
import hmac
import hashlib
import base64

from subscriptions.provider_base import FallbackSubscriptionProvider, register_provider

logger = logging.getLogger(__name__)

# Zero-decimal currencies (amount is already in smallest unit)
ZERO_DECIMAL_CURRENCIES = {'JPY', 'KRW', 'VND', 'BIF', 'CLP', 'DJF',
                           'GNF', 'ISK', 'KMF', 'MGA', 'PYG', 'RWF',
                           'UGX', 'VUV', 'XAF', 'XOF', 'XPF'}


def _to_smallest_unit(amount: Decimal, currency: str) -> int:
    """Convert a decimal amount to the smallest currency unit (integer)."""
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@register_provider('square')
class SquareSubscriptionProvider(FallbackSubscriptionProvider):
    """
    Square provider using fallback billing engine.
    Square has limited subscription API support, so we manage
    billing internally and use Square only for charging.
    """

    def _get_square_client(self):
        """Get configured Square client (supports dual-credential structure)."""
        try:
            from square.client import Square, SquareEnvironment
        except ImportError:
            raise ImportError(
                "Square SDK not installed. Install with: pip install squareup>=38.0.0"
            )

        config = self.config

        # Handle dual-credential structure (test_mode + prefixed keys)
        if 'test_mode' in config and any(
            k.startswith('test_') or k.startswith('live_') for k in config.keys()
        ):
            test_mode = config.get('test_mode', True)
            prefix = 'test_' if test_mode else 'live_'
            access_token = config.get(f'{prefix}access_token', '')
            environment = SquareEnvironment.SANDBOX if test_mode else SquareEnvironment.PRODUCTION
        else:
            # Legacy structure
            access_token = config.get('access_token', '')
            env_str = config.get('environment', 'sandbox')
            environment = (SquareEnvironment.PRODUCTION
                           if env_str == 'production'
                           else SquareEnvironment.SANDBOX)

        return Square(
            token=access_token,
            environment=environment,
        )

    # ===========================
    # Customer & Token Management
    # ===========================

    def create_customer(self, user, email: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a Square Customer.

        Args:
            user: Django User instance
            email: Customer email
            metadata: Optional metadata

        Returns:
            dict: {'customer_id': str, 'metadata': dict}
        """
        client = self._get_square_client()

        try:
            body = {
                'given_name': user.first_name or user.username,
                'family_name': user.last_name or '',
                'email_address': email,
                'reference_id': str(user.id),
            }

            result = client.customers.create_customer(body)
            customer = result.customer

            if customer:
                customer_id = customer.id

                logger.info(f"Created Square customer: {customer_id} for user {user.id}")

                return {
                    'customer_id': customer_id,
                    'metadata': metadata or {},
                }
            else:
                errors = result.errors or []
                logger.error(f"Failed to create Square customer: {errors}")
                raise Exception(f"Square API error: {errors}")

        except Exception as e:
            logger.error(f"Failed to create Square customer: {str(e)}")
            raise

    def create_payment_token(
        self,
        customer_id: str,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a card on file for Square customer.

        Args:
            customer_id: Square customer ID
            payment_method_data: {
                'card_nonce': str,  # From Square Payment Form on frontend
                'billing_postal_code': str,
                'cardholder_name': str,
            }

        Returns:
            dict: Token information
        """
        client = self._get_square_client()
        card_nonce = payment_method_data.get('card_nonce')

        if not card_nonce:
            raise ValueError("card_nonce is required")

        try:
            body = {
                'source_id': card_nonce,
                'card': {
                    'customer_id': customer_id,
                    'billing_address': {
                        'postal_code': payment_method_data.get('billing_postal_code', ''),
                    },
                    'cardholder_name': payment_method_data.get('cardholder_name', ''),
                }
            }

            result = client.cards.create_card(body)
            card = result.card

            if card:
                card_id = card.id

                logger.info(f"Created Square card: {card_id} for customer {customer_id}")

                return {
                    'token_id': card_id,
                    'payment_method_type': 'card',
                    'card_brand': (card.card_brand or '').lower(),
                    'card_last4': card.last_4 or '',
                    'card_exp_month': card.exp_month,
                    'card_exp_year': card.exp_year,
                }
            else:
                errors = result.errors or []
                logger.error(f"Failed to create Square card: {errors}")
                raise Exception(f"Square API error: {errors}")

        except Exception as e:
            logger.error(f"Failed to create Square card: {str(e)}")
            raise

    def delete_payment_token(self, token_id: str) -> bool:
        """
        Disable a Square card on file.

        Args:
            token_id: Square card ID

        Returns:
            bool: True if successful
        """
        client = self._get_square_client()

        try:
            client.cards.disable_card(card_id=token_id)
            logger.info(f"Disabled Square card: {token_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable Square card: {str(e)}")
            return False

    # ===========================
    # One-time Charging (Used by Fallback Engine)
    # ===========================

    def charge_payment_token(
        self,
        token_id: str,
        amount: Decimal,
        currency: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Charge a Square card on file.
        Called by the fallback billing engine for each billing cycle.

        Args:
            token_id: Square card ID
            amount: Charge amount
            currency: Currency code
            description: Charge description
            metadata: Optional metadata

        Returns:
            dict: Charge information
        """
        client = self._get_square_client()

        # Convert to Square's smallest currency unit (handles zero-decimal currencies)
        amount_money = {
            'amount': _to_smallest_unit(amount, currency),
            'currency': currency.upper(),
        }

        try:
            body = {
                'source_id': token_id,
                'idempotency_key': str(uuid.uuid4()),
                'amount_money': amount_money,
                'note': description,
            }

            # Add reference ID from metadata if present
            if metadata and 'order_id' in metadata:
                body['reference_id'] = metadata['order_id']

            result = client.payments.create_payment(body=body)
            payment = result.payment

            if payment:
                payment_id = payment.id
                status = payment.status or ''

                logger.info(f"Created Square payment: {payment_id}")

                return {
                    'transaction_id': payment_id,
                    'status': 'succeeded' if status == 'COMPLETED' else 'pending',
                    'amount': amount,
                    'currency': currency,
                    'error_message': '',
                    'error_code': '',
                }
            else:
                errors = result.errors or []
                error_messages = [str(e) for e in errors]

                logger.error(f"Failed to create Square payment: {errors}")

                return {
                    'transaction_id': '',
                    'status': 'failed',
                    'amount': amount,
                    'currency': currency,
                    'error_message': '; '.join(error_messages),
                    'error_code': 'PROVIDER_ERROR',
                }

        except Exception as e:
            logger.error(f"Failed to create Square payment: {str(e)}")
            return {
                'transaction_id': '',
                'status': 'failed',
                'amount': amount,
                'currency': currency,
                'error_message': str(e),
                'error_code': 'exception',
            }

    # ===========================
    # Webhook Handling
    # ===========================

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify Square webhook signature using HMAC-SHA256.

        Args:
            payload: Raw webhook payload
            signature: X-Square-HMACSHA256-Signature header value
            **kwargs: Must include 'notification_url'

        Returns:
            bool: True if signature is valid
        """
        webhook_signature_key = self.config.get('webhook_signature_key')

        if not webhook_signature_key:
            logger.error("Square webhook signature key not configured - cannot verify webhook signature")
            return False

        notification_url = kwargs.get('notification_url', '')
        if not notification_url:
            logger.warning("notification_url not provided for Square webhook verification")
            return False

        try:
            payload_str = payload.decode('utf-8') if isinstance(payload, bytes) else payload
            string_to_sign = notification_url + payload_str

            expected_signature = hmac.new(
                key=webhook_signature_key.encode('utf-8'),
                msg=string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()

            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')

            is_valid = hmac.compare_digest(expected_b64, signature)

            if not is_valid:
                logger.error("Invalid Square webhook signature")

            return is_valid

        except Exception as e:
            logger.error(f"Square webhook signature verification error: {e}")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Square webhook payload.

        Args:
            payload: Square webhook event

        Returns:
            dict: Standardized event format
        """
        event_type = payload.get('type', '')
        event_id = payload.get('event_id', '')
        data = payload.get('data', {})

        result = {
            'event_type': event_type,
            'event_id': event_id,
            'data': data,
        }

        # Extract payment ID if present
        if 'object' in data and 'payment' in data['object']:
            payment = data['object']['payment']
            result['transaction_id'] = payment.get('id')

        return result
