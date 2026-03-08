"""
AirWallex Subscription Provider
Fallback mode - uses internal billing engine.
"""
import requests
import logging
import uuid
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from subscriptions.provider_base import FallbackSubscriptionProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider('airwallex')
class AirWallexSubscriptionProvider(FallbackSubscriptionProvider):
    """
    AirWallex provider using fallback billing engine.
    AirWallex doesn't have native subscription APIs, so billing
    is managed internally via Celery tasks and AirWallex is used
    only for tokenization and charging.
    """

    DEMO_API_BASE = "https://api-demo.airwallex.com/api/v1"
    PRODUCTION_API_BASE = "https://api.airwallex.com/api/v1"

    def _get_api_base(self) -> str:
        """Get API base URL based on environment."""
        # Support both dual-credential and legacy config structures
        test_mode = self.config.get('test_mode', True)
        environment = self.config.get('environment', 'demo')
        if test_mode or environment == 'demo':
            return self.DEMO_API_BASE
        return self.PRODUCTION_API_BASE

    def _get_credentials(self) -> tuple:
        """
        Get active client_id and api_key from config.
        Handles both dual-credential and legacy structures.
        """
        test_mode = self.config.get('test_mode', True)

        if test_mode:
            client_id = self.config.get('test_client_id', self.config.get('client_id', ''))
            api_key = self.config.get('test_api_key', self.config.get('api_key', ''))
        else:
            client_id = self.config.get('live_client_id', self.config.get('client_id', ''))
            api_key = self.config.get('live_api_key', self.config.get('api_key', ''))

        return client_id, api_key

    def _get_access_token(self) -> str:
        """
        Obtain access token from AirWallex authentication endpoint.
        Tokens are cached for 50 minutes (valid ~1 hour).
        """
        if hasattr(self, '_access_token') and hasattr(self, '_token_expires_at'):
            if self._access_token and self._token_expires_at:
                if datetime.now() < self._token_expires_at:
                    return self._access_token

        api_base = self._get_api_base()
        client_id, api_key = self._get_credentials()

        headers = {
            'x-client-id': client_id,
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                f"{api_base}/authentication/login",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get('token')
            self._token_expires_at = datetime.now() + timedelta(minutes=50)

            return self._access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain AirWallex access token: {e}")
            raise Exception(f"AirWallex authentication failed: {e}")

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
            method: HTTP method
            endpoint: API endpoint path
            data: Request body data
            params: URL query parameters

        Returns:
            Response JSON as dictionary

        Raises:
            Exception: If request fails
        """
        token = self._get_access_token()
        api_base = self._get_api_base()
        url = f"{api_base}{endpoint}"

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

            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"AirWallex API request failed: {method} {endpoint} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"AirWallex error details: {error_data}")
                except (ValueError, KeyError):
                    pass
            raise Exception(f"AirWallex API error: {e}")

    # ===========================
    # Customer & Token Management
    # ===========================

    def create_customer(self, user, email: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create an AirWallex customer.

        Args:
            user: Django User instance
            email: Customer email
            metadata: Optional metadata

        Returns:
            dict: {'customer_id': str, 'metadata': dict}
        """
        try:
            body = {
                'email': email,
                'first_name': user.first_name or user.username,
                'last_name': user.last_name or '',
                'merchant_customer_id': str(user.id),
                'request_id': str(uuid.uuid4()),
            }

            result = self._make_request('POST', '/pa/customers/create', data=body)
            customer_id = result.get('id', '')

            logger.info(f"Created AirWallex customer: {customer_id} for user {user.id}")

            return {
                'customer_id': customer_id,
                'metadata': metadata or {},
            }

        except Exception as e:
            logger.error(f"Failed to create AirWallex customer: {e}")
            raise

    def create_payment_token(
        self,
        customer_id: str,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a payment consent for recurring billing.

        Uses AirWallex payment consents to tokenize a payment method
        for future off-session charges.

        Args:
            customer_id: AirWallex customer ID
            payment_method_data: {
                'payment_method_id': str,    # From AirWallex SDK
                'payment_method_type': str,  # e.g., 'card'
            }

        Returns:
            dict: Token information
        """
        payment_method_id = payment_method_data.get('payment_method_id')
        if not payment_method_id:
            raise ValueError("payment_method_id is required")

        try:
            # Create a payment consent for recurring charges
            body = {
                'customer_id': customer_id,
                'payment_method_id': payment_method_id,
                'payment_method_type': payment_method_data.get('payment_method_type', 'card'),
                'merchant_trigger_reason': 'scheduled',
                'request_id': str(uuid.uuid4()),
            }

            result = self._make_request('POST', '/pa/payment_consents/create', data=body)
            consent_id = result.get('id', '')

            # Retrieve payment method details for card info
            card_info = {}
            try:
                pm_response = self._make_request(
                    'GET',
                    f'/pa/payment_methods/{payment_method_id}'
                )
                card = pm_response.get('card', {})
                if card:
                    card_info = {
                        'card_brand': card.get('brand', '').lower(),
                        'card_last4': card.get('last4', ''),
                        'card_exp_month': card.get('expiry_month'),
                        'card_exp_year': card.get('expiry_year'),
                    }
            except Exception:
                pass  # Card info is supplementary, don't fail on it

            token_result = {
                'token_id': consent_id,
                'payment_method_type': payment_method_data.get('payment_method_type', 'card'),
            }
            token_result.update(card_info)

            logger.info(f"Created AirWallex payment consent: {consent_id} for customer {customer_id}")
            return token_result

        except Exception as e:
            logger.error(f"Failed to create AirWallex payment consent: {e}")
            raise

    def delete_payment_token(self, token_id: str) -> bool:
        """
        Disable an AirWallex payment consent.

        Args:
            token_id: Payment consent ID

        Returns:
            bool: True if successful
        """
        try:
            self._make_request(
                'POST',
                f'/pa/payment_consents/{token_id}/disable'
            )
            logger.info(f"Disabled AirWallex payment consent: {token_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable AirWallex payment consent: {e}")
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
        Charge using an AirWallex payment consent.
        Called by the fallback billing engine for each billing cycle.

        Creates a PaymentIntent and confirms it off-session using
        the saved payment consent.

        Args:
            token_id: Payment consent ID
            amount: Charge amount
            currency: Currency code
            description: Charge description
            metadata: Optional metadata

        Returns:
            dict: Charge result
        """
        request_id = str(uuid.uuid4())

        # Step 1: Create payment intent
        intent_body = {
            'amount': float(amount),
            'currency': currency.lower(),
            'descriptor': description[:64] if description else 'Subscription charge',
            'request_id': request_id,
            'merchant_order_id': metadata.get('order_id', request_id) if metadata else request_id,
        }

        try:
            intent_result = self._make_request(
                'POST',
                '/pa/payment_intents/create',
                data=intent_body
            )
            intent_id = intent_result.get('id', '')

            # Step 2: Confirm with payment consent (off-session)
            confirm_body = {
                'payment_consent_id': token_id,
                'payment_method_type': 'card',
                'request_id': str(uuid.uuid4()),
            }

            confirm_result = self._make_request(
                'POST',
                f'/pa/payment_intents/{intent_id}/confirm',
                data=confirm_body
            )

            status = confirm_result.get('status', '')
            is_success = status == 'SUCCEEDED'

            logger.info(f"AirWallex charge {intent_id}: {status}")

            return {
                'transaction_id': intent_id,
                'status': 'succeeded' if is_success else ('pending' if status == 'REQUIRES_CAPTURE' else 'failed'),
                'amount': amount,
                'currency': currency,
                'error_message': '' if is_success else f'Payment status: {status}',
                'error_code': '' if is_success else status,
            }

        except Exception as e:
            logger.error(f"Failed to charge AirWallex payment consent: {e}")
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
        Verify AirWallex webhook signature using HMAC-SHA256.

        Airwallex signs: timestamp + payload_json (per API docs).
        The x-timestamp header must be included in the HMAC computation.

        Args:
            payload: Raw webhook payload
            signature: X-Signature header value
            **kwargs: Additional context (timestamp, headers)

        Returns:
            bool: True if signature is valid
        """
        import hmac as hmac_mod
        import hashlib

        # Get webhook secret from config (handles both credential structures)
        test_mode = self.config.get('test_mode', True)
        if test_mode:
            webhook_secret = self.config.get('test_webhook_secret', self.config.get('webhook_secret', ''))
        else:
            webhook_secret = self.config.get('live_webhook_secret', self.config.get('webhook_secret', ''))

        if not webhook_secret:
            logger.warning("AirWallex webhook secret not configured")
            return False

        # Extract timestamp from kwargs (passed by webhook handler)
        timestamp = kwargs.get('timestamp', '')
        if not timestamp:
            headers = kwargs.get('headers', {})
            timestamp = headers.get('x-timestamp', headers.get('HTTP_X_TIMESTAMP', ''))

        # Build signed payload: timestamp + raw payload (per Airwallex spec)
        payload_str = payload.decode('utf-8') if isinstance(payload, bytes) else payload
        signed_payload = f"{timestamp}{payload_str}"

        expected = hmac_mod.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        is_valid = hmac_mod.compare_digest(expected, signature)

        if not is_valid:
            logger.error("Invalid AirWallex webhook signature")

        return is_valid

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AirWallex webhook payload.

        Args:
            payload: AirWallex webhook event

        Returns:
            dict: Standardized event format
        """
        event_type = payload.get('name', '')
        event_id = payload.get('id', '')
        data = payload.get('data', {}).get('object', payload.get('data', {}))

        result = {
            'event_type': event_type,
            'event_id': event_id,
            'data': data,
        }

        # Extract payment intent ID if present
        if 'id' in data:
            result['transaction_id'] = data.get('id')

        return result
