"""
USPS Shipping Provider

OAuth 2.0 authenticated shipping provider for USPS Web Tools API.
Implements rate calculation, label generation, and tracking.

Author: Spwig
Version: 1.0.0
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from shipping.providers.base import ProviderBase
from shipping.providers.usps.auth import create_oauth_client, USPSOAuthClient
from shipping.providers.usps import utils, documents
from shipping.providers.usps.exceptions import (
    USPSError,
    USPSAuthenticationError,
    USPSAuthorizationError,
    USPSValidationError,
    USPSRateLimitError,
    USPSServiceUnavailableError,
    USPSPaymentError,
    USPSShipmentError,
    USPSTrackingError,
    USPSAddressError,
    USPSAPIError,
    create_exception_from_response,
    handle_request_exception,
)
from shipping.providers.usps.retry import retry_with_backoff, RetryConfig
import requests


logger = logging.getLogger(__name__)


class USPSProvider(ProviderBase):
    """
    USPS shipping provider implementation.

    Provides rate calculation, label generation, and tracking
    via USPS Web Tools REST API with OAuth 2.0 authentication.

    Capabilities:
        - Rate quotes (Ground Advantage, Priority, Express)
        - Shipping label generation (PDF format, multipart response)
        - Real-time tracking with numeric tracking numbers
        - Domestic shipping only (v1.0.0)
        - Insurance support via extra services
        - Signature confirmation via extra services

    API Documentation: https://developer.usps.com/

    Notes:
        - OAuth tokens valid for 8 hours
        - Labels require payment authorization token for actual use
        - Tracking uses POST method (not GET)
        - Status uses text descriptions (not codes)
        - Processing category auto-determined from dimensions
    """

    # Provider identification
    provider_key = 'usps'
    provider_name = _('USPS')

    # API URLs
    SANDBOX_BASE_URL = 'https://apis-tem.usps.com'
    PRODUCTION_BASE_URL = 'https://apis.usps.com'

    # API version
    API_VERSION = 'v3'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize USPS provider.

        Args:
            credentials: Dictionary containing:
                - consumer_key: USPS API Consumer Key (Client ID)
                - consumer_secret: USPS API Consumer Secret (Client Secret)
                - environment: 'test' or 'production'
                - payment_account_number: Optional payment account (required for labels)
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

        # Store payment account number (required for label purchase)
        self.payment_account_number = credentials.get('payment_account_number')
        self.environment = environment

        # Create OAuth client
        self.oauth_client: USPSOAuthClient = create_oauth_client(credentials)

        logger.info(f"USPS provider initialized (environment={environment})")

    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Return USPS provider capabilities.

        Returns:
            Dictionary of supported features
        """
        return {
            'rates': True,              # Rate calculation
            'labels': True,             # Label generation (requires payment token)
            'tracking': True,           # Shipment tracking
            'international': False,     # Domestic only (v1.0.0)
            'returns': True,            # Return labels supported
            'pickup': False,            # Pickup scheduling (deferred to v1.1.0)
            'insurance': True,          # Insurance via extra services
            'signature': True,          # Signature via extra services
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for USPS credentials.

        Returns:
            JSON schema dictionary
        """
        return {
            'type': 'object',
            'properties': {
                'consumer_key': {
                    'type': 'string',
                    'title': _('Consumer Key'),
                    'description': _('Your USPS API Consumer Key (Client ID) from the USPS Developer Portal'),
                    'required': True,
                    'secret': True,
                    'min_length': 20
                },
                'consumer_secret': {
                    'type': 'string',
                    'title': _('Consumer Secret'),
                    'description': _('Your USPS API Consumer Secret (Client Secret) from the USPS Developer Portal'),
                    'required': True,
                    'secret': True,
                    'min_length': 20
                },
                'payment_account_number': {
                    'type': 'string',
                    'title': _('Payment Account Number'),
                    'description': _('USPS Payment Account Number (required for label generation)'),
                    'required': False,
                    'pattern': r'^\d{10}$'
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
        Validate USPS credentials.

        Args:
            credentials: Dictionary of credential values

        Raises:
            ValueError: If credentials are invalid or missing
        """
        required_fields = ['consumer_key', 'consumer_secret']
        missing_fields = [f for f in required_fields if not credentials.get(f)]

        if missing_fields:
            raise ValueError(
                _("Missing required USPS credentials: %(fields)s") %
                {'fields': ', '.join(missing_fields)}
            )

        # Validate consumer key length
        consumer_key = credentials.get('consumer_key', '')
        if len(consumer_key) < 20:
            raise ValueError(_("USPS Consumer Key must be at least 20 characters"))

        # Validate consumer secret length
        consumer_secret = credentials.get('consumer_secret', '')
        if len(consumer_secret) < 20:
            raise ValueError(_("USPS Consumer Secret must be at least 20 characters"))

        # Validate payment account format if provided (10 digits)
        payment_account = credentials.get('payment_account_number')
        if payment_account:
            if not payment_account.isdigit() or len(payment_account) != 10:
                raise ValueError(_("USPS Payment Account Number must be exactly 10 digits"))

        # Validate environment
        environment = credentials.get('environment', 'test')
        if environment not in ['test', 'production']:
            raise ValueError(_("Environment must be 'test' or 'production'"))

        logger.debug(f"USPS credentials validated successfully (environment={environment})")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Dictionary with masked sensitive values
        """
        redacted = credentials.copy()

        if 'consumer_key' in redacted:
            key = redacted['consumer_key']
            redacted['consumer_key'] = f"***{key[-4:]}" if len(key) > 4 else '***'

        if 'consumer_secret' in redacted:
            redacted['consumer_secret'] = '***HIDDEN***'

        # Payment account is semi-sensitive - show last 4 digits
        if 'payment_account_number' in redacted:
            acct = redacted['payment_account_number']
            redacted['payment_account_number'] = f"******{acct[-4:]}" if len(acct) > 4 else '***'

        return redacted

    def _handle_api_error(self, response: requests.Response, context: str = "API call") -> None:
        """
        Handle USPS API error responses.

        Parses USPS error response and raises appropriate exception.

        Args:
            response: HTTP response from USPS API
            context: Description of what operation failed (for logging)

        Raises:
            USPSAuthenticationError: For authentication failures
            USPSAuthorizationError: For authorization/permission failures
            USPSValidationError: For validation errors
            USPSPaymentError: For payment-related errors
            USPSRateLimitError: For rate limiting
            USPSServiceUnavailableError: For service unavailability
            USPSAPIError: For other API errors
        """
        status_code = response.status_code

        # Try to parse error response
        try:
            error_data = response.json()
        except Exception:
            # Can't parse JSON, create exception from status code
            exception = create_exception_from_response(
                status_code,
                None,
                default_message=f"{context} failed: HTTP {status_code}"
            )
            logger.error(f"USPS API error in {context}: {exception.message}")
            raise exception

        # Create exception from parsed error data
        exception = create_exception_from_response(
            status_code,
            error_data,
            default_message=f"{context} failed"
        )

        # Log error details
        logger.error(
            f"USPS API error in {context}: "
            f"code={exception.error_code}, message={exception.message}, "
            f"status={status_code}"
        )

        raise exception

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        context: str = "API request",
        timeout: int = 30,
        retry: bool = True,
        expect_multipart: bool = False,
    ) -> Any:
        """
        Make an authenticated API request to USPS with error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/prices/v3/base-rates/search')
            payload: Request payload (for POST/PUT)
            context: Description for logging
            timeout: Request timeout in seconds
            retry: Whether to retry on transient failures
            expect_multipart: If True, return raw response for multipart parsing

        Returns:
            Parsed JSON response or raw Response object if expect_multipart=True

        Raises:
            Various USPSError subclasses based on error type
        """
        url = f"{self.base_url}{endpoint}"

        # Get OAuth token
        token = self.oauth_client.get_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Log request (redact sensitive data)
        logger.info(f"USPS {method} {endpoint} - {context}")
        if payload and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Request payload: {payload}")

        # Define request function for retry decorator
        def make_request():
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )

                # Check for errors
                if response.status_code >= 400:
                    self._handle_api_error(response, context)

                # Return raw response for multipart parsing
                if expect_multipart:
                    logger.info(f"USPS {method} {endpoint} - {context} succeeded (multipart)")
                    return response

                # Parse and return successful JSON response
                result = response.json()
                logger.info(f"USPS {method} {endpoint} - {context} succeeded")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Response: {result}")

                return result

            except requests.exceptions.Timeout:
                logger.error(f"{context} timed out after {timeout}s")
                raise USPSServiceUnavailableError(f"{context} timed out")

            except requests.exceptions.ConnectionError as e:
                logger.error(f"{context} connection error: {e}")
                raise USPSServiceUnavailableError(f"{context} connection failed: {e}")

            except requests.exceptions.RequestException as e:
                logger.error(f"{context} request error: {e}")
                raise USPSAPIError(f"{context} failed: {e}")

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
        Test USPS API connection and credentials.

        Attempts to acquire OAuth token to verify credentials work.

        Returns:
            Dictionary with test results
        """
        logger.info("Testing USPS API connection")

        try:
            # Attempt to get OAuth token (this validates credentials)
            token = self.oauth_client.get_token()

            logger.info("USPS connection test successful")

            return {
                'success': True,
                'message': _('Connection successful'),
                'details': {
                    'provider': 'USPS',
                    'environment': self.environment,
                    'payment_account': f"******{self.payment_account_number[-4:]}" if self.payment_account_number else _('Not configured'),
                    'token_acquired': True
                }
            }

        except (USPSAuthenticationError, USPSAuthorizationError) as e:
            # Invalid credentials
            logger.error(f"USPS connection test failed - authentication: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'authentication'}
            }

        except USPSServiceUnavailableError as e:
            # Service unavailable
            logger.error(f"USPS connection test failed - service unavailable: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'service_unavailable'}
            }

        except USPSError as e:
            # Other USPS errors
            logger.error(f"USPS connection test failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'usps_error'}
            }

        except Exception as e:
            # Unexpected error
            logger.error(f"USPS connection test failed with unexpected error: {e}", exc_info=True)
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
        Get USPS shipping rates.

        Args:
            origin: Origin address
            destination: Destination address
            parcels: List of parcels
            options: Optional shipping options

        Returns:
            List of rate dictionaries sorted by price

        Raises:
            USPSValidationError: If parameters are invalid
            USPSAuthenticationError: If authentication fails
            USPSServiceUnavailableError: If service is unavailable
            USPSAPIError: For other API errors
        """
        logger.info(f"Getting USPS rates: {origin.get('country', 'US')} -> {destination.get('country', 'US')}")

        # Build request payload
        payload = self._build_rate_request(origin, destination, parcels, options or {})

        # Make API request with centralized error handling and retry
        data = self._make_api_request(
            method='POST',
            endpoint='/prices/v3/base-rates/search',
            payload=payload,
            context='Getting rates',
            retry=True
        )

        # Parse response
        rates = self._parse_rate_response(data)

        logger.info(f"Retrieved {len(rates)} USPS rates")
        return rates

    def _build_rate_request(
        self,
        origin: Dict[str, str],
        destination: Dict[str, str],
        parcels: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build USPS rate request payload.

        Args:
            origin: Origin address
            destination: Destination address
            parcels: List of parcels
            options: Shipping options

        Returns:
            Rate request payload dictionary
        """
        # Format addresses for USPS
        origin_address = utils.format_address(origin)
        destination_address = utils.format_address(destination)

        # Get first parcel (USPS v3 API handles single package per request)
        parcel = parcels[0] if parcels else {}
        package = utils.format_parcel(parcel)

        # Determine processing category based on dimensions
        processing_category = 'MACHINABLE'
        if all(k in package for k in ['length', 'width', 'height', 'weight']):
            processing_category = utils.determine_processing_category(
                package['length'],
                package['width'],
                package['height'],
                package['weight']
            )

        # Build request
        payload = {
            'originZIPCode': origin_address.get('ZIPCode', ''),
            'destinationZIPCode': destination_address.get('ZIPCode', ''),
            'weight': package.get('weight', 0),
            'length': package.get('length', 0),
            'width': package.get('width', 0),
            'height': package.get('height', 0),
            'mailClass': options.get('mail_class', 'USPS_GROUND_ADVANTAGE'),
            'processingCategory': processing_category,
            'destinationEntryFacilityType': 'NONE',
            'rateIndicator': options.get('rate_indicator', 'DR'),  # DR = Delivered Rate
            'priceType': options.get('price_type', 'RETAIL'),  # RETAIL, COMMERCIAL, COMMERCIAL_PLUS
        }

        # Add mail date if specified
        if 'mail_date' in options:
            mail_date = options['mail_date']
            if isinstance(mail_date, str):
                payload['mailDate'] = mail_date
            else:
                payload['mailDate'] = mail_date.strftime('%Y-%m-%d')
        else:
            # Default to today
            payload['mailDate'] = timezone.now().strftime('%Y-%m-%d')

        logger.debug(f"Built rate request for {package.get('weight', 0)} lb package")
        return payload

    def _parse_rate_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse USPS rate response into standard format.

        Args:
            data: USPS API response data

        Returns:
            List of rate dictionaries
        """
        rates = []

        # USPS v3 API returns single rate in response
        # Multiple rates require multiple API calls with different mail classes
        try:
            # Get price from response
            price = data.get('totalPrice') or data.get('price')

            if price is None:
                logger.warning("No price found in USPS rate response")
                return rates

            # Get mail class information
            mail_class = data.get('mailClass', '')
            service_name = utils.get_mail_class_name(mail_class)

            # Get delivery information
            delivery_days = None
            delivery_date = None

            if 'estimatedDeliveryDate' in data:
                delivery_date = utils.parse_usps_date(data['estimatedDeliveryDate'])

            if 'transitDays' in data:
                delivery_days = int(data['transitDays'])

            # Build rate dictionary
            rate = {
                'service_code': mail_class,
                'service_name': service_name,
                'carrier': 'USPS',
                'rate': Decimal(str(price)),
                'currency': 'USD',
                'delivery_days': delivery_days,
                'delivery_date': delivery_date,
                'billable_weight': data.get('weight'),
                'included_insurance': Decimal('0.00')  # USPS basic liability included
            }

            rates.append(rate)

        except Exception as e:
            logger.warning(f"Failed to parse rate data: {e}")

        # Sort by rate (cheapest first)
        rates.sort(key=lambda r: r['rate'] if r['rate'] else Decimal('9999999'))

        return rates

    def buy_label(
        self,
        shipment_id: str,
        rate: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Purchase USPS shipping label.

        Args:
            shipment_id: Internal shipment ID
            rate: Selected rate from get_rates()
            options: Required shipping options:
                {
                    'origin': {...},  # Origin address (same format as get_rates)
                    'destination': {...},  # Destination address
                    'parcels': [...],  # Parcel list
                    'label_format': 'PDF',  # PDF only (default: PDF)
                    'label_size': '4x6',  # 4x6 only (default: 4x6)
                    'from_name': 'Company Name',  # Required
                    'from_phone': '+1234567890',  # Required
                    'to_name': 'John Doe',  # Required
                    'to_phone': '+1987654321',  # Optional
                }

        Returns:
            Label information dictionary:
            {
                'tracking_number': '9400100000000000000000',
                'label_url': 'data:application/pdf;base64,...',
                'label_format': 'PDF',
                'cost': Decimal('17.30'),
                'currency': 'USD',
                'carrier': 'USPS',
                'service': 'USPS Ground Advantage™',
                'external_shipment_id': 'usps_9400100000000000000000',
                'created_at': datetime(...)
            }

        Raises:
            USPSValidationError: If required options are missing or invalid
            USPSPaymentError: If payment authorization fails
            USPSShipmentError: If shipment creation fails
            USPSAuthenticationError: If authentication fails
            USPSServiceUnavailableError: If service is unavailable
            USPSAPIError: For other API errors
        """
        logger.info(f"Purchasing USPS label for shipment {shipment_id}")

        # Validate payment account configured
        if not self.payment_account_number:
            raise USPSPaymentError(
                _("Payment account number not configured. Label purchase requires payment authorization."),
                error_code="PAYMENT_ACCOUNT_REQUIRED"
            )

        # Validate required options
        if not options:
            raise USPSValidationError(_("Options are required for label purchase"))

        required_fields = ['origin', 'destination', 'parcels', 'from_name', 'from_phone', 'to_name']
        missing = [f for f in required_fields if f not in options]
        if missing:
            raise USPSValidationError(_("Missing required options: %(fields)s") % {'fields': ', '.join(missing)})

        # Build ship request payload
        payload = self._build_ship_request(shipment_id, rate, options)

        # Make API request with centralized error handling and retry
        # Label endpoint returns multipart/form-data response
        response = self._make_api_request(
            method='POST',
            endpoint='/labels/v3/label',
            payload=payload,
            context='Purchasing label',
            timeout=60,
            retry=True,
            expect_multipart=True
        )

        # Parse multipart response
        label_data = documents.parse_multipart_label_response(response)

        # Parse metadata and build result
        label_info = self._parse_ship_response(label_data, rate, options)

        logger.info(f"Successfully created USPS label: {label_info['tracking_number']}")
        return label_info

    def _build_ship_request(
        self,
        shipment_id: str,
        rate: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build USPS ship request payload.

        Args:
            shipment_id: Internal shipment ID
            rate: Selected rate
            options: Shipping options with origin, destination, parcels, etc.

        Returns:
            Ship request payload dictionary
        """
        origin = options['origin']
        destination = options['destination']
        parcels = options['parcels']

        # Format addresses
        from_address = utils.format_address(origin)
        to_address = utils.format_address(destination)

        # Get first parcel
        parcel = parcels[0] if parcels else {}
        package = utils.format_parcel(parcel)

        # Determine processing category
        processing_category = 'MACHINABLE'
        if all(k in package for k in ['length', 'width', 'height', 'weight']):
            processing_category = utils.determine_processing_category(
                package['length'],
                package['width'],
                package['height'],
                package['weight']
            )

        # Build request payload
        payload = {
            'imageInfo': {
                'imageType': 'PDF',  # USPS v3 currently supports PDF only
                'labelType': 'SHIPPING',
            },
            'fromAddress': {
                'streetAddress': from_address.get('streetAddress', ''),
                'city': from_address.get('city', ''),
                'state': from_address.get('state', ''),
                'ZIPCode': from_address.get('ZIPCode', ''),
                'firstName': options.get('from_name', '').split()[0] if options.get('from_name') else '',
                'lastName': ' '.join(options.get('from_name', '').split()[1:]) if len(options.get('from_name', '').split()) > 1 else '',
                'phone': options.get('from_phone', ''),
            },
            'toAddress': {
                'streetAddress': to_address.get('streetAddress', ''),
                'city': to_address.get('city', ''),
                'state': to_address.get('state', ''),
                'ZIPCode': to_address.get('ZIPCode', ''),
                'firstName': options.get('to_name', '').split()[0] if options.get('to_name') else '',
                'lastName': ' '.join(options.get('to_name', '').split()[1:]) if len(options.get('to_name', '').split()) > 1 else '',
                'phone': options.get('to_phone', ''),
            },
            'weight': package.get('weight', 0),
            'length': package.get('length', 0),
            'width': package.get('width', 0),
            'height': package.get('height', 0),
            'mailClass': rate.get('service_code', 'USPS_GROUND_ADVANTAGE'),
            'processingCategory': processing_category,
            'rateIndicator': 'DR',
            'destinationEntryFacilityType': 'NONE',
            'paymentAccountNumber': self.payment_account_number,
        }

        # Add address line 2 if provided
        if from_address.get('streetAddressAbbreviation'):
            payload['fromAddress']['streetAddressAbbreviation'] = from_address['streetAddressAbbreviation']

        if to_address.get('streetAddressAbbreviation'):
            payload['toAddress']['streetAddressAbbreviation'] = to_address['streetAddressAbbreviation']

        # Add company/firm names if provided
        if from_address.get('firm'):
            payload['fromAddress']['firm'] = from_address['firm']

        if to_address.get('firm'):
            payload['toAddress']['firm'] = to_address['firm']

        # Add extra services if requested
        extra_services = []

        if options.get('insurance_amount'):
            insurance_amount = float(options['insurance_amount'])
            if insurance_amount > 0:
                extra_services.append({
                    'extraService': 'INSURANCE',
                    'value': insurance_amount
                })

        if options.get('signature_required'):
            extra_services.append({
                'extraService': 'SIGNATURE_CONFIRMATION'
            })

        if extra_services:
            payload['extraServices'] = extra_services

        logger.debug(f"Built ship request for {package.get('weight', 0)} lb package")
        return payload

    def _parse_ship_response(
        self,
        label_data: Dict[str, Any],
        rate: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse USPS ship response into standard format.

        Args:
            label_data: Parsed label data from multipart response
            rate: Selected rate
            options: Shipping options

        Returns:
            Label information dictionary
        """
        metadata = label_data['metadata']
        label_binary = label_data['label']

        # Extract tracking number
        tracking_number = documents.extract_tracking_number(metadata)
        if not tracking_number:
            raise USPSShipmentError(
                _("No tracking number in USPS label response"),
                error_code="MISSING_TRACKING_NUMBER"
            )

        # Extract postage amount
        postage = documents.extract_postage_amount(metadata)
        cost = Decimal(str(postage)) if postage else rate.get('rate', Decimal('0.00'))

        # Get label format
        label_format = documents.get_label_format_from_metadata(metadata)

        # Convert binary label to data URI
        import base64
        label_base64 = base64.b64encode(label_binary).decode('utf-8')
        mime_types = {
            'PDF': 'application/pdf',
            'PNG': 'image/png',
        }
        mime_type = mime_types.get(label_format, 'application/pdf')
        label_url = f"data:{mime_type};base64,{label_base64}"

        # Build return dictionary
        return {
            'tracking_number': tracking_number,
            'label_url': label_url,
            'label_format': label_format,
            'cost': cost,
            'currency': 'USD',
            'carrier': 'USPS',
            'service': rate.get('service_name', rate.get('service_code', 'USPS')),
            'external_shipment_id': f"usps_{tracking_number}",
            'created_at': timezone.now()
        }

    def cancel_label(self, tracking_number: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel USPS shipping label.

        Note: USPS v3 API does not provide label cancellation via API.
        Labels must be cancelled through USPS Business Customer Gateway.

        Args:
            tracking_number: Tracking number to cancel
            reason: Optional cancellation reason

        Returns:
            Cancellation result dictionary

        Raises:
            NotImplementedError: Label cancellation not available via API
        """
        raise NotImplementedError(
            _("USPS label cancellation not available via API. "
              "Please cancel through USPS Business Customer Gateway at https://gateway.usps.com")
        )

    def get_tracking(self, tracking_number: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get USPS tracking information via Track API.

        Fetches detailed tracking information including scan events, delivery status,
        estimated delivery time, and location history.

        Args:
            tracking_number: USPS tracking number to look up
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with tracking information:
            {
                'tracking_number': '9400100000000000000000',
                'status': 'in_transit',  # Platform status
                'carrier': 'USPS',
                'service': 'USPS Ground Advantage™',
                'estimated_delivery': datetime(2025, 10, 23, 20, 0),
                'actual_delivery': datetime(2025, 10, 22, 14, 30) or None,
                'current_location': 'Memphis, TN',
                'events': [
                    {
                        'timestamp': datetime(2025, 10, 20, 10, 30),
                        'status': 'in_transit',
                        'location': 'Los Angeles, CA',
                        'description': 'Picked up',
                    },
                    ...
                ],
            }

        Raises:
            USPSTrackingError: If tracking lookup fails
            USPSValidationError: If tracking number format is invalid
            USPSAuthenticationError: If authentication fails
            USPSServiceUnavailableError: If service is unavailable
            USPSAPIError: For other API errors
        """
        logger.info(f"Fetching USPS tracking: {tracking_number}")

        # Validate tracking number format
        if not utils.validate_tracking_number(tracking_number):
            raise USPSValidationError(
                _("Invalid USPS tracking number format: %(tracking)s") %
                {'tracking': tracking_number}
            )

        # Build Track API request (USPS uses POST, not GET)
        payload = {
            'trackingNumber': tracking_number
        }

        # Make API request with centralized error handling
        try:
            data = self._make_api_request(
                method='POST',
                endpoint='/tracking/v3/tracking',
                payload=payload,
                context=f'Getting tracking for {tracking_number}',
                retry=True
            )
        except USPSValidationError as e:
            # Re-raise validation errors
            raise
        except USPSError:
            # Re-raise other USPS errors
            raise

        # Parse tracking results
        try:
            tracking_info = data.get('trackingEvents', [])
            if not tracking_info:
                raise USPSTrackingError(
                    _("No tracking information found for %(tracking)s") %
                    {'tracking': tracking_number}
                )

            # Get latest status (first event is most recent)
            latest_event = tracking_info[0] if tracking_info else {}
            status_text = latest_event.get('eventType', '') or latest_event.get('status', '')
            platform_status = utils.map_usps_status(status_text)

            # Extract service information
            service_name = data.get('mailClass', 'USPS')
            if service_name:
                service_name = utils.get_mail_class_name(service_name)

            # Extract delivery information
            estimated_delivery = None
            actual_delivery = None

            if 'expectedDeliveryDate' in data:
                estimated_delivery = utils.parse_usps_date(data['expectedDeliveryDate'])

            if 'deliveryDate' in data:
                actual_delivery = utils.parse_usps_datetime(data['deliveryDate'])

            # Extract current location from latest event
            current_location = None
            if latest_event.get('eventCity') or latest_event.get('eventState'):
                city = latest_event.get('eventCity', '')
                state = latest_event.get('eventState', '')
                current_location = f"{city}, {state}" if city and state else city or state

            # Parse tracking events
            events = []
            for event in tracking_info:
                event_time = utils.parse_usps_datetime(event.get('eventTimestamp') or event.get('eventDate'))
                event_status_text = event.get('eventType', '') or event.get('status', '')
                event_status = utils.map_usps_status(event_status_text)

                # Extract location
                event_city = event.get('eventCity', '')
                event_state = event.get('eventState', '')
                location_str = f"{event_city}, {event_state}" if event_city and event_state else event_city or event_state or ''

                events.append({
                    'timestamp': event_time,
                    'status': event_status,
                    'location': location_str,
                    'description': event.get('eventDescription', event_status_text),
                })

            # Events are already sorted chronologically (most recent first)
            # Reverse to oldest first for consistency with other providers
            events.reverse()

            # Build result dictionary
            result = {
                'tracking_number': tracking_number,
                'status': platform_status,
                'status_description': status_text,
                'carrier': 'USPS',
                'service': service_name,
                'estimated_delivery': estimated_delivery,
                'actual_delivery': actual_delivery,
                'current_location': current_location,
                'events': events,
            }

            logger.info(f"Fetched tracking data for {tracking_number} (status={platform_status})")
            return result

        except (KeyError, IndexError) as e:
            raise USPSTrackingError(
                _("Unexpected USPS Track API response format: %(error)s") %
                {'error': str(e)}
            )

    def verify_webhook_signature(self, payload: bytes, signature: str, **kwargs) -> bool:
        """
        Verify USPS webhook signature.

        NOTE: USPS REST API does not support webhooks as of v1.0.0.
        Use polling with get_tracking() instead.

        Args:
            payload: Raw request body
            signature: Signature header
            **kwargs: Additional headers

        Returns:
            False (webhooks not supported)

        Raises:
            NotImplementedError: USPS does not support webhooks
        """
        raise NotImplementedError(
            _("USPS REST API does not support webhooks. Use polling with get_tracking() instead.")
        )

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle USPS webhook event.

        NOTE: USPS REST API does not support webhooks as of v1.0.0.
        Use polling with get_tracking() instead.

        Args:
            event_type: Event type
            payload: Webhook payload

        Returns:
            Processed webhook data

        Raises:
            NotImplementedError: USPS does not support webhooks
        """
        raise NotImplementedError(
            _("USPS REST API does not support webhooks. Use polling with get_tracking() instead.")
        )
