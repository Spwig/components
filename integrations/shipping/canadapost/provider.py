"""
Canada Post Shipping Provider

XML-based REST API authenticated shipping provider for Canada Post.
Implements rate calculation, label generation, tracking, and supports both
contract and non-contract customer types.

Author: Spwig
Version: 1.0.0
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import requests

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from shipping.providers.base import ProviderBase
from . import xml_builder, xml_parser, utils
from .auth import create_auth_client, CanadaPostAuthClient
from .exceptions import (
    CanadaPostError,
    CanadaPostAuthenticationError,
    CanadaPostValidationError,
    CanadaPostShipmentError,
    CanadaPostTrackingError,
    CanadaPostServiceUnavailableError,
    CanadaPostAPIError,
    create_exception_from_response,
)
from .retry import retry_with_backoff, RetryConfig


logger = logging.getLogger(__name__)


class CanadaPostProvider(ProviderBase):
    """
    Canada Post shipping provider implementation.

    Provides rate calculation, label generation, and tracking
    via Canada Post REST API with XML request/response format and
    Basic Authentication.

    Capabilities:
        - Rate quotes (Domestic, USA, International)
        - Shipping label generation (PDF format)
        - Real-time tracking
        - International shipping with customs
        - Dual customer type support (Contract/Non-Contract)
        - Insurance and signature options
        - Return labels

    API Documentation: https://www.canadapost-postescanada.ca/information/app/drc/home

    Customer Types:
        - Contract: Has customer_number + contract_id, full service access
        - Non-Contract: Has customer_number only, limited services

    Notes:
        - Uses XML format (not JSON)
        - Basic Authentication (username/password)
        - Labels retrieved via artifact href links
        - Manifest system for contract customers
    """

    # Provider identification
    provider_key = 'canadapost'
    provider_name = _('Canada Post')

    # API URLs
    SANDBOX_BASE_URL = 'https://ct.soa-gw.canadapost.ca'
    PRODUCTION_BASE_URL = 'https://soa-gw.canadapost.ca'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Canada Post provider.

        Args:
            credentials: Dictionary containing:
                - username: Canada Post API username (API key)
                - password: Canada Post API password (API secret)
                - customer_number: 10-digit customer number
                - contract_id: Optional contract ID (for contract customers)
                - environment: 'test' or 'production'
            config: Optional configuration dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        # Initialize parent class (validates credentials)
        super().__init__(credentials, config)

        # Set API base URL based on environment
        environment = credentials.get('environment', 'test')
        self.base_url = (
            self.PRODUCTION_BASE_URL if environment == 'production'
            else self.SANDBOX_BASE_URL
        )

        # Store customer information
        self.customer_number = credentials.get('customer_number', '').strip()
        self.contract_id = credentials.get('contract_id', '').strip() if credentials.get('contract_id') else None
        self.mobo = credentials.get('mobo', '').strip() if credentials.get('mobo') else self.customer_number
        self.environment = environment

        # Detect customer type
        self.customer_type = utils.detect_customer_type(self.customer_number, self.contract_id)

        # Create auth client
        self.auth_client: CanadaPostAuthClient = create_auth_client(credentials)

        logger.info(f"Canada Post provider initialized (environment={environment}, type={self.customer_type})")

    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Return Canada Post provider capabilities.

        Returns:
            Dictionary of supported features
        """
        return {
            'rates': True,              # Rate calculation
            'labels': True,             # Label generation
            'tracking': True,           # Shipment tracking
            'international': True,      # International shipping
            'returns': True,            # Return labels supported
            'pickup': False,            # Pickup scheduling (deferred)
            'insurance': True,          # Insurance via COV option
            'signature': True,          # Signature via SO option
            'manifests': self.customer_type == 'contract',  # Contract customers only
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for Canada Post credentials.

        Returns:
            JSON schema dictionary
        """
        return {
            'type': 'object',
            'properties': {
                'username': {
                    'type': 'string',
                    'title': _('API Username'),
                    'description': _('Your Canada Post API username (API key) from the Developer Portal'),
                    'required': True,
                    'secret': True,
                    'min_length': 8
                },
                'password': {
                    'type': 'string',
                    'title': _('API Password'),
                    'description': _('Your Canada Post API password (API secret) from the Developer Portal'),
                    'required': True,
                    'secret': True,
                    'min_length': 8
                },
                'customer_number': {
                    'type': 'string',
                    'title': _('Customer Number'),
                    'description': _('Your 10-digit Canada Post customer number'),
                    'required': True,
                    'pattern': r'^\d{10}$'
                },
                'contract_id': {
                    'type': 'string',
                    'title': _('Contract ID'),
                    'description': _('Your Canada Post contract ID (required for contract customers, leave empty for non-contract)'),
                    'required': False,
                },
                'mobo': {
                    'type': 'string',
                    'title': _('MOBO Number'),
                    'description': _('Mailed On Behalf Of number (optional, defaults to customer number)'),
                    'required': False,
                },
                'environment': {
                    'type': 'string',
                    'title': _('Environment'),
                    'enum': ['test', 'production'],
                    'default': 'test',
                    'description': _('API environment to use. Use test for testing, production for live shipping.')
                }
            }
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate Canada Post credentials.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing
        """
        required_fields = ['username', 'password', 'customer_number']
        missing_fields = [f for f in required_fields if not credentials.get(f)]

        if missing_fields:
            raise ValueError(
                _("Missing required Canada Post credentials: %(fields)s") %
                {'fields': ', '.join(missing_fields)}
            )

        # Validate username/password length
        username = credentials.get('username', '')
        if len(username) < 8:
            raise ValueError(_("Canada Post API username must be at least 8 characters"))

        password = credentials.get('password', '')
        if len(password) < 8:
            raise ValueError(_("Canada Post API password must be at least 8 characters"))

        # Validate customer number format (10 digits)
        customer_number = credentials.get('customer_number', '')
        if not utils.validate_customer_number(customer_number):
            raise ValueError(_("Canada Post customer number must be exactly 10 digits"))

        # Validate environment
        environment = credentials.get('environment', 'test')
        if environment not in ['test', 'production']:
            raise ValueError(_("Environment must be 'test' or 'production'"))

        logger.debug(f"Canada Post credentials validated successfully (environment={environment})")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with masked sensitive values
        """
        redacted = credentials.copy()

        if 'username' in redacted:
            username = redacted['username']
            redacted['username'] = f"***{username[-4:]}" if len(username) > 4 else '***'

        if 'password' in redacted:
            redacted['password'] = '***HIDDEN***'

        # Customer number is semi-sensitive - show last 4 digits
        if 'customer_number' in redacted:
            cust_num = redacted['customer_number']
            redacted['customer_number'] = f"******{cust_num[-4:]}" if len(cust_num) > 4 else '***'

        return redacted

    def _handle_api_error(self, response: requests.Response, context: str = "API call") -> None:
        """
        Handle Canada Post API error responses.

        Parses XML error response and raises appropriate exception.

        Args:
            response: HTTP response from Canada Post API
            context: Description of what operation failed (for logging)

        Raises:
            Various CanadaPostError subclasses based on error type
        """
        status_code = response.status_code

        # Create exception from response (parses XML error)
        exception = create_exception_from_response(
            status_code,
            response,
            default_message=f"{context} failed: HTTP {status_code}"
        )

        # Log error details
        logger.error(
            f"Canada Post API error in {context}: "
            f"code={exception.error_code}, message={exception.message}, "
            f"status={status_code}"
        )

        raise exception

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        context: str = "API request",
        timeout: int = 30,
        retry: bool = True,
        content_type: Optional[str] = None,
        accept: Optional[str] = None,
        expect_binary: bool = False,
    ) -> Any:
        """
        Make an authenticated API request to Canada Post with error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            data: XML request data (for POST)
            context: Description for logging
            timeout: Request timeout in seconds
            retry: Whether to retry on transient failures
            content_type: Content-Type header (for POST requests)
            accept: Accept header
            expect_binary: If True, return raw binary response

        Returns:
            Parsed XML string or binary data if expect_binary=True

        Raises:
            Various CanadaPostError subclasses based on error type
        """
        url = f"{self.base_url}{endpoint}"

        # Get auth headers
        headers = self.auth_client.get_headers(content_type=content_type, accept=accept)

        # Log request (redact sensitive data)
        logger.info(f"Canada Post {method} {endpoint} - {context}")
        if data and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Request XML: {data[:500]}...")  # Truncate for logging

        # Define request function for retry decorator
        def make_request():
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    data=data.encode('utf-8') if data else None,
                    headers=headers,
                    timeout=timeout
                )

                # Check for errors
                if response.status_code >= 400:
                    self._handle_api_error(response, context)

                # Return raw binary for PDF artifacts
                if expect_binary:
                    logger.info(f"Canada Post {method} {endpoint} - {context} succeeded (binary)")
                    return response.content

                # Return text/XML response
                result = response.text
                logger.info(f"Canada Post {method} {endpoint} - {context} succeeded")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Response XML: {result[:500]}...")  # Truncate

                return result

            except requests.exceptions.Timeout:
                logger.error(f"{context} timed out after {timeout}s")
                raise CanadaPostServiceUnavailableError(f"{context} timed out")

            except requests.exceptions.ConnectionError as e:
                logger.error(f"{context} connection error: {e}")
                raise CanadaPostServiceUnavailableError(f"{context} connection failed: {e}")

            except requests.exceptions.RequestException as e:
                logger.error(f"{context} request error: {e}")
                raise CanadaPostAPIError(f"{context} failed: {e}")

        # Execute with or without retry
        if retry:
            # Apply retry decorator
            @retry_with_backoff(config=RetryConfig(max_attempts=3))
            def retry_wrapper():
                return make_request()

            return retry_wrapper()
        else:
            return make_request()

    def test_connection(self) -> Dict[str, Any]:
        """
        Test Canada Post API connection and credentials.

        Attempts a simple rate request to verify credentials work.

        Returns:
            Dictionary with test results
        """
        logger.info("Testing Canada Post API connection")

        try:
            # Build simple rate request
            xml_data = xml_builder.build_rate_request(
                origin_postal_code='K1A0B1',
                destination={'country': 'CA', 'postal_code': 'M5H2N2'},
                parcel={'weight': 1.0, 'length': 10.0, 'width': 10.0, 'height': 10.0},
                customer_number=self.customer_number,
                contract_id=self.contract_id
            )

            # Make test request
            response = self._make_api_request(
                method='POST',
                endpoint='/rs/ship/price',
                data=xml_data,
                context='Testing connection',
                content_type='application/vnd.cpc.ship.rate-v4+xml',
                accept='application/vnd.cpc.ship.rate-v4+xml',
                retry=False
            )

            # If we got here, connection successful
            logger.info("Canada Post connection test successful")

            return {
                'success': True,
                'message': _('Connection successful'),
                'details': {
                    'provider': 'Canada Post',
                    'environment': self.environment,
                    'customer_type': self.customer_type,
                    'customer_number': f"******{self.customer_number[-4:]}",
                }
            }

        except (CanadaPostAuthenticationError, CanadaPostValidationError) as e:
            # Invalid credentials or validation error
            logger.error(f"Canada Post connection test failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'authentication'}
            }

        except CanadaPostServiceUnavailableError as e:
            # Service unavailable
            logger.error(f"Canada Post connection test failed - service unavailable: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'service_unavailable'}
            }

        except CanadaPostError as e:
            # Other Canada Post errors
            logger.error(f"Canada Post connection test failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'canadapost_error'}
            }

        except Exception as e:
            # Unexpected error
            logger.error(f"Canada Post connection test failed with unexpected error: {e}", exc_info=True)
            return {
                'success': False,
                'message': _('Unexpected error: %(error)s') % {'error': str(e)},
                'details': {'error_type': 'unexpected'}
            }

    def get_rates(
        self,
        origin: Dict[str, str],
        destination: Dict[str, str],
        parcels: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Canada Post shipping rates.

        Args:
            origin: Origin address with postal_code
            destination: Destination address with country and postal_code
            parcels: List of parcels (uses first parcel)
            options: Optional shipping options

        Returns:
            List of rate dictionaries sorted by price

        Raises:
            CanadaPostValidationError: If parameters are invalid
            CanadaPostAuthenticationError: If authentication fails
            CanadaPostServiceUnavailableError: If service is unavailable
            CanadaPostAPIError: For other API errors
        """
        logger.info(f"Getting Canada Post rates: {origin.get('country', 'CA')} -> {destination.get('country', 'CA')}")

        # Get first parcel and format for API
        parcel = parcels[0] if parcels else {}
        formatted_parcel = utils.format_parcel_for_api(parcel)

        # Format origin postal code
        origin_postal = utils.format_canadian_postal_code(origin.get('postal_code', ''))

        # Build request XML
        xml_data = xml_builder.build_rate_request(
            origin_postal_code=origin_postal,
            destination=destination,
            parcel=formatted_parcel,
            customer_number=self.customer_number,
            contract_id=self.contract_id
        )

        # Make API request
        response_xml = self._make_api_request(
            method='POST',
            endpoint='/rs/ship/price',
            data=xml_data,
            context='Getting rates',
            content_type='application/vnd.cpc.ship.rate-v4+xml',
            accept='application/vnd.cpc.ship.rate-v4+xml',
            retry=True
        )

        # Parse response
        rates = xml_parser.parse_rate_response(response_xml)

        logger.info(f"Retrieved {len(rates)} Canada Post rates")
        return rates

    def buy_label(
        self,
        shipment_id: str,
        rate: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Purchase Canada Post shipping label.

        Two-step process:
        1. POST shipment creation (returns shipment-id and artifact links)
        2. GET label artifact via href link

        Args:
            shipment_id: Internal shipment ID
            rate: Selected rate from get_rates()
            options: Required shipping options:
                {
                    'origin': {...},  # Origin address
                    'destination': {...},  # Destination address
                    'parcels': [...],  # Parcel list
                    'sender_name': 'Company Name',
                    'sender_company': 'ACME Corp',
                    'sender_phone': '613-555-1234',
                    'recipient_name': 'John Doe',
                    'recipient_phone': '416-555-5678',
                    'options': [{'code': 'SO'}, {'code': 'COV', 'amount': '500'}],
                    'customs': {...}  # For international shipments
                }

        Returns:
            Label information dictionary

        Raises:
            CanadaPostValidationError: If required options are missing
            CanadaPostShipmentError: If shipment creation fails
        """
        logger.info(f"Purchasing Canada Post label for shipment {shipment_id}")

        # Validate required options
        if not options:
            raise CanadaPostValidationError(_("Options are required for label purchase"))

        required_fields = ['origin', 'destination', 'parcels', 'sender_name', 'sender_phone', 'recipient_name']
        missing = [f for f in required_fields if f not in options]
        if missing:
            raise CanadaPostValidationError(_("Missing required options: %(fields)s") % {'fields': ', '.join(missing)})

        # Build sender and recipient addresses
        sender = self._build_address(options['origin'], options)
        recipient = self._build_address(options['destination'], options, is_recipient=True)

        # Format parcel
        parcel = options['parcels'][0] if options['parcels'] else {}
        formatted_parcel = utils.format_parcel_for_api(parcel)

        # Get service code
        service_code = rate.get('service_code', 'DOM.RP')

        # Get shipping options
        shipping_options = options.get('options', [])

        # Get customs data for international shipments
        customs = options.get('customs')

        # Build shipment request XML
        xml_data = xml_builder.build_shipment_request(
            sender=sender,
            recipient=recipient,
            parcel=formatted_parcel,
            service_code=service_code,
            options=shipping_options,
            customer_number=self.customer_number,
            mobo=self.mobo,
            group_id_or_transmit='transmit',
            customs=customs
        )

        # Determine endpoint based on customer type
        if self.customer_type == 'contract':
            endpoint = f"/rs/{self.customer_number}/{self.mobo}/shipment"
            content_type = 'application/vnd.cpc.shipment-v8+xml'
            accept = 'application/vnd.cpc.shipment-v8+xml'
        else:
            endpoint = f"/rs/{self.customer_number}/ncshipment"
            content_type = 'application/vnd.cpc.ncshipment-v4+xml'
            accept = 'application/vnd.cpc.ncshipment-v4+xml'

        # Create shipment
        response_xml = self._make_api_request(
            method='POST',
            endpoint=endpoint,
            data=xml_data,
            context='Creating shipment',
            content_type=content_type,
            accept=accept,
            timeout=60,
            retry=True
        )

        # Parse shipment response
        shipment_info = xml_parser.parse_shipment_response(response_xml)

        # Get label artifact
        label_href = shipment_info.get('label_href')
        if not label_href:
            raise CanadaPostShipmentError(_("No label link in shipment response"))

        # Download label PDF
        label_pdf = self._make_api_request(
            method='GET',
            endpoint=label_href.replace(self.base_url, ''),
            context='Downloading label',
            accept='application/pdf',
            expect_binary=True,
            retry=True
        )

        # Build label info response
        import base64
        label_base64 = base64.b64encode(label_pdf).decode('utf-8')
        label_url = f"data:application/pdf;base64,{label_base64}"

        result = {
            'tracking_number': shipment_info['tracking_number'],
            'label_url': label_url,
            'label_format': 'PDF',
            'cost': rate.get('rate', Decimal('0.00')),
            'currency': 'CAD',
            'carrier': 'Canada Post',
            'service': rate.get('service_name', service_code),
            'external_shipment_id': f"canadapost_{shipment_info['shipment_id']}",
            'created_at': timezone.now()
        }

        logger.info(f"Successfully created Canada Post label: {result['tracking_number']}")
        return result

    def _build_address(self, address: Dict[str, str], options: Dict[str, Any], is_recipient: bool = False) -> Dict[str, str]:
        """
        Build address dictionary for shipment request.

        Args:
            address: Platform address dictionary
            options: Full options dictionary with name/phone
            is_recipient: True for recipient, False for sender

        Returns:
            Address dictionary formatted for XML builder
        """
        prefix = 'recipient_' if is_recipient else 'sender_'

        return {
            'name': options.get(f'{prefix}name', ''),
            'company': options.get(f'{prefix}company', ''),
            'phone': options.get(f'{prefix}phone', ''),
            'address_line_1': address.get('address1', address.get('street', '')),
            'address_line_2': address.get('address2', ''),
            'city': address.get('city', ''),
            'province': address.get('state', address.get('province', '')),
            'postal_code': address.get('postal_code', address.get('zip', '')),
            'country': address.get('country', 'CA'),
        }

    def cancel_label(self, tracking_number: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel/void Canada Post shipping label.

        Note: Requires shipment ID, not tracking number. Must be called before
        shipment is manifested.

        Args:
            tracking_number: Tracking number (actually need shipment_id)
            reason: Optional cancellation reason

        Returns:
            Cancellation result dictionary

        Raises:
            NotImplementedError: Void requires shipment ID mapping
        """
        raise NotImplementedError(
            _("Label cancellation requires shipment ID. "
              "Store shipment_id from buy_label response for void operations.")
        )

    def get_tracking(self, tracking_number: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get Canada Post tracking information.

        Args:
            tracking_number: Canada Post tracking number (tracking PIN)
            force_refresh: If True, bypass cache

        Returns:
            Dictionary with tracking information

        Raises:
            CanadaPostTrackingError: If tracking lookup fails
            CanadaPostValidationError: If tracking number invalid
        """
        logger.info(f"Fetching Canada Post tracking: {tracking_number}")

        # Clean tracking number
        tracking_clean = tracking_number.strip().replace(' ', '').replace('-', '')

        if not tracking_clean:
            raise CanadaPostValidationError(_("Invalid tracking number"))

        # Make tracking request
        endpoint = f"/vis/track/pin/{tracking_clean}/summary"

        try:
            response_xml = self._make_api_request(
                method='GET',
                endpoint=endpoint,
                context=f'Getting tracking for {tracking_clean}',
                accept='application/vnd.cpc.track+xml',
                retry=True
            )

            # Parse tracking response
            tracking_info = xml_parser.parse_tracking_response(response_xml)

            logger.info(f"Fetched tracking data for {tracking_clean} (status={tracking_info['status']})")
            return tracking_info

        except CanadaPostError:
            raise
        except Exception as e:
            raise CanadaPostTrackingError(
                _("Failed to fetch tracking information: %(error)s") % {'error': str(e)}
            )
