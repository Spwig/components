"""
Stripe Payment Provider
Full payment processing with cards, digital wallets, BNPL, and bank transfers.

API Documentation: https://stripe.com/docs/api
"""
import stripe
import hmac
import hashlib
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from django.utils import timezone as django_timezone

from payment_providers.providers.base import PaymentProviderBase
from subscriptions.events import SubscriptionEvent, SubscriptionEventType

logger = logging.getLogger(__name__)


# Zero-decimal currencies where amounts are already in the smallest unit
ZERO_DECIMAL_CURRENCIES = {
    'BIF', 'CLP', 'DJF', 'GNF', 'JPY', 'KMF', 'KRW', 'MGA',
    'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF', 'XOF', 'XPF'
}

# Three-decimal currencies (Stripe treats these as zero-decimal)
THREE_DECIMAL_CURRENCIES = {
    'BHD', 'JOD', 'KWD', 'OMR', 'TND'
}


def _to_stripe_amount(amount: Decimal, currency: str) -> int:
    """
    Convert a Decimal amount to Stripe's integer format.

    Stripe expects amounts in the smallest currency unit (e.g., cents for USD).
    Zero-decimal currencies like JPY should not be multiplied.

    Args:
        amount: The decimal amount (e.g., Decimal('99.99'))
        currency: ISO 4217 currency code

    Returns:
        Integer amount in smallest currency unit
    """
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return int(amount)
    elif currency_upper in THREE_DECIMAL_CURRENCIES:
        # Stripe treats these as zero-decimal
        return int(amount)
    else:
        return int(amount * 100)


def _from_stripe_amount(amount: int, currency: str) -> Decimal:
    """
    Convert Stripe's integer amount back to a Decimal.

    Args:
        amount: Integer amount from Stripe
        currency: ISO 4217 currency code

    Returns:
        Decimal amount
    """
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES or currency_upper in THREE_DECIMAL_CURRENCIES:
        return Decimal(str(amount))
    else:
        return Decimal(str(amount)) / Decimal('100')


# Stripe PaymentIntent status -> our normalized status
STATUS_MAP = {
    'requires_payment_method': 'requires_payment_method',
    'requires_confirmation': 'requires_action',
    'requires_action': 'requires_action',
    'processing': 'processing',
    'requires_capture': 'processing',
    'succeeded': 'succeeded',
    'canceled': 'canceled',
}


class StripeProvider(PaymentProviderBase):
    """
    Stripe payment provider implementation.

    Supports:
    - Card payments (Visa, Mastercard, Amex, Discover, JCB, UnionPay, Diners)
    - Digital wallets (Apple Pay, Google Pay, Link)
    - Buy Now Pay Later (Klarna, Affirm, Afterpay/Clearpay)
    - Bank transfers (iDEAL, Bancontact, Giropay, EPS, SEPA, Sofort, P24, BLIK, etc.)
    - Hosted checkout via Stripe Checkout Sessions
    - Integrated checkout via Payment Intents + Elements
    - Webhook signature verification
    - Full and partial refunds
    - Authorize and capture workflow
    - 3D Secure authentication
    - Multi-currency support (135+ currencies)
    """

    provider_key = 'stripe'
    provider_name = 'Stripe'

    # Stripe API version to use
    API_VERSION = '2024-12-18.acacia'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Stripe provider with credentials.

        Args:
            credentials: Dictionary containing either:
                NEW (dual-credential):
                    - test_mode: boolean flag
                    - test_secret_key, test_publishable_key, test_webhook_secret: Test credentials
                    - live_secret_key, live_publishable_key, live_webhook_secret: Live credentials
                LEGACY (single-credential):
                    - secret_key: Stripe Secret Key (sk_test_... or sk_live_...)
                    - publishable_key: Stripe Publishable Key (pk_test_... or pk_live_...)
                    - webhook_secret: Optional webhook signing secret (whsec_...)
                    - environment: 'test' or 'live'
            config: Optional additional configuration
        """
        # Base class handles credential selection and validation
        super().__init__(credentials, config)

        # Extract selected credentials (base class already validated via _select_credentials)
        selected = self._select_credentials(credentials)
        self._secret_key = selected.get('secret_key', '')
        self._publishable_key = selected.get('publishable_key', '')
        self._webhook_secret = selected.get('webhook_secret', '')
        self._environment = selected.get('environment', 'test')
        self.test_mode = selected.get('test_mode', self._environment == 'test')

        # Configure the stripe library
        stripe.api_key = self._secret_key
        stripe.api_version = self.API_VERSION

        logger.info(
            "Stripe provider initialized (test_mode=%s, environment=%s)",
            self.test_mode,
            self._environment
        )

    # -------------------------------------------------------------------------
    # Properties (abstract)
    # -------------------------------------------------------------------------

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return dictionary of provider capabilities."""
        return {
            'charge': True,
            'authorize': True,
            'capture': True,
            'void': True,
            'refund': True,
            'partial_refund': True,
            'recurring': True,
            'save_payment_method': True,
            'hosted_checkout': True,
            'integrated_checkout': True,
            'webhooks': True,
            'multi_currency': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema describing required credentials (post-selection, unprefixed).
        Note: The authoritative schema for the wizard UI is in manifest.json.
        """
        return {
            'type': 'object',
            'properties': {
                'publishable_key': {
                    'type': 'string',
                    'title': 'Publishable Key',
                    'description': 'Your Stripe Publishable Key (starts with pk_test_ or pk_live_)',
                    'required': True,
                    'secret': False,
                },
                'secret_key': {
                    'type': 'string',
                    'title': 'Secret Key',
                    'description': 'Your Stripe Secret Key (starts with sk_test_ or sk_live_)',
                    'required': True,
                    'secret': True,
                },
                'webhook_secret': {
                    'type': 'string',
                    'title': 'Webhook Signing Secret',
                    'description': 'Signing secret from your Stripe webhook endpoint (starts with whsec_)',
                    'required': False,
                    'secret': True,
                },
            },
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        """Return list of supported payment method types."""
        return [
            'credit_card', 'debit_card', 'digital_wallet',
            'buy_now_pay_later', 'bank_transfer',
        ]

    @property
    def supported_currencies(self) -> List[str]:
        """Return list of supported currency codes."""
        return [
            'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY', 'CHF', 'SEK', 'DKK',
            'NOK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'BRL', 'MXN',
            'SGD', 'HKD', 'NZD', 'INR', 'THB', 'MYR', 'PHP', 'IDR', 'TWD',
            'KRW', 'ZAR', 'AED', 'SAR', 'ILS', 'TRY', 'CNY', 'VND', 'CLP',
            'COP', 'PEN', 'ARS', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'EGP',
            'PKR', 'BDT', 'LKR', 'NGN', 'KES', 'GHS', 'TZS', 'UGX', 'RWF',
            'MAD', 'XOF', 'XAF', 'ETB', 'DZD', 'TND', 'MUR', 'BWP', 'GEL',
            'MDL', 'ALL', 'MKD', 'BAM', 'RSD', 'ISK', 'UAH', 'KZT', 'UZS',
            'AZN', 'AMD', 'GIP', 'FKP', 'SHP', 'BMD', 'KYD', 'BSD', 'BZD',
            'TTD', 'JMD', 'BBD', 'AWG', 'ANG', 'SRD', 'HTG', 'DOP', 'CRC',
            'GTQ', 'HNL', 'NIO', 'PAB', 'PYG', 'UYU', 'BOB', 'VES', 'GYD',
            'FJD', 'PGK', 'SBD', 'TOP', 'WST', 'VUV', 'SCR', 'GMD', 'MWK',
            'ZMW', 'MZN', 'SZL', 'LSL', 'NAD', 'MMK', 'KHR', 'LAK', 'BND',
            'MVR', 'NPR', 'AFN', 'MNT', 'KGS', 'TJS',
        ]

    @property
    def supported_countries(self) -> List[str]:
        """Return list of supported country codes (for merchant accounts)."""
        return [
            'US', 'GB', 'AU', 'CA', 'SG', 'HK', 'JP', 'NZ',
            'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE',
            'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV',
            'LT', 'LU', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO',
            'SK', 'SI', 'ES', 'SE', 'CH', 'BR', 'MX', 'IN',
            'TH', 'MY',
        ]

    # -------------------------------------------------------------------------
    # Credential Management
    # -------------------------------------------------------------------------

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate Stripe credentials.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing required fields
        """
        secret_key = credentials.get('secret_key', '')
        publishable_key = credentials.get('publishable_key', '')

        if not secret_key:
            raise ValueError("Stripe Secret Key is required")

        if not publishable_key:
            raise ValueError("Stripe Publishable Key is required")

        # Basic format validation
        if not (secret_key.startswith('sk_test_') or secret_key.startswith('sk_live_')):
            raise ValueError(
                "Invalid Secret Key format. Must start with 'sk_test_' or 'sk_live_'"
            )

        if not (publishable_key.startswith('pk_test_') or publishable_key.startswith('pk_live_')):
            raise ValueError(
                "Invalid Publishable Key format. Must start with 'pk_test_' or 'pk_live_'"
            )

        # Warn if environment doesn't match key prefix
        environment = credentials.get('environment', 'test')
        if environment == 'live' and 'test' in secret_key:
            logger.warning(
                "Environment is set to 'live' but secret key appears to be a test key"
            )
        elif environment == 'test' and 'live' in secret_key:
            logger.warning(
                "Environment is set to 'test' but secret key appears to be a live key"
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = dict(credentials)

        # Redact all secret/publishable/webhook keys (both prefixed and unprefixed)
        for key_name, value in list(redacted.items()):
            if not value or not isinstance(value, str):
                continue

            if 'secret_key' in key_name:
                # Keep prefix and last 4 chars: sk_test_***abc4
                if len(value) > 12:
                    prefix = value[:8]
                    suffix = value[-4:]
                    redacted[key_name] = f"{prefix}***{suffix}"
                else:
                    redacted[key_name] = '***'
            elif 'publishable_key' in key_name:
                if len(value) > 12:
                    prefix = value[:8]
                    suffix = value[-4:]
                    redacted[key_name] = f"{prefix}***{suffix}"
                else:
                    redacted[key_name] = '***'
            elif 'webhook_secret' in key_name:
                if len(value) > 10:
                    redacted[key_name] = f"whsec_***{value[-4:]}"
                else:
                    redacted[key_name] = '***'

        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection by retrieving the Stripe account.

        Returns:
            Dictionary with test results including account details
        """
        try:
            account = stripe.Account.retrieve()

            return {
                'success': True,
                'message': 'Successfully connected to Stripe',
                'details': {
                    'account_id': account.get('id', 'N/A'),
                    'account_name': account.get('settings', {}).get(
                        'dashboard', {}
                    ).get('display_name', account.get('business_profile', {}).get('name', 'N/A')),
                    'environment': self._environment,
                    'api_version': self.API_VERSION,
                    'country': account.get('country', 'N/A'),
                    'default_currency': account.get('default_currency', 'N/A'),
                    'charges_enabled': account.get('charges_enabled', False),
                    'payouts_enabled': account.get('payouts_enabled', False),
                },
            }

        except stripe.error.AuthenticationError as e:
            logger.error("Stripe authentication failed: %s", str(e))
            return {
                'success': False,
                'message': f'Authentication failed: Invalid API key',
                'details': {
                    'environment': self._environment,
                    'error': str(e),
                },
            }
        except stripe.error.PermissionError as e:
            logger.error("Stripe permission error: %s", str(e))
            return {
                'success': False,
                'message': f'Permission denied: {str(e)}',
                'details': {
                    'environment': self._environment,
                    'error': str(e),
                },
            }
        except stripe.error.APIConnectionError as e:
            logger.error("Stripe connection error: %s", str(e))
            return {
                'success': False,
                'message': f'Connection failed: Unable to reach Stripe API',
                'details': {
                    'environment': self._environment,
                    'error': str(e),
                },
            }
        except Exception as e:
            logger.error("Stripe connection test failed: %s", str(e))
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {
                    'environment': self._environment,
                    'error': str(e),
                },
            }

    # -------------------------------------------------------------------------
    # Payment Processing
    # -------------------------------------------------------------------------

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an immediate payment charge using Stripe PaymentIntent.

        Args:
            amount: Payment amount (e.g., Decimal('99.99'))
            currency: Currency code (e.g., 'USD')
            payment_method: Payment method details with 'token' key
            metadata: Optional metadata to attach

        Returns:
            Dictionary with transaction result
        """
        try:
            stripe_amount = _to_stripe_amount(amount, currency)

            intent_params = {
                'amount': stripe_amount,
                'currency': currency.lower(),
                'confirm': True,
                'automatic_payment_methods': {
                    'enabled': True,
                    'allow_redirects': 'never',
                },
            }

            # Attach payment method if provided
            token = payment_method.get('token')
            if token:
                intent_params['payment_method'] = token

            # Attach customer if provided
            customer_id = payment_method.get('customer_id')
            if customer_id:
                intent_params['customer'] = customer_id

            # Add metadata
            if metadata:
                intent_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }

            # Add receipt email
            if metadata and metadata.get('customer_email'):
                intent_params['receipt_email'] = metadata['customer_email']

            pi = stripe.PaymentIntent.create(**intent_params)

            logger.info(
                "Stripe charge created: %s (amount=%s %s, status=%s)",
                pi.id, amount, currency, pi.status
            )

            success = pi.status == 'succeeded'

            return {
                'success': success,
                'transaction_id': pi.id,
                'provider_transaction_id': pi.id,
                'status': 'completed' if success else STATUS_MAP.get(pi.status, pi.status),
                'amount': amount,
                'currency': currency.upper(),
                'payment_method_id': pi.get('payment_method'),
                'created_at': datetime.now(),
                'message': 'Payment successful' if success else f'Payment status: {pi.status}',
                'raw_response': dict(pi),
            }

        except stripe.error.CardError as e:
            err = e.error
            logger.warning(
                "Stripe card error: code=%s, message=%s",
                err.code, err.message
            )
            return {
                'success': False,
                'transaction_id': None,
                'provider_transaction_id': getattr(e, 'payment_intent', {}).get('id') if hasattr(e, 'payment_intent') and e.payment_intent else None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': err.message,
                'error_code': err.code,
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error during charge: %s", str(e))
            return {
                'success': False,
                'transaction_id': None,
                'provider_transaction_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': str(e),
                'error_code': getattr(e, 'code', 'stripe_error'),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error during Stripe charge: %s", str(e))
            return {
                'success': False,
                'transaction_id': None,
                'provider_transaction_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': f'Payment processing error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def authorize(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Authorize a payment without capturing funds.

        Uses capture_method='manual' so the PaymentIntent must be
        explicitly captured later.

        Args:
            amount: Authorization amount
            currency: Currency code
            payment_method: Payment method details with 'token' key
            metadata: Optional metadata

        Returns:
            Dictionary with authorization result
        """
        try:
            stripe_amount = _to_stripe_amount(amount, currency)

            intent_params = {
                'amount': stripe_amount,
                'currency': currency.lower(),
                'confirm': True,
                'capture_method': 'manual',
                'automatic_payment_methods': {
                    'enabled': True,
                    'allow_redirects': 'never',
                },
            }

            token = payment_method.get('token')
            if token:
                intent_params['payment_method'] = token

            customer_id = payment_method.get('customer_id')
            if customer_id:
                intent_params['customer'] = customer_id

            if metadata:
                intent_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }

            if metadata and metadata.get('customer_email'):
                intent_params['receipt_email'] = metadata['customer_email']

            pi = stripe.PaymentIntent.create(**intent_params)

            logger.info(
                "Stripe authorization created: %s (amount=%s %s, status=%s)",
                pi.id, amount, currency, pi.status
            )

            success = pi.status in ('requires_capture', 'succeeded')

            return {
                'success': success,
                'authorization_id': pi.id,
                'provider_authorization_id': pi.id,
                'status': 'authorized' if success else STATUS_MAP.get(pi.status, pi.status),
                'amount': amount,
                'currency': currency.upper(),
                'expires_at': datetime.now() + timedelta(days=7),  # Stripe auths expire in ~7 days
                'created_at': datetime.now(),
                'message': 'Authorization successful' if success else f'Authorization status: {pi.status}',
                'raw_response': dict(pi),
            }

        except stripe.error.CardError as e:
            err = e.error
            logger.warning("Stripe card error during authorization: %s", err.message)
            return {
                'success': False,
                'authorization_id': None,
                'provider_authorization_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': err.message,
                'error_code': err.code,
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error during authorization: %s", str(e))
            return {
                'success': False,
                'authorization_id': None,
                'provider_authorization_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': str(e),
                'error_code': getattr(e, 'code', 'stripe_error'),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error during Stripe authorization: %s", str(e))
            return {
                'success': False,
                'authorization_id': None,
                'provider_authorization_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': f'Authorization error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def capture(
        self,
        authorization_id: str,
        amount: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Capture funds from a previous authorization.

        Args:
            authorization_id: Stripe PaymentIntent ID (pi_...)
            amount: Amount to capture (None captures full amount)
            metadata: Optional metadata

        Returns:
            Dictionary with capture result
        """
        try:
            capture_params = {}

            if amount is not None:
                # Need to retrieve the PI to get the currency for amount conversion
                pi = stripe.PaymentIntent.retrieve(authorization_id)
                stripe_amount = _to_stripe_amount(amount, pi.currency)
                capture_params['amount_to_capture'] = stripe_amount

            if metadata:
                capture_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }

            pi = stripe.PaymentIntent.capture(authorization_id, **capture_params)

            captured_amount = _from_stripe_amount(pi.amount_received, pi.currency)

            logger.info(
                "Stripe capture successful: %s (amount=%s %s)",
                pi.id, captured_amount, pi.currency
            )

            return {
                'success': True,
                'transaction_id': pi.id,
                'provider_transaction_id': pi.id,
                'status': 'completed',
                'amount': captured_amount,
                'currency': pi.currency.upper(),
                'created_at': datetime.now(),
                'message': 'Capture successful',
                'raw_response': dict(pi),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid capture request: %s", str(e))
            return {
                'success': False,
                'transaction_id': authorization_id,
                'provider_transaction_id': authorization_id,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error during capture: %s", str(e))
            return {
                'success': False,
                'transaction_id': authorization_id,
                'provider_transaction_id': authorization_id,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error during Stripe capture: %s", str(e))
            return {
                'success': False,
                'transaction_id': authorization_id,
                'provider_transaction_id': authorization_id,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': f'Capture error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def void(
        self,
        authorization_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Void an uncaptured authorization by canceling the PaymentIntent.

        Args:
            authorization_id: Stripe PaymentIntent ID (pi_...)
            metadata: Optional metadata

        Returns:
            Dictionary with void result
        """
        try:
            cancel_params = {}
            if metadata:
                cancel_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }
            cancel_params['cancellation_reason'] = 'requested_by_customer'

            pi = stripe.PaymentIntent.cancel(authorization_id, **cancel_params)

            logger.info("Stripe void successful: %s", pi.id)

            return {
                'success': True,
                'authorization_id': pi.id,
                'status': 'voided',
                'message': 'Authorization voided',
                'raw_response': dict(pi),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid void request: %s", str(e))
            return {
                'success': False,
                'authorization_id': authorization_id,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error during void: %s", str(e))
            return {
                'success': False,
                'authorization_id': authorization_id,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error during Stripe void: %s", str(e))
            return {
                'success': False,
                'authorization_id': authorization_id,
                'status': 'failed',
                'message': f'Void error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refund a completed payment (full or partial).

        Args:
            transaction_id: Stripe PaymentIntent ID (pi_...)
            amount: Amount to refund (None for full refund)
            reason: Optional refund reason
            metadata: Optional metadata

        Returns:
            Dictionary with refund result
        """
        try:
            refund_params = {
                'payment_intent': transaction_id,
            }

            if amount is not None:
                # Retrieve PI to get currency for amount conversion
                pi = stripe.PaymentIntent.retrieve(transaction_id)
                stripe_amount = _to_stripe_amount(amount, pi.currency)
                refund_params['amount'] = stripe_amount

            # Map reason to Stripe's accepted values
            if reason:
                reason_map = {
                    'duplicate': 'duplicate',
                    'fraudulent': 'fraudulent',
                    'requested_by_customer': 'requested_by_customer',
                }
                stripe_reason = reason_map.get(reason.lower())
                if stripe_reason:
                    refund_params['reason'] = stripe_reason

            if metadata:
                refund_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }

            ref = stripe.Refund.create(**refund_params)

            refund_amount = _from_stripe_amount(ref.amount, ref.currency)

            logger.info(
                "Stripe refund created: %s (amount=%s %s, status=%s)",
                ref.id, refund_amount, ref.currency, ref.status
            )

            return {
                'success': ref.status in ('succeeded', 'pending'),
                'refund_id': ref.id,
                'provider_refund_id': ref.id,
                'status': 'completed' if ref.status == 'succeeded' else ref.status,
                'amount': refund_amount,
                'currency': ref.currency.upper(),
                'created_at': datetime.now(),
                'message': 'Refund successful' if ref.status == 'succeeded' else f'Refund status: {ref.status}',
                'raw_response': dict(ref),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid refund request: %s", str(e))
            return {
                'success': False,
                'refund_id': None,
                'provider_refund_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error during refund: %s", str(e))
            return {
                'success': False,
                'refund_id': None,
                'provider_refund_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error during Stripe refund: %s", str(e))
            return {
                'success': False,
                'refund_id': None,
                'provider_refund_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': None,
                'created_at': datetime.now(),
                'message': f'Refund error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    # -------------------------------------------------------------------------
    # Webhook Methods
    # -------------------------------------------------------------------------

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify Stripe webhook signature using the stripe library.

        Args:
            payload: Raw request body as bytes
            signature: Value of the 'stripe-signature' header
            **kwargs: Additional keyword arguments (unused)

        Returns:
            True if signature is valid, False otherwise
        """
        if not self._webhook_secret:
            logger.error(
                "Webhook secret not configured - cannot verify webhook signature"
            )
            return False

        try:
            stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self._webhook_secret,
            )
            return True
        except stripe.error.SignatureVerificationError as e:
            logger.warning("Stripe webhook signature verification failed: %s", str(e))
            return False
        except Exception as e:
            logger.error("Error verifying Stripe webhook signature: %s", str(e))
            return False

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event from Stripe.

        Args:
            event_type: Type of webhook event (e.g., 'payment_intent.succeeded')
            payload: Webhook payload dictionary

        Returns:
            Dictionary with processed webhook data
        """
        logger.info("Processing Stripe webhook: %s", event_type)

        data_object = payload.get('data', {}).get('object', {})

        if event_type == 'payment_intent.succeeded':
            return self._handle_payment_succeeded(data_object, payload)

        elif event_type == 'payment_intent.payment_failed':
            return self._handle_payment_failed(data_object, payload)

        elif event_type == 'charge.refunded':
            return self._handle_charge_refunded(data_object, payload)

        elif event_type == 'charge.refund.updated':
            return self._handle_refund_updated(data_object, payload)

        elif event_type == 'checkout.session.completed':
            return self._handle_checkout_completed(data_object, payload)

        else:
            logger.info("Unhandled Stripe webhook event: %s", event_type)
            return {
                'action': 'unknown',
                'event_type': event_type,
                'handled': False,
                'raw_event': payload,
            }

    def _handle_payment_succeeded(self, data: Dict, raw_event: Dict) -> Dict[str, Any]:
        """Handle payment_intent.succeeded webhook event."""
        amount = _from_stripe_amount(
            data.get('amount_received', data.get('amount', 0)),
            data.get('currency', 'usd')
        )

        return {
            'action': 'payment_completed',
            'transaction_id': data.get('id'),
            'status': 'completed',
            'amount': amount,
            'currency': data.get('currency', '').upper(),
            'metadata': data.get('metadata', {}),
            'raw_event': raw_event,
        }

    def _handle_payment_failed(self, data: Dict, raw_event: Dict) -> Dict[str, Any]:
        """Handle payment_intent.payment_failed webhook event."""
        last_error = data.get('last_payment_error', {})

        return {
            'action': 'payment_failed',
            'transaction_id': data.get('id'),
            'status': 'failed',
            'amount': _from_stripe_amount(
                data.get('amount', 0),
                data.get('currency', 'usd')
            ),
            'currency': data.get('currency', '').upper(),
            'error_code': last_error.get('code', 'unknown'),
            'error_message': last_error.get('message', 'Payment failed'),
            'metadata': data.get('metadata', {}),
            'raw_event': raw_event,
        }

    def _handle_charge_refunded(self, data: Dict, raw_event: Dict) -> Dict[str, Any]:
        """Handle charge.refunded webhook event."""
        amount_refunded = _from_stripe_amount(
            data.get('amount_refunded', 0),
            data.get('currency', 'usd')
        )

        return {
            'action': 'refund_completed',
            'transaction_id': data.get('payment_intent'),
            'charge_id': data.get('id'),
            'status': 'refunded',
            'amount': amount_refunded,
            'currency': data.get('currency', '').upper(),
            'metadata': data.get('metadata', {}),
            'raw_event': raw_event,
        }

    def _handle_refund_updated(self, data: Dict, raw_event: Dict) -> Dict[str, Any]:
        """Handle charge.refund.updated webhook event."""
        refund_amount = _from_stripe_amount(
            data.get('amount', 0),
            data.get('currency', 'usd')
        )

        status = data.get('status', 'unknown')
        action = 'refund_completed' if status == 'succeeded' else 'refund_updated'

        return {
            'action': action,
            'refund_id': data.get('id'),
            'transaction_id': data.get('payment_intent'),
            'status': status,
            'amount': refund_amount,
            'currency': data.get('currency', '').upper(),
            'metadata': data.get('metadata', {}),
            'raw_event': raw_event,
        }

    def _handle_checkout_completed(self, data: Dict, raw_event: Dict) -> Dict[str, Any]:
        """Handle checkout.session.completed webhook event."""
        amount = _from_stripe_amount(
            data.get('amount_total', 0),
            data.get('currency', 'usd')
        )

        return {
            'action': 'payment_completed',
            'transaction_id': data.get('payment_intent'),
            'session_id': data.get('id'),
            'status': 'completed',
            'amount': amount,
            'currency': data.get('currency', '').upper(),
            'customer_email': data.get('customer_details', {}).get('email'),
            'metadata': data.get('metadata', {}),
            'raw_event': raw_event,
        }

    # -------------------------------------------------------------------------
    # Checkout / Payment Intent Methods
    # -------------------------------------------------------------------------

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout Session (hosted checkout page).

        Args:
            amount: Payment amount
            currency: Currency code
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancellation
            metadata: Optional metadata

        Returns:
            Dictionary with checkout session details
        """
        try:
            stripe_amount = _to_stripe_amount(amount, currency)

            session_params = {
                'mode': 'payment',
                'line_items': [{
                    'price_data': {
                        'currency': currency.lower(),
                        'unit_amount': stripe_amount,
                        'product_data': {
                            'name': metadata.get('description', 'Order Payment') if metadata else 'Order Payment',
                        },
                    },
                    'quantity': 1,
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
            }

            if metadata:
                session_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }
                if metadata.get('customer_email'):
                    session_params['customer_email'] = metadata['customer_email']

            session = stripe.checkout.Session.create(**session_params)

            logger.info("Stripe checkout session created: %s", session.id)

            return {
                'success': True,
                'session_id': session.id,
                'checkout_url': session.url,
                'expires_at': datetime.fromtimestamp(session.expires_at) if session.expires_at else None,
                'message': 'Checkout session created',
                'raw_response': dict(session),
            }

        except stripe.error.StripeError as e:
            logger.error("Failed to create Stripe checkout session: %s", str(e))
            return {
                'success': False,
                'session_id': None,
                'checkout_url': None,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error creating checkout session: %s", str(e))
            return {
                'success': False,
                'session_id': None,
                'checkout_url': None,
                'message': f'Checkout session error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def get_checkout_client_secret(
        self,
        amount: Decimal,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get client secret for integrated checkout (Stripe Elements).

        Creates a PaymentIntent and returns the client_secret for use
        with Stripe.js on the frontend.

        Args:
            amount: Payment amount
            currency: Currency code
            metadata: Optional metadata

        Returns:
            Dictionary with client secret and intent details
        """
        try:
            stripe_amount = _to_stripe_amount(amount, currency)

            intent_params = {
                'amount': stripe_amount,
                'currency': currency.lower(),
                'automatic_payment_methods': {
                    'enabled': True,
                },
            }

            if metadata:
                intent_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }
                if metadata.get('customer_email'):
                    intent_params['receipt_email'] = metadata['customer_email']

            pi = stripe.PaymentIntent.create(**intent_params)

            logger.info("Stripe client secret generated for intent: %s", pi.id)

            return {
                'success': True,
                'client_secret': pi.client_secret,
                'publishable_key': self._publishable_key,
                'intent_id': pi.id,
                'message': 'Client secret generated',
                'raw_response': dict(pi),
            }

        except stripe.error.StripeError as e:
            logger.error("Failed to generate Stripe client secret: %s", str(e))
            return {
                'success': False,
                'client_secret': None,
                'publishable_key': self._publishable_key,
                'intent_id': None,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error generating client secret: %s", str(e))
            return {
                'success': False,
                'client_secret': None,
                'publishable_key': self._publishable_key,
                'intent_id': None,
                'message': f'Client secret error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def create_payment_intent_for_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for checkout orchestration.

        Supports both hosted (Checkout Session) and integrated (PaymentIntent) modes.

        Args:
            amount: Payment amount
            currency: Currency code
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect on cancellation
            customer_email: Optional customer email
            metadata: Optional metadata (order_id, checkout_session_id, etc.)

        Returns:
            Dictionary with payment intent details
        """
        try:
            stripe_amount = _to_stripe_amount(amount, currency)

            # Determine checkout mode from config
            checkout_mode = self.config.get('checkout_mode', 'integrated')

            if checkout_mode == 'hosted':
                # Use Stripe Checkout Session for hosted checkout
                session_params = {
                    'mode': 'payment',
                    'line_items': [{
                        'price_data': {
                            'currency': currency.lower(),
                            'unit_amount': stripe_amount,
                            'product_data': {
                                'name': metadata.get('description', 'Order Payment') if metadata else 'Order Payment',
                            },
                        },
                        'quantity': 1,
                    }],
                    'success_url': return_url,
                    'cancel_url': cancel_url,
                }

                if customer_email:
                    session_params['customer_email'] = customer_email

                if metadata:
                    session_params['metadata'] = {
                        str(k): str(v) for k, v in metadata.items()
                    }

                session = stripe.checkout.Session.create(**session_params)

                logger.info(
                    "Stripe hosted checkout created: session=%s, pi=%s",
                    session.id, session.payment_intent
                )

                return {
                    'success': True,
                    'provider_intent_id': session.payment_intent or session.id,
                    'client_secret': None,
                    'checkout_url': session.url,
                    'status': 'created',
                    'requires_action': True,
                    'action': {
                        'type': 'redirect',
                        'url': session.url,
                    },
                    'expires_at': datetime.fromtimestamp(session.expires_at) if session.expires_at else None,
                    'raw_response': dict(session),
                }

            else:
                # Use PaymentIntent for integrated/embedded checkout
                intent_params = {
                    'amount': stripe_amount,
                    'currency': currency.lower(),
                    'automatic_payment_methods': {
                        'enabled': True,
                    },
                }

                if customer_email:
                    intent_params['receipt_email'] = customer_email

                if metadata:
                    intent_params['metadata'] = {
                        str(k): str(v) for k, v in metadata.items()
                    }

                pi = stripe.PaymentIntent.create(**intent_params)

                logger.info(
                    "Stripe payment intent created for checkout: %s (status=%s)",
                    pi.id, pi.status
                )

                # Build handler_config for plugin architecture
                handler_config = {
                    'intent_id': pi.id,
                    'publishable_key': self._publishable_key,
                    'currency': currency.upper(),
                    'country_code': (metadata or {}).get('country_code', 'US'),
                    'environment': self._environment,
                }

                return {
                    'success': True,
                    'provider_intent_id': pi.id,
                    'client_secret': pi.client_secret,
                    'checkout_url': None,
                    'status': STATUS_MAP.get(pi.status, pi.status),
                    'requires_action': pi.status == 'requires_action',
                    'action': None,
                    'expires_at': None,
                    'handler_config': handler_config,  # NEW: For plugin architecture
                    'raw_response': dict(pi),
                }

        except stripe.error.StripeError as e:
            logger.error("Stripe error creating payment intent for checkout: %s", str(e))
            return {
                'success': False,
                'provider_intent_id': None,
                'client_secret': None,
                'checkout_url': None,
                'status': 'failed',
                'requires_action': False,
                'action': None,
                'expires_at': None,
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error creating payment intent for checkout: %s", str(e))
            return {
                'success': False,
                'provider_intent_id': None,
                'client_secret': None,
                'checkout_url': None,
                'status': 'failed',
                'requires_action': False,
                'action': None,
                'expires_at': None,
                'raw_response': {'error': str(e)},
            }

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve current status of a payment intent.

        Args:
            intent_id: Stripe PaymentIntent ID

        Returns:
            Dictionary with intent status
        """
        try:
            pi = stripe.PaymentIntent.retrieve(intent_id)

            normalized_status = STATUS_MAP.get(pi.status, pi.status)
            requires_action = pi.status in ('requires_action', 'requires_confirmation')

            result = {
                'success': True,
                'status': normalized_status,
                'provider_status': pi.status,
                'requires_action': requires_action,
                'action': None,
                'payment_method_type': None,
                'payment_method_last4': None,
                'error': None,
                'raw_response': dict(pi),
            }

            # Extract action details if needed
            if requires_action and pi.get('next_action'):
                next_action = pi['next_action']
                result['action'] = {
                    'type': next_action.get('type', 'unknown'),
                    'url': next_action.get('redirect_to_url', {}).get('url')
                           if next_action.get('redirect_to_url') else None,
                    'data': dict(next_action),
                }

            # Extract payment method details if available
            if pi.get('payment_method'):
                try:
                    pm = stripe.PaymentMethod.retrieve(pi['payment_method'])
                    result['payment_method_type'] = pm.type
                    if pm.type == 'card' and pm.get('card'):
                        result['payment_method_last4'] = pm['card'].get('last4')
                except Exception:
                    pass  # Non-critical, skip if retrieval fails

            # Extract error details if failed
            if pi.get('last_payment_error'):
                error = pi['last_payment_error']
                result['error'] = {
                    'code': error.get('code', 'unknown'),
                    'message': error.get('message', 'Payment failed'),
                }

            return result

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid payment intent ID: %s - %s", intent_id, str(e))
            return {
                'success': False,
                'status': 'failed',
                'provider_status': None,
                'requires_action': False,
                'error': {
                    'code': 'invalid_request',
                    'message': str(e),
                },
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error retrieving payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'provider_status': None,
                'requires_action': False,
                'error': {
                    'code': 'stripe_error',
                    'message': str(e),
                },
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error retrieving payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'provider_status': None,
                'requires_action': False,
                'error': {
                    'code': 'unknown_error',
                    'message': str(e),
                },
                'raw_response': {'error': str(e)},
            }

    def confirm_payment_intent(
        self,
        intent_id: str,
        confirmation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent after customer action (e.g., 3DS).

        Args:
            intent_id: Stripe PaymentIntent ID
            confirmation_data: Optional data with payment_method and return_url

        Returns:
            Dictionary with confirmation result
        """
        try:
            confirm_params = {}

            if confirmation_data:
                if confirmation_data.get('payment_method'):
                    confirm_params['payment_method'] = confirmation_data['payment_method']
                if confirmation_data.get('return_url'):
                    confirm_params['return_url'] = confirmation_data['return_url']

            pi = stripe.PaymentIntent.confirm(intent_id, **confirm_params)

            normalized_status = STATUS_MAP.get(pi.status, pi.status)
            requires_action = pi.status in ('requires_action', 'requires_confirmation')

            result = {
                'success': pi.status in ('succeeded', 'processing', 'requires_capture'),
                'status': normalized_status,
                'requires_action': requires_action,
                'action': None,
                'payment_method_type': None,
                'payment_method_last4': None,
                'message': f'Payment intent status: {pi.status}',
                'error': None,
                'raw_response': dict(pi),
            }

            if requires_action and pi.get('next_action'):
                next_action = pi['next_action']
                result['action'] = {
                    'type': next_action.get('type', 'unknown'),
                    'url': next_action.get('redirect_to_url', {}).get('url')
                           if next_action.get('redirect_to_url') else None,
                    'data': dict(next_action),
                }

            if pi.get('last_payment_error'):
                error = pi['last_payment_error']
                result['success'] = False
                result['error'] = {
                    'code': error.get('code', 'unknown'),
                    'message': error.get('message', 'Confirmation failed'),
                }

            return result

        except stripe.error.CardError as e:
            err = e.error
            logger.warning("Card error during confirmation: %s", err.message)
            return {
                'success': False,
                'status': 'failed',
                'requires_action': False,
                'message': err.message,
                'error': {
                    'code': err.code,
                    'message': err.message,
                },
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error confirming payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'requires_action': False,
                'message': str(e),
                'error': {
                    'code': 'stripe_error',
                    'message': str(e),
                },
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error confirming payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'requires_action': False,
                'message': f'Confirmation error: {str(e)}',
                'error': {
                    'code': 'unknown_error',
                    'message': str(e),
                },
                'raw_response': {'error': str(e)},
            }

    def cancel_payment_intent(
        self,
        intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a payment intent.

        Args:
            intent_id: Stripe PaymentIntent ID
            cancellation_reason: Optional reason for cancellation

        Returns:
            Dictionary with cancellation result
        """
        try:
            cancel_params = {}
            if cancellation_reason:
                # Map to Stripe's accepted cancellation reasons
                reason_map = {
                    'duplicate': 'duplicate',
                    'fraudulent': 'fraudulent',
                    'requested_by_customer': 'requested_by_customer',
                    'abandoned': 'abandoned',
                }
                stripe_reason = reason_map.get(
                    cancellation_reason.lower(),
                    'requested_by_customer'
                )
                cancel_params['cancellation_reason'] = stripe_reason

            pi = stripe.PaymentIntent.cancel(intent_id, **cancel_params)

            logger.info("Stripe payment intent canceled: %s", pi.id)

            return {
                'success': True,
                'status': 'canceled',
                'message': 'Payment intent canceled',
                'raw_response': dict(pi),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid cancel request: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error canceling payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error canceling payment intent: %s", str(e))
            return {
                'success': False,
                'status': 'failed',
                'message': f'Cancellation error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    # -------------------------------------------------------------------------
    # Payment Method Types
    # -------------------------------------------------------------------------

    def get_payment_method_types(self) -> Dict[str, Any]:
        """
        Get available payment method types.

        Stripe payment methods are configured in the Stripe Dashboard,
        so we return a static list of commonly available methods per region.

        Returns:
            Dictionary with payment methods organized by country
        """
        card_methods = ['card', 'apple_pay', 'google_pay', 'link']

        methods = {
            'US': card_methods + ['affirm', 'afterpay_clearpay', 'klarna'],
            'GB': card_methods + ['klarna', 'afterpay_clearpay'],
            'CA': card_methods + ['affirm', 'afterpay_clearpay'],
            'AU': card_methods + ['afterpay_clearpay', 'klarna'],
            'NZ': card_methods + ['afterpay_clearpay', 'klarna'],
            'DE': card_methods + ['klarna', 'giropay', 'sofort', 'sepa_debit'],
            'AT': card_methods + ['klarna', 'eps', 'sofort', 'sepa_debit'],
            'NL': card_methods + ['ideal', 'klarna', 'sofort', 'sepa_debit', 'bancontact'],
            'BE': card_methods + ['bancontact', 'klarna', 'sofort', 'sepa_debit'],
            'FR': card_methods + ['klarna', 'sepa_debit'],
            'ES': card_methods + ['klarna', 'sofort', 'sepa_debit'],
            'IT': card_methods + ['klarna', 'sofort', 'sepa_debit'],
            'SE': card_methods + ['klarna'],
            'NO': card_methods + ['klarna'],
            'DK': card_methods + ['klarna'],
            'FI': card_methods + ['klarna'],
            'PL': card_methods + ['przelewy24', 'blik', 'klarna'],
            'CH': card_methods + ['klarna'],
            'IE': card_methods + ['klarna', 'sepa_debit'],
            'SG': card_methods + ['grabpay', 'alipay', 'wechat_pay'],
            'HK': card_methods + ['alipay', 'wechat_pay'],
            'JP': card_methods + ['wechat_pay'],
            'MY': card_methods + ['fpx', 'grabpay'],
            'IN': card_methods,
            'TH': card_methods,
            'BR': card_methods,
            'MX': card_methods,
        }

        return {
            'success': True,
            'methods': methods,
            'raw_response': {},
        }

    # -------------------------------------------------------------------------
    # Payment Method Storage
    # -------------------------------------------------------------------------

    def save_payment_method(
        self,
        customer_id: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a payment method for future use by attaching it to a Stripe Customer.

        Args:
            customer_id: Stripe Customer ID (cus_...)
            payment_method: Dict with 'token' key containing the PaymentMethod ID (pm_...)
            metadata: Optional metadata

        Returns:
            Dictionary with saved payment method details
        """
        try:
            pm_id = payment_method.get('token')
            if not pm_id:
                raise ValueError("Payment method token (PaymentMethod ID) is required")

            pm = stripe.PaymentMethod.attach(pm_id, customer=customer_id)

            card = pm.get('card', {})

            logger.info(
                "Payment method attached: %s to customer %s",
                pm.id, customer_id
            )

            return {
                'success': True,
                'payment_method_id': pm.id,
                'provider_payment_method_id': pm.id,
                'type': pm.type,
                'last4': card.get('last4', ''),
                'brand': card.get('brand', ''),
                'exp_month': card.get('exp_month'),
                'exp_year': card.get('exp_year'),
                'message': 'Payment method saved',
                'raw_response': dict(pm),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid request saving payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': None,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error saving payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': None,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error saving payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': None,
                'message': f'Error saving payment method: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def delete_payment_method(
        self,
        payment_method_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delete a saved payment method by detaching it from the customer.

        Args:
            payment_method_id: Stripe PaymentMethod ID (pm_...)
            metadata: Optional metadata (unused)

        Returns:
            Dictionary with deletion result
        """
        try:
            pm = stripe.PaymentMethod.detach(payment_method_id)

            logger.info("Payment method detached: %s", pm.id)

            return {
                'success': True,
                'payment_method_id': pm.id,
                'message': 'Payment method deleted',
                'raw_response': dict(pm),
            }

        except stripe.error.InvalidRequestError as e:
            logger.error("Invalid request deleting payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': payment_method_id,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except stripe.error.StripeError as e:
            logger.error("Stripe error deleting payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': payment_method_id,
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error deleting payment method: %s", str(e))
            return {
                'success': False,
                'payment_method_id': payment_method_id,
                'message': f'Error deleting payment method: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    # -------------------------------------------------------------------------
    # Subscription Methods
    # -------------------------------------------------------------------------

    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription using Stripe Subscriptions.

        Args:
            customer_id: Stripe Customer ID (cus_...)
            plan_id: Stripe Price ID (price_...)
            payment_method: Dict with 'token' key for default payment method
            metadata: Optional metadata

        Returns:
            Dictionary with subscription result
        """
        try:
            sub_params = {
                'customer': customer_id,
                'items': [{'price': plan_id}],
            }

            pm_token = payment_method.get('token')
            if pm_token:
                sub_params['default_payment_method'] = pm_token

            if metadata:
                sub_params['metadata'] = {
                    str(k): str(v) for k, v in metadata.items()
                }

            sub = stripe.Subscription.create(**sub_params)

            logger.info(
                "Stripe subscription created: %s (status=%s)",
                sub.id, sub.status
            )

            return {
                'success': sub.status in ('active', 'trialing'),
                'subscription_id': sub.id,
                'provider_subscription_id': sub.id,
                'status': sub.status,
                'current_period_start': datetime.fromtimestamp(sub.current_period_start) if sub.current_period_start else None,
                'current_period_end': datetime.fromtimestamp(sub.current_period_end) if sub.current_period_end else None,
                'next_billing_date': datetime.fromtimestamp(sub.current_period_end) if sub.current_period_end else None,
                'message': f'Subscription {sub.status}',
                'raw_response': dict(sub),
            }

        except stripe.error.StripeError as e:
            logger.error("Stripe error creating subscription: %s", str(e))
            return {
                'success': False,
                'subscription_id': None,
                'provider_subscription_id': None,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error creating subscription: %s", str(e))
            return {
                'success': False,
                'subscription_id': None,
                'provider_subscription_id': None,
                'status': 'failed',
                'message': f'Subscription error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription.

        Args:
            subscription_id: Stripe Subscription ID (sub_...)
            immediately: If True, cancel immediately; if False, cancel at period end
            metadata: Optional metadata

        Returns:
            Dictionary with cancellation result
        """
        try:
            if immediately:
                sub = stripe.Subscription.cancel(subscription_id)
            else:
                sub = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )

            logger.info(
                "Stripe subscription canceled: %s (immediately=%s)",
                sub.id, immediately
            )

            return {
                'success': True,
                'subscription_id': sub.id,
                'status': 'canceled' if immediately else 'cancel_at_period_end',
                'canceled_at': datetime.now() if immediately else None,
                'ends_at': datetime.fromtimestamp(sub.current_period_end) if sub.current_period_end else None,
                'message': 'Subscription canceled' if immediately else 'Subscription will cancel at period end',
                'raw_response': dict(sub),
            }

        except stripe.error.StripeError as e:
            logger.error("Stripe error canceling subscription: %s", str(e))
            return {
                'success': False,
                'subscription_id': subscription_id,
                'status': 'failed',
                'message': str(e),
                'raw_response': {'error': str(e)},
            }
        except Exception as e:
            logger.error("Unexpected error canceling subscription: %s", str(e))
            return {
                'success': False,
                'subscription_id': subscription_id,
                'status': 'failed',
                'message': f'Cancellation error: {str(e)}',
                'raw_response': {'error': str(e)},
            }

    # ===========================
    # Subscription Webhook Translation
    # ===========================

    _SUBSCRIPTION_EVENT_MAP = {
        'customer.subscription.created': SubscriptionEventType.CREATED,
        'customer.subscription.deleted': SubscriptionEventType.CANCELED,
        'customer.subscription.paused': SubscriptionEventType.PAUSED,
        'customer.subscription.resumed': SubscriptionEventType.RESUMED,
        'customer.subscription.trial_will_end': SubscriptionEventType.TRIAL_ENDING,
    }

    def translate_subscription_webhook(
        self, event_type: str, payload: dict
    ) -> Optional[SubscriptionEvent]:
        """
        Translate Stripe webhook event to standardized SubscriptionEvent.
        Returns None for non-subscription events.
        """
        data_object = payload.get('data', {}).get('object', {})
        event_id = payload.get('id', '')

        # Direct subscription events
        if event_type in self._SUBSCRIPTION_EVENT_MAP:
            return self._translate_subscription_event(
                event_type, event_id, data_object,
                self._SUBSCRIPTION_EVENT_MAP[event_type]
            )

        # customer.subscription.updated requires status inspection
        if event_type == 'customer.subscription.updated':
            return self._translate_subscription_updated(
                event_type, event_id, data_object, payload
            )

        # Invoice events - only if they have a subscription field
        if event_type in (
            'invoice.payment_succeeded', 'invoice.payment_failed', 'invoice.upcoming'
        ):
            subscription_id = data_object.get('subscription')
            if not subscription_id:
                return None  # Not a subscription invoice
            return self._translate_invoice_event(event_type, event_id, data_object)

        return None

    def _translate_subscription_event(
        self, stripe_event_type: str, event_id: str,
        data: dict, std_type: SubscriptionEventType
    ) -> SubscriptionEvent:
        """Translate a direct subscription event."""
        sub_id = data.get('id', '')
        customer_id = data.get('customer', '')

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': customer_id,
            'provider_event_type': stripe_event_type,
        }

        # Extract period from subscription data
        if data.get('current_period_start'):
            kwargs['period_start'] = datetime.fromtimestamp(
                data['current_period_start'], tz=django_timezone.utc
            )
        if data.get('current_period_end'):
            kwargs['period_end'] = datetime.fromtimestamp(
                data['current_period_end'], tz=django_timezone.utc
            )

        return SubscriptionEvent(**kwargs)

    def _translate_subscription_updated(
        self, stripe_event_type: str, event_id: str,
        data: dict, payload: dict
    ) -> SubscriptionEvent:
        """Translate customer.subscription.updated based on status changes."""
        status = data.get('status', '')
        previous_attributes = payload.get('data', {}).get('previous_attributes', {})
        previous_status = previous_attributes.get('status', '')

        # Determine the most specific event type
        if status == 'past_due':
            std_type = SubscriptionEventType.PAST_DUE
        elif status == 'active' and previous_status == 'trialing':
            std_type = SubscriptionEventType.ACTIVATED
        else:
            std_type = SubscriptionEventType.UPDATED

        return self._translate_subscription_event(
            stripe_event_type, event_id, data, std_type
        )

    def _translate_invoice_event(
        self, stripe_event_type: str, event_id: str, data: dict
    ) -> SubscriptionEvent:
        """Translate invoice events related to subscriptions."""
        event_map = {
            'invoice.payment_succeeded': SubscriptionEventType.PAYMENT_SUCCEEDED,
            'invoice.payment_failed': SubscriptionEventType.PAYMENT_FAILED,
            'invoice.upcoming': SubscriptionEventType.RENEWAL_UPCOMING,
        }

        std_type = event_map[stripe_event_type]
        sub_id = data.get('subscription', '')
        customer_id = data.get('customer', '')

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': customer_id,
            'provider_event_type': stripe_event_type,
        }

        # Extract financial details from invoice - Stripe uses cents
        amount_cents = data.get('amount_paid') or data.get('amount_due') or 0
        if amount_cents:
            kwargs['amount'] = Decimal(str(amount_cents)) / Decimal('100')
        kwargs['currency'] = (data.get('currency') or '').upper()

        # Extract period from invoice lines
        lines = data.get('lines', {}).get('data', [])
        if lines:
            period = lines[0].get('period', {})
            if period.get('start'):
                kwargs['period_start'] = datetime.fromtimestamp(
                    period['start'], tz=django_timezone.utc
                )
            if period.get('end'):
                kwargs['period_end'] = datetime.fromtimestamp(
                    period['end'], tz=django_timezone.utc
                )

        # Extract error details for failed payments
        if std_type == SubscriptionEventType.PAYMENT_FAILED:
            charge = data.get('charge')
            if isinstance(charge, dict):
                failure = charge.get('failure_message', '')
                code = charge.get('failure_code', '')
            else:
                error_info = data.get('last_finalization_error') or {}
                failure = error_info.get('message', '')
                code = error_info.get('code', '')
            kwargs['error_message'] = failure
            kwargs['error_code'] = code

        return SubscriptionEvent(**kwargs)
