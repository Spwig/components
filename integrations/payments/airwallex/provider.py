"""
Airwallex Payment Provider
Global payment processing with 160+ payment methods

API Documentation: https://www.airwallex.com/docs/api
"""
import requests
import hmac
import hashlib
import json
import logging
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from payment_providers.providers.base import PaymentProviderBase
from subscriptions.events import SubscriptionEvent, SubscriptionEventType

logger = logging.getLogger(__name__)


class AirwallexProvider(PaymentProviderBase):
    """
    Airwallex payment provider implementation.

    Supports:
    - Payment intent creation and processing
    - Full and partial refunds
    - Webhook verification (HMAC-SHA256)
    - Multi-currency transactions
    - 160+ payment methods globally
    """

    # Required class attributes
    provider_key = 'airwallex'
    provider_name = 'Airwallex'

    DEMO_API_BASE = "https://api-demo.airwallex.com/api/v1"
    PRODUCTION_API_BASE = "https://api.airwallex.com/api/v1"

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Airwallex provider with credentials and configuration.

        Args:
            credentials: Dictionary containing either:
                NEW (dual-credential):
                    - test_mode: boolean flag
                    - test_client_id, test_api_key, test_webhook_secret: Demo credentials
                    - live_client_id, live_api_key, live_webhook_secret: Production credentials
                LEGACY (single-credential):
                    - client_id: Airwallex Client ID
                    - api_key: Airwallex API Key
                    - environment: 'demo' or 'production'
                    - webhook_secret: Optional webhook secret for verification
            config: Optional configuration dictionary
        """
        # Call parent constructor (validates credentials)
        super().__init__(credentials, config)

        # Select active credentials (handles both new dual-credential and legacy structures)
        active_creds = self._select_credentials(credentials)

        # Extract credentials (now unprefixed)
        self.client_id = active_creds.get('client_id')
        self.api_key = active_creds.get('api_key')
        self.webhook_secret = active_creds.get('webhook_secret')
        self.test_mode = active_creds.get('test_mode', True)

        # Set environment string (for compatibility with existing code)
        self.environment = 'demo' if self.test_mode else 'production'

        # Config options
        self.auto_capture = self.config.get('auto_capture', True)
        self.payment_descriptor = self.config.get('payment_descriptor')
        # Payment method types (e.g., ['card', 'wechatpay', 'alipaycn', 'googlepay', 'applepay'])
        # If not specified, AirWallex will show all available methods for the merchant
        self.payment_method_types = self.config.get('payment_method_types')

        # Set API base URL based on test_mode
        self.api_base = (
            self.DEMO_API_BASE if self.test_mode
            else self.PRODUCTION_API_BASE
        )

        # Access token cache
        self._access_token = None
        self._token_expires_at = None

    # =========================================================================
    # Abstract Properties Implementation
    # =========================================================================

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities."""
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
        """
        Credential schema for programmatic validation (unprefixed keys).
        The authoritative schema with dual-credential structure is in manifest.json.
        """
        return {
            'type': 'object',
            'properties': {
                'client_id': {
                    'type': 'string',
                    'title': 'Client ID',
                    'description': 'Your Airwallex Client ID from Developer settings',
                    'required': True
                },
                'api_key': {
                    'type': 'string',
                    'title': 'API Key',
                    'description': 'Your Airwallex API Key',
                    'required': True,
                    'secret': True
                },
                'webhook_secret': {
                    'type': 'string',
                    'title': 'Webhook Secret',
                    'description': 'Secret for webhook signature verification',
                    'required': False,
                    'secret': True
                }
            }
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        """Return supported payment methods."""
        return ['card', 'bank_transfer', 'digital_wallet', 'local_methods']

    @property
    def supported_currencies(self) -> List[str]:
        """Return supported currencies."""
        return [
            'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD', 'HKD', 'CNY', 'JPY',
            'NZD', 'CHF', 'SEK', 'DKK', 'NOK', 'PLN', 'CZK', 'HUF', 'RON',
            'BGN', 'HRK', 'THB', 'MYR', 'PHP', 'IDR', 'VND', 'KRW', 'TWD',
            'INR', 'BRL', 'MXN', 'CLP', 'COP', 'PEN', 'ARS', 'ZAR', 'AED',
            'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'ILS', 'EGP', 'TRY'
        ]

    @property
    def supported_countries(self) -> List[str]:
        """Return supported merchant countries."""
        return ['US', 'GB', 'AU', 'SG', 'HK', 'CN', 'NZ', 'CA', 'EU']

    # =========================================================================
    # Abstract Methods Implementation
    # =========================================================================

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """Validate credentials."""
        if not credentials.get('client_id'):
            raise ValueError("client_id is required")
        if not credentials.get('api_key'):
            raise ValueError("api_key is required")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive credential values (handles both prefixed and unprefixed keys)."""
        redacted = credentials.copy()
        sensitive_substrings = ('api_key', 'webhook_secret')
        for key, value in redacted.items():
            if isinstance(value, str) and any(s in key for s in sensitive_substrings):
                if len(value) > 12:
                    redacted[key] = f"{value[:8]}...{value[-4:]}"
                elif value:
                    redacted[key] = '***'
        return redacted

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process an immediate payment charge."""
        return self.create_payment(
            amount=amount,
            currency=currency,
            order_id=metadata.get('order_id') if metadata else None or str(uuid.uuid4()),
            customer_email=metadata.get('customer_email') if metadata else None,
            metadata=metadata
        )

    def authorize(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Authorize a payment without capturing."""
        # Create payment intent without auto-capture
        original_auto_capture = self.auto_capture
        self.auto_capture = False
        try:
            result = self.create_payment(
                amount=amount,
                currency=currency,
                order_id=metadata.get('order_id') if metadata else None or str(uuid.uuid4()),
                customer_email=metadata.get('customer_email') if metadata else None,
                metadata=metadata
            )
            if result.get('success'):
                result['authorization_id'] = result.get('payment_intent_id')
                result['provider_authorization_id'] = result.get('payment_intent_id')
                result['status'] = 'authorized'
            return result
        finally:
            self.auto_capture = original_auto_capture

    def capture(
        self,
        authorization_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Capture an authorized payment."""
        return self.capture_payment(authorization_id, amount)

    def void(self, authorization_id: str) -> Dict[str, Any]:
        """Void an authorization."""
        return self.cancel_payment_intent(authorization_id)

    def refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refund a payment."""
        return self.refund_payment(transaction_id, amount, reason)

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """Verify webhook signature (implements abstract method)."""
        timestamp = kwargs.get('timestamp', kwargs.get('headers', {}).get('x-timestamp', ''))
        return self.verify_webhook(payload, timestamp, signature)

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle webhook event (implements abstract method)."""
        # Add event_type to payload if not present
        if 'name' not in payload:
            payload['name'] = event_type
        result = self.process_webhook(payload)
        result['success'] = result.get('handled', False)
        return result

    # =========================================================================
    # Airwallex-specific Methods
    # =========================================================================

    def _get_access_token(self) -> str:
        """
        Obtain access token from AirWallex.
        Tokens are cached and reused until expiration.

        Returns:
            Access token string

        Raises:
            Exception: If authentication fails
        """
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token

        # Request new token
        url = f"{self.api_base}/authentication/login"
        headers = {
            'x-client-id': self.client_id,
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get('token')

            # Cache token for 50 minutes (tokens typically valid for 1 hour)
            self._token_expires_at = datetime.now() + timedelta(minutes=50)

            logger.info("AirWallex access token obtained successfully")
            return self._access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain AirWallex access token: {str(e)}")
            raise Exception(f"Authentication failed: {str(e)}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to AirWallex API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL query parameters

        Returns:
            Response JSON as dictionary

        Raises:
            Exception: If request fails
        """
        token = self._get_access_token()
        url = f"{self.api_base}{endpoint}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"AirWallex API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    pass
            raise Exception(f"API request failed: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to AirWallex API.

        Returns:
            Dictionary with 'success', 'message', and optional 'details'
        """
        try:
            # Try to obtain access token
            token = self._get_access_token()

            # Verify token works by querying payment method types
            # Uses /pa/ scoped endpoint (not /account which requires admin permissions)
            response = self._make_request(
                method='GET',
                endpoint='/pa/config/payment_method_types'
            )

            method_count = len(response.get('items', []))

            return {
                'success': True,
                'message': 'Successfully connected to AirWallex',
                'details': {
                    'environment': self.environment,
                    'api_base': self.api_base,
                    'payment_methods_available': method_count
                }
            }

        except Exception as e:
            logger.error(f"AirWallex test_connection failed: {str(e)}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {
                    'environment': self.environment,
                    'error': str(e)
                }
            }

    def get_payment_method_types(self) -> Dict[str, Any]:
        """
        Fetch available payment method types from Airwallex account.

        This queries the Airwallex API to get all payment methods that are enabled
        in the merchant's Airwallex account, organized by country.

        API Endpoint: /api/v1/pa/config/payment_method_types
        Documentation: https://www.airwallex.com/docs/api#/Payment_Acceptance/Config/_api_v1_pa_config_payment_method_types/get

        Returns:
            Dictionary with:
                - success: bool - Whether the API call succeeded
                - message: str - Status message
                - methods: dict - Payment methods organized by country code
                              Format: {"US": ["card", "apple_pay"], "SG": ["card", "paynow"]}
        """
        try:
            # Fetch payment method types from Airwallex
            response = self._make_request(
                method='GET',
                endpoint='/pa/config/payment_method_types'
            )

            logger.info("Fetched payment method types from Airwallex")

            # Parse and organize payment methods by country
            methods_by_country = self._parse_payment_methods_by_country(response)

            return {
                'success': True,
                'message': 'Payment methods fetched successfully',
                'methods': methods_by_country,
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to fetch payment method types: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to fetch payment methods: {str(e)}',
                'methods': {}
            }

    def _parse_payment_methods_by_country(self, api_response: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Parse Airwallex payment method types API response and organize by country.

        The Airwallex API returns payment methods with their available countries.
        We need to invert this structure to get: country → [methods]

        Args:
            api_response: Raw response from Airwallex payment_method_types API

        Returns:
            Dictionary mapping country codes to lists of payment method slugs
            Example: {"US": ["card", "apple_pay", "google_pay"], "SG": ["card", "paynow"]}
        """
        methods_by_country = {}

        # Extract payment method types from response
        # API structure: { "items": [ { "name": "card", "countries": ["US", "GB", "SG"], ... }, ... ] }
        payment_method_types = api_response.get('items', [])

        for method in payment_method_types:
            method_name = method.get('name')  # e.g., "card", "alipay_cn", "wechatpay"
            active = method.get('active', False)
            available_countries = method.get('countries', [])

            # Only include active payment methods
            if not active or not method_name:
                continue

            # Normalize method name to slug format
            method_slug = method_name.lower()

            # Add method to each country it supports
            for country_code in available_countries:
                country_code = country_code.upper()

                if country_code not in methods_by_country:
                    methods_by_country[country_code] = []

                if method_slug not in methods_by_country[country_code]:
                    methods_by_country[country_code].append(method_slug)

        # Sort methods within each country for consistency
        for country_code in methods_by_country:
            methods_by_country[country_code].sort()

        logger.info(f"Parsed {len(payment_method_types)} payment methods across {len(methods_by_country)} countries")

        return methods_by_country

    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        order_id: str,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent with AirWallex.

        Args:
            amount: Payment amount (Decimal)
            currency: ISO currency code (e.g., 'USD')
            order_id: Merchant order ID (for reference)
            customer_email: Customer email address
            customer_name: Customer name
            description: Payment description
            metadata: Additional metadata to store
            return_url: URL to redirect after payment

        Returns:
            Dictionary containing:
                - payment_intent_id: AirWallex payment intent ID
                - client_secret: Secret for client-side completion
                - status: Payment status
                - amount: Payment amount
                - currency: Payment currency
        """
        # Build payment intent data
        intent_data = {
            'request_id': order_id,  # Idempotency key
            'amount': float(amount),
            'currency': currency.upper(),
            'merchant_order_id': order_id,
            'descriptor': self.payment_descriptor or 'Online Payment',
        }

        # Add customer information if provided
        if customer_email or customer_name:
            intent_data['customer'] = {}
            if customer_email:
                intent_data['customer']['email'] = customer_email
            if customer_name:
                intent_data['customer']['name'] = customer_name

        # Add description
        if description:
            intent_data['descriptor'] = description[:22]  # Max 22 chars

        # Add metadata
        if metadata:
            intent_data['metadata'] = metadata

        # Add return URL if provided
        if return_url:
            intent_data['return_url'] = return_url

        try:
            # Create payment intent
            response = self._make_request(
                method='POST',
                endpoint='/pa/payment_intents/create',
                data=intent_data
            )

            logger.info(f"Created AirWallex payment intent: {response.get('id')}")

            return {
                'success': True,
                'payment_intent_id': response.get('id'),
                'client_secret': response.get('client_secret'),
                'status': response.get('status'),
                'amount': Decimal(str(response.get('amount', 0))),
                'currency': response.get('currency'),
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to create payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'payment_intent_creation_failed'
            }

    def capture_payment(
        self,
        payment_intent_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Capture an authorized payment.

        Args:
            payment_intent_id: AirWallex payment intent ID
            amount: Optional amount to capture (for partial capture)

        Returns:
            Dictionary with capture result
        """
        try:
            # Build capture data
            capture_data = {
                'request_id': str(uuid.uuid4()),
                'payment_intent_id': payment_intent_id
            }

            if amount:
                capture_data['amount'] = float(amount)

            # Capture the payment
            response = self._make_request(
                method='POST',
                endpoint=f'/pa/payment_intents/{payment_intent_id}/capture',
                data=capture_data
            )

            logger.info(f"Captured payment intent: {payment_intent_id}")

            return {
                'success': True,
                'payment_intent_id': response.get('id'),
                'status': response.get('status'),
                'amount_captured': Decimal(str(response.get('amount', 0))),
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to capture payment: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'payment_capture_failed'
            }

    def refund_payment(
        self,
        payment_intent_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment (full or partial).

        Args:
            payment_intent_id: AirWallex payment intent ID
            amount: Amount to refund (None for full refund)
            reason: Reason for refund
            metadata: Additional metadata

        Returns:
            Dictionary with refund result
        """
        try:
            # Build refund data
            refund_data = {
                'request_id': str(uuid.uuid4()),
                'payment_intent_id': payment_intent_id
            }

            if amount:
                refund_data['amount'] = float(amount)

            if reason:
                refund_data['reason'] = reason

            if metadata:
                refund_data['metadata'] = metadata

            # Create refund
            response = self._make_request(
                method='POST',
                endpoint='/pa/refunds/create',
                data=refund_data
            )

            logger.info(f"Created refund for payment intent: {payment_intent_id}")

            return {
                'success': True,
                'refund_id': response.get('id'),
                'payment_intent_id': response.get('payment_intent_id'),
                'status': response.get('status'),
                'amount': Decimal(str(response.get('amount', 0))),
                'currency': response.get('currency'),
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to create refund: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'refund_creation_failed'
            }

    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Get the current status of a payment.

        Args:
            payment_intent_id: AirWallex payment intent ID

        Returns:
            Dictionary with payment details and status
        """
        try:
            response = self._make_request(
                method='GET',
                endpoint=f'/pa/payment_intents/{payment_intent_id}'
            )

            return {
                'success': True,
                'payment_intent_id': response.get('id'),
                'status': response.get('status'),
                'amount': Decimal(str(response.get('amount', 0))),
                'currency': response.get('currency'),
                'customer': response.get('customer'),
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to get payment status: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'status_retrieval_failed'
            }

    def verify_webhook(
        self,
        payload: bytes,
        timestamp: str,
        signature: str
    ) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw webhook payload (bytes)
            timestamp: x-timestamp header value
            signature: x-signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True  # Allow webhook if secret not configured

        try:
            # Construct the signed payload: timestamp + raw JSON
            signed_payload = f"{timestamp}{payload.decode('utf-8')}"

            # Compute HMAC-SHA256
            expected_signature = hmac.new(
                key=self.webhook_secret.encode('utf-8'),
                msg=signed_payload.encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()

            # Compare signatures (constant-time comparison)
            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            logger.error(f"Webhook verification failed: {str(e)}")
            return False

    def process_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event from AirWallex.

        Args:
            event_data: Parsed webhook JSON data

        Returns:
            Dictionary with processed event information
        """
        event_type = event_data.get('name')  # AirWallex uses 'name' for event type

        logger.info(f"Processing AirWallex webhook: {event_type}")

        # Extract data based on event type
        if event_type == 'payment_intent.succeeded':
            return self._process_payment_succeeded(event_data)

        elif event_type == 'payment_intent.failed':
            return self._process_payment_failed(event_data)

        elif event_type == 'payment_intent.requires_capture':
            return self._process_payment_requires_capture(event_data)

        elif event_type in ['refund.received', 'refund.accepted', 'refund.settled']:
            return self._process_refund_event(event_data)

        elif event_type == 'refund.failed':
            return self._process_refund_failed(event_data)

        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
            return {
                'event_type': event_type,
                'handled': False,
                'data': event_data
            }

    def _process_payment_succeeded(self, event_data: Dict) -> Dict[str, Any]:
        """Process payment_intent.succeeded event."""
        data = event_data.get('data', {}).get('object', {})

        return {
            'event_type': 'payment.succeeded',
            'handled': True,
            'payment_intent_id': data.get('id'),
            'amount': Decimal(str(data.get('amount', 0))),
            'currency': data.get('currency'),
            'merchant_order_id': data.get('merchant_order_id'),
            'status': 'succeeded',
            'raw_data': event_data
        }

    def _process_payment_failed(self, event_data: Dict) -> Dict[str, Any]:
        """Process payment_intent.failed event."""
        data = event_data.get('data', {}).get('object', {})

        return {
            'event_type': 'payment.failed',
            'handled': True,
            'payment_intent_id': data.get('id'),
            'merchant_order_id': data.get('merchant_order_id'),
            'status': 'failed',
            'error': data.get('latest_payment_error', {}),
            'raw_data': event_data
        }

    def _process_payment_requires_capture(self, event_data: Dict) -> Dict[str, Any]:
        """Process payment_intent.requires_capture event."""
        data = event_data.get('data', {}).get('object', {})

        return {
            'event_type': 'payment.requires_capture',
            'handled': True,
            'payment_intent_id': data.get('id'),
            'amount': Decimal(str(data.get('amount', 0))),
            'currency': data.get('currency'),
            'merchant_order_id': data.get('merchant_order_id'),
            'status': 'requires_capture',
            'raw_data': event_data
        }

    def _process_refund_event(self, event_data: Dict) -> Dict[str, Any]:
        """Process refund events (received, accepted, settled)."""
        event_type = event_data.get('name')
        data = event_data.get('data', {}).get('object', {})

        # Map AirWallex status to our status
        status_mapping = {
            'refund.received': 'refund_pending',
            'refund.accepted': 'refund_processing',
            'refund.settled': 'refund_completed'
        }

        return {
            'event_type': status_mapping.get(event_type, 'refund_update'),
            'handled': True,
            'refund_id': data.get('id'),
            'payment_intent_id': data.get('payment_intent_id'),
            'amount': Decimal(str(data.get('amount', 0))),
            'currency': data.get('currency'),
            'status': data.get('status'),
            'raw_data': event_data
        }

    def _process_refund_failed(self, event_data: Dict) -> Dict[str, Any]:
        """Process refund.failed event."""
        data = event_data.get('data', {}).get('object', {})

        return {
            'event_type': 'refund.failed',
            'handled': True,
            'refund_id': data.get('id'),
            'payment_intent_id': data.get('payment_intent_id'),
            'status': 'failed',
            'error': data.get('failure_message'),
            'raw_data': event_data
        }

    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currencies.

        Returns:
            List of ISO currency codes
        """
        return [
            'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD', 'HKD',
            'CNY', 'JPY', 'NZD', 'CHF', 'SEK', 'NOK', 'DKK'
        ]

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get provider capabilities.

        Returns:
            Dictionary of supported features
        """
        return {
            'capture': True,
            'authorize': True,
            'refund': True,
            'partial_refund': True,
            'webhooks': True,
            'recurring': True,
            '3d_secure': True,
            'multi_currency': True,
            'payment_methods': ['card', 'bank_transfer', 'digital_wallet', 'local_methods'],
            'supported_currencies': self.get_supported_currencies()
        }

    # =========================================================================
    # Payment Orchestration Methods (v1.1.0)
    # For checkout flow integration with PaymentIntent lifecycle
    # =========================================================================

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a hosted checkout session via Airwallex payment intent."""
        order_id = metadata.get('order_id') if metadata else None
        result = self.create_payment_intent_for_checkout(
            amount=amount,
            currency=currency,
            return_url=success_url,
            cancel_url=cancel_url,
            order_id=order_id,
            customer_email=metadata.get('customer_email') if metadata else None,
            metadata=metadata,
        )
        if result.get('success'):
            result['session_id'] = result.get('provider_intent_id')
            result['checkout_url'] = result.get('checkout_url')
        return result

    def create_payment_intent_for_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        order_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_country: Optional[str] = None,
        saved_token: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for checkout orchestration.

        This method supports both hosted checkout (redirect) and embedded checkout flows.
        For hosted checkout, use the returned checkout_url to redirect the customer.
        For embedded checkout, use the client_secret with the AirWallex JavaScript SDK.

        Args:
            amount: Payment amount as Decimal
            currency: ISO currency code (e.g., 'USD', 'EUR')
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect if customer cancels
            order_id: Merchant order ID (used for idempotency)
            customer_email: Customer email address
            customer_name: Customer full name
            customer_country: ISO country code (e.g., 'US', 'GB') from shipping/billing address
            saved_token: Optional saved payment method token for returning customers
            metadata: Additional metadata to attach to the payment

        Returns:
            Dictionary containing:
                - success: bool
                - provider_intent_id: AirWallex payment intent ID
                - client_secret: Secret for embedded checkout SDK
                - checkout_url: URL for hosted checkout redirect
                - status: Current intent status
                - requires_action: Whether customer action (3DS) is needed
                - action: Action details if requires_action is True
                - expires_at: When the intent expires
                - raw_response: Full API response

        AirWallex API: POST /api/v1/pa/payment_intents/create
        """
        # Build payment intent data
        intent_data = {
            'amount': float(amount),
            'currency': currency.upper(),
            'return_url': return_url,
            'cancel_url': cancel_url,
            'descriptor': self.payment_descriptor or 'Online Payment',
        }

        # Add payment method types if configured (otherwise AirWallex shows all available)
        # Supported types: card, wechatpay, alipaycn, alipayhk, gcash, dana, kakaopay,
        # tng, truemoney, googlepay, applepay, grabpay, etc.
        if self.payment_method_types:
            intent_data['payment_method_types'] = self.payment_method_types

        # Add idempotency key — Airwallex requires request_id and merchant_order_id
        request_id = order_id or str(uuid.uuid4())
        intent_data['request_id'] = request_id
        intent_data['merchant_order_id'] = request_id

        # Add customer information
        if customer_email or customer_name:
            intent_data['customer'] = {}
            if customer_email:
                intent_data['customer']['email'] = customer_email
            if customer_name:
                # AirWallex expects first/last name split
                name_parts = customer_name.split(' ', 1)
                intent_data['customer']['first_name'] = name_parts[0]
                if len(name_parts) > 1:
                    intent_data['customer']['last_name'] = name_parts[1]
                else:
                    # Fallback: use first name as last name if no space
                    intent_data['customer']['last_name'] = name_parts[0]

        # Add saved payment method if provided
        if saved_token:
            intent_data['payment_method_id'] = saved_token
            # Auto-confirm when using saved payment method
            intent_data['confirm'] = True

        # Auto-capture setting
        intent_data['capture_method'] = 'automatic' if self.auto_capture else 'manual'

        # Add metadata
        if metadata:
            intent_data['metadata'] = metadata

        # Debug: Log the full request data
        logger.info(f"AirWallex payment intent request data: {json.dumps(intent_data, indent=2)}")

        try:
            # Create payment intent
            response = self._make_request(
                method='POST',
                endpoint='/pa/payment_intents/create',
                data=intent_data
            )

            intent_id = response.get('id')
            client_secret = response.get('client_secret')
            status = response.get('status', 'INITIAL')

            logger.info(f"Created AirWallex payment intent for checkout: {intent_id}")
            logger.info(f"AirWallex payment intent response: {json.dumps(response, indent=2)}")

            # Deprecated: Hosted checkout URL (v1.1.3 and earlier)
            # Now using embedded checkout with handler-based integration
            # checkout_url = self.get_hosted_checkout_url(intent_id, client_secret)

            # Check if 3DS or other action is required
            requires_action = status in ['REQUIRES_CUSTOMER_ACTION', 'REQUIRES_PAYMENT_METHOD']
            action = None

            if requires_action and status == 'REQUIRES_CUSTOMER_ACTION':
                next_action = response.get('next_action', {})
                action = {
                    'type': next_action.get('type', 'redirect'),
                    'url': next_action.get('url') or next_action.get('redirect_url'),
                    'data': next_action
                }

            # Calculate expiry (AirWallex intents typically valid for 24 hours)
            expires_at = datetime.now() + timedelta(hours=24)

            return {
                'success': True,
                'provider_intent_id': intent_id,
                'client_secret': client_secret,
                # Use handler_config instead of checkout_url for plugin-based checkout
                'handler_config': {
                    'intent_id': intent_id,
                    'environment': self.environment,
                    'currency': currency.upper(),
                    'country_code': customer_country or 'US',
                },
                'status': self._map_intent_status(status),
                'requires_action': requires_action,
                'action': action,
                'expires_at': expires_at,
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to create payment intent for checkout: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'payment_intent_creation_failed'
            }

    def get_hosted_checkout_url(
        self,
        intent_id: str,
        client_secret: str
    ) -> str:
        """
        Construct the AirWallex hosted checkout URL.

        Args:
            intent_id: Payment intent ID
            client_secret: Client secret for the intent

        Returns:
            Full hosted checkout URL
        """
        # AirWallex hosted checkout URL format
        if self.environment == 'demo':
            base_url = "https://checkout-demo.airwallex.com"
        else:
            base_url = "https://checkout.airwallex.com"

        return f"{base_url}/pay/{intent_id}?client_secret={client_secret}"

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve the current status of a payment intent.

        Use this to poll for status after hosted checkout redirect or
        during embedded checkout to check payment completion.

        Args:
            intent_id: AirWallex payment intent ID

        Returns:
            Dictionary containing:
                - success: bool
                - provider_intent_id: Payment intent ID
                - status: Normalized status string
                - amount: Payment amount
                - currency: Currency code
                - requires_action: Whether action needed
                - action: Action details if needed
                - error: Error details if failed
                - raw_response: Full API response

        AirWallex API: GET /api/v1/pa/payment_intents/{id}
        """
        try:
            response = self._make_request(
                method='GET',
                endpoint=f'/pa/payment_intents/{intent_id}'
            )

            status = response.get('status', 'INITIAL')
            requires_action = status in ['REQUIRES_CUSTOMER_ACTION', 'REQUIRES_PAYMENT_METHOD']

            action = None
            if requires_action and status == 'REQUIRES_CUSTOMER_ACTION':
                next_action = response.get('next_action', {})
                action = {
                    'type': next_action.get('type', 'redirect'),
                    'url': next_action.get('url') or next_action.get('redirect_url'),
                    'data': next_action
                }

            # Extract error info if failed
            error = None
            if status in ['FAILED', 'CANCELLED']:
                latest_error = response.get('latest_payment_error', {})
                if latest_error:
                    error = {
                        'code': latest_error.get('code'),
                        'message': latest_error.get('message')
                    }

            return {
                'success': True,
                'provider_intent_id': response.get('id'),
                'status': self._map_intent_status(status),
                'amount': Decimal(str(response.get('amount', 0))),
                'currency': response.get('currency'),
                'requires_action': requires_action,
                'action': action,
                'error': error,
                'merchant_order_id': response.get('merchant_order_id'),
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to retrieve payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'intent_retrieval_failed'
            }

    def confirm_payment_intent(
        self,
        intent_id: str,
        payment_method_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent after customer action (3DS, etc.).

        Call this after the customer completes 3DS authentication or
        provides additional payment method details.

        Args:
            intent_id: AirWallex payment intent ID
            payment_method_data: Optional payment method details for confirmation

        Returns:
            Dictionary containing:
                - success: bool
                - status: Updated status
                - requires_action: Whether additional action needed
                - action: Action details if needed
                - error: Error details if failed
                - raw_response: Full API response

        AirWallex API: POST /api/v1/pa/payment_intents/{id}/confirm
        """
        try:
            confirm_data = {
                'request_id': str(uuid.uuid4()),
            }

            if payment_method_data:
                confirm_data['payment_method'] = payment_method_data

            response = self._make_request(
                method='POST',
                endpoint=f'/pa/payment_intents/{intent_id}/confirm',
                data=confirm_data
            )

            status = response.get('status', 'INITIAL')
            requires_action = status in ['REQUIRES_CUSTOMER_ACTION']

            action = None
            if requires_action:
                next_action = response.get('next_action', {})
                action = {
                    'type': next_action.get('type', 'redirect'),
                    'url': next_action.get('url') or next_action.get('redirect_url'),
                    'data': next_action
                }

            logger.info(f"Confirmed payment intent {intent_id}, status: {status}")

            return {
                'success': True,
                'status': self._map_intent_status(status),
                'requires_action': requires_action,
                'action': action,
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to confirm payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'intent_confirmation_failed'
            }

    def cancel_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Cancel a payment intent.

        Can only cancel intents that are not in a terminal state
        (succeeded, failed, or already cancelled).

        Args:
            intent_id: AirWallex payment intent ID

        Returns:
            Dictionary containing:
                - success: bool
                - status: Updated status ('canceled')
                - raw_response: Full API response

        AirWallex API: POST /api/v1/pa/payment_intents/{id}/cancel
        """
        try:
            response = self._make_request(
                method='POST',
                endpoint=f'/pa/payment_intents/{intent_id}/cancel',
                data={
                    'request_id': str(uuid.uuid4()),
                    'cancellation_reason': 'Cancelled by merchant',
                }
            )

            logger.info(f"Cancelled payment intent: {intent_id}")

            return {
                'success': True,
                'status': 'canceled',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"Failed to cancel payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'intent_cancellation_failed'
            }

    def _map_intent_status(self, airwallex_status: str) -> str:
        """
        Map AirWallex payment intent status to our normalized status.

        AirWallex statuses:
        - INITIAL: Intent created, not yet processed
        - REQUIRES_PAYMENT_METHOD: Needs payment method
        - REQUIRES_CUSTOMER_ACTION: 3DS or other action needed
        - REQUIRES_CAPTURE: Authorized, needs capture
        - SUCCEEDED: Payment successful
        - CANCELLED: Intent cancelled
        - FAILED: Payment failed

        Args:
            airwallex_status: Status from AirWallex API

        Returns:
            Normalized status string matching PaymentIntent model choices
        """
        status_map = {
            'INITIAL': 'created',
            'REQUIRES_PAYMENT_METHOD': 'requires_payment_method',
            'REQUIRES_CUSTOMER_ACTION': 'requires_action',
            'REQUIRES_CAPTURE': 'processing',  # Authorized but not captured
            'SUCCEEDED': 'succeeded',
            'CANCELLED': 'canceled',
            'FAILED': 'failed',
        }
        return status_map.get(airwallex_status.upper(), 'created')

    def save_payment_method(
        self,
        token: str,
        customer_email: str
    ) -> Dict[str, Any]:
        """
        Save a payment method for future use.

        This creates a customer in AirWallex (if not exists) and attaches
        the payment method token for recurring charges.

        Args:
            token: Payment method token from SDK
            customer_email: Customer email for linking

        Returns:
            Dictionary containing:
                - success: bool
                - token_id: Saved token ID
                - payment_method_type: Type (card, etc.)
                - last_four: Last 4 digits (for cards)
                - brand: Card brand
                - exp_month/exp_year: Expiry (for cards)
        """
        try:
            # First, create or get customer
            customer_data = {
                'email': customer_email,
                'request_id': f'cust_{customer_email}'  # Idempotency
            }

            try:
                customer_response = self._make_request(
                    method='POST',
                    endpoint='/pa/customers/create',
                    data=customer_data
                )
                customer_id = customer_response.get('id')
            except Exception as e:
                # Customer might already exist, try to retrieve
                logger.warning(f"Customer creation failed, may already exist: {e}")
                # For now, proceed without customer ID
                customer_id = None

            # Attach payment method
            # Note: The token from SDK is typically a payment_method_id
            pm_response = self._make_request(
                method='GET',
                endpoint=f'/pa/payment_methods/{token}'
            )

            card_info = pm_response.get('card', {})

            return {
                'success': True,
                'token_id': token,
                'payment_method_type': pm_response.get('type', 'card'),
                'last_four': card_info.get('last4', ''),
                'brand': card_info.get('brand', ''),
                'exp_month': card_info.get('expiry_month'),
                'exp_year': card_info.get('expiry_year')
            }

        except Exception as e:
            logger.error(f"Failed to save payment method: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }

    def delete_payment_method(self, token_id: str) -> bool:
        """
        Delete a saved payment method.

        Args:
            token_id: Payment method token ID to delete

        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            # AirWallex doesn't have a direct delete endpoint for payment methods
            # They are typically managed at customer level
            # For now, return True as the local record will be deleted
            logger.info(f"Payment method {token_id} marked for deletion")
            return True

        except Exception as e:
            logger.error(f"Failed to delete payment method: {str(e)}")
            return False

    # =========================================================================
    # Subscription Webhook Translation
    # =========================================================================

    # Airwallex subscription event type -> standardized event type mapping
    # Ref: https://www.airwallex.com/docs/billing/subscriptions
    # Event names use the format: subscription.{status}
    _SUBSCRIPTION_EVENT_MAP = {
        'subscription.created': SubscriptionEventType.CREATED,
        'subscription.active': SubscriptionEventType.ACTIVATED,
        'subscription.cancelled': SubscriptionEventType.CANCELED,
        'subscription.expired': SubscriptionEventType.EXPIRED,
        'subscription.unpaid': SubscriptionEventType.PAST_DUE,
        'subscription.paused': SubscriptionEventType.PAUSED,
    }

    def translate_subscription_webhook(
        self, event_type: str, payload: dict
    ) -> Optional[SubscriptionEvent]:
        """
        Translate Airwallex webhook event to standardized SubscriptionEvent.
        Returns None for non-subscription events.

        Airwallex billing webhooks (API version 2025-06-16+) use the structure:
            {id, name, account_id, data: {<subscription object>}, created_at}

        Legacy format (API <=2025-04-25) nests under data.object.
        We support both.
        """
        # Route invoice events to dedicated handler
        if event_type.startswith('invoice.'):
            return self._translate_airwallex_invoice_event(event_type, payload)

        # Only handle subscription.* events below
        if not event_type.startswith('subscription.'):
            return None

        event_id = payload.get('id', '')

        # Modern billing API: data IS the subscription object
        # Legacy format: data.object is the subscription object
        data = payload.get('data', {})
        if 'object' in data and isinstance(data['object'], dict):
            data = data['object']

        sub_id = data.get('id', '')
        customer_id = data.get('customer_id', '')

        # Direct mapping events
        if event_type in self._SUBSCRIPTION_EVENT_MAP:
            std_type = self._SUBSCRIPTION_EVENT_MAP[event_type]
        elif event_type == 'subscription.updated':
            # Inspect status for more specific event type
            status = data.get('status', '')
            if status == 'ACTIVE':
                std_type = SubscriptionEventType.ACTIVATED
            elif status == 'PAST_DUE' or status == 'UNPAID':
                std_type = SubscriptionEventType.PAST_DUE
            else:
                std_type = SubscriptionEventType.UPDATED
        else:
            return None  # Unknown subscription event

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': customer_id,
            'provider_event_type': event_type,
        }

        # Extract billing period timestamps
        period_start = data.get('current_period_start')
        period_end = data.get('current_period_end')
        if period_start:
            try:
                kwargs['period_start'] = datetime.fromisoformat(
                    period_start.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass
        if period_end:
            try:
                kwargs['period_end'] = datetime.fromisoformat(
                    period_end.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        # Extract currency from the subscription's pricing
        currency = data.get('currency', '')
        if currency:
            kwargs['currency'] = currency.upper()

        return SubscriptionEvent(**kwargs)

    def _translate_airwallex_invoice_event(
        self, event_type: str, payload: dict
    ) -> Optional[SubscriptionEvent]:
        """
        Translate Airwallex invoice events related to subscriptions.
        Called from translate_subscription_webhook for invoice.* events.
        """
        event_id = payload.get('id', '')
        data = payload.get('data', {})
        if 'object' in data and isinstance(data['object'], dict):
            data = data['object']

        sub_id = data.get('subscription_id', '')
        if not sub_id:
            return None  # Not a subscription invoice

        customer_id = data.get('customer_id', '')

        event_map = {
            'invoice.paid': SubscriptionEventType.PAYMENT_SUCCEEDED,
            'invoice.payment_failed': SubscriptionEventType.PAYMENT_FAILED,
            'invoice.upcoming': SubscriptionEventType.RENEWAL_UPCOMING,
        }

        std_type = event_map.get(event_type)
        if not std_type:
            return None

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': customer_id,
            'provider_event_type': event_type,
        }

        # Extract amount from invoice
        total = data.get('total') or data.get('amount_due') or 0
        if total:
            kwargs['amount'] = Decimal(str(total))
        currency = data.get('currency', '')
        if currency:
            kwargs['currency'] = currency.upper()

        return SubscriptionEvent(**kwargs)

    def get_frontend_metadata(self) -> Dict[str, Any]:
        """
        Return frontend integration metadata from manifest.

        This provides information about the JavaScript checkout handler
        and required SDK dependencies for dynamic loading in the frontend.

        Returns:
            Dictionary containing:
                - checkout_handler: Filename of the checkout handler JavaScript
                - sdk_dependencies: List of external SDK URLs to load
        """
        return {
            'checkout_handler': 'checkout-handler.js',
            'sdk_dependencies': [
                'https://static.airwallex.com/components/sdk/v1/index.js'
            ]
        }
