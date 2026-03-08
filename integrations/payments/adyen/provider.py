"""
Adyen Payment Provider for Spwig eCommerce Platform

Enterprise-grade payment processing with 250+ payment methods across 40+ countries.
Uses the Adyen Checkout API v71 and Management API v3.

API Documentation: https://docs.adyen.com/api-explorer/
"""
import base64
import binascii
import hashlib
import hmac
import json
import logging
import requests
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from payment_providers.providers.base import PaymentProviderBase

logger = logging.getLogger(__name__)

# Currencies that use zero decimal (minor units = 1)
ZERO_DECIMAL_CURRENCIES = {
    'BIF', 'CLP', 'DJF', 'GNF', 'ISK', 'JPY', 'KMF', 'KRW',
    'PYG', 'RWF', 'UGX', 'UYI', 'VND', 'VUV', 'XAF', 'XOF', 'XPF',
}

# Currencies that use 3 decimal places
THREE_DECIMAL_CURRENCIES = {
    'BHD', 'IQD', 'JOD', 'KWD', 'LYD', 'OMR', 'TND',
}


def amount_to_minor_units(amount: Decimal, currency: str) -> int:
    """
    Convert a Decimal amount to Adyen minor units (integer).

    Adyen expects amounts in the smallest currency unit:
    - Most currencies: cents (multiply by 100). $99.99 -> 9999
    - Zero-decimal currencies (JPY, KRW, etc.): no multiplier. 100 JPY -> 100
    - Three-decimal currencies (BHD, KWD, etc.): multiply by 1000

    Args:
        amount: Decimal amount (e.g., Decimal('99.99'))
        currency: ISO 4217 currency code

    Returns:
        Integer amount in minor units
    """
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return int(amount)
    elif currency_upper in THREE_DECIMAL_CURRENCIES:
        return int(amount * 1000)
    else:
        return int(amount * 100)


def minor_units_to_amount(minor_units: int, currency: str) -> Decimal:
    """
    Convert Adyen minor units back to a Decimal amount.

    Args:
        minor_units: Integer amount in minor units
        currency: ISO 4217 currency code

    Returns:
        Decimal amount
    """
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return Decimal(str(minor_units))
    elif currency_upper in THREE_DECIMAL_CURRENCIES:
        return Decimal(str(minor_units)) / Decimal('1000')
    else:
        return Decimal(str(minor_units)) / Decimal('100')


class AdyenProvider(PaymentProviderBase):
    """
    Adyen payment provider implementation.

    Supports:
    - Payment sessions (Drop-in / Components)
    - Authorize and capture workflows
    - Full and partial refunds
    - Webhook verification (HMAC-SHA256)
    - Multi-currency transactions across 150+ currencies
    - 250+ payment methods globally
    - 3D Secure 2 authentication

    API Versions:
    - Checkout API: v71
    - Management API: v3
    """

    provider_key = 'adyen'
    provider_name = 'Adyen'

    # API version constants
    CHECKOUT_API_VERSION = 'v71'
    MANAGEMENT_API_VERSION = 'v3'

    # Base URLs
    CHECKOUT_TEST_BASE = 'https://checkout-test.adyen.com'
    MANAGEMENT_TEST_BASE = 'https://management-test.adyen.com'
    MANAGEMENT_LIVE_BASE = 'https://management-live.adyen.com'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Adyen provider with credentials.

        Args:
            credentials: Dictionary containing:
                - api_key: Adyen API Key (required)
                - merchant_account: Adyen Merchant Account name (required)
                - client_key: Client-side key for Drop-in (required)
                - hmac_key: HMAC key for webhook verification (optional)
                - environment: 'test' or 'live' (default: 'test')
                - live_endpoint_prefix: Required for live environment
            config: Optional additional configuration
        """
        # Extract credentials before calling super().__init__
        # (super calls validate_credentials which needs these)
        self.api_key = credentials.get('api_key', '')
        self.merchant_account = credentials.get('merchant_account', '')
        self.client_key = credentials.get('client_key', '')
        self.hmac_key = credentials.get('hmac_key', '')
        self.environment = credentials.get('environment', 'test')
        self.live_endpoint_prefix = credentials.get('live_endpoint_prefix', '')

        # Set API base URLs based on environment
        self._setup_api_urls()

        # Call parent init (validates credentials)
        super().__init__(credentials, config)

    def _setup_api_urls(self):
        """Configure API base URLs based on environment."""
        if self.environment == 'live':
            if not self.live_endpoint_prefix:
                logger.warning(
                    "Live endpoint prefix not set. Live API calls will fail. "
                    "Get your prefix from Adyen Customer Area -> Settings -> API URLs"
                )
            self.checkout_base = (
                f'https://{self.live_endpoint_prefix}-checkout-live.adyenpayments.com'
                f'/checkout/{self.CHECKOUT_API_VERSION}'
            )
            self.management_base = f'{self.MANAGEMENT_LIVE_BASE}/{self.MANAGEMENT_API_VERSION}'
        else:
            self.checkout_base = f'{self.CHECKOUT_TEST_BASE}/{self.CHECKOUT_API_VERSION}'
            self.management_base = f'{self.MANAGEMENT_TEST_BASE}/{self.MANAGEMENT_API_VERSION}'

    # -------------------------------------------------------------------------
    # Abstract property implementations
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
            '3d_secure': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """Return JSON schema describing required credentials."""
        return {
            'type': 'object',
            'properties': {
                'api_key': {
                    'type': 'string',
                    'title': 'API Key',
                    'description': 'Your Adyen API key from Customer Area -> Developers -> API credentials',
                    'required': True,
                    'secret': True,
                },
                'merchant_account': {
                    'type': 'string',
                    'title': 'Merchant Account',
                    'description': 'Your Adyen merchant account name',
                    'required': True,
                },
                'client_key': {
                    'type': 'string',
                    'title': 'Client Key',
                    'description': 'Client-side key for Adyen Drop-in/Components',
                    'required': True,
                },
                'hmac_key': {
                    'type': 'string',
                    'title': 'HMAC Key',
                    'description': 'HMAC key for webhook signature verification',
                    'required': False,
                    'secret': True,
                },
                'environment': {
                    'type': 'string',
                    'title': 'Environment',
                    'enum': ['test', 'live'],
                    'default': 'test',
                    'required': True,
                },
                'live_endpoint_prefix': {
                    'type': 'string',
                    'title': 'Live Endpoint Prefix',
                    'description': 'Required for live environment. Found in Customer Area -> Settings -> API URLs',
                    'required': False,
                },
            }
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        """Return list of supported payment method types."""
        return [
            'credit_card', 'debit_card', 'bank_transfer', 'digital_wallet',
            'buy_now_pay_later', 'local_methods',
        ]

    @property
    def supported_currencies(self) -> List[str]:
        """Return list of supported currency codes (150+)."""
        return [
            'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD', 'HKD', 'CNY', 'JPY',
            'NZD', 'CHF', 'SEK', 'DKK', 'NOK', 'PLN', 'CZK', 'HUF', 'RON',
            'BGN', 'HRK', 'THB', 'MYR', 'PHP', 'IDR', 'VND', 'KRW', 'TWD',
            'INR', 'BRL', 'MXN', 'CLP', 'COP', 'PEN', 'ARS', 'ZAR', 'AED',
            'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'ILS', 'EGP', 'TRY',
            'RUB', 'UAH', 'KZT', 'NGN', 'KES', 'GHS', 'MAD', 'TND',
        ]

    @property
    def supported_countries(self) -> List[str]:
        """Return list of supported country codes (40+)."""
        return [
            'US', 'GB', 'DE', 'FR', 'NL', 'BE', 'AT', 'CH', 'IT', 'ES',
            'PT', 'IE', 'SE', 'NO', 'DK', 'FI', 'PL', 'CZ', 'HU', 'RO',
            'BG', 'HR', 'LT', 'LV', 'EE', 'SK', 'SI', 'AU', 'NZ', 'SG',
            'HK', 'JP', 'KR', 'TW', 'TH', 'MY', 'PH', 'ID', 'VN', 'IN',
            'BR', 'MX', 'CA', 'ZA', 'AE', 'SA', 'QA', 'KW', 'BH', 'OM',
        ]

    # -------------------------------------------------------------------------
    # Credential methods
    # -------------------------------------------------------------------------

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate Adyen credentials.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If required credentials are missing
        """
        api_key = credentials.get('api_key', '')
        merchant_account = credentials.get('merchant_account', '')

        if not api_key:
            raise ValueError("Adyen API Key is required")

        if not merchant_account:
            raise ValueError("Adyen Merchant Account is required")

        environment = credentials.get('environment', 'test')
        if environment == 'live':
            live_prefix = credentials.get('live_endpoint_prefix', '')
            if not live_prefix:
                raise ValueError(
                    "Live Endpoint Prefix is required for the live environment. "
                    "Find it in Customer Area -> Settings -> API URLs"
                )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging/display.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = dict(credentials)

        if 'api_key' in redacted and redacted['api_key']:
            key = redacted['api_key']
            if len(key) > 8:
                redacted['api_key'] = f"{key[:4]}...{key[-4:]}"
            else:
                redacted['api_key'] = '***'

        if 'hmac_key' in redacted and redacted['hmac_key']:
            key = redacted['hmac_key']
            if len(key) > 8:
                redacted['hmac_key'] = f"{key[:4]}...{key[-4:]}"
            else:
                redacted['hmac_key'] = '***'

        if 'client_key' in redacted and redacted['client_key']:
            key = redacted['client_key']
            if len(key) > 8:
                redacted['client_key'] = f"{key[:8]}...{key[-4:]}"
            else:
                redacted['client_key'] = '***'

        return redacted

    # -------------------------------------------------------------------------
    # HTTP request helper
    # -------------------------------------------------------------------------

    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Adyen API.

        Adyen uses API Key authentication via the X-API-Key header.
        No token exchange is required.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full API URL
            data: Request body data
            params: URL query parameters
            timeout: Request timeout in seconds

        Returns:
            Response JSON as dictionary

        Raises:
            ConnectionError: If request fails
        """
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()

            # Some endpoints return empty body on success (e.g., 204)
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_detail = ''
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get('message', '')
                    error_code = error_data.get('errorCode', '')
                    logger.error(
                        f"Adyen API error: status={e.response.status_code}, "
                        f"code={error_code}, message={error_detail}"
                    )
                except (ValueError, KeyError):
                    error_detail = e.response.text[:500]
                    logger.error(f"Adyen API error: {error_detail}")

            raise ConnectionError(
                f"Adyen API request failed ({method} {url}): "
                f"{error_detail or str(e)}"
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Adyen connection error: {str(e)}")
            raise ConnectionError(f"Could not connect to Adyen API: {str(e)}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Adyen request timeout: {str(e)}")
            raise ConnectionError(f"Adyen API request timed out after {timeout}s")

        except requests.exceptions.RequestException as e:
            logger.error(f"Adyen request exception: {str(e)}")
            raise ConnectionError(f"Adyen API request failed: {str(e)}")

    # -------------------------------------------------------------------------
    # Connection test
    # -------------------------------------------------------------------------

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Adyen API by fetching merchant accounts.

        Uses the Management API to verify the API key is valid and
        the merchant account exists.

        Returns:
            Dictionary with 'success', 'message', and 'details'
        """
        try:
            url = f"{self.management_base}/merchants"
            response = self._make_request(method='GET', url=url, timeout=15)

            # Check if our merchant account is in the list
            merchants = response.get('data', [])
            merchant_ids = [m.get('merchantAccountCode', '') for m in merchants]

            found = self.merchant_account in merchant_ids

            if found:
                return {
                    'success': True,
                    'message': f'Successfully connected to Adyen (merchant: {self.merchant_account})',
                    'details': {
                        'environment': self.environment,
                        'merchant_account': self.merchant_account,
                        'total_merchants': len(merchants),
                        'api_version': self.CHECKOUT_API_VERSION,
                    }
                }
            else:
                return {
                    'success': True,
                    'message': (
                        f'Connected to Adyen API, but merchant account '
                        f'\"{self.merchant_account}\" was not found in the list of '
                        f'{len(merchants)} merchant account(s). Please verify the name.'
                    ),
                    'details': {
                        'environment': self.environment,
                        'merchant_account': self.merchant_account,
                        'available_merchants': merchant_ids[:10],
                    }
                }

        except ConnectionError as e:
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {
                    'environment': self.environment,
                    'error': str(e),
                }
            }
        except Exception as e:
            logger.exception("Unexpected error during Adyen connection test")
            return {
                'success': False,
                'message': f'Connection test failed unexpectedly: {str(e)}',
                'details': {
                    'environment': self.environment,
                    'error': str(e),
                }
            }

    # -------------------------------------------------------------------------
    # Payment processing methods
    # -------------------------------------------------------------------------

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process an immediate payment charge (authorize + capture).

        Uses Adyen /payments endpoint with captureDelayHours=0 for
        immediate capture.

        Args:
            amount: Payment amount (e.g., Decimal('99.99'))
            currency: Currency code (e.g., 'USD')
            payment_method: Payment method details with 'type' and 'token' keys
            metadata: Optional metadata (order_id, customer_email, etc.)

        Returns:
            Dictionary with transaction result
        """
        metadata = metadata or {}
        currency_upper = currency.upper()
        minor_amount = amount_to_minor_units(amount, currency_upper)
        reference = metadata.get('order_id', f'charge_{datetime.now().strftime("%Y%m%d%H%M%S")}')

        payload = {
            'amount': {
                'currency': currency_upper,
                'value': minor_amount,
            },
            'paymentMethod': payment_method.get('token', payment_method),
            'merchantAccount': self.merchant_account,
            'reference': reference,
            'captureDelayHours': 0,  # Immediate capture
        }

        # Add return URL for 3DS
        if metadata.get('return_url'):
            payload['returnUrl'] = metadata['return_url']

        # Add shopper details
        if metadata.get('customer_email'):
            payload['shopperEmail'] = metadata['customer_email']
        if metadata.get('customer_id'):
            payload['shopperReference'] = metadata['customer_id']

        # Add metadata
        clean_meta = {k: str(v) for k, v in metadata.items()
                     if k not in ('return_url', 'customer_email', 'customer_id', 'order_id')}
        if clean_meta:
            payload['metadata'] = clean_meta

        try:
            url = f"{self.checkout_base}/payments"
            response = self._make_request(method='POST', url=url, data=payload)

            result_code = response.get('resultCode', '')
            psp_reference = response.get('pspReference', '')

            if result_code == 'Authorised':
                logger.info(f"Adyen charge successful: pspRef={psp_reference}, amount={amount} {currency_upper}")
                return {
                    'success': True,
                    'transaction_id': psp_reference,
                    'provider_transaction_id': psp_reference,
                    'status': 'completed',
                    'amount': amount,
                    'currency': currency_upper,
                    'created_at': datetime.now(),
                    'message': 'Payment successful',
                    'raw_response': response,
                }
            elif result_code in ('RedirectShopper', 'IdentifyShopper', 'ChallengeShopper'):
                logger.info(f"Adyen charge requires action: {result_code}")
                return {
                    'success': False,
                    'transaction_id': psp_reference,
                    'provider_transaction_id': psp_reference,
                    'status': 'requires_action',
                    'amount': amount,
                    'currency': currency_upper,
                    'requires_action': True,
                    'action': response.get('action', {}),
                    'message': f'Customer action required: {result_code}',
                    'raw_response': response,
                }
            else:
                refusal_reason = response.get('refusalReason', 'Unknown')
                logger.warning(f"Adyen charge failed: {result_code} - {refusal_reason}")
                return {
                    'success': False,
                    'transaction_id': psp_reference,
                    'provider_transaction_id': psp_reference,
                    'status': 'failed',
                    'amount': amount,
                    'currency': currency_upper,
                    'created_at': datetime.now(),
                    'message': f'Payment failed: {refusal_reason}',
                    'error_code': response.get('refusalReasonCode', ''),
                    'raw_response': response,
                }

        except ConnectionError as e:
            logger.error(f"Adyen charge connection error: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency_upper,
                'message': f'Payment request failed: {str(e)}',
                'raw_response': {},
            }

    def authorize(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Authorize a payment without capturing funds.

        Uses Adyen /payments endpoint with captureDelayHours=-1 (manual capture).

        Args:
            amount: Authorization amount
            currency: Currency code
            payment_method: Payment method details
            metadata: Optional metadata

        Returns:
            Dictionary with authorization result
        """
        metadata = metadata or {}
        currency_upper = currency.upper()
        minor_amount = amount_to_minor_units(amount, currency_upper)
        reference = metadata.get('order_id', f'auth_{datetime.now().strftime("%Y%m%d%H%M%S")}')

        payload = {
            'amount': {
                'currency': currency_upper,
                'value': minor_amount,
            },
            'paymentMethod': payment_method.get('token', payment_method),
            'merchantAccount': self.merchant_account,
            'reference': reference,
            'captureDelayHours': -1,  # Manual capture (authorize only)
        }

        if metadata.get('return_url'):
            payload['returnUrl'] = metadata['return_url']
        if metadata.get('customer_email'):
            payload['shopperEmail'] = metadata['customer_email']
        if metadata.get('customer_id'):
            payload['shopperReference'] = metadata['customer_id']

        try:
            url = f"{self.checkout_base}/payments"
            response = self._make_request(method='POST', url=url, data=payload)

            result_code = response.get('resultCode', '')
            psp_reference = response.get('pspReference', '')

            if result_code == 'Authorised':
                logger.info(f"Adyen authorization successful: pspRef={psp_reference}")
                return {
                    'success': True,
                    'authorization_id': psp_reference,
                    'provider_authorization_id': psp_reference,
                    'status': 'authorized',
                    'amount': amount,
                    'currency': currency_upper,
                    'expires_at': datetime.now() + timedelta(days=28),
                    'created_at': datetime.now(),
                    'message': 'Authorization successful',
                    'raw_response': response,
                }
            elif result_code in ('RedirectShopper', 'IdentifyShopper', 'ChallengeShopper'):
                return {
                    'success': False,
                    'authorization_id': psp_reference,
                    'provider_authorization_id': psp_reference,
                    'status': 'requires_action',
                    'amount': amount,
                    'currency': currency_upper,
                    'requires_action': True,
                    'action': response.get('action', {}),
                    'message': f'Customer action required: {result_code}',
                    'raw_response': response,
                }
            else:
                refusal_reason = response.get('refusalReason', 'Unknown')
                logger.warning(f"Adyen authorization failed: {result_code} - {refusal_reason}")
                return {
                    'success': False,
                    'authorization_id': psp_reference,
                    'provider_authorization_id': psp_reference,
                    'status': 'failed',
                    'amount': amount,
                    'currency': currency_upper,
                    'created_at': datetime.now(),
                    'message': f'Authorization failed: {refusal_reason}',
                    'raw_response': response,
                }

        except ConnectionError as e:
            logger.error(f"Adyen authorize connection error: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency_upper,
                'message': f'Authorization request failed: {str(e)}',
                'raw_response': {},
            }

    def capture(
        self,
        authorization_id: str,
        amount: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture funds from a previous authorization.

        Uses POST /payments/{pspReference}/captures.

        Args:
            authorization_id: Adyen pspReference from the authorization
            amount: Amount to capture (partial capture supported)
            metadata: Optional metadata (must include 'currency')

        Returns:
            Dictionary with capture result
        """
        metadata = metadata or {}

        payload = {
            'merchantAccount': self.merchant_account,
        }

        # Amount is required for Adyen captures
        if amount is not None:
            currency = metadata.get('currency', 'USD')
            minor_amount = amount_to_minor_units(amount, currency)
            payload['amount'] = {
                'currency': currency.upper(),
                'value': minor_amount,
            }

        if metadata.get('reference'):
            payload['reference'] = metadata['reference']

        try:
            url = f"{self.checkout_base}/payments/{authorization_id}/captures"
            response = self._make_request(method='POST', url=url, data=payload)

            psp_reference = response.get('pspReference', '')
            status = response.get('status', '')

            logger.info(f"Adyen capture submitted: original={authorization_id}, capture={psp_reference}")

            return {
                'success': True,
                'transaction_id': psp_reference,
                'provider_transaction_id': psp_reference,
                'status': 'completed' if status == 'received' else status,
                'amount': amount,
                'currency': metadata.get('currency', 'USD'),
                'created_at': datetime.now(),
                'message': 'Capture submitted successfully',
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Adyen capture failed: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Capture request failed: {str(e)}',
                'raw_response': {},
            }

    def void(
        self,
        authorization_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Void an uncaptured authorization (cancel).

        Uses POST /payments/{pspReference}/cancels.

        Args:
            authorization_id: Adyen pspReference from the authorization
            metadata: Optional metadata

        Returns:
            Dictionary with void result
        """
        metadata = metadata or {}

        payload = {
            'merchantAccount': self.merchant_account,
        }

        if metadata.get('reference'):
            payload['reference'] = metadata['reference']

        try:
            url = f"{self.checkout_base}/payments/{authorization_id}/cancels"
            response = self._make_request(method='POST', url=url, data=payload)

            psp_reference = response.get('pspReference', '')
            status = response.get('status', '')

            logger.info(f"Adyen void submitted: original={authorization_id}, cancel={psp_reference}")

            return {
                'success': True,
                'authorization_id': authorization_id,
                'status': 'voided' if status == 'received' else status,
                'message': 'Authorization void submitted successfully',
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Adyen void failed: {str(e)}")
            return {
                'success': False,
                'authorization_id': authorization_id,
                'status': 'failed',
                'message': f'Void request failed: {str(e)}',
                'raw_response': {},
            }

    def refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Refund a completed payment (full or partial).

        Uses POST /payments/{pspReference}/refunds.

        Args:
            transaction_id: Adyen pspReference of the original payment
            amount: Amount to refund (None for full refund)
            reason: Optional refund reason
            metadata: Optional metadata (must include 'currency' for partial refunds)

        Returns:
            Dictionary with refund result
        """
        metadata = metadata or {}

        payload = {
            'merchantAccount': self.merchant_account,
        }

        if amount is not None:
            currency = metadata.get('currency', 'USD')
            minor_amount = amount_to_minor_units(amount, currency)
            payload['amount'] = {
                'currency': currency.upper(),
                'value': minor_amount,
            }

        if reason:
            payload['reference'] = reason[:80]  # Adyen reference max length

        try:
            url = f"{self.checkout_base}/payments/{transaction_id}/refunds"
            response = self._make_request(method='POST', url=url, data=payload)

            psp_reference = response.get('pspReference', '')
            status = response.get('status', '')

            logger.info(
                f"Adyen refund submitted: original={transaction_id}, "
                f"refund={psp_reference}, amount={amount}"
            )

            return {
                'success': True,
                'refund_id': psp_reference,
                'provider_refund_id': psp_reference,
                'status': 'completed' if status == 'received' else status,
                'amount': amount,
                'currency': metadata.get('currency', 'USD'),
                'created_at': datetime.now(),
                'message': 'Refund submitted successfully',
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Adyen refund failed: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Refund request failed: {str(e)}',
                'raw_response': {},
            }

    # -------------------------------------------------------------------------
    # Webhook methods
    # -------------------------------------------------------------------------

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify Adyen webhook HMAC-SHA256 signature.

        Adyen webhook verification uses HMAC-SHA256 with a specific signing string
        format composed of notification fields separated by colons.

        The signing string format is:
            pspReference:originalReference:merchantAccountCode:merchantReference:
            amount.value:amount.currency:eventCode:success

        Args:
            payload: Raw request body as bytes (JSON)
            signature: The HMAC signature from the notification
            **kwargs: Additional headers (not used for Adyen HMAC)

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.hmac_key:
            logger.warning(
                "HMAC key not configured for Adyen webhook verification. "
                "Allowing webhook without signature check."
            )
            return True

        try:
            # Parse the notification payload
            data = json.loads(payload.decode('utf-8'))

            # Adyen sends notifications in notificationItems array
            notification_items = data.get('notificationItems', [])
            if not notification_items:
                logger.error("No notification items found in webhook payload")
                return False

            # Verify each notification item
            for item in notification_items:
                notification = item.get('NotificationRequestItem', {})

                # Build the signing string from notification fields
                sign_fields = [
                    notification.get('pspReference', ''),
                    notification.get('originalReference', ''),
                    notification.get('merchantAccountCode', ''),
                    notification.get('merchantReference', ''),
                    str(notification.get('amount', {}).get('value', '')),
                    notification.get('amount', {}).get('currency', ''),
                    notification.get('eventCode', ''),
                    notification.get('success', ''),
                ]
                sign_string = ':'.join(sign_fields)

                # Compute HMAC-SHA256
                hmac_key_bytes = binascii.a2b_hex(self.hmac_key)
                computed = base64.b64encode(
                    hmac.new(
                        hmac_key_bytes,
                        sign_string.encode('utf-8'),
                        hashlib.sha256
                    ).digest()
                ).decode('utf-8')

                # Get the signature from the notification additionalData
                notification_signature = notification.get(
                    'additionalData', {}
                ).get('hmacSignature', '')

                if not notification_signature:
                    # Fall back to the passed signature parameter
                    notification_signature = signature

                if not hmac.compare_digest(computed, notification_signature):
                    logger.error("Adyen webhook HMAC signature mismatch")
                    return False

            return True

        except (json.JSONDecodeError, ValueError, binascii.Error) as e:
            logger.error(f"Adyen webhook signature verification error: {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error verifying Adyen webhook: {str(e)}")
            return False

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event from Adyen.

        Adyen webhook event types:
        - AUTHORISATION: Payment authorized (success or failure)
        - CAPTURE: Payment captured
        - CANCELLATION: Payment canceled/voided
        - REFUND: Refund processed
        - REFUND_FAILED: Refund failed

        Args:
            event_type: Adyen event code (e.g., 'AUTHORISATION')
            payload: Parsed webhook notification item

        Returns:
            Dictionary with processed webhook data
        """
        logger.info(f"Processing Adyen webhook: {event_type}")

        # Extract common fields from the notification
        notification = payload.get('NotificationRequestItem', payload)
        psp_reference = notification.get('pspReference', '')
        merchant_reference = notification.get('merchantReference', '')
        success = notification.get('success', 'false').lower() == 'true'
        amount_data = notification.get('amount', {})
        currency = amount_data.get('currency', 'USD')
        minor_value = amount_data.get('value', 0)
        amount = minor_units_to_amount(minor_value, currency)

        if event_type == 'AUTHORISATION':
            if success:
                return {
                    'action': 'payment_completed',
                    'transaction_id': psp_reference,
                    'status': 'completed',
                    'amount': amount,
                    'currency': currency,
                    'metadata': {
                        'merchant_reference': merchant_reference,
                        'payment_method': notification.get('paymentMethod', ''),
                    },
                    'raw_event': payload,
                }
            else:
                reason = notification.get('reason', 'Unknown')
                return {
                    'action': 'payment_failed',
                    'transaction_id': psp_reference,
                    'status': 'failed',
                    'amount': amount,
                    'currency': currency,
                    'error': reason,
                    'metadata': {
                        'merchant_reference': merchant_reference,
                        'refusal_reason': reason,
                    },
                    'raw_event': payload,
                }

        elif event_type == 'CAPTURE':
            return {
                'action': 'payment_captured',
                'transaction_id': psp_reference,
                'status': 'captured',
                'amount': amount,
                'currency': currency,
                'metadata': {
                    'merchant_reference': merchant_reference,
                    'original_reference': notification.get('originalReference', ''),
                },
                'raw_event': payload,
            }

        elif event_type == 'CANCELLATION':
            return {
                'action': 'payment_voided',
                'transaction_id': psp_reference,
                'status': 'voided',
                'amount': amount,
                'currency': currency,
                'metadata': {
                    'merchant_reference': merchant_reference,
                    'original_reference': notification.get('originalReference', ''),
                },
                'raw_event': payload,
            }

        elif event_type == 'REFUND':
            return {
                'action': 'refund_completed',
                'transaction_id': psp_reference,
                'status': 'refunded',
                'amount': amount,
                'currency': currency,
                'metadata': {
                    'merchant_reference': merchant_reference,
                    'original_reference': notification.get('originalReference', ''),
                },
                'raw_event': payload,
            }

        elif event_type == 'REFUND_FAILED':
            reason = notification.get('reason', 'Unknown')
            return {
                'action': 'refund_failed',
                'transaction_id': psp_reference,
                'status': 'refund_failed',
                'amount': amount,
                'currency': currency,
                'error': reason,
                'metadata': {
                    'merchant_reference': merchant_reference,
                    'original_reference': notification.get('originalReference', ''),
                },
                'raw_event': payload,
            }

        else:
            logger.warning(f"Unhandled Adyen webhook event type: {event_type}")
            return {
                'action': 'unknown',
                'transaction_id': psp_reference,
                'status': event_type.lower(),
                'amount': amount,
                'currency': currency,
                'metadata': {'merchant_reference': merchant_reference},
                'raw_event': payload,
            }

    # -------------------------------------------------------------------------
    # Checkout / Payment Intent methods
    # -------------------------------------------------------------------------

    def create_payment_intent_for_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an Adyen payment session for Drop-in checkout.

        Uses POST /sessions to create a session that can be used with the
        Adyen Drop-in or Components frontend integration. This is Adyen's
        recommended checkout integration method.

        Args:
            amount: Payment amount
            currency: Currency code
            return_url: URL to redirect after payment
            cancel_url: URL to redirect on cancellation
            customer_email: Optional customer email
            metadata: Optional metadata (order_id, checkout_session_id, etc.)

        Returns:
            Dictionary with payment session details including sessionData
            and sessionId for the Drop-in component.
        """
        metadata = metadata or {}
        currency_upper = currency.upper()
        minor_amount = amount_to_minor_units(amount, currency_upper)
        reference = metadata.get(
            'order_id',
            f'session_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        )

        payload = {
            'amount': {
                'currency': currency_upper,
                'value': minor_amount,
            },
            'merchantAccount': self.merchant_account,
            'reference': reference,
            'returnUrl': return_url,
        }

        # Add country code if available (improves payment method availability)
        if metadata.get('country_code'):
            payload['countryCode'] = metadata['country_code'].upper()

        if customer_email:
            payload['shopperEmail'] = customer_email

        if metadata.get('customer_id'):
            payload['shopperReference'] = metadata['customer_id']

        # Add line items if provided
        if metadata.get('line_items'):
            payload['lineItems'] = metadata['line_items']

        # Store metadata
        clean_meta = {
            k: str(v) for k, v in metadata.items()
            if k not in ('return_url', 'cancel_url', 'customer_email',
                         'customer_id', 'order_id', 'country_code', 'line_items')
        }
        if clean_meta:
            payload['metadata'] = clean_meta

        try:
            url = f"{self.checkout_base}/sessions"
            response = self._make_request(method='POST', url=url, data=payload)

            session_id = response.get('id', '')
            session_data = response.get('sessionData', '')

            logger.info(f"Adyen session created: id={session_id}, ref={reference}")

            # For Drop-in, the frontend uses sessionId + sessionData
            checkout_url = response.get('url', '')

            return {
                'success': True,
                'provider_intent_id': session_id,
                'client_secret': session_data,  # sessionData for Drop-in
                'checkout_url': checkout_url,
                'status': 'created',
                'requires_action': False,
                'expires_at': datetime.now() + timedelta(hours=1),
                'extra': {
                    'session_id': session_id,
                    'session_data': session_data,
                    'client_key': self.client_key,
                    'environment': self.environment,
                },
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Adyen session creation failed: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Session creation failed: {str(e)}',
                'raw_response': {},
            }

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve payment details by pspReference.

        Note: Adyen sessions are one-shot and cannot be retrieved after creation.
        For payment status, use the pspReference from the payment result or
        webhook notification. Adyen delivers payment results asynchronously
        via webhooks.

        Args:
            intent_id: The pspReference (PSP reference) from a payment

        Returns:
            Dictionary with payment status
        """
        try:
            logger.info(f"Retrieving Adyen payment: {intent_id}")

            return {
                'success': True,
                'status': 'unknown',
                'provider_status': 'PENDING_WEBHOOK',
                'requires_action': False,
                'message': (
                    'Adyen payment status is delivered asynchronously via webhooks. '
                    'The payment status will be updated when the webhook notification arrives.'
                ),
                'raw_response': {'pspReference': intent_id},
            }

        except Exception as e:
            logger.error(f"Error retrieving Adyen payment: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'message': f'Failed to retrieve payment: {str(e)}',
                'raw_response': {},
            }

    def confirm_payment_intent(
        self,
        intent_id: str,
        confirmation_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Confirm a payment after 3DS redirect or other customer action.

        Uses POST /payments/details to submit the 3DS authentication result
        or redirect data back to Adyen.

        Args:
            intent_id: The pspReference or payment session ID
            confirmation_data: The redirect/3DS result data containing 'details'

        Returns:
            Dictionary with confirmation result
        """
        confirmation_data = confirmation_data or {}

        payload = {
            'details': confirmation_data.get('details', confirmation_data),
        }

        try:
            url = f"{self.checkout_base}/payments/details"
            response = self._make_request(method='POST', url=url, data=payload)

            result_code = response.get('resultCode', '')
            psp_reference = response.get('pspReference', '')

            if result_code == 'Authorised':
                logger.info(f"Adyen payment confirmed: pspRef={psp_reference}")
                return {
                    'success': True,
                    'status': 'succeeded',
                    'requires_action': False,
                    'payment_method_type': response.get('additionalData', {}).get('paymentMethod', ''),
                    'payment_method_last4': response.get('additionalData', {}).get('cardSummary', ''),
                    'message': 'Payment confirmed',
                    'raw_response': response,
                }
            elif result_code in ('RedirectShopper', 'IdentifyShopper', 'ChallengeShopper'):
                return {
                    'success': False,
                    'status': 'requires_action',
                    'requires_action': True,
                    'action': response.get('action', {}),
                    'message': f'Additional action required: {result_code}',
                    'raw_response': response,
                }
            else:
                refusal_reason = response.get('refusalReason', 'Unknown')
                return {
                    'success': False,
                    'status': 'failed',
                    'requires_action': False,
                    'error': {
                        'code': response.get('refusalReasonCode', ''),
                        'message': refusal_reason,
                    },
                    'message': f'Payment failed: {refusal_reason}',
                    'raw_response': response,
                }

        except ConnectionError as e:
            logger.error(f"Adyen payment confirmation failed: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Payment confirmation failed: {str(e)}',
                'raw_response': {},
            }

    def cancel_payment_intent(
        self,
        intent_id: str,
        cancellation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Cancel a payment (void an authorization).

        Uses POST /payments/{pspReference}/cancels.

        Args:
            intent_id: The pspReference of the payment to cancel
            cancellation_reason: Optional reason for cancellation

        Returns:
            Dictionary with cancellation result
        """
        payload = {
            'merchantAccount': self.merchant_account,
        }

        if cancellation_reason:
            payload['reference'] = cancellation_reason[:80]

        try:
            url = f"{self.checkout_base}/payments/{intent_id}/cancels"
            response = self._make_request(method='POST', url=url, data=payload)

            psp_reference = response.get('pspReference', '')

            logger.info(f"Adyen payment cancelled: original={intent_id}, cancel={psp_reference}")

            return {
                'success': True,
                'status': 'canceled',
                'message': 'Payment intent canceled',
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Adyen payment cancellation failed: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Cancellation failed: {str(e)}',
                'raw_response': {},
            }

    def get_payment_method_types(self) -> Dict[str, Any]:
        """
        Fetch available payment methods from Adyen for the merchant account.

        Uses POST /paymentMethods to query Adyen for available payment methods.
        Can be filtered by country and amount.

        Returns:
            Dictionary with payment methods organized by country
        """
        try:
            payload = {
                'merchantAccount': self.merchant_account,
            }

            url = f"{self.checkout_base}/paymentMethods"
            response = self._make_request(method='POST', url=url, data=payload)

            # Parse the response
            payment_methods = response.get('paymentMethods', [])

            # Organize by slug
            method_slugs = []
            for method in payment_methods:
                method_type = method.get('type', '')
                if method_type:
                    method_slugs.append(method_type)

            # Distribute across supported countries
            countries = self.supported_countries
            methods_by_country = {country: list(method_slugs) for country in countries}

            logger.info(f"Fetched {len(method_slugs)} payment methods from Adyen")

            return {
                'success': True,
                'methods': methods_by_country,
                'raw_response': response,
            }

        except ConnectionError as e:
            logger.error(f"Failed to fetch Adyen payment methods: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to fetch payment methods: {str(e)}',
                'methods': {},
            }

    # -------------------------------------------------------------------------
    # Hosted checkout (pay by link)
    # -------------------------------------------------------------------------

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a hosted checkout session (Adyen Pay by Link).

        This creates a payment link that the customer can be redirected to.

        Args:
            amount: Payment amount
            currency: Currency code
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancellation
            metadata: Optional metadata

        Returns:
            Dictionary with checkout session details
        """
        return self.create_payment_intent_for_checkout(
            amount=amount,
            currency=currency,
            return_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )

    def get_checkout_client_secret(
        self,
        amount: Decimal,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get client secret for integrated (Drop-in) checkout.

        Creates a session and returns the sessionData as client_secret
        along with the client key needed for the frontend SDK.

        Args:
            amount: Payment amount
            currency: Currency code
            metadata: Optional metadata

        Returns:
            Dictionary with client secret and publishable key
        """
        metadata = metadata or {}
        return_url = metadata.get('return_url', '')

        result = self.create_payment_intent_for_checkout(
            amount=amount,
            currency=currency,
            return_url=return_url,
            cancel_url=return_url,
            metadata=metadata,
        )

        if result.get('success'):
            return {
                'success': True,
                'client_secret': result.get('client_secret', ''),
                'publishable_key': self.client_key,
                'intent_id': result.get('provider_intent_id', ''),
                'message': 'Client secret generated',
                'extra': result.get('extra', {}),
                'raw_response': result.get('raw_response', {}),
            }

        return result

    # -------------------------------------------------------------------------
    # String representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """String representation of provider."""
        return (
            f"<AdyenProvider(merchant={self.merchant_account}, "
            f"env={self.environment})>"
        )
