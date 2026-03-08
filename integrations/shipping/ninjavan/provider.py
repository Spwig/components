"""
NinjaVan Shipping Provider

OAuth 2.0 authenticated shipping provider for NinjaVan Plugin APIs.
Implements label generation, order cancellation, and webhook-based tracking
for Southeast Asian markets.

Author: Spwig
Version: 1.0.0
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from shipping.providers.base import ProviderBase
from .auth import NinjaVanOAuthClient
from .retry import with_retry, RetryConfig, create_retry_config_from_environment
from .exceptions import (
    NinjaVanError,
    NinjaVanOAuthError,
    NinjaVanAuthenticationError,
    NinjaVanValidationError,
    NinjaVanNetworkError,
    parse_error_response,
)
from . import utils


logger = logging.getLogger(__name__)


class NinjaVanProvider(ProviderBase):
    """
    NinjaVan shipping provider implementation.

    Provides label generation and webhook-based tracking via NinjaVan Plugin APIs
    with OAuth 2.0 authentication. Supports multi-country operations across
    Southeast Asia (SG, MY, TH, ID, VN, PH, MM).

    Capabilities:
        - Shipping label generation (PDF format)
        - Order cancellation (Pending Pickup only)
        - Webhook-based tracking
        - Multi-country support
        - COD and pickup scheduling
        - Return service

    Note: Rate calculation is NOT supported by NinjaVan Plugin APIs.
    Merchants already have established pricing with NinjaVan.

    API Documentation: https://api-docs.ninjavan.co/en#tag/Plugin-APIs
    """

    # Provider identification
    provider_key = 'ninjavan'
    provider_name = _('NinjaVan')

    # API request timeout
    REQUEST_TIMEOUT = 30

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize NinjaVan provider.

        Args:
            credentials: Dictionary containing:
                - client_id: Client ID from NinjaVan Dashboard
                - client_secret: Client Secret from NinjaVan Dashboard
                - country_code: Country code (SG, MY, TH, ID, VN, PH, MM)
                - environment: 'sandbox' or 'production'
                - oauth_access_token: Access token (optional, obtained via OAuth)
                - oauth_refresh_token: Refresh token (optional)
                - oauth_expires_at: Token expiration (optional)
            config: Optional configuration dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        # Initialize parent class (validates credentials)
        super().__init__(credentials, config)

        # Extract credentials
        self.client_id = credentials.get('client_id')
        self.client_secret = credentials.get('client_secret')
        self.country_code = credentials.get('country_code', 'SG').upper()
        self.environment = credentials.get('environment', 'sandbox').lower()

        # OAuth tokens (may be None initially, obtained through OAuth flow)
        self.access_token = credentials.get('oauth_access_token')
        self.refresh_token = credentials.get('oauth_refresh_token')
        self.expires_at = credentials.get('oauth_expires_at')

        # Construct base URL
        self.base_url = utils.get_base_url(self.environment, self.country_code)

        # Create OAuth client
        self.oauth_client = NinjaVanOAuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            environment=self.environment,
            timeout=self.REQUEST_TIMEOUT,
        )

        # Create retry configuration
        self.retry_config = create_retry_config_from_environment(self.environment)

        logger.info(
            f"NinjaVan provider initialized "
            f"(environment={self.environment}, country={self.country_code})"
        )

    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Return NinjaVan provider capabilities.

        Returns:
            Dictionary of supported features
        """
        return {
            'rates': False,             # Not supported by Plugin APIs
            'labels': True,             # Label generation
            'tracking': True,           # Webhook-based tracking
            'international': True,      # Multi-country support
            'returns': True,            # Return service type
            'pickup': False,            # Pickup scheduling (not in v1.0)
            'insurance': True,          # Insurance support
            'signature': False,         # No signature confirmation
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for NinjaVan credentials.

        Returns:
            JSON schema dictionary
        """
        return {
            'type': 'object',
            'properties': {
                'client_id': {
                    'type': 'string',
                    'title': _('Client ID'),
                    'description': _('Client ID from NinjaVan Dashboard > Settings > IT Settings'),
                    'required': True,
                    'secret': False,
                },
                'client_secret': {
                    'type': 'string',
                    'title': _('Client Secret'),
                    'description': _('Client Secret from NinjaVan Dashboard > Settings > IT Settings'),
                    'required': True,
                    'secret': True,
                },
                'country_code': {
                    'type': 'string',
                    'title': _('Country'),
                    'description': _('Country of your NinjaVan account'),
                    'enum': ['SG', 'MY', 'TH', 'ID', 'VN', 'PH', 'MM'],
                    'default': 'SG',
                    'required': True,
                },
                'environment': {
                    'type': 'string',
                    'title': _('Environment'),
                    'description': _('Use sandbox for testing, production after passing integration audit'),
                    'enum': ['sandbox', 'production'],
                    'default': 'sandbox',
                    'required': True,
                },
            }
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credentials against schema and business logic.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing required fields
        """
        # Check required fields
        required_fields = ['client_id', 'client_secret', 'country_code', 'environment']
        for field in required_fields:
            if not credentials.get(field):
                raise ValueError(f"Missing required credential: {field}")

        # Validate country code
        country_code = credentials.get('country_code', '').upper()
        if not utils.validate_country_code(country_code):
            raise ValueError(
                f"Invalid country code: {country_code}. "
                f"Must be one of: {', '.join(utils.NINJAVAN_COUNTRIES.keys())}"
            )

        # Validate environment
        environment = credentials.get('environment', '').lower()
        if environment not in ['sandbox', 'production']:
            raise ValueError(
                f"Invalid environment: {environment}. Must be 'sandbox' or 'production'"
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()

        # Redact client secret
        if 'client_secret' in redacted and redacted['client_secret']:
            secret = redacted['client_secret']
            redacted['client_secret'] = f"{secret[:4]}***{secret[-4:]}" if len(secret) > 8 else "***"

        # Redact OAuth tokens
        if 'oauth_access_token' in redacted and redacted['oauth_access_token']:
            token = redacted['oauth_access_token']
            redacted['oauth_access_token'] = f"{token[:8]}***" if len(token) > 8 else "***"

        if 'oauth_refresh_token' in redacted and redacted['oauth_refresh_token']:
            token = redacted['oauth_refresh_token']
            redacted['oauth_refresh_token'] = f"{token[:8]}***" if len(token) > 8 else "***"

        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity.

        Validates OAuth tokens and fetches shipper settings to verify access.

        Returns:
            Dictionary with test results including shipper settings

        Raises:
            NinjaVanAuthenticationError: If authentication fails
            NinjaVanError: If API request fails
        """
        logger.info("Testing NinjaVan connection")

        try:
            # Ensure we have valid OAuth tokens
            if not self.access_token:
                return {
                    'success': False,
                    'message': _('OAuth not completed. Please authorize your NinjaVan account.'),
                    'requires_oauth': True,
                }

            # Fetch shipper settings to validate connection
            settings = self._get_shipper_settings()

            logger.info("Connection test successful")

            return {
                'success': True,
                'message': _('Connection successful'),
                'details': {
                    'environment': self.environment,
                    'country': self.country_code,
                    'shipper_id': settings.get('id'),
                    'service_types': settings.get('service_types', []),
                    'service_levels': settings.get('service_levels', []),
                },
            }

        except NinjaVanAuthenticationError as e:
            logger.error(f"Authentication failed during connection test: {e}")
            return {
                'success': False,
                'message': _('Authentication failed. Please re-authorize your NinjaVan account.'),
                'error': str(e),
                'requires_oauth': True,
            }

        except NinjaVanError as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'message': _('Connection failed: {error}').format(error=str(e)),
                'error': str(e),
            }

    def get_rates(
        self,
        origin: Dict[str, str],
        destination: Dict[str, str],
        parcels: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get shipping rates for a shipment.

        Note: NinjaVan Plugin APIs do NOT support rate calculation.
        This method raises NotImplementedError.

        Args:
            origin: Origin address dictionary
            destination: Destination address dictionary
            parcels: List of parcel dictionaries
            options: Optional shipping options

        Raises:
            NotImplementedError: Always raises as rates are not supported
        """
        raise NotImplementedError(
            "Rate calculation is not supported by NinjaVan Plugin APIs. "
            "Merchants have established pricing with NinjaVan through their accounts."
        )

    def buy_label(
        self,
        shipment_id: str,
        rate: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Purchase shipping label (create NinjaVan order and generate waybill).

        This is a two-step process:
        1. Create order via POST /{countryCode}/plugins/4.2/orders
        2. Generate waybill PDF via GET /{countryCode}/plugins/2.0/waybills?tids={trackingNo}

        Args:
            shipment_id: Internal shipment ID
            rate: Rate dictionary (contains shipment details for NinjaVan)
            options: Optional purchase options

        Returns:
            Dictionary with label information including tracking number and PDF

        Raises:
            NinjaVanValidationError: If shipment data is invalid
            NinjaVanError: If API request fails
        """
        logger.info(f"Creating NinjaVan order for shipment {shipment_id}")

        # Refresh token if needed
        self._refresh_access_token_if_needed()

        # Extract shipment data from rate dictionary
        # (In NinjaVan's case, the "rate" contains the full shipment details)
        shipment_data = rate.get('shipment_data', {})

        # Build order payload
        order_payload = self._build_order_payload(shipment_data, options)

        # Step 1: Create order
        order_response = self._create_order(order_payload)

        tracking_number = order_response.get('tracking_number')
        if not tracking_number:
            raise NinjaVanError("Order created but no tracking number returned")

        logger.info(f"Order created successfully: {tracking_number}")

        # Step 2: Generate waybill
        label_data = self._generate_waybill(tracking_number)

        # Build response
        result = {
            'tracking_number': tracking_number,
            'label_data': label_data['label_data'],  # Base64-encoded PDF
            'label_format': 'pdf',
            'label_size': label_data['label_size'],
            'cost': order_response.get('cost'),  # May be None
            'currency': order_response.get('currency', 'SGD'),
            'carrier': 'NinjaVan',
            'service': order_response.get('service_type', 'Parcel'),
            'external_shipment_id': order_response.get('order_id'),
            'created_at': datetime.utcnow(),
        }

        logger.info(f"Label generated successfully for {tracking_number}")

        return result

    def cancel_label(self, tracking_number: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel a NinjaVan order (void label).

        Note: Orders can only be cancelled while in "Pending Pickup" status.

        Args:
            tracking_number: NinjaVan tracking number
            reason: Optional cancellation reason (not used by API)

        Returns:
            Dictionary with cancellation result

        Raises:
            NinjaVanValidationError: If order cannot be cancelled (wrong status)
            NinjaVanError: If API request fails
        """
        logger.info(f"Cancelling NinjaVan order: {tracking_number}")

        # Refresh token if needed
        self._refresh_access_token_if_needed()

        # Cancel order via DELETE endpoint
        endpoint = f"/plugins/2.2/orders/{tracking_number}"

        try:
            response_data = self._make_request('DELETE', endpoint)

            logger.info(f"Order {tracking_number} cancelled successfully")

            return {
                'success': True,
                'refunded': False,  # NinjaVan doesn't provide refund info via API
                'refund_amount': None,
                'currency': None,
                'message': _('Order cancelled successfully'),
            }

        except NinjaVanValidationError as e:
            # Likely wrong status (not "Pending Pickup")
            logger.warning(f"Failed to cancel order {tracking_number}: {e}")
            return {
                'success': False,
                'refunded': False,
                'refund_amount': None,
                'currency': None,
                'message': str(e),
            }

    def get_tracking(self, tracking_number: str) -> Dict[str, Any]:
        """
        Get tracking information for a shipment.

        Note: NinjaVan Plugin APIs don't provide a tracking query endpoint.
        Tracking data comes from webhooks. This method queries the local
        database for stored webhook events.

        Args:
            tracking_number: NinjaVan tracking number

        Returns:
            Dictionary with tracking data from stored webhook events

        Raises:
            ValueError: If tracking number is invalid
        """
        logger.info(f"Getting tracking info for {tracking_number}")

        # Import here to avoid circular dependency
        from .webhooks import WebhookReceiver

        # Query local database for webhook events
        receiver = WebhookReceiver(self.client_secret)
        events = receiver.get_tracking_events(tracking_number)

        if not events:
            return {
                'tracking_number': tracking_number,
                'status': 'pending',
                'carrier': 'NinjaVan',
                'service': None,
                'estimated_delivery': None,
                'actual_delivery': None,
                'events': [],
            }

        # Get latest event for current status
        latest_event = events[0] if events else None
        current_status = latest_event.get('status', 'pending') if latest_event else 'pending'

        # Check if delivered
        actual_delivery = None
        if current_status == 'delivered':
            actual_delivery = latest_event.get('timestamp')

        return {
            'tracking_number': tracking_number,
            'status': current_status,
            'carrier': 'NinjaVan',
            'service': latest_event.get('service_type') if latest_event else None,
            'estimated_delivery': None,  # Not provided by webhooks
            'actual_delivery': actual_delivery,
            'events': events,
        }

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify webhook authenticity using HMAC-SHA256 signature.

        Args:
            payload: Raw request body as bytes
            signature: Signature from X-Ninjavan-Hmac-Sha256 header
            **kwargs: Additional headers (not used)

        Returns:
            True if signature is valid, False otherwise
        """
        payload_str = payload.decode('utf-8') if isinstance(payload, bytes) else payload
        return utils.verify_webhook_signature(payload_str, signature, self.client_secret)

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event from NinjaVan.

        Args:
            event_type: NinjaVan event type (e.g., "Delivered, Received by Customer")
            payload: Webhook payload dictionary

        Returns:
            Dictionary with processed webhook data for storage

        Raises:
            ValueError: If payload is invalid
        """
        logger.info(f"Processing NinjaVan webhook: {event_type}")

        # Extract tracking number
        tracking_number = payload.get('tracking_number')
        if not tracking_number:
            raise ValueError("Webhook payload missing tracking_number")

        # Map NinjaVan status to platform status
        platform_status = utils.map_ninjavan_status(event_type)

        # Extract timestamp
        timestamp_str = payload.get('timestamp')
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # Build event data
        event = {
            'timestamp': timestamp,
            'status': platform_status,
            'location': payload.get('location'),
            'description': event_type,
            'raw_status': event_type,
        }

        # Add proof of delivery URL if available
        if 'proof_of_delivery_url' in payload:
            event['proof_of_delivery_url'] = payload['proof_of_delivery_url']

        return {
            'action': 'update_tracking',
            'tracking_number': tracking_number,
            'status': platform_status,
            'event': event,
        }

    # Helper methods

    def get_oauth_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple:
        """
        Generate OAuth authorization URL for merchant to authorize plugin.

        Args:
            redirect_uri: URL to redirect back to after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Tuple of (authorization_url, state)
        """
        return self.oauth_client.get_authorization_url(redirect_uri, state)

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dictionary with tokens (access_token, refresh_token, expires_at)
        """
        return self.oauth_client.exchange_code_for_token(code)

    def logout(self) -> bool:
        """
        Logout and invalidate OAuth tokens.

        Returns:
            True if logout successful
        """
        if self.access_token:
            return self.oauth_client.logout(self.access_token)
        return True

    def _refresh_access_token_if_needed(self) -> None:
        """
        Refresh access token if it's expired or about to expire.

        Updates self.access_token, self.refresh_token, and self.expires_at.
        """
        if not self.refresh_token:
            return

        # Convert expires_at to datetime if string
        expires_at = self.expires_at
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except Exception:
                expires_at = None

        # Check if refresh needed
        if not self.oauth_client.should_refresh_token(expires_at):
            return

        logger.info("Refreshing access token")

        try:
            # Refresh token (thread-safe)
            new_access, new_refresh, new_expires, was_refreshed = self.oauth_client.refresh_if_needed(
                self.access_token,
                self.refresh_token,
                expires_at,
            )

            if was_refreshed:
                # Update stored tokens
                self.access_token = new_access
                self.refresh_token = new_refresh
                self.expires_at = new_expires

                # Update credentials in database (callback to platform)
                # This would be handled by the platform's credential update mechanism
                logger.info("Access token refreshed successfully")

        except NinjaVanOAuthError as e:
            logger.error(f"Failed to refresh token: {e}. Re-authorization required.")
            raise NinjaVanAuthenticationError(
                "Token refresh failed. Please re-authorize your NinjaVan account.",
                status_code=401,
            )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to NinjaVan API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path (e.g., '/plugins/4.2/orders')
            **kwargs: Additional arguments for requests (json, params, etc.)

        Returns:
            JSON response data

        Raises:
            NinjaVanAuthenticationError: If authentication fails
            NinjaVanError: If API request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Add authorization header
        headers = kwargs.pop('headers', {})
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        headers['Content-Type'] = 'application/json'

        # Set timeout
        timeout = kwargs.pop('timeout', self.REQUEST_TIMEOUT)

        logger.debug(f"Making {method} request to {endpoint}")

        @with_retry(self.retry_config)
        def make_request():
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                # Handle successful response
                if response.status_code in [200, 201, 204]:
                    # 204 No Content returns empty body
                    if response.status_code == 204:
                        return {}
                    # Some endpoints return PDF (waybill)
                    if 'application/pdf' in response.headers.get('Content-Type', ''):
                        return response  # Return response object for binary data
                    return response.json()

                # Handle error response
                error = parse_error_response(response)
                logger.error(f"API error: {error}")
                raise error

            except requests.exceptions.Timeout:
                raise NinjaVanNetworkError(
                    f"Request to {endpoint} timed out",
                    status_code=None,
                )
            except requests.exceptions.ConnectionError as e:
                raise NinjaVanNetworkError(
                    f"Failed to connect to NinjaVan API: {str(e)}",
                    status_code=None,
                )
            except requests.exceptions.RequestException as e:
                raise NinjaVanNetworkError(
                    f"Network error during API request: {str(e)}",
                    status_code=None,
                )

        return make_request()

    def _get_shipper_settings(self) -> Dict[str, Any]:
        """
        Fetch shipper settings from NinjaVan API.

        Returns:
            Dictionary with shipper configuration
        """
        endpoint = "/plugins/2.0/shippers/settings"
        return self._make_request('GET', endpoint)

    def _build_order_payload(
        self,
        shipment_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build order payload for NinjaVan API.

        Args:
            shipment_data: Shipment data containing origin, destination, parcels
            options: Optional shipping options

        Returns:
            Order payload dictionary
        """
        options = options or {}

        # Extract addresses
        origin = shipment_data.get('origin', {})
        destination = shipment_data.get('destination', {})

        # Extract parcels
        parcels = shipment_data.get('parcels', [])
        if not parcels:
            raise NinjaVanValidationError("At least one parcel is required")

        # Format addresses
        from_address = utils.format_address(origin)
        to_address = utils.format_address(destination)

        # Format parcel (use first parcel)
        parcel = utils.format_parcel(parcels[0])

        # Build payload
        payload = {
            'service_type': options.get('service_type', 'Parcel'),
            'service_level': options.get('service_level', 'Standard'),
            'from': from_address,
            'to': to_address,
            'parcel_job': parcel,
        }

        # Add optional fields
        if options.get('requested_tracking_number'):
            payload['requested_tracking_number'] = options['requested_tracking_number']

        if options.get('pickup_date'):
            payload['pickup_date'] = options['pickup_date']

        if options.get('pickup_timeslot'):
            payload['pickup_timeslot'] = options['pickup_timeslot']

        if options.get('delivery_timeslot'):
            payload['delivery_timeslot'] = options['delivery_timeslot']

        if options.get('allow_weekend_delivery') is not None:
            payload['allow_weekend_delivery'] = options['allow_weekend_delivery']

        # COD support
        if options.get('cod_amount'):
            payload['cod_amount_to_collect'] = float(options['cod_amount'])

        return payload

    def _create_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create order via NinjaVan API.

        Args:
            order_payload: Order payload

        Returns:
            Order response with tracking number
        """
        endpoint = "/plugins/4.2/orders"
        response = self._make_request('POST', endpoint, json=order_payload)

        # Extract tracking number
        tracking_number = response.get('tracking_number') or response.get('tracking_id')

        return {
            'tracking_number': tracking_number,
            'order_id': response.get('id'),
            'status': response.get('status'),
            'service_type': response.get('service_type'),
            'cost': response.get('price_amount'),  # May not be available
            'currency': response.get('price_currency'),
        }

    def _generate_waybill(self, tracking_number: str) -> Dict[str, Any]:
        """
        Generate waybill (shipping label) PDF.

        Args:
            tracking_number: NinjaVan tracking number

        Returns:
            Dictionary with base64-encoded PDF data
        """
        endpoint = f"/plugins/2.0/waybills?tids={tracking_number}"
        response = self._make_request('GET', endpoint)

        # Parse PDF response
        return utils.parse_waybill_response(response)
