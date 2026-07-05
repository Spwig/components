"""
PayPal Payment Provider
Global payment processing via PayPal Orders API v2

API Documentation: https://developer.paypal.com/docs/api/orders/v2/
"""
import requests
import hmac
import hashlib
import json
import logging
import base64
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from payment_providers.providers.base import PaymentProviderBase
from subscriptions.events import SubscriptionEvent, SubscriptionEventType

logger = logging.getLogger(__name__)


class PayPalProvider(PaymentProviderBase):
    """
    PayPal payment provider implementation using Orders API v2.

    Supports:
    - PayPal wallet payments (redirect flow)
    - Credit and debit card processing
    - Venmo and PayPal Credit
    - Buy Now Pay Later (Pay in 4, Pay Monthly)
    - Full and partial refunds
    - Authorize and capture flows
    - Webhook verification via PayPal server-side verification
    - Multi-currency transactions across 25+ currencies
    """

    provider_key = "paypal"
    provider_name = "PayPal"

    SANDBOX_API_BASE = "https://api-m.sandbox.paypal.com"
    LIVE_API_BASE = "https://api-m.paypal.com"

    # Currencies that use zero decimal places
    ZERO_DECIMAL_CURRENCIES = {'JPY', 'HUF', 'TWD', 'KRW'}

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize PayPal provider with credentials.

        Args:
            credentials: Dictionary containing:
                - client_id: PayPal REST API Client ID
                - client_secret: PayPal REST API Secret
                - webhook_id: Optional webhook ID for signature verification
                - environment: 'sandbox' or 'live'
            config: Optional configuration dictionary
        """
        # Extract credentials before calling super().__init__ which calls validate_credentials
        self.client_id = credentials.get('client_id', '')
        self.client_secret = credentials.get('client_secret', '')
        self.webhook_id = credentials.get('webhook_id', '')
        self.environment = credentials.get('environment', 'sandbox')

        # Set API base URL based on environment
        self.api_base = (
            self.SANDBOX_API_BASE if self.environment == 'sandbox'
            else self.LIVE_API_BASE
        )

        # Access token cache
        self._access_token = None
        self._token_expires_at = None

        # Call parent init (this calls validate_credentials)
        super().__init__(credentials, config)

    # ─── Abstract Property Implementations ────────────────────────────────────

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
            'save_payment_method': False,
            'hosted_checkout': True,
            'integrated_checkout': True,
            'webhooks': True,
            'multi_currency': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """Return JSON schema describing required credentials."""
        return {
            'type': 'object',
            'properties': {
                'client_id': {
                    'type': 'string',
                    'title': 'Client ID',
                    'description': 'Your PayPal REST API Client ID from the Developer Dashboard',
                    'required': True,
                    'secret': False
                },
                'client_secret': {
                    'type': 'string',
                    'title': 'Client Secret',
                    'description': 'Your PayPal REST API Secret from the Developer Dashboard',
                    'required': True,
                    'secret': True
                },
                'webhook_id': {
                    'type': 'string',
                    'title': 'Webhook ID',
                    'description': 'Optional: Webhook ID for signature verification',
                    'required': False,
                    'secret': False
                },
                'environment': {
                    'type': 'string',
                    'title': 'Environment',
                    'enum': ['sandbox', 'live'],
                    'default': 'sandbox',
                    'required': True
                }
            }
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        """Return list of supported payment method types."""
        return ['credit_card', 'debit_card', 'digital_wallet', 'buy_now_pay_later']

    @property
    def supported_currencies(self) -> List[str]:
        """Return list of supported currency codes."""
        return [
            'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'JPY', 'CHF', 'SEK',
            'DKK', 'NOK', 'PLN', 'CZK', 'HUF', 'BRL', 'MXN', 'SGD',
            'HKD', 'NZD', 'INR', 'THB', 'MYR', 'PHP', 'ILS', 'TRY',
            'ZAR', 'TWD', 'KRW'
        ]

    @property
    def supported_countries(self) -> List[str]:
        """Return list of supported country codes."""
        return [
            'US', 'GB', 'AU', 'CA', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE',
            'AT', 'CH', 'JP', 'SG', 'HK', 'BR', 'MX', 'IN'
        ]

    # ─── Credential Management ────────────────────────────────────────────────

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credentials against schema and business logic.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing required fields
        """
        client_id = credentials.get('client_id', '').strip()
        client_secret = credentials.get('client_secret', '').strip()

        if not client_id:
            raise ValueError("PayPal Client ID is required")
        if not client_secret:
            raise ValueError("PayPal Client Secret is required")

        environment = credentials.get('environment', 'sandbox')
        if environment not in ('sandbox', 'live'):
            raise ValueError(f"Invalid environment: {environment}. Must be 'sandbox' or 'live'")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = dict(credentials)
        sensitive_substrings = ('secret', 'webhook_id')
        for key, value in redacted.items():
            if isinstance(value, str) and any(s in key for s in sensitive_substrings):
                if len(value) > 12:
                    redacted[key] = f"{value[:4]}***{value[-4:]}"
                elif value:
                    redacted[key] = '***'

        # Also partially redact client_id (public but still sensitive in logs)
        if 'client_id' in redacted and isinstance(redacted['client_id'], str):
            cid = redacted['client_id']
            if len(cid) > 8:
                redacted['client_id'] = f"{cid[:4]}***{cid[-4:]}"
            elif cid:
                redacted['client_id'] = f"{cid[:2]}***"

        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity.

        Returns:
            Dictionary with test results
        """
        try:
            # Attempt to get access token (validates credentials)
            token = self._get_access_token()

            # Make a simple API call to verify the token works
            response = requests.get(
                f"{self.api_base}/v1/notifications/webhooks",
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            response.raise_for_status()
            webhooks_data = response.json()

            return {
                'success': True,
                'message': 'Successfully connected to PayPal',
                'details': {
                    'environment': self.environment,
                    'api_base': self.api_base,
                    'webhooks_configured': len(webhooks_data.get('webhooks', [])),
                    'api_version': 'v2'
                }
            }

        except Exception as e:
            logger.error(f"PayPal connection test failed: {str(e)}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': {
                    'environment': self.environment,
                    'error': str(e)
                }
            }

    # ─── Internal Helpers ─────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """
        Obtain OAuth2 access token from PayPal.

        Uses client credentials grant type with Basic auth.
        Tokens are cached for 8 hours (PayPal tokens typically valid for 9 hours).

        Returns:
            Access token string

        Raises:
            Exception: If authentication fails
        """
        # Return cached token if still valid
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at:
                return self._access_token

        url = f"{self.api_base}/v1/oauth2/token"

        # PayPal uses Basic auth with client_id:client_secret
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode('utf-8')
        ).decode('utf-8')

        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data='grant_type=client_credentials',
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get('access_token')

            # Cache token for 8 hours (PayPal tokens are valid ~9 hours)
            expires_in = data.get('expires_in', 32400)  # Default 9 hours
            # Use 80% of the reported lifetime for safety margin
            cache_seconds = int(expires_in * 0.8)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=cache_seconds)

            logger.info("PayPal access token obtained successfully")
            return self._access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain PayPal access token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error_description', str(e))
                    logger.error(f"PayPal auth error: {error_msg}")
                    raise Exception(f"PayPal authentication failed: {error_msg}")
                except (ValueError, KeyError):
                    pass
            raise Exception(f"PayPal authentication failed: {str(e)}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        extra_headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to PayPal API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/v2/checkout/orders')
            data: Request body data
            params: URL query parameters
            extra_headers: Additional headers to include

        Returns:
            Response JSON as dictionary (or empty dict for 204 responses)

        Raises:
            Exception: If request fails
        """
        token = self._get_access_token()
        url = f"{self.api_base}{endpoint}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if extra_headers:
            headers.update(extra_headers)

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

            # Some PayPal endpoints return 204 No Content (e.g., void)
            if response.status_code == 204:
                return {}

            try:
                return response.json()
            except (ValueError, json.JSONDecodeError):
                logger.error(f"PayPal API returned non-JSON response: {method} {endpoint} (status {response.status_code})")
                return {'error': f'Non-JSON response: {response.status_code}'}

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal API request failed: {method} {endpoint} - {str(e)}")
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"PayPal error details: {json.dumps(error_data, indent=2)}")
                    # Extract meaningful error message
                    if 'details' in error_data and error_data['details']:
                        detail_msgs = [d.get('description', d.get('issue', '')) for d in error_data['details']]
                        error_detail = '; '.join(filter(None, detail_msgs)) or error_data.get('message', str(e))
                    elif 'message' in error_data:
                        error_detail = error_data['message']
                except (ValueError, KeyError):
                    pass
            raise Exception(f"PayPal API request failed: {error_detail}")

    def _format_amount(self, amount: Decimal, currency: str) -> str:
        """
        Format amount as string for PayPal API.

        PayPal requires amounts as strings with appropriate decimal places.
        Most currencies use 2 decimal places, some (JPY, HUF, etc.) use 0.

        Args:
            amount: Decimal amount
            currency: ISO currency code

        Returns:
            Formatted amount string (e.g., "99.99" or "1000")
        """
        currency_upper = currency.upper()
        if currency_upper in self.ZERO_DECIMAL_CURRENCIES:
            return str(int(amount))
        else:
            # Round to 2 decimal places
            rounded = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return str(rounded)

    def _extract_approve_link(self, links: List[Dict]) -> Optional[str]:
        """
        Extract the approval URL from PayPal HATEOAS links.

        Args:
            links: List of link objects from PayPal response

        Returns:
            Approval URL string or None
        """
        for link in links:
            if link.get('rel') == 'approve':
                return link.get('href')
            elif link.get('rel') == 'payer-action':
                return link.get('href')
        return None

    def _map_order_status(self, paypal_status: str) -> str:
        """
        Map PayPal order status to standardized status.

        Args:
            paypal_status: PayPal order status string

        Returns:
            Standardized status string
        """
        status_map = {
            'CREATED': 'created',
            'SAVED': 'created',
            'APPROVED': 'requires_action',
            'VOIDED': 'canceled',
            'COMPLETED': 'succeeded',
            'PAYER_ACTION_REQUIRED': 'requires_action',
        }
        return status_map.get(paypal_status, 'unknown')

    # ─── Payment Processing Methods ───────────────────────────────────────────

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an immediate payment charge.

        Creates a PayPal order with intent=CAPTURE and captures it.
        For PayPal wallet payments, this creates the order and returns
        the approval URL for redirect-based checkout.

        Args:
            amount: Payment amount
            currency: Currency code
            payment_method: Payment method details
            metadata: Optional metadata

        Returns:
            Dictionary with transaction result
        """
        metadata = metadata or {}
        order_id = metadata.get('order_id', '')
        customer_email = metadata.get('customer_email', '')
        description = metadata.get('description', f'Order {order_id}') if order_id else 'Payment'

        try:
            # Create order with CAPTURE intent
            order_data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'reference_id': str(order_id) if order_id else 'default',
                    'amount': {
                        'currency_code': currency.upper(),
                        'value': self._format_amount(amount, currency)
                    },
                    'description': description[:127]  # PayPal max 127 chars
                }]
            }

            # Add PayPal-Request-Id for idempotency
            extra_headers = {}
            if order_id:
                extra_headers['PayPal-Request-Id'] = f'charge-{order_id}'

            response = self._make_request(
                method='POST',
                endpoint='/v2/checkout/orders',
                data=order_data,
                extra_headers=extra_headers
            )

            paypal_order_id = response.get('id')
            status = response.get('status')
            approve_link = self._extract_approve_link(response.get('links', []))

            logger.info(f"Created PayPal order {paypal_order_id} with status {status}")

            # If order is immediately completable (e.g., card token), attempt capture
            if status == 'COMPLETED':
                capture_data = self._extract_capture_data(response)
                return {
                    'success': True,
                    'transaction_id': capture_data.get('id', paypal_order_id),
                    'provider_transaction_id': paypal_order_id,
                    'status': 'completed',
                    'amount': amount,
                    'currency': currency.upper(),
                    'created_at': datetime.now(),
                    'message': 'Payment completed successfully',
                    'raw_response': response
                }

            # For redirect flows, return the approval URL
            return {
                'success': True,
                'transaction_id': paypal_order_id,
                'provider_transaction_id': paypal_order_id,
                'status': 'pending',
                'amount': amount,
                'currency': currency.upper(),
                'checkout_url': approve_link,
                'requires_redirect': True,
                'created_at': datetime.now(),
                'message': 'Order created - redirect customer to approve payment',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal charge failed: {str(e)}")
            return {
                'success': False,
                'transaction_id': None,
                'provider_transaction_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': f'Payment failed: {str(e)}',
                'raw_response': {}
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

        Creates a PayPal order with intent=AUTHORIZE.

        Args:
            amount: Authorization amount
            currency: Currency code
            payment_method: Payment method details
            metadata: Optional metadata

        Returns:
            Dictionary with authorization result
        """
        metadata = metadata or {}
        order_id = metadata.get('order_id', '')
        description = metadata.get('description', f'Order {order_id}') if order_id else 'Authorization'

        try:
            order_data = {
                'intent': 'AUTHORIZE',
                'purchase_units': [{
                    'reference_id': str(order_id) if order_id else 'default',
                    'amount': {
                        'currency_code': currency.upper(),
                        'value': self._format_amount(amount, currency)
                    },
                    'description': description[:127]
                }]
            }

            extra_headers = {}
            if order_id:
                extra_headers['PayPal-Request-Id'] = f'auth-{order_id}'

            response = self._make_request(
                method='POST',
                endpoint='/v2/checkout/orders',
                data=order_data,
                extra_headers=extra_headers
            )

            paypal_order_id = response.get('id')
            status = response.get('status')
            approve_link = self._extract_approve_link(response.get('links', []))

            logger.info(f"Created PayPal authorization order {paypal_order_id}")

            # PayPal authorizations are valid for up to 29 days, honor period 3 days
            expires_at = datetime.now() + timedelta(days=29)

            return {
                'success': True,
                'authorization_id': paypal_order_id,
                'provider_authorization_id': paypal_order_id,
                'status': 'authorized' if status == 'COMPLETED' else 'pending',
                'amount': amount,
                'currency': currency.upper(),
                'checkout_url': approve_link,
                'requires_redirect': status != 'COMPLETED',
                'expires_at': expires_at,
                'created_at': datetime.now(),
                'message': 'Authorization created successfully',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal authorization failed: {str(e)}")
            return {
                'success': False,
                'authorization_id': None,
                'provider_authorization_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'created_at': datetime.now(),
                'message': f'Authorization failed: {str(e)}',
                'raw_response': {}
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
            authorization_id: PayPal authorization ID
            amount: Amount to capture (if None, captures full authorized amount)
            metadata: Optional metadata

        Returns:
            Dictionary with capture result
        """
        try:
            capture_data = {}

            if amount is not None:
                # For partial capture, we need the currency from the authorization
                # Retrieve authorization to get the currency
                auth_response = self._make_request(
                    method='GET',
                    endpoint=f'/v2/payments/authorizations/{authorization_id}'
                )
                currency = (auth_response.get('amount') or {}).get('currency_code', 'USD')

                capture_data['amount'] = {
                    'currency_code': currency,
                    'value': self._format_amount(amount, currency)
                }

            response = self._make_request(
                method='POST',
                endpoint=f'/v2/payments/authorizations/{authorization_id}/capture',
                data=capture_data if capture_data else None,
                extra_headers={'PayPal-Request-Id': f'capture-{authorization_id}'}
            )

            capture_id = response.get('id')
            captured_amount = Decimal((response.get('amount') or {}).get('value', '0'))
            captured_currency = (response.get('amount') or {}).get('currency_code', '')

            logger.info(f"Captured PayPal authorization {authorization_id}: {capture_id}")

            return {
                'success': True,
                'transaction_id': capture_id,
                'provider_transaction_id': capture_id,
                'status': 'completed',
                'amount': captured_amount,
                'currency': captured_currency,
                'created_at': datetime.now(),
                'message': 'Capture successful',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal capture failed for {authorization_id}: {str(e)}")
            return {
                'success': False,
                'transaction_id': None,
                'provider_transaction_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': '',
                'created_at': datetime.now(),
                'message': f'Capture failed: {str(e)}',
                'raw_response': {}
            }

    def void(
        self,
        authorization_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Void an uncaptured authorization.

        Args:
            authorization_id: PayPal authorization ID
            metadata: Optional metadata

        Returns:
            Dictionary with void result
        """
        try:
            # PayPal void returns 204 No Content on success
            self._make_request(
                method='POST',
                endpoint=f'/v2/payments/authorizations/{authorization_id}/void',
                extra_headers={'PayPal-Request-Id': f'void-{authorization_id}'}
            )

            logger.info(f"Voided PayPal authorization {authorization_id}")

            return {
                'success': True,
                'authorization_id': authorization_id,
                'status': 'voided',
                'message': 'Authorization voided successfully',
                'raw_response': {}
            }

        except Exception as e:
            logger.error(f"PayPal void failed for {authorization_id}: {str(e)}")
            return {
                'success': False,
                'authorization_id': authorization_id,
                'status': 'failed',
                'message': f'Void failed: {str(e)}',
                'raw_response': {}
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
            transaction_id: PayPal capture ID to refund
            amount: Amount to refund (if None, refunds full amount)
            reason: Optional refund reason
            metadata: Optional metadata

        Returns:
            Dictionary with refund result
        """
        try:
            refund_data = {}

            if amount is not None:
                # For partial refund, get capture details for currency
                capture_response = self._make_request(
                    method='GET',
                    endpoint=f'/v2/payments/captures/{transaction_id}'
                )
                currency = (capture_response.get('amount') or {}).get('currency_code', 'USD')

                refund_data['amount'] = {
                    'currency_code': currency,
                    'value': self._format_amount(amount, currency)
                }

            if reason:
                refund_data['note_to_payer'] = reason[:255]  # PayPal max 255 chars

            response = self._make_request(
                method='POST',
                endpoint=f'/v2/payments/captures/{transaction_id}/refund',
                data=refund_data if refund_data else None,
                extra_headers={'PayPal-Request-Id': f'refund-{transaction_id}-{uuid.uuid4().hex[:8]}'}
            )

            refund_id = response.get('id')
            refund_status = response.get('status', 'COMPLETED')
            refund_amount = Decimal((response.get('amount') or {}).get('value', '0'))
            refund_currency = (response.get('amount') or {}).get('currency_code', '')

            # Map PayPal refund status
            status_map = {
                'COMPLETED': 'completed',
                'PENDING': 'pending',
                'CANCELLED': 'failed'
            }

            logger.info(f"Created PayPal refund {refund_id} for capture {transaction_id}")

            return {
                'success': True,
                'refund_id': refund_id,
                'provider_refund_id': refund_id,
                'status': status_map.get(refund_status, 'pending'),
                'amount': refund_amount,
                'currency': refund_currency,
                'created_at': datetime.now(),
                'message': 'Refund processed successfully',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal refund failed for {transaction_id}: {str(e)}")
            return {
                'success': False,
                'refund_id': None,
                'provider_refund_id': None,
                'status': 'failed',
                'amount': amount,
                'currency': '',
                'created_at': datetime.now(),
                'message': f'Refund failed: {str(e)}',
                'raw_response': {}
            }

    # ─── Webhook Methods ──────────────────────────────────────────────────────

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify webhook authenticity using PayPal's server-side verification.

        PayPal webhooks are verified by posting the webhook data back to PayPal's
        verification endpoint rather than computing a local signature.

        Args:
            payload: Raw request body as bytes
            signature: paypal-transmission-sig header value
            **kwargs: Additional headers needed for verification:
                - transmission_id: paypal-transmission-id header
                - transmission_time: paypal-transmission-time header
                - cert_url: paypal-cert-url header
                - auth_algo: paypal-auth-algo header (optional)

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_id:
            logger.error("PayPal webhook_id not configured - cannot verify webhook signature")
            return False

        transmission_id = kwargs.get('transmission_id', '')
        transmission_time = kwargs.get('transmission_time', '')
        cert_url = kwargs.get('cert_url', '')
        auth_algo = kwargs.get('auth_algo', 'SHA256withRSA')

        if not all([transmission_id, transmission_time, cert_url, signature]):
            logger.error("Missing required PayPal webhook verification headers")
            return False

        try:
            # Parse the webhook body
            webhook_event = json.loads(payload.decode('utf-8'))

            # Use PayPal's verification endpoint
            verification_data = {
                'auth_algo': auth_algo,
                'cert_url': cert_url,
                'transmission_id': transmission_id,
                'transmission_sig': signature,
                'transmission_time': transmission_time,
                'webhook_id': self.webhook_id,
                'webhook_event': webhook_event
            }

            response = self._make_request(
                method='POST',
                endpoint='/v1/notifications/verify-webhook-signature',
                data=verification_data
            )

            verification_status = response.get('verification_status', '')
            is_valid = verification_status == 'SUCCESS'

            if not is_valid:
                logger.warning(
                    f"PayPal webhook verification failed: status={verification_status}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"PayPal webhook verification error: {str(e)}")
            return False

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event from PayPal.

        Args:
            event_type: Type of webhook event (e.g., 'PAYMENT.CAPTURE.COMPLETED')
            payload: Webhook payload dictionary

        Returns:
            Dictionary with processed webhook data
        """
        logger.info(f"Processing PayPal webhook: {event_type}")

        resource = payload.get('resource', {})

        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            return self._handle_capture_completed(resource, payload)

        elif event_type == 'PAYMENT.CAPTURE.DENIED':
            return self._handle_capture_denied(resource, payload)

        elif event_type == 'PAYMENT.CAPTURE.REFUNDED':
            return self._handle_capture_refunded(resource, payload)

        elif event_type == 'CHECKOUT.ORDER.APPROVED':
            return self._handle_order_approved(resource, payload)

        elif event_type == 'CHECKOUT.ORDER.COMPLETED':
            return self._handle_order_completed(resource, payload)

        elif event_type == 'PAYMENT.AUTHORIZATION.VOIDED':
            return {
                'action': 'authorization_voided',
                'event_type': 'payment.voided',
                'transaction_id': resource.get('id'),
                'status': 'voided',
                'handled': True,
                'raw_event': payload,
            }

        elif event_type == 'PAYMENT.CAPTURE.REVERSED':
            amount = resource.get('amount') or {}
            return {
                'action': 'payment_reversed',
                'event_type': 'payment.reversed',
                'transaction_id': resource.get('id'),
                'status': 'reversed',
                'amount': Decimal(amount.get('value', '0')),
                'currency': amount.get('currency_code', ''),
                'handled': True,
                'raw_event': payload,
            }

        else:
            logger.warning(f"Unhandled PayPal webhook event type: {event_type}")
            return {
                'action': 'unknown',
                'event_type': event_type,
                'handled': False,
                'raw_event': payload
            }

    def _handle_capture_completed(self, resource: Dict, payload: Dict) -> Dict[str, Any]:
        """Handle PAYMENT.CAPTURE.COMPLETED webhook event."""
        amount = resource.get('amount') or {}
        capture_amount = Decimal(amount.get('value', '0'))
        capture_currency = amount.get('currency_code', '')

        return {
            'action': 'payment_completed',
            'transaction_id': resource.get('id'),
            'status': 'completed',
            'amount': capture_amount,
            'currency': capture_currency,
            'metadata': {
                'custom_id': resource.get('custom_id', ''),
                'invoice_id': resource.get('invoice_id', ''),
            },
            'raw_event': payload
        }

    def _handle_capture_denied(self, resource: Dict, payload: Dict) -> Dict[str, Any]:
        """Handle PAYMENT.CAPTURE.DENIED webhook event."""
        amount = resource.get('amount') or {}
        return {
            'action': 'payment_failed',
            'transaction_id': resource.get('id'),
            'status': 'failed',
            'amount': Decimal(amount.get('value', '0')),
            'currency': amount.get('currency_code', ''),
            'metadata': {
                'reason': (resource.get('status_details') or {}).get('reason', 'DENIED'),
            },
            'raw_event': payload
        }

    def _handle_capture_refunded(self, resource: Dict, payload: Dict) -> Dict[str, Any]:
        """Handle PAYMENT.CAPTURE.REFUNDED webhook event."""
        amount = resource.get('amount') or {}
        return {
            'action': 'refund_completed',
            'transaction_id': resource.get('id'),
            'status': 'refunded',
            'amount': Decimal(amount.get('value', '0')),
            'currency': amount.get('currency_code', ''),
            'metadata': {},
            'raw_event': payload
        }

    def _handle_order_approved(self, resource: Dict, payload: Dict) -> Dict[str, Any]:
        """Handle CHECKOUT.ORDER.APPROVED webhook event."""
        purchase_unit = resource.get('purchase_units', [{}])[0] if resource.get('purchase_units') else {}
        amount_data = purchase_unit.get('amount') or {}

        return {
            'action': 'payment_approved',
            'transaction_id': resource.get('id'),
            'status': 'approved',
            'amount': Decimal(amount_data.get('value', '0')),
            'currency': amount_data.get('currency_code', ''),
            'metadata': {
                'reference_id': purchase_unit.get('reference_id', ''),
                'payer_email': (resource.get('payer') or {}).get('email_address', ''),
            },
            'raw_event': payload
        }

    def _handle_order_completed(self, resource: Dict, payload: Dict) -> Dict[str, Any]:
        """Handle CHECKOUT.ORDER.COMPLETED webhook event."""
        purchase_unit = resource.get('purchase_units', [{}])[0] if resource.get('purchase_units') else {}
        amount_data = purchase_unit.get('amount') or {}

        # Extract capture ID from completed order
        captures = (purchase_unit.get('payments') or {}).get('captures', [])
        capture_id = captures[0].get('id') if captures else resource.get('id')

        return {
            'action': 'payment_completed',
            'transaction_id': capture_id,
            'status': 'completed',
            'amount': Decimal(amount_data.get('value', '0')),
            'currency': amount_data.get('currency_code', ''),
            'metadata': {
                'order_id': resource.get('id'),
                'reference_id': purchase_unit.get('reference_id', ''),
                'payer_email': (resource.get('payer') or {}).get('email_address', ''),
            },
            'raw_event': payload
        }

    # ─── Checkout Orchestration Methods ───────────────────────────────────────

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a hosted checkout session via PayPal redirect.

        Args:
            amount: Payment amount
            currency: Currency code
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancellation
            metadata: Optional metadata

        Returns:
            Dictionary with checkout session details
        """
        metadata = metadata or {}
        order_id = metadata.get('order_id', '')
        description = metadata.get('description', f'Order {order_id}') if order_id else 'Payment'

        try:
            order_data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'reference_id': str(order_id) if order_id else 'default',
                    'amount': {
                        'currency_code': currency.upper(),
                        'value': self._format_amount(amount, currency)
                    },
                    'description': description[:127]
                }],
                'payment_source': {
                    'paypal': {
                        'experience_context': {
                            'payment_method_preference': 'IMMEDIATE_PAYMENT_REQUIRED',
                            'landing_page': 'LOGIN',
                            'user_action': 'PAY_NOW',
                            'return_url': success_url,
                            'cancel_url': cancel_url
                        }
                    }
                }
            }

            extra_headers = {}
            if order_id:
                extra_headers['PayPal-Request-Id'] = f'checkout-{order_id}'

            response = self._make_request(
                method='POST',
                endpoint='/v2/checkout/orders',
                data=order_data,
                extra_headers=extra_headers
            )

            paypal_order_id = response.get('id')
            approve_link = self._extract_approve_link(response.get('links', []))

            logger.info(f"Created PayPal checkout session: {paypal_order_id}")

            return {
                'success': True,
                'session_id': paypal_order_id,
                'checkout_url': approve_link,
                'expires_at': datetime.now() + timedelta(hours=3),  # PayPal orders expire in ~3 hours
                'message': 'Checkout session created',
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal checkout session creation failed: {str(e)}")
            return {
                'success': False,
                'session_id': None,
                'checkout_url': None,
                'message': f'Checkout session creation failed: {str(e)}',
                'raw_response': {}
            }

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
        """
        Create a payment intent for checkout orchestration.

        Creates a PayPal order with CAPTURE intent and payment_source configured
        for the redirect flow, returning the order ID and approval link.

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
        metadata = metadata or {}
        order_id = metadata.get('order_id', '')
        description = metadata.get('description', f'Order {order_id}') if order_id else 'Payment'

        try:
            purchase_unit = {
                'reference_id': str(order_id) if order_id else 'default',
                'amount': {
                    'currency_code': currency.upper(),
                    'value': self._format_amount(amount, currency)
                },
                'description': description[:127]
            }

            # Add custom_id for merchant reference if available
            if order_id:
                purchase_unit['custom_id'] = str(order_id)

            order_data = {
                'intent': 'CAPTURE',
                'purchase_units': [purchase_unit],
                'payment_source': {
                    'paypal': {
                        'experience_context': {
                            'payment_method_preference': 'IMMEDIATE_PAYMENT_REQUIRED',
                            'landing_page': 'LOGIN',
                            'user_action': 'PAY_NOW',
                            'return_url': return_url,
                            'cancel_url': cancel_url
                        }
                    }
                }
            }

            # Add payer email if provided
            if customer_email:
                order_data['payment_source']['paypal']['email_address'] = customer_email

            extra_headers = {}
            if order_id:
                extra_headers['PayPal-Request-Id'] = f'intent-{order_id}'

            response = self._make_request(
                method='POST',
                endpoint='/v2/checkout/orders',
                data=order_data,
                extra_headers=extra_headers
            )

            paypal_order_id = response.get('id')
            status = response.get('status', 'CREATED')
            approve_link = self._extract_approve_link(response.get('links', []))

            logger.info(f"Created PayPal payment intent: {paypal_order_id}")

            # Build handler_config for plugin architecture (v1.1.0)
            handler_config = {
                'order_id': paypal_order_id,
                'client_id': self.client_id,
                'environment': self.environment,
                'amount': self._format_amount(amount, currency),
                'currency': currency.upper(),
            }

            return {
                'success': True,
                'provider_intent_id': paypal_order_id,
                'client_secret': None,  # PayPal uses redirect, not client secret
                'checkout_url': approve_link,
                'status': self._map_order_status(status),
                'requires_action': status in ('CREATED', 'PAYER_ACTION_REQUIRED'),
                'action': {
                    'type': 'redirect',
                    'url': approve_link,
                    'data': {}
                } if approve_link else None,
                'expires_at': datetime.now() + timedelta(hours=3),
                'handler_config': handler_config,  # NEW: For plugin architecture
                'raw_response': response
            }

        except Exception as e:
            logger.error(f"PayPal payment intent creation failed: {str(e)}")
            return {
                'success': False,
                'provider_intent_id': None,
                'client_secret': None,
                'checkout_url': None,
                'status': 'failed',
                'requires_action': False,
                'action': None,
                'error': {
                    'code': 'intent_creation_failed',
                    'message': str(e)
                },
                'raw_response': {}
            }

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve current status of a payment intent (PayPal order).

        Args:
            intent_id: PayPal order ID

        Returns:
            Dictionary with intent status
        """
        try:
            response = self._make_request(
                method='GET',
                endpoint=f'/v2/checkout/orders/{intent_id}'
            )

            paypal_status = response.get('status', '')
            mapped_status = self._map_order_status(paypal_status)

            # Extract payer info if available
            payer = response.get('payer', {})
            purchase_unit = response.get('purchase_units', [{}])[0] if response.get('purchase_units') else {}

            # Check for captures to determine payment method details
            captures = (purchase_unit.get('payments') or {}).get('captures', [])
            payment_method_type = 'paypal'  # Default for PayPal
            payment_method_last4 = None

            result = {
                'success': True,
                'status': mapped_status,
                'provider_status': paypal_status,
                'requires_action': mapped_status == 'requires_action',
                'payment_method_type': payment_method_type,
                'payment_method_last4': payment_method_last4,
                'raw_response': response
            }

            if mapped_status == 'requires_action':
                approve_link = self._extract_approve_link(response.get('links', []))
                result['action'] = {
                    'type': 'redirect',
                    'url': approve_link,
                    'data': {}
                }

            if mapped_status == 'failed':
                result['error'] = {
                    'code': 'payment_failed',
                    'message': f'PayPal order status: {paypal_status}'
                }

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve PayPal order {intent_id}: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'provider_status': 'ERROR',
                'requires_action': False,
                'error': {
                    'code': 'retrieval_failed',
                    'message': str(e)
                },
                'raw_response': {}
            }

    def confirm_payment_intent(
        self,
        intent_id: str,
        confirmation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent by capturing the approved PayPal order.

        Called after the customer approves the PayPal order via redirect.

        Args:
            intent_id: PayPal order ID
            confirmation_data: Optional confirmation data

        Returns:
            Dictionary with confirmation result
        """
        try:
            response = self._make_request(
                method='POST',
                endpoint=f'/v2/checkout/orders/{intent_id}/capture'
            )

            status = response.get('status', '')
            purchase_unit = response.get('purchase_units', [{}])[0] if response.get('purchase_units') else {}
            captures = (purchase_unit.get('payments') or {}).get('captures', [])
            capture = captures[0] if captures else {}

            capture_status = capture.get('status', status)

            # Map capture status
            status_map = {
                'COMPLETED': 'succeeded',
                'PENDING': 'processing',
                'DECLINED': 'failed',
                'FAILED': 'failed',
            }

            mapped_status = status_map.get(capture_status, self._map_order_status(status))

            logger.info(f"Confirmed PayPal order {intent_id}: {mapped_status}")

            result = {
                'success': mapped_status in ('succeeded', 'processing'),
                'status': mapped_status,
                'requires_action': False,
                'payment_method_type': 'paypal',
                'payment_method_last4': None,
                'message': f'Payment {mapped_status}',
                'raw_response': response
            }

            if mapped_status == 'failed':
                reason = (capture.get('status_details') or {}).get('reason', 'Unknown')
                result['error'] = {
                    'code': 'capture_failed',
                    'message': f'Payment capture failed: {reason}'
                }

            return result

        except Exception as e:
            logger.error(f"PayPal order confirmation failed for {intent_id}: {str(e)}")
            return {
                'success': False,
                'status': 'failed',
                'requires_action': False,
                'error': {
                    'code': 'confirmation_failed',
                    'message': str(e)
                },
                'raw_response': {}
            }

    def cancel_payment_intent(
        self,
        intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a payment intent.

        PayPal orders automatically expire after ~3 hours if not approved,
        so cancellation is a no-op that returns success.

        Args:
            intent_id: PayPal order ID
            cancellation_reason: Optional reason for cancellation

        Returns:
            Dictionary with cancellation result
        """
        logger.info(
            f"PayPal order {intent_id} cancellation requested. "
            f"PayPal orders auto-expire if not approved."
        )

        return {
            'success': True,
            'status': 'canceled',
            'message': 'Payment intent canceled. PayPal orders auto-expire if not approved by the customer.',
            'raw_response': {}
        }

    # ─── Helper Methods ───────────────────────────────────────────────────────

    def _extract_capture_data(self, order_response: Dict) -> Dict[str, Any]:
        """
        Extract capture data from a completed order response.

        Args:
            order_response: PayPal order response

        Returns:
            Capture data dictionary
        """
        purchase_units = order_response.get('purchase_units', [])
        if purchase_units:
            payments = purchase_units[0].get('payments', {})
            captures = payments.get('captures', [])
            if captures:
                return captures[0]
        return {}

    def get_payment_method_types(self) -> Dict[str, Any]:
        """
        Get available payment method types.

        Returns static PayPal payment methods organized by country.

        Returns:
            Dictionary with payment methods by country
        """
        # PayPal payment methods vary by country
        methods_by_country = {
            'US': ['paypal', 'card', 'venmo', 'pay_later', 'paypal_credit'],
            'GB': ['paypal', 'card', 'pay_later', 'paypal_credit'],
            'DE': ['paypal', 'card', 'pay_later'],
            'FR': ['paypal', 'card', 'pay_later'],
            'AU': ['paypal', 'card', 'pay_later'],
            'CA': ['paypal', 'card'],
            'IT': ['paypal', 'card'],
            'ES': ['paypal', 'card'],
            'NL': ['paypal', 'card'],
            'BE': ['paypal', 'card'],
            'AT': ['paypal', 'card'],
            'CH': ['paypal', 'card'],
            'JP': ['paypal', 'card'],
            'SG': ['paypal', 'card'],
            'HK': ['paypal', 'card'],
            'BR': ['paypal', 'card'],
            'MX': ['paypal', 'card'],
            'IN': ['paypal', 'card'],
        }

        return {
            'success': True,
            'methods': methods_by_country,
            'raw_response': {}
        }

    # =========================================================================
    # Subscription Webhook Translation
    # =========================================================================

    # PayPal subscription event type -> standardized event type mapping
    # Ref: https://developer.paypal.com/api/rest/webhooks/event-names/
    _SUBSCRIPTION_EVENT_MAP = {
        'BILLING.SUBSCRIPTION.CREATED': SubscriptionEventType.CREATED,
        'BILLING.SUBSCRIPTION.ACTIVATED': SubscriptionEventType.ACTIVATED,
        'BILLING.SUBSCRIPTION.CANCELLED': SubscriptionEventType.CANCELED,
        'BILLING.SUBSCRIPTION.EXPIRED': SubscriptionEventType.EXPIRED,
        'BILLING.SUBSCRIPTION.SUSPENDED': SubscriptionEventType.PAST_DUE,
        'BILLING.SUBSCRIPTION.RE-ACTIVATED': SubscriptionEventType.RESUMED,
        'BILLING.SUBSCRIPTION.UPDATED': SubscriptionEventType.UPDATED,
    }

    def translate_subscription_webhook(
        self, event_type: str, payload: dict
    ) -> Optional[SubscriptionEvent]:
        """
        Translate PayPal webhook event to standardized SubscriptionEvent.
        Returns None for non-subscription events.

        PayPal subscription webhooks use the structure:
            {id, event_type, resource: {<subscription or sale object>}, ...}

        Subscription events: BILLING.SUBSCRIPTION.*
        Payment events: PAYMENT.SALE.COMPLETED / PAYMENT.SALE.DENIED
        """
        # Direct subscription lifecycle events
        if event_type in self._SUBSCRIPTION_EVENT_MAP:
            return self._translate_paypal_subscription_event(
                event_type, payload, self._SUBSCRIPTION_EVENT_MAP[event_type]
            )

        # Payment events tied to subscriptions
        if event_type == 'PAYMENT.SALE.COMPLETED':
            return self._translate_paypal_sale_event(
                event_type, payload, SubscriptionEventType.PAYMENT_SUCCEEDED
            )
        if event_type == 'PAYMENT.SALE.DENIED':
            return self._translate_paypal_sale_event(
                event_type, payload, SubscriptionEventType.PAYMENT_FAILED
            )
        if event_type == 'BILLING.SUBSCRIPTION.PAYMENT.FAILED':
            return self._translate_paypal_subscription_event(
                event_type, payload, SubscriptionEventType.PAYMENT_FAILED
            )

        return None

    def _translate_paypal_subscription_event(
        self, paypal_event_type: str, payload: dict,
        std_type: SubscriptionEventType
    ) -> SubscriptionEvent:
        """Translate a PayPal subscription lifecycle event."""
        event_id = payload.get('id', '')
        resource = payload.get('resource', {})

        sub_id = resource.get('id', '')
        # PayPal subscriber info is nested
        subscriber = resource.get('subscriber', {})
        payer_id = subscriber.get('payer_id', '')

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': payer_id,
            'provider_event_type': paypal_event_type,
        }

        # Extract billing period from billing_info
        billing_info = resource.get('billing_info', {})
        last_payment = billing_info.get('last_payment', {})
        if last_payment.get('time'):
            try:
                kwargs['period_start'] = datetime.fromisoformat(
                    last_payment['time'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        next_billing_time = billing_info.get('next_billing_time')
        if next_billing_time:
            try:
                kwargs['period_end'] = datetime.fromisoformat(
                    next_billing_time.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        # Extract amount from last payment
        amount_data = last_payment.get('amount', {})
        if amount_data.get('value'):
            kwargs['amount'] = Decimal(str(amount_data['value']))
        if amount_data.get('currency_code'):
            kwargs['currency'] = amount_data['currency_code'].upper()

        # Extract error info for failed payments
        if std_type == SubscriptionEventType.PAYMENT_FAILED:
            last_failed = billing_info.get('last_failed_payment', {})
            kwargs['error_message'] = last_failed.get(
                'reason_code', (resource.get('status_details') or {}).get('reason', '')
            )

        return SubscriptionEvent(**kwargs)

    def _translate_paypal_sale_event(
        self, paypal_event_type: str, payload: dict,
        std_type: SubscriptionEventType
    ) -> Optional[SubscriptionEvent]:
        """Translate PayPal PAYMENT.SALE.* events linked to subscriptions."""
        event_id = payload.get('id', '')
        resource = payload.get('resource', {})

        # Only handle sale events that are linked to a subscription
        sub_id = resource.get('billing_agreement_id', '')
        if not sub_id:
            return None  # Not a subscription-related sale

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': '',
            'provider_event_type': paypal_event_type,
        }

        # Extract payment amount
        amount_data = resource.get('amount') or {}
        amount_value = amount_data.get('total', '0')
        if amount_value:
            kwargs['amount'] = Decimal(str(amount_value))
        currency = amount_data.get('currency', '')
        if currency:
            kwargs['currency'] = currency.upper()

        return SubscriptionEvent(**kwargs)
