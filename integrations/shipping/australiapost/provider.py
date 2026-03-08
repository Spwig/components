"""
Australia Post Shipping Provider

HTTP Basic Auth authenticated shipping provider for Australia Post Shipping API.
Implements rate calculation, two-step label generation, tracking with rate limiting,
and v2.0.0 features: order management, basket management, validation services, and more.

Author: Spwig
Version: 2.0.2
"""
import logging
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

import requests

from shipping.providers.base import ProviderBase
from .auth import create_auth_client, AustraliaPostAuthClient, pad_account_number, detect_service_type
from . import utils
from .exceptions import (
    AustraliaPostError,
    AustraliaPostAuthenticationError,
    AustraliaPostValidationError,
    AustraliaPostAccountError,
    AustraliaPostShipmentError,
    AustraliaPostRateLimitError,
    AustraliaPostServiceUnavailableError,
    AustraliaPostLabelError,
    AustraliaPostTrackingError,
    AustraliaPostAPIError,
    AustraliaPostOrderError,
    AustraliaPostBasketError,
    AustraliaPostPickupError,
    create_exception_from_response,
    handle_request_exception,
)
from .retry import retry_with_backoff, RetryConfig
from .rate_limiter import get_tracking_limiter

# v2.0.0 module imports
from .order_manager import OrderManager
from .basket_manager import BasketManager
from .shipment_manager import ShipmentManager
from .validation_service import ValidationService
from .pricing_service import PricingService
from .features import ShipmentFeatures
from .pickup_service import PickupService


logger = logging.getLogger(__name__)


class AustraliaPostProvider(ProviderBase):
    """
    Australia Post shipping provider implementation v2.0.0.

    Production-ready implementation meeting full Australia Post lodgement validation requirements.
    Provides comprehensive order management, basket management, validation services, and all
    product features for eParcel, StarTrack, Same Day, and On Demand services.

    Key Features (v2.0.0):
        - **Order Management**: Create orders from shipments with auto-split (>2,000 items)
        - **Basket Management**: Track up to 10,000 items before order creation
        - **Validation Services**: Address validation, serviceability checks, pre-flight validation
        - **Product Features**: ATL, Safe Drop, Signature, Dangerous Goods, SSCC barcoding
        - **Enhanced Pricing**: Individual shipment pricing, ETA calculations
        - **Adhoc Pickups**: Schedule pickups with time slot selection
        - **Account Types**: Full support for 4 account types (eParcel, StarTrack, Same Day, On Demand)

    Core Capabilities (v1.0.1):
        - API Key authentication (UUID format)
        - Account number padding (10-digit Australia Post, 8-digit StarTrack)
        - Two-step label generation (create shipment, then create labels)
        - Rate limiting for tracking API (10 requests/60 seconds)
        - JSON request/response format
        - Exponential backoff retry logic
        - Rate quotes (domestic and international)
        - Shipping label generation (PDF format, synchronous <250 parcels)
        - Real-time tracking with rate limiting

    Production Workflow:
        1. Validate address/suburb (ValidationService)
        2. Create shipments and add to basket (BasketManager)
        3. Manage basket (update/delete as needed)
        4. Create order from basket (OrderManager, auto-splits if needed)
        5. Generate labels
        6. Get order summary/manifest
        7. Track shipments

    API Documentation: https://developers.auspost.com.au/

    Limits:
        - Basket size: 10,000 items maximum
        - Order size: 2,000 items maximum per order
        - Tracking rate: 10 requests per 60 seconds
    """

    # Provider identification
    provider_key = 'australiapost'
    provider_name = _('Australia Post')

    # API URLs
    SANDBOX_BASE_URL = 'https://digitalapi.auspost.com.au/test'
    PRODUCTION_BASE_URL = 'https://digitalapi.auspost.com.au'

    # API version
    API_VERSION = 'v1'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Australia Post provider.

        Args:
            credentials: Dictionary containing:
                - api_key: Australia Post API Key (UUID format)
                - api_password: Password associated with API Key
                - account_number: Charge account number (8-10 digits)
                - account_type: Account type (eparcel, startrack, same_day, on_demand)
                - environment: 'test' or 'production'
            config: Optional configuration dictionary

        Raises:
            ValueError: If credentials are invalid

        Example:
            credentials = {
                'api_key': '601a4032-6dbd-46aa-9c6c-8c6dacca5e61',
                'api_password': 'my_password',
                'account_number': '0000123456',
                'account_type': 'eparcel',
                'environment': 'production'
            }
            provider = AustraliaPostProvider(credentials)
        """
        # Initialize parent class (validates credentials)
        super().__init__(credentials, config)

        # Set API base URL based on environment
        environment = credentials.get('environment', 'test')
        self.base_url = (
            self.PRODUCTION_BASE_URL if environment == 'production'
            else self.SANDBOX_BASE_URL
        )
        self.environment = environment

        # Create auth client
        self.auth_client: AustraliaPostAuthClient = create_auth_client(credentials)

        # Initialize retry configuration
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0
        )

        # Session for connection pooling
        self.session = requests.Session()

        # v2.0.0: Initialize new service managers
        self.order_manager = OrderManager(
            auth_client=self.auth_client,
            base_url=self.base_url,
            api_version=self.API_VERSION
        )

        self.basket_manager = BasketManager(
            max_size=self.config.get('basket_max_size', 10000)
        )

        self.shipment_manager = ShipmentManager(
            auth_client=self.auth_client,
            base_url=self.base_url,
            api_version=self.API_VERSION
        )

        self.validation_service = ValidationService(
            auth_client=self.auth_client,
            base_url=self.base_url,
            api_version=self.API_VERSION,
            cache_ttl=self.config.get('validation_cache_ttl', 3600)
        )

        self.pricing_service = PricingService(
            auth_client=self.auth_client,
            base_url=self.base_url,
            api_version=self.API_VERSION
        )

        self.features = ShipmentFeatures()

        self.pickup_service = PickupService(
            auth_client=self.auth_client,
            base_url=self.base_url,
            api_version=self.API_VERSION
        )

        logger.info(
            f"Australia Post provider v2.0.0 initialized "
            f"(environment={environment}, basket_limit={self.basket_manager.max_size})"
        )

    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Return Australia Post provider capabilities (v2.0.0).

        Returns:
            Dictionary of supported features
        """
        return {
            # Core v1.0.1 capabilities
            'rates': True,                      # Rate calculation
            'labels': True,                     # Label generation (two-step process)
            'tracking': True,                   # Shipment tracking (rate limited)
            'international': True,              # International shipping
            'returns': True,                    # Return labels
            'pickup': True,                     # Pickup scheduling
            'insurance': True,                  # Insurance support
            'signature': True,                  # Signature confirmation
            'dangerous_goods': True,            # Dangerous goods support

            # v2.0.0 additions - Order Management
            'orders': True,                     # Create orders from shipments
            'order_summary': True,              # Generate manifests
            'order_splitting': True,            # Auto-split >2,000 items

            # v2.0.0 additions - Basket Management
            'basket_management': True,          # Track shipments in basket
            'shipment_update': True,            # Update shipments
            'item_operations': True,            # Add/update/delete items

            # v2.0.0 additions - Validation
            'validation': True,                 # Pre-flight validation
            'address_validation': True,         # Suburb/postcode validation
            'serviceability': True,             # Address serviceability checks

            # v2.0.0 additions - Product Features
            'authority_to_leave': True,         # ATL support
            'safe_drop': True,                  # Safe drop support
            'sscc_barcoding': True,             # SSCC barcode support

            # v2.0.0 additions - Enhanced Services
            'adhoc_pickups': True,              # Adhoc pickup scheduling
            'eta_calculation': True,            # ETA calculations
            'enhanced_pricing': True,           # Individual shipment pricing
            'charge_code_expiry': True,         # Expiry management
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for Australia Post credentials.

        Returns:
            JSON schema dictionary
        """
        return {
            'type': 'object',
            'properties': {
                'api_key': {
                    'type': 'string',
                    'title': _('API Key'),
                    'description': _('Your Australia Post API Key in UUID format from the Developer Portal'),
                    'required': True,
                    'secret': True,
                    'pattern': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    'placeholder': '601a4032-6dbd-46aa-9c6c-8c6dacca5e61'
                },
                'api_password': {
                    'type': 'string',
                    'title': _('API Password'),
                    'description': _('Password you set when generating your API Key'),
                    'required': True,
                    'secret': True,
                    'min_length': 6
                },
                'account_number': {
                    'type': 'string',
                    'title': _('Account Number'),
                    'description': _('Your charge account number. Australia Post: 10 digits (will be left-padded with zeros). StarTrack: 8 digits (no padding needed).'),
                    'required': True,
                    'pattern': r'^\d{8,10}$',
                    'placeholder': '0000123456 or 12345678'
                },
                'account_type': {
                    'type': 'string',
                    'title': _('Account Type'),
                    'enum': ['eparcel', 'startrack', 'same_day', 'on_demand'],
                    'default': 'eparcel',
                    'description': _('Select your account type for proper validation and feature support')
                },
                'environment': {
                    'type': 'string',
                    'title': _('Environment'),
                    'enum': ['test', 'production'],
                    'default': 'test',
                    'description': _('Use Test for development with sandbox credentials')
                }
            }
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate Australia Post credentials.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing

        Checks:
        - API key is UUID format
        - Account number is 8 or 10 digits
        - Password is provided
        - Account type is valid
        """
        required_fields = ['api_key', 'api_password', 'account_number']
        missing_fields = [f for f in required_fields if not credentials.get(f)]

        if missing_fields:
            raise ValueError(
                _("Missing required Australia Post credentials: %(fields)s") %
                {'fields': ', '.join(missing_fields)}
            )

        # Validate API key format (UUID)
        api_key = credentials.get('api_key', '')
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, api_key.lower()):
            raise ValueError(_("Australia Post API Key must be in UUID format"))

        # Validate API password length
        api_password = credentials.get('api_password', '')
        if len(api_password) < 6:
            raise ValueError(_("Australia Post API Password must be at least 6 characters"))

        # Validate account number format (8 or 10 digits)
        account_number = credentials.get('account_number', '')
        if not account_number.isdigit() or len(account_number) not in [8, 10]:
            raise ValueError(_("Australia Post Account Number must be 8 or 10 digits"))

        # Validate account type
        account_type = credentials.get('account_type', 'eparcel')
        valid_types = ['eparcel', 'startrack', 'same_day', 'on_demand']
        if account_type not in valid_types:
            raise ValueError(
                _("Account type must be one of: %(types)s") %
                {'types': ', '.join(valid_types)}
            )

        # Validate environment
        environment = credentials.get('environment', 'test')
        if environment not in ['test', 'production']:
            raise ValueError(_("Environment must be 'test' or 'production'"))

        logger.debug(f"Australia Post credentials validated successfully (account={account_number})")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with masked sensitive values
        """
        redacted = credentials.copy()

        # Mask API key - show last 12 chars (last segment of UUID)
        if 'api_key' in redacted:
            key = redacted['api_key']
            if len(key) > 12:
                redacted['api_key'] = f"***-***-***-{key[-12:]}"
            else:
                redacted['api_key'] = '***'

        # Completely hide password
        if 'api_password' in redacted:
            redacted['api_password'] = '***HIDDEN***'

        # Account number is semi-sensitive - show last 4 digits
        if 'account_number' in redacted:
            acct = redacted['account_number']
            redacted['account_number'] = f"***{acct[-4:]}" if len(acct) > 4 else '***'

        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Australia Post API.

        Makes a GET request to /shipping/v1/accounts/{account_number} to verify:
        - API key is valid
        - Password is correct
        - Account number exists and is accessible

        Returns:
            dict: Connection test results

        Raises:
            AustraliaPostAuthenticationError: If authentication fails
            AustraliaPostAccountError: If account not found

        Example:
            result = provider.test_connection()
            # {
            #     'success': True,
            #     'message': 'Connection successful',
            #     'account_info': {...}
            # }
        """
        try:
            logger.info("Testing connection to Australia Post API...")

            # Get account number from credentials
            account_number = self.credentials.get('account_number')
            if not account_number:
                raise AustraliaPostValidationError(
                    _("Account number is required for connection test"),
                    error_code="MISSING_ACCOUNT_NUMBER"
                )

            # Build endpoint with account number in path (required by API)
            endpoint = f'/shipping/{self.API_VERSION}/accounts/{account_number}'
            response = self._make_request('GET', endpoint, include_account=False)

            return {
                'success': True,
                'message': _('Connection successful'),
                'account_info': response
            }

        except AustraliaPostError as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'error_code': e.error_code
            }

    def get_rates(
        self,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        parcels: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get shipping rates from Australia Post.

        Makes POST request to /shipping/v1/prices/shipments.

        Args:
            origin: Origin address dict
            destination: Destination address dict
            parcels: List of parcel dicts
            options: Optional service options

        Returns:
            List of rate quotes

        Raises:
            AustraliaPostError: If rate request fails

        Example:
            rates = provider.get_rates(
                origin={'postal_code': '2000', 'country_code': 'AU'},
                destination={'postal_code': '3000', 'country_code': 'AU'},
                parcels=[{'weight_kg': 2.5, 'length_cm': 30, 'width_cm': 20, 'height_cm': 15}]
            )
            # [
            #     {
            #         'service_code': 'AUS_PARCEL_REGULAR',
            #         'service_name': 'Regular Parcel',
            #         'total_charge': 12.50,
            #         'currency': 'AUD',
            #         'delivery_days': 3
            #     }
            # ]
        """
        try:
            logger.info("Fetching rates from Australia Post...")

            # Build request payload
            payload = {
                'from': utils.format_address(origin),
                'to': utils.format_address(destination),
                'items': [utils.format_parcel(p) for p in parcels]
            }

            # Add options if provided
            if options:
                if options.get('service_code'):
                    payload['service_code'] = options['service_code']

            endpoint = f'/shipping/{self.API_VERSION}/prices/shipments'
            response = self._make_request('POST', endpoint, json=payload, include_account=True)

            # Parse response and return rates
            rates = self._parse_rates_response(response)

            logger.info(f"Retrieved {len(rates)} rate quotes")
            return rates

        except AustraliaPostError:
            raise
        except Exception as e:
            logger.error(f"Failed to get rates: {e}")
            raise AustraliaPostAPIError(
                _("Failed to retrieve rates: {error}").format(error=str(e)),
                error_code="RATE_REQUEST_FAILED"
            )

    def buy_label(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Purchase shipping label (two-step process).

        Step 1: POST /shipping/v1/shipments (create shipment)
        Step 2: POST /shipping/v1/labels with wait_for_label_url=true (synchronous)

        Args:
            shipment_data: Shipment information dict

        Returns:
            dict: Label information with URL and tracking number

        Raises:
            AustraliaPostShipmentError: If shipment creation fails
            AustraliaPostLabelError: If label generation fails

        Example:
            label = provider.buy_label({
                'origin': {...},
                'destination': {...},
                'parcels': [{...}],
                'service_code': 'AUS_PARCEL_EXPRESS'
            })
            # {
            #     'shipment_id': 'ship_123',
            #     'tracking_number': 'AA123456789AU',
            #     'label_url': 'https://...',
            #     'total_charge': 12.50
            # }
        """
        try:
            logger.info("Creating shipment...")

            # Step 1: Create shipment
            shipment = self._create_shipment(shipment_data)
            shipment_id = shipment.get('shipment_id')

            if not shipment_id:
                raise AustraliaPostShipmentError(
                    _("Shipment creation did not return shipment ID"),
                    error_code="MISSING_SHIPMENT_ID"
                )

            logger.info(f"Shipment created: {shipment_id}")

            # Step 2: Create labels (synchronous)
            labels = self._create_labels(shipment_id, synchronous=True)

            logger.info("Label generated successfully")

            return {
                'shipment_id': shipment_id,
                'tracking_number': shipment.get('tracking_number'),
                'label_url': labels.get('label_url'),
                'label_format': 'PDF',
                'total_charge': shipment.get('total_charge'),
                'currency': 'AUD'
            }

        except AustraliaPostError:
            raise
        except Exception as e:
            logger.error(f"Failed to buy label: {e}")
            raise AustraliaPostShipmentError(
                _("Failed to purchase label: {error}").format(error=str(e)),
                error_code="LABEL_PURCHASE_FAILED"
            )

    def _create_shipment(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create shipment (step 1 of label generation).

        POST /shipping/v1/shipments

        Args:
            shipment_data: Shipment information

        Returns:
            dict: Shipment response with shipment_id
        """
        payload = {
            'shipments': [
                {
                    'from': utils.format_address(shipment_data['origin']),
                    'to': utils.format_address(shipment_data['destination']),
                    'items': [utils.format_parcel(p) for p in shipment_data['parcels']],
                    'shipment_reference': shipment_data.get('reference', ''),
                    'customer_reference_1': shipment_data.get('customer_reference_1', ''),
                    'customer_reference_2': shipment_data.get('customer_reference_2', ''),
                }
            ]
        }

        # Add service code if provided
        if shipment_data.get('service_code'):
            payload['shipments'][0]['product_id'] = shipment_data['service_code']

        endpoint = f'/shipping/{self.API_VERSION}/shipments'
        response = self._make_request('POST', endpoint, json=payload, include_account=True)

        # Extract first shipment from response
        if 'shipments' in response and response['shipments']:
            return response['shipments'][0]

        raise AustraliaPostShipmentError(
            _("Invalid shipment response"),
            error_code="INVALID_SHIPMENT_RESPONSE"
        )

    def _create_labels(self, shipment_id: str, synchronous: bool = True) -> Dict[str, Any]:
        """
        Create labels for shipment (step 2 of label generation).

        POST /shipping/v1/labels

        Args:
            shipment_id: Shipment ID from step 1
            synchronous: Wait for label URL (True for <250 parcels)

        Returns:
            dict: Label response with label_url
        """
        payload = {
            'shipments': [
                {
                    'shipment_id': shipment_id
                }
            ],
            'preferences': {
                'format': 'PDF',
                'groups': []
            }
        }

        # Synchronous mode for <250 parcels (most common case)
        if synchronous:
            payload['wait_for_label_url'] = True

        endpoint = f'/shipping/{self.API_VERSION}/labels'
        response = self._make_request('POST', endpoint, json=payload, include_account=True)

        # If synchronous, label URL should be in response
        if synchronous:
            if 'labels' in response and response['labels']:
                label_info = response['labels'][0]
                return {
                    'label_url': label_info.get('url'),
                    'request_id': response.get('request_id')
                }

        # If asynchronous, need to poll for label
        request_id = response.get('request_id')
        if request_id:
            return self._wait_for_label(request_id)

        raise AustraliaPostLabelError(
            _("Label creation failed - no label URL or request ID"),
            error_code="LABEL_CREATION_FAILED"
        )

    def _wait_for_label(self, request_id: str, max_attempts: int = 30) -> Dict[str, Any]:
        """
        Poll for label URL (async label generation).

        GET /shipping/v1/labels/{request_id}

        Args:
            request_id: Label request ID
            max_attempts: Maximum polling attempts

        Returns:
            dict: Label information with URL
        """
        logger.info(f"Polling for label: {request_id}")

        for attempt in range(max_attempts):
            endpoint = f'/shipping/{self.API_VERSION}/labels/{request_id}'
            response = self._make_request('GET', endpoint, include_account=True)

            status = response.get('status')

            if status == 'COMPLETE':
                if 'labels' in response and response['labels']:
                    return {
                        'label_url': response['labels'][0].get('url'),
                        'request_id': request_id
                    }

            elif status == 'FAILED':
                raise AustraliaPostLabelError(
                    _("Label generation failed"),
                    error_code="LABEL_GENERATION_FAILED"
                )

            # Wait before next poll (2 seconds)
            time.sleep(2)

        raise AustraliaPostLabelError(
            _("Label generation timeout"),
            error_code="LABEL_TIMEOUT"
        )

    def void_label(self, shipment_id: str) -> Dict[str, Any]:
        """
        Void/cancel shipment and refund label.

        DELETE /shipping/v1/shipments/{shipment_id}

        Args:
            shipment_id: Shipment ID to void

        Returns:
            dict: Void result

        Raises:
            AustraliaPostShipmentError: If void fails

        Example:
            result = provider.void_label('ship_123')
            # {'success': True, 'message': 'Shipment voided'}
        """
        try:
            logger.info(f"Voiding shipment: {shipment_id}")

            endpoint = f'/shipping/{self.API_VERSION}/shipments/{shipment_id}'
            self._make_request('DELETE', endpoint, include_account=True)

            logger.info("Shipment voided successfully")

            return {
                'success': True,
                'message': _('Shipment voided successfully')
            }

        except AustraliaPostError:
            raise
        except Exception as e:
            logger.error(f"Failed to void shipment: {e}")
            raise AustraliaPostShipmentError(
                _("Failed to void shipment: {error}").format(error=str(e)),
                error_code="VOID_FAILED"
            )

    def cancel_label(self, tracking_number: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel a shipping label and request refund (base class interface).

        Note: Australia Post API requires shipment_id for cancellation, not tracking_number.
        This method is provided for base class compatibility but will raise an error unless
        you pass shipment_id as the tracking_number parameter.

        For direct cancellation, use void_label(shipment_id) instead.

        Args:
            tracking_number: In Australia Post's case, this should be the shipment_id
            reason: Optional cancellation reason (not used by Australia Post API)

        Returns:
            Dictionary with cancellation result:
            {
                'success': True,
                'refunded': True,
                'message': 'Shipment voided successfully'
            }

        Raises:
            ValueError: If tracking_number format is invalid
            AustraliaPostShipmentError: If cancellation fails

        Note:
            Australia Post API uses shipment IDs for voiding, not tracking numbers.
            If you have a tracking number, you need to look up the shipment ID first
            or store the shipment_id when the label was created.
        """
        # Australia Post API requires shipment_id, not tracking_number
        # The tracking number format is different from shipment_id
        # We'll pass through to void_label and let it handle the shipment_id
        logger.info(f"Cancel label called with identifier: {tracking_number}")

        result = self.void_label(shipment_id=tracking_number)

        # Adapt response to match base class format
        return {
            'success': result.get('success', False),
            'refunded': True,  # Australia Post voids and refunds
            'message': result.get('message', _('Label cancelled successfully'))
        }

    def get_tracking(self, tracking_numbers: List[str]) -> List[Dict[str, Any]]:
        """
        Get tracking information with rate limiting.

        GET /shipping/v1/track
        Rate limit: 10 requests per 60 seconds

        Args:
            tracking_numbers: List of tracking numbers

        Returns:
            List of tracking information

        Raises:
            AustraliaPostTrackingError: If tracking fails
            AustraliaPostRateLimitError: If rate limit exceeded

        Example:
            tracking = provider.get_tracking(['AA123456789AU'])
            # [
            #     {
            #         'tracking_number': 'AA123456789AU',
            #         'status': 'delivered',
            #         'events': [...]
            #     }
            # ]
        """
        try:
            # Apply rate limiting (10 req/60s)
            limiter = get_tracking_limiter()

            results = []

            for tracking_number in tracking_numbers:
                # Acquire rate limit token (will wait if limit reached)
                limiter.acquire()

                logger.info(f"Fetching tracking for: {tracking_number}")

                endpoint = f'/shipping/{self.API_VERSION}/track'
                params = {'tracking_id': tracking_number}

                response = self._make_request('GET', endpoint, params=params, include_account=False)

                # Parse tracking response
                tracking_info = self._parse_tracking_response(tracking_number, response)
                results.append(tracking_info)

            return results

        except AustraliaPostError:
            raise
        except Exception as e:
            logger.error(f"Failed to get tracking: {e}")
            raise AustraliaPostTrackingError(
                _("Failed to retrieve tracking: {error}").format(error=str(e)),
                error_code="TRACKING_FAILED"
            )

    # =========================================================================
    # v2.0.0 Order Management Methods
    # =========================================================================

    def create_order(
        self,
        shipment_ids: List[str],
        order_reference: Optional[str] = None,
        order_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an order from shipments.

        Args:
            shipment_ids: List of shipment IDs to include in order
            order_reference: Optional order reference
            order_metadata: Optional order metadata

        Returns:
            dict: Order creation response

        Raises:
            AustraliaPostOrderError: If order creation fails
            AustraliaPostValidationError: If >2,000 items

        Example:
            order = provider.create_order(
                shipment_ids=['ship_123', 'ship_124'],
                order_reference='ORDER-2025-001'
            )
        """
        account_number = self.credentials.get('account_number')
        return self.order_manager.create_order(
            account_number=account_number,
            shipment_ids=shipment_ids,
            order_reference=order_reference,
            order_metadata=order_metadata
        )

    def create_order_with_split(
        self,
        shipment_ids: List[str],
        order_reference_prefix: Optional[str] = None,
        order_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Create order(s) from shipments with automatic splitting if needed.

        Automatically splits into multiple orders if total items exceed 2,000.

        Args:
            shipment_ids: List of shipment IDs
            order_reference_prefix: Prefix for order references
            order_metadata: Metadata for all orders

        Returns:
            list: List of created orders

        Example:
            orders = provider.create_order_with_split(
                shipment_ids=[...],  # 3,500 total items
                order_reference_prefix='BATCH-2025-001'
            )
            # Returns: [
            #     {'order_id': 'ORD1', 'shipment_count': 120, ...},
            #     {'order_id': 'ORD2', 'shipment_count': 80, ...}
            # ]
        """
        account_number = self.credentials.get('account_number')
        return self.order_manager.create_order_with_split(
            account_number=account_number,
            shipment_ids=shipment_ids,
            order_reference_prefix=order_reference_prefix,
            order_metadata=order_metadata
        )

    def get_order(self, order_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Retrieve order details.

        Args:
            order_id: Order ID to retrieve
            use_cache: Use cached result if available

        Returns:
            dict: Order details

        Example:
            order = provider.get_order('order_123')
        """
        account_number = self.credentials.get('account_number')
        return self.order_manager.get_order(
            account_number=account_number,
            order_id=order_id,
            use_cache=use_cache
        )

    def get_order_summary(
        self,
        order_id: str,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Get order summary (manifest).

        Args:
            order_id: Order ID
            format: Output format ('json', 'pdf', 'csv')

        Returns:
            dict: Order summary/manifest

        Example:
            manifest = provider.get_order_summary('order_123', format='json')
        """
        account_number = self.credentials.get('account_number')
        return self.order_manager.get_order_summary(
            account_number=account_number,
            order_id=order_id,
            format=format
        )

    # =========================================================================
    # v2.0.0 Basket Management Methods
    # =========================================================================

    def add_to_basket(
        self,
        shipment_id: str,
        item_count: int,
        shipment_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add shipment to basket.

        Args:
            shipment_id: Shipment ID
            item_count: Number of items in shipment
            shipment_data: Optional shipment metadata

        Returns:
            dict: Basket status after addition

        Raises:
            AustraliaPostBasketError: If basket limit exceeded

        Example:
            status = provider.add_to_basket('ship_123', item_count=5)
        """
        return self.basket_manager.add_shipment(
            shipment_id=shipment_id,
            item_count=item_count,
            shipment_data=shipment_data
        )

    def remove_from_basket(self, shipment_id: str) -> Dict[str, Any]:
        """
        Remove shipment from basket.

        Args:
            shipment_id: Shipment ID to remove

        Returns:
            dict: Basket status after removal

        Example:
            status = provider.remove_from_basket('ship_123')
        """
        return self.basket_manager.remove_shipment(shipment_id)

    def clear_basket(self) -> Dict[str, Any]:
        """
        Clear all shipments from basket.

        Returns:
            dict: Empty basket status

        Example:
            status = provider.clear_basket()
        """
        return self.basket_manager.clear()

    def get_basket_status(self) -> Dict[str, Any]:
        """
        Get current basket status.

        Returns:
            dict: Basket status with item counts and shipment list

        Example:
            status = provider.get_basket_status()
            # {
            #     'total_items': 150,
            #     'total_shipments': 25,
            #     'max_size': 10000,
            #     'is_locked': False,
            #     'shipment_ids': [...]
            # }
        """
        return self.basket_manager.get_status()

    def get_basket_statistics(self) -> Dict[str, Any]:
        """
        Get detailed basket statistics.

        Returns:
            dict: Detailed basket statistics

        Example:
            stats = provider.get_basket_statistics()
        """
        return self.basket_manager.get_statistics()

    # =========================================================================
    # v2.0.0 Shipment Management Methods
    # =========================================================================

    def get_shipment(
        self,
        shipment_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve shipment details.

        Args:
            shipment_id: Shipment ID
            use_cache: Use cached result if available

        Returns:
            dict: Shipment details

        Example:
            shipment = provider.get_shipment('ship_123')
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.get_shipment(
            account_number=account_number,
            shipment_id=shipment_id,
            use_cache=use_cache
        )

    def get_shipments(
        self,
        status: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        reference: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List shipments with filtering and pagination.

        Args:
            status: Filter by status
            created_after: Filter by creation date (ISO format)
            created_before: Filter by creation date (ISO format)
            reference: Filter by reference
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            dict: Shipment list with pagination info

        Example:
            shipments = provider.get_shipments(
                status='created',
                limit=50
            )
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.get_shipments(
            account_number=account_number,
            status=status,
            created_after=created_after,
            created_before=created_before,
            reference=reference,
            limit=limit,
            offset=offset
        )

    def update_shipment(
        self,
        shipment_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update shipment details.

        Args:
            shipment_id: Shipment ID
            updates: Fields to update

        Returns:
            dict: Updated shipment

        Example:
            shipment = provider.update_shipment(
                'ship_123',
                {'shipment_reference': 'NEW-REF-001'}
            )
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.update_shipment(
            account_number=account_number,
            shipment_id=shipment_id,
            updates=updates
        )

    def delete_shipment(self, shipment_id: str) -> Dict[str, Any]:
        """
        Delete shipment.

        Args:
            shipment_id: Shipment ID to delete

        Returns:
            dict: Deletion confirmation

        Example:
            result = provider.delete_shipment('ship_123')
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.delete_shipment(
            account_number=account_number,
            shipment_id=shipment_id
        )

    def update_shipment_item(
        self,
        shipment_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update individual item in shipment.

        Args:
            shipment_id: Shipment ID
            item_id: Item ID to update
            updates: Item fields to update

        Returns:
            dict: Updated item

        Example:
            item = provider.update_shipment_item(
                'ship_123',
                'item_1',
                {'weight': 2.5}
            )
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.update_item(
            account_number=account_number,
            shipment_id=shipment_id,
            item_id=item_id,
            updates=updates
        )

    def delete_shipment_item(
        self,
        shipment_id: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        Delete individual item from shipment.

        Args:
            shipment_id: Shipment ID
            item_id: Item ID to delete

        Returns:
            dict: Deletion confirmation

        Example:
            result = provider.delete_shipment_item('ship_123', 'item_1')
        """
        account_number = self.credentials.get('account_number')
        return self.shipment_manager.delete_item(
            account_number=account_number,
            shipment_id=shipment_id,
            item_id=item_id
        )

    # =========================================================================
    # v2.0.0 Validation Services Methods
    # =========================================================================

    def validate_suburb(
        self,
        suburb: str,
        state: str,
        postcode: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Validate Australian suburb and postcode combination.

        Args:
            suburb: Suburb name
            state: State code (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
            postcode: 4-digit postcode
            use_cache: Use cached result if available

        Returns:
            dict: Validation result with suggestions if invalid

        Example:
            result = provider.validate_suburb('Sydney', 'NSW', '2000')
            # {
            #     'valid': True,
            #     'suburb': 'SYDNEY',
            #     'state': 'NSW',
            #     'postcode': '2000'
            # }
        """
        return self.validation_service.validate_suburb(
            suburb=suburb,
            state=state,
            postcode=postcode,
            use_cache=use_cache
        )

    def lookup_serviceability(
        self,
        address: Dict[str, str],
        service_code: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Check if address is serviceable.

        Args:
            address: Address dictionary
            service_code: Optional service code to check
            use_cache: Use cached result if available

        Returns:
            dict: Serviceability result

        Example:
            result = provider.lookup_serviceability(
                address={'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
                service_code='AUS_PARCEL_EXPRESS'
            )
        """
        return self.validation_service.lookup_serviceability(
            address=address,
            service_code=service_code,
            use_cache=use_cache
        )

    def validate_shipments(
        self,
        shipments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Pre-flight validation for shipment data.

        Args:
            shipments: List of shipment dictionaries

        Returns:
            dict: Validation results with errors and warnings

        Example:
            result = provider.validate_shipments([
                {'from': {...}, 'to': {...}, 'items': [...]}
            ])
        """
        account_number = self.credentials.get('account_number')
        return self.validation_service.validate_shipments(
            shipments=shipments,
            account_number=account_number
        )

    def validate_postcode_format(self, postcode: str) -> tuple:
        """
        Validate postcode format.

        Args:
            postcode: Postcode to validate

        Returns:
            tuple: (is_valid, message)

        Example:
            is_valid, msg = provider.validate_postcode_format('2000')
        """
        return self.validation_service.validate_postcode_format(postcode)

    def validate_state_code(self, state: str) -> tuple:
        """
        Validate state code.

        Args:
            state: State code to validate

        Returns:
            tuple: (is_valid, message)

        Example:
            is_valid, msg = provider.validate_state_code('NSW')
        """
        return self.validation_service.validate_state_code(state)

    # =========================================================================
    # v2.0.0 Enhanced Pricing Methods
    # =========================================================================

    def get_shipment_price(
        self,
        from_address: Dict[str, str],
        to_address: Dict[str, str],
        items: List[Dict[str, Any]],
        service_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed pricing for individual shipment.

        Args:
            from_address: Origin address
            to_address: Destination address
            items: List of items
            service_code: Optional service code

        Returns:
            dict: Detailed pricing with surcharges and taxes

        Example:
            price = provider.get_shipment_price(
                from_address={'suburb': 'Melbourne', 'state': 'VIC', 'postcode': '3000'},
                to_address={'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
                items=[{'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}]
            )
        """
        account_number = self.credentials.get('account_number')
        return self.pricing_service.get_shipment_price(
            account_number=account_number,
            from_address=from_address,
            to_address=to_address,
            items=items,
            service_code=service_code
        )

    def calculate_eta(
        self,
        from_postcode: str,
        to_postcode: str,
        service_code: str,
        ship_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate estimated delivery time.

        Args:
            from_postcode: Origin postcode
            to_postcode: Destination postcode
            service_code: Service code
            ship_date: Optional ship date (ISO format)

        Returns:
            dict: ETA information

        Example:
            eta = provider.calculate_eta(
                from_postcode='3000',
                to_postcode='2000',
                service_code='AUS_PARCEL_EXPRESS'
            )
        """
        return self.pricing_service.calculate_eta(
            from_postcode=from_postcode,
            to_postcode=to_postcode,
            service_code=service_code,
            ship_date=ship_date
        )

    def compare_service_prices(
        self,
        from_address: Dict[str, str],
        to_address: Dict[str, str],
        items: List[Dict[str, Any]],
        service_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Compare pricing across multiple services.

        Args:
            from_address: Origin address
            to_address: Destination address
            items: List of items
            service_codes: Optional list of service codes to compare

        Returns:
            list: Sorted list of price comparisons

        Example:
            comparisons = provider.compare_service_prices(
                from_address={...},
                to_address={...},
                items=[...]
            )
        """
        account_number = self.credentials.get('account_number')
        return self.pricing_service.compare_service_prices(
            account_number=account_number,
            from_address=from_address,
            to_address=to_address,
            items=items,
            service_codes=service_codes
        )

    # =========================================================================
    # v2.0.0 Product Features Methods
    # =========================================================================

    def add_authority_to_leave(
        self,
        shipment_data: Dict[str, Any],
        enabled: bool = True,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Authority To Leave feature to shipment.

        Args:
            shipment_data: Shipment data
            enabled: Enable ATL
            location: Optional specific location

        Returns:
            dict: Updated shipment data

        Example:
            shipment = provider.add_authority_to_leave(
                shipment_data,
                enabled=True,
                location='Front porch'
            )
        """
        return self.features.add_authority_to_leave(
            shipment_data=shipment_data,
            enabled=enabled,
            location=location
        )

    def add_safe_drop(
        self,
        shipment_data: Dict[str, Any],
        enabled: bool = True,
        instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Safe Drop feature to shipment.

        Args:
            shipment_data: Shipment data
            enabled: Enable Safe Drop
            instructions: Optional instructions

        Returns:
            dict: Updated shipment data

        Example:
            shipment = provider.add_safe_drop(
                shipment_data,
                enabled=True,
                instructions='Leave in mailbox'
            )
        """
        return self.features.add_safe_drop(
            shipment_data=shipment_data,
            enabled=enabled,
            instructions=instructions
        )

    def add_signature_required(
        self,
        shipment_data: Dict[str, Any],
        required: bool = True,
        signature_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add signature requirement to shipment.

        Args:
            shipment_data: Shipment data
            required: Require signature
            signature_type: Type ('standard', 'adult')

        Returns:
            dict: Updated shipment data

        Example:
            shipment = provider.add_signature_required(
                shipment_data,
                required=True,
                signature_type='adult'
            )
        """
        return self.features.add_signature_required(
            shipment_data=shipment_data,
            required=required,
            signature_type=signature_type
        )

    def add_dangerous_goods(
        self,
        shipment_data: Dict[str, Any],
        dg_class: str,
        un_number: Optional[str] = None,
        packing_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add dangerous goods declaration to shipment.

        Args:
            shipment_data: Shipment data
            dg_class: DG class (e.g., '3', '4.1', '9')
            un_number: UN number (e.g., 'UN1090')
            packing_group: Packing group ('I', 'II', 'III')

        Returns:
            dict: Updated shipment data

        Example:
            shipment = provider.add_dangerous_goods(
                shipment_data,
                dg_class='3',
                un_number='UN1090',
                packing_group='II'
            )
        """
        return self.features.add_dangerous_goods(
            shipment_data=shipment_data,
            dg_class=dg_class,
            un_number=un_number,
            packing_group=packing_group
        )

    def add_sscc_barcode(
        self,
        shipment_data: Dict[str, Any],
        sscc: Optional[str] = None,
        auto_generate: bool = False
    ) -> Dict[str, Any]:
        """
        Add SSCC barcode to shipment.

        Args:
            shipment_data: Shipment data
            sscc: 18-digit SSCC barcode
            auto_generate: Auto-generate SSCC

        Returns:
            dict: Updated shipment data

        Example:
            shipment = provider.add_sscc_barcode(
                shipment_data,
                auto_generate=True
            )
        """
        return self.features.add_sscc_barcode(
            shipment_data=shipment_data,
            sscc=sscc,
            auto_generate=auto_generate
        )

    def validate_features_for_product(
        self,
        product_code: str,
        features: Dict[str, Any]
    ) -> tuple:
        """
        Validate features are compatible with product.

        Args:
            product_code: Product code
            features: Features dictionary

        Returns:
            tuple: (is_valid, list of errors)

        Example:
            is_valid, errors = provider.validate_features_for_product(
                'AUS_PARCEL_EXPRESS',
                {'authority_to_leave': True, 'safe_drop': True}
            )
        """
        return self.features.validate_features_for_product(
            product_code=product_code,
            features=features
        )

    # =========================================================================
    # v2.0.0 Pickup Services Methods
    # =========================================================================

    def schedule_pickup(
        self,
        pickup_address: Dict[str, str],
        pickup_date: str,
        time_slot: str = 'all_day',
        shipment_ids: Optional[List[str]] = None,
        instructions: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule adhoc pickup.

        Args:
            pickup_address: Pickup location address
            pickup_date: Pickup date (YYYY-MM-DD)
            time_slot: Time slot ('morning', 'afternoon', 'all_day')
            shipment_ids: Optional list of shipment IDs
            instructions: Optional pickup instructions
            contact_name: Optional contact name
            contact_phone: Optional contact phone

        Returns:
            dict: Pickup confirmation

        Example:
            pickup = provider.schedule_pickup(
                pickup_address={'street': '123 Main St', 'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
                pickup_date='2025-11-08',
                time_slot='morning',
                shipment_ids=['ship_123', 'ship_124']
            )
        """
        account_number = self.credentials.get('account_number')
        return self.pickup_service.create_adhoc_pickup(
            account_number=account_number,
            pickup_address=pickup_address,
            pickup_date=pickup_date,
            time_slot=time_slot,
            shipment_ids=shipment_ids,
            instructions=instructions,
            contact_name=contact_name,
            contact_phone=contact_phone
        )

    def get_pickup(self, pickup_id: str) -> Dict[str, Any]:
        """
        Retrieve pickup details.

        Args:
            pickup_id: Pickup ID

        Returns:
            dict: Pickup details

        Example:
            pickup = provider.get_pickup('pickup_123')
        """
        account_number = self.credentials.get('account_number')
        return self.pickup_service.get_pickup(
            account_number=account_number,
            pickup_id=pickup_id
        )

    def cancel_pickup(self, pickup_id: str) -> Dict[str, Any]:
        """
        Cancel scheduled pickup.

        Args:
            pickup_id: Pickup ID to cancel

        Returns:
            dict: Cancellation confirmation

        Example:
            result = provider.cancel_pickup('pickup_123')
        """
        account_number = self.credentials.get('account_number')
        return self.pickup_service.cancel_pickup(
            account_number=account_number,
            pickup_id=pickup_id
        )

    def get_available_time_slots(self, pickup_date: str) -> List[Dict[str, str]]:
        """
        Get available pickup time slots for date.

        Args:
            pickup_date: Pickup date (YYYY-MM-DD)

        Returns:
            list: Available time slots

        Example:
            slots = provider.get_available_time_slots('2025-11-08')
        """
        return self.pickup_service.get_available_time_slots(pickup_date)

    # =========================================================================
    # Internal Helper Methods
    # =========================================================================

    def _parse_rates_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse rates response into standardized format."""
        rates = []

        if 'items' in response:
            for item in response['items']:
                for product in item.get('products', []):
                    rate = {
                        'service_code': product.get('product_id'),
                        'service_name': utils.get_product_name(product.get('product_id', '')),
                        'total_charge': Decimal(str(product.get('price', 0))),
                        'currency': 'AUD',
                        'delivery_days': product.get('delivery_time')
                    }
                    rates.append(rate)

        return rates

    def _parse_tracking_response(
        self,
        tracking_number: str,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse tracking response into standardized format."""
        tracking_info = {
            'tracking_number': tracking_number,
            'status': 'unknown',
            'events': []
        }

        if 'tracking_results' in response:
            results = response['tracking_results']
            if results:
                result = results[0]

                # Map status
                status_desc = result.get('status', '')
                tracking_info['status'] = utils.map_tracking_status(status_desc)

                # Parse events
                events = result.get('trackable_items', [])
                for event in events:
                    tracking_info['events'].append({
                        'timestamp': utils.parse_auspost_datetime(event.get('date_time')),
                        'description': event.get('description'),
                        'location': event.get('location'),
                        'status': utils.map_tracking_status(event.get('description', ''))
                    })

        return tracking_info

    @retry_with_backoff()
    def _make_request(
        self,
        method: str,
        endpoint: str,
        include_account: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Australia Post API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            include_account: Include Account-Number header
            **kwargs: Additional request arguments

        Returns:
            dict: Response JSON data

        Raises:
            AustraliaPostError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Get authentication headers
        headers = self.auth_client.get_headers(include_account=include_account)

        # Merge with any provided headers
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        try:
            logger.debug(f"{method} {url}")

            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=30,
                **kwargs
            )

            # Check for successful response
            if response.status_code in [200, 201]:
                # Parse JSON response
                if response.content:
                    return response.json()
                return {}

            # Handle error response
            error_data = None
            try:
                error_data = response.json()
            except Exception:
                pass

            exception = create_exception_from_response(
                response.status_code,
                error_data,
                default_message=_("Australia Post API error")
            )

            logger.error(
                f"API request failed: {exception.message} "
                f"(status: {response.status_code})"
            )
            raise exception

        except requests.exceptions.RequestException as e:
            exception = handle_request_exception(e, f"{method} {endpoint}")
            logger.error(f"Request failed: {exception.message}")
            raise exception

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify Australia Post webhook signature.

        NOTE: Australia Post Shipping API does not support webhooks as of v2.0.0.
        Use polling with get_tracking() instead.

        Args:
            payload: Raw request body
            signature: Signature header
            **kwargs: Additional headers

        Returns:
            False (webhooks not supported)

        Raises:
            NotImplementedError: Australia Post does not support webhooks
        """
        raise NotImplementedError(_("Australia Post Shipping API does not support webhooks. Use polling instead."))

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Australia Post webhook event.

        NOTE: Australia Post Shipping API does not support webhooks as of v2.0.0.
        Use polling with get_tracking() instead.

        Args:
            event_type: Event type
            payload: Webhook payload

        Returns:
            Processed webhook data

        Raises:
            NotImplementedError: Australia Post does not support webhooks
        """
        raise NotImplementedError(_("Australia Post Shipping API does not support webhooks. Use polling instead."))

    def __del__(self):
        """Cleanup session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()
