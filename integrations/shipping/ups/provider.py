"""
UPS Shipping Provider

OAuth 2.0 authenticated shipping provider for UPS REST API.
Implements rate calculation, label generation, and tracking.

Author: Spwig
Version: 1.0.0
"""
import logging
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from shipping.providers.base import ProviderBase
from shipping.providers.ups.auth import create_oauth_client, UPSOAuthClient
from shipping.providers.ups import utils
from shipping.providers.ups.exceptions import (
    UPSError,
    UPSAuthenticationError,
    UPSAuthorizationError,
    UPSValidationError,
    UPSRateLimitError,
    UPSServiceUnavailableError,
    UPSAccountError,
    UPSShipmentError,
    UPSTrackingError,
    UPSAPIError,
    parse_ups_error,
)
from shipping.providers.ups.retry import retry_with_backoff, RetryConfig
import requests


logger = logging.getLogger(__name__)


class UPSProvider(ProviderBase):
    """
    UPS shipping provider implementation.

    Provides rate calculation, label generation, and tracking
    via UPS REST API with OAuth 2.0 authentication.

    Capabilities:
        - Rate quotes (Ground, Express, International)
        - Shipping label generation (PDF, PNG, ZPL)
        - Real-time tracking with 1Z tracking numbers
        - International shipping
        - Insurance support
        - Signature confirmation

    API Documentation: https://developer.ups.com/
    """

    # Provider identification
    provider_key = 'ups'
    provider_name = _('UPS')

    # API URLs
    SANDBOX_BASE_URL = 'https://wwwcie.ups.com'
    PRODUCTION_BASE_URL = 'https://onlinetools.ups.com'

    # API version
    API_VERSION = 'v1'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize UPS provider.

        Args:
            credentials: Dictionary containing:
                - api_key: UPS Client ID
                - api_secret: UPS Client Secret
                - account_number: UPS account number (6 characters, optional for rates)
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

        # Store account number
        self.account_number = credentials.get('account_number')
        self.environment = environment

        # Create OAuth client
        self.oauth_client: UPSOAuthClient = create_oauth_client(credentials)

        logger.info(f"UPS provider initialized (environment={environment})")

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities."""
        return {
            'rates': True,
            'labels': True,
            'tracking': True,
            'international': True,
            'returns': False,  # Not supported in v1.0.0
            'pickup': False,   # Not supported in v1.0.0
            'insurance': True,
            'signature': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for credentials.

        Note: Main schema is in manifest.json. This is minimal for compatibility.
        """
        return {
            'type': 'object',
            'properties': {
                'api_key': {'type': 'string', 'required': True},
                'api_secret': {'type': 'string', 'required': True},
                'account_number': {'type': 'string', 'required': False},
                'environment': {'type': 'string', 'enum': ['test', 'production']}
            }
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credentials against schema.

        Args:
            credentials: Credentials dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        required = ['api_key', 'api_secret']
        missing = [f for f in required if not credentials.get(f)]

        if missing:
            raise ValueError(
                _("Missing required credentials: %(fields)s") %
                {'fields': ', '.join(missing)}
            )

        # Validate API key format (basic check)
        api_key = credentials['api_key']
        if len(api_key) < 10:
            raise ValueError(_("API Key (Client ID) must be at least 10 characters"))

        # Validate environment
        environment = credentials.get('environment', 'test')
        if environment not in ['test', 'production']:
            raise ValueError(_("Environment must be 'test' or 'production'"))

        # Validate account number format if provided (6 alphanumeric characters)
        account_number = credentials.get('account_number')
        if account_number:
            if len(account_number) != 6:
                raise ValueError(_("UPS account number must be exactly 6 characters"))

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging.

        Args:
            credentials: Original credentials

        Returns:
            Dictionary with masked sensitive values
        """
        redacted = credentials.copy()

        # Mask API key - show last 4 characters
        if 'api_key' in redacted and redacted['api_key']:
            key = redacted['api_key']
            redacted['api_key'] = f"***{key[-4:]}" if len(key) >= 4 else '***'

        # Hide API secret completely
        if 'api_secret' in redacted:
            redacted['api_secret'] = '***HIDDEN***'

        # Keep account number visible (not secret)
        # Keep environment visible

        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity.

        Makes a simple API call to verify credentials work.
        Uses address validation as a lightweight test endpoint.

        Returns:
            Dictionary with test results
        """
        try:
            # Attempt to get OAuth token (validates credentials)
            token = self.oauth_client.get_token()

            # Make a simple API call to verify token works
            # Use address validation endpoint as it's lightweight
            headers = self._get_auth_headers()
            headers['transId'] = 'test-connection'
            headers['transactionSrc'] = 'testing'

            test_payload = {
                "AddressValidationRequest": {
                    "Request": {
                        "TransactionReference": {
                            "CustomerContext": "Connection Test"
                        }
                    },
                    "Address": {
                        "City": "New York",
                        "StateProvinceCode": "NY",
                        "CountryCode": "US"
                    }
                }
            }

            response = requests.post(
                f"{self.base_url}/api/addressvalidation/{self.API_VERSION}/1",
                headers=headers,
                json=test_payload,
                timeout=10
            )

            # 200 or 400 (validation error) both indicate working credentials
            if response.status_code in [200, 400]:
                return {
                    'success': True,
                    'message': _('Connection successful'),
                    'details': {
                        'environment': self.environment,
                        'api_base_url': self.base_url,
                        'account_number': self.account_number or _('Not provided'),
                        'oauth_token_acquired': True,
                    }
                }

            # Handle errors
            error_msg = self._parse_error_response(response)
            return {
                'success': False,
                'message': _('Connection test failed: %(error)s') % {'error': error_msg},
                'details': {}
            }

        except (UPSAuthenticationError, UPSAuthorizationError) as e:
            return {
                'success': False,
                'message': str(e),
                'details': {'error_type': 'authentication'}
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}", exc_info=True)
            return {
                'success': False,
                'message': _('Connection failed: %(error)s') % {'error': str(e)},
                'details': {}
            }

    @retry_with_backoff(config=RetryConfig(max_attempts=3))
    def get_rates(
        self,
        origin: Dict[str, str],
        destination: Dict[str, str],
        parcels: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get shipping rates from UPS.

        Args:
            origin: Origin address dict
            destination: Destination address dict
            parcels: List of parcel dicts
            options: Optional shipping options

        Returns:
            List of rate dictionaries

        Raises:
            UPSError: If rate request fails
        """
        logger.info(f"Fetching UPS rates: {origin.get('country')} -> {destination.get('country')}")

        try:
            # Build request payload
            payload = {
                "RateRequest": {
                    "Request": {
                        "TransactionReference": {
                            "CustomerContext": "Rate Request"
                        }
                    },
                    "Shipment": {
                        "Shipper": {
                            "Address": utils.format_address(origin)
                        },
                        "ShipTo": {
                            "Address": utils.format_address(destination)
                        },
                        "Package": [utils.format_parcel(p) for p in parcels]
                    }
                }
            }

            # Add shipper number if available
            if self.account_number:
                payload["RateRequest"]["Shipment"]["Shipper"]["ShipperNumber"] = self.account_number

            # Make API request
            response = self._make_request(
                'POST',
                f'/api/rating/{self.API_VERSION}/Rate',
                json=payload
            )

            # Parse rates from response
            rates = []
            rate_response = response.get('RateResponse', {})
            rated_shipments = rate_response.get('RatedShipment', [])

            # Ensure it's a list
            if isinstance(rated_shipments, dict):
                rated_shipments = [rated_shipments]

            for rated_shipment in rated_shipments:
                rate = utils.parse_rate_response(rated_shipment)
                rates.append(rate)

            logger.debug(f"Received {len(rates)} rates from UPS")

            # Sort by price (cheapest first)
            rates.sort(key=lambda r: r['rate'])

            return rates

        except UPSError:
            raise
        except Exception as e:
            logger.error(f"Rate request failed: {e}", exc_info=True)
            raise UPSAPIError(f"Failed to fetch rates: {str(e)}")

    @retry_with_backoff(config=RetryConfig(max_attempts=2))
    def buy_label(
        self,
        shipment_id: str,
        rate: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Purchase shipping label from UPS.

        Args:
            shipment_id: Internal shipment ID
            rate: Selected rate from get_rates()
            options: Optional purchase options (label_format, label_size)

        Returns:
            Label information dictionary

        Raises:
            UPSError: If label purchase fails
            ValueError: If account_number not configured
        """
        if not self.account_number:
            raise ValueError(_("UPS account number is required for label generation"))

        logger.info(f"Purchasing UPS label for shipment {shipment_id}")

        try:
            options = options or {}

            # Get shipment details from options
            origin = options.get('origin', {})
            destination = options.get('destination', {})
            parcels = options.get('parcels', [])

            # Label format (PDF, PNG, ZPL)
            label_format = options.get('label_format', 'PDF').upper()
            format_codes = {'PDF': 'PDF', 'PNG': 'GIF', 'ZPL': 'ZPL'}
            format_code = format_codes.get(label_format, 'PDF')

            # Build request payload
            payload = {
                "ShipmentRequest": {
                    "Request": {
                        "TransactionReference": {
                            "CustomerContext": shipment_id
                        }
                    },
                    "Shipment": {
                        "Shipper": {
                            "Name": origin.get('name', ''),
                            "ShipperNumber": self.account_number,
                            "Address": utils.format_address(origin)
                        },
                        "ShipTo": {
                            "Name": destination.get('name', ''),
                            "Address": utils.format_address(destination)
                        },
                        "Service": {
                            "Code": rate['service_code']
                        },
                        "Package": [utils.format_parcel(p) for p in parcels],
                        "PaymentInformation": {
                            "ShipmentCharge": {
                                "Type": "01",  # Prepaid
                                "BillShipper": {
                                    "AccountNumber": self.account_number
                                }
                            }
                        }
                    },
                    "LabelSpecification": {
                        "LabelImageFormat": {
                            "Code": format_code
                        },
                        "LabelStockSize": {
                            "Height": "6",
                            "Width": "4"
                        }
                    }
                }
            }

            # Add shipper phone if available
            if origin.get('phone'):
                payload["ShipmentRequest"]["Shipment"]["Shipper"]["Phone"] = {
                    "Number": origin['phone']
                }

            # Add recipient phone if available
            if destination.get('phone'):
                payload["ShipmentRequest"]["Shipment"]["ShipTo"]["Phone"] = {
                    "Number": destination['phone']
                }

            # Make API request
            response = self._make_request(
                'POST',
                f'/api/shipments/{self.API_VERSION}/ship',
                json=payload
            )

            # Parse response
            ship_response = response.get('ShipmentResponse', {})
            shipment_results = ship_response.get('ShipmentResults', {})

            # Extract tracking number
            package_results = shipment_results.get('PackageResults', {})
            if isinstance(package_results, list):
                package_results = package_results[0]

            tracking_number = package_results.get('TrackingNumber', '')

            # Extract label data
            label_image = package_results.get('ShippingLabel', {})
            label_data = label_image.get('GraphicImage', '')

            # Extract charges
            charges = shipment_results.get('ShipmentCharges', {})
            total_charges = charges.get('TotalCharges', {})

            result = {
                'tracking_number': tracking_number,
                'label_data': label_data,  # Base64 encoded
                'label_format': label_format,
                'cost': Decimal(str(total_charges.get('MonetaryValue', '0'))),
                'currency': total_charges.get('CurrencyCode', 'USD'),
                'carrier': 'UPS',
                'service': rate['service_name'],
                'external_shipment_id': shipment_results.get('ShipmentIdentificationNumber', ''),
                'created_at': timezone.now()
            }

            logger.info(f"Label purchased successfully: {tracking_number}")
            return result

        except UPSError:
            raise
        except Exception as e:
            logger.error(f"Label purchase failed: {e}", exc_info=True)
            raise UPSShipmentError(f"Failed to purchase label: {str(e)}")

    def cancel_label(
        self,
        tracking_number: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cancel/void shipping label.

        Args:
            tracking_number: Tracking number to cancel
            options: Optional cancellation options

        Returns:
            Cancellation result dictionary

        Raises:
            UPSError: If cancellation fails
        """
        logger.info(f"Cancelling UPS label: {tracking_number}")

        try:
            # Build request payload
            payload = {
                "VoidShipmentRequest": {
                    "Request": {
                        "TransactionReference": {
                            "CustomerContext": f"Cancel {tracking_number}"
                        }
                    },
                    "VoidShipment": {
                        "ShipmentIdentificationNumber": tracking_number
                    }
                }
            }

            # Make API request
            response = self._make_request(
                'DELETE',
                f'/api/shipments/{self.API_VERSION}/void/cancel/{tracking_number}',
                json=payload
            )

            # Parse response
            void_response = response.get('VoidShipmentResponse', {})
            status = void_response.get('Status', {})
            status_code = status.get('Code', '')

            success = status_code == '1'

            return {
                'success': success,
                'tracking_number': tracking_number,
                'message': status.get('Description', 'Label cancelled' if success else 'Cancellation failed')
            }

        except UPSError:
            raise
        except Exception as e:
            logger.error(f"Label cancellation failed: {e}", exc_info=True)
            raise UPSShipmentError(f"Failed to cancel label: {str(e)}")

    @retry_with_backoff(config=RetryConfig(max_attempts=3))
    def get_tracking(self, tracking_number: str) -> Dict[str, Any]:
        """
        Get tracking information for shipment.

        Args:
            tracking_number: UPS tracking number (1Z format)

        Returns:
            Tracking data dictionary

        Raises:
            UPSError: If tracking lookup fails
        """
        logger.info(f"Fetching UPS tracking: {tracking_number}")

        # Validate tracking number format
        if not utils.validate_tracking_number(tracking_number):
            raise UPSTrackingError(
                _("Invalid UPS tracking number format: %(tracking)s") %
                {'tracking': tracking_number}
            )

        try:
            # Make API request
            headers = self._get_auth_headers()
            headers['transId'] = f'track-{tracking_number}'
            headers['transactionSrc'] = 'shipping'

            response = requests.get(
                f"{self.base_url}/api/track/{self.API_VERSION}/details/{tracking_number}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                error_msg = self._parse_error_response(response)
                raise UPSTrackingError(f"Tracking lookup failed: {error_msg}")

            # Parse response
            data = response.json()
            track_response = data.get('trackResponse', {})
            shipment = track_response.get('shipment', [])

            if not shipment:
                raise UPSTrackingError(_("No tracking information found"))

            # Use first shipment
            if isinstance(shipment, list):
                shipment = shipment[0]

            # Extract package information
            package = shipment.get('package', [])
            if isinstance(package, list):
                package = package[0] if package else {}

            # Current status
            current_status = package.get('currentStatus', {})
            status_type = current_status.get('type', 'I')
            status = utils.map_ups_status(status_type)

            # Delivery information
            delivery_date = None
            delivery_time = package.get('deliveryTime', {})
            if delivery_time.get('endTime'):
                delivery_date = utils.parse_ups_date(delivery_time['endTime'])

            # Parse tracking events
            events = []
            activity = package.get('activity', [])
            if not isinstance(activity, list):
                activity = [activity] if activity else []

            for event in activity:
                parsed_event = utils.parse_tracking_event(event)
                events.append(parsed_event)

            # Sort events by timestamp (most recent first)
            events.sort(key=lambda e: e.get('timestamp') or datetime.min, reverse=True)

            return {
                'tracking_number': tracking_number,
                'status': status,
                'carrier': 'UPS',
                'service': shipment.get('service', {}).get('description', ''),
                'estimated_delivery': delivery_date,
                'actual_delivery': delivery_date if status == 'delivered' else None,
                'events': events
            }

        except UPSError:
            raise
        except Exception as e:
            logger.error(f"Tracking lookup failed: {e}", exc_info=True)
            raise UPSTrackingError(f"Failed to fetch tracking: {str(e)}")

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        **kwargs
    ) -> bool:
        """
        Verify webhook signature using HMAC SHA-256.

        Args:
            payload: Raw request body as bytes
            signature: Signature from webhook header
            **kwargs: Additional headers

        Returns:
            True if signature is valid
        """
        try:
            # Use API secret as signing key
            secret = self.credentials['api_secret'].encode('utf-8')

            # Calculate expected signature
            expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()

            # Constant-time comparison
            return hmac.compare_digest(signature, expected)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle webhook event from UPS.

        Args:
            event_type: Event type (e.g., 'tracking.updated')
            payload: Event payload

        Returns:
            Processed event data
        """
        logger.info(f"Handling UPS webhook: {event_type}")

        if event_type == 'tracking.updated':
            # Extract tracking information
            tracking_number = payload.get('trackingNumber', '')
            status = payload.get('status', {})
            status_type = status.get('type', 'I')

            return {
                'action': 'update_tracking',
                'tracking_number': tracking_number,
                'status': utils.map_ups_status(status_type),
                'event': {
                    'timestamp': utils.parse_ups_date(payload.get('timestamp')),
                    'status': status_type,
                    'location': payload.get('location', ''),
                    'description': status.get('description', '')
                }
            }

        elif event_type == 'shipment.delivered':
            return {
                'action': 'mark_delivered',
                'tracking_number': payload.get('trackingNumber', ''),
                'delivered_at': utils.parse_ups_date(payload.get('deliveredAt'))
            }

        else:
            # Unknown event type
            logger.warning(f"Unknown webhook event type: {event_type}")
            return {
                'action': 'unknown',
                'event_type': event_type
            }

    # Private helper methods

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return self.oauth_client.get_auth_headers()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request to UPS API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests

        Returns:
            Parsed JSON response

        Raises:
            UPSError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers()

        # Merge with any additional headers
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Add transaction tracking headers
        if 'transId' not in headers:
            import uuid
            headers['transId'] = str(uuid.uuid4())
        if 'transactionSrc' not in headers:
            headers['transactionSrc'] = 'shipping-platform'

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=30,
                **kwargs
            )

            # Handle errors
            if response.status_code >= 400:
                error_data = self._parse_error_response(response)
                raise error_data

            response.raise_for_status()
            return response.json()

        except UPSError:
            raise
        except requests.exceptions.Timeout:
            raise UPSServiceUnavailableError(_("Request timeout - UPS API did not respond in time"))
        except requests.exceptions.ConnectionError as e:
            raise UPSServiceUnavailableError(f"Connection error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise UPSAPIError(f"Request failed: {str(e)}")

    def _parse_error_response(self, response: requests.Response) -> UPSError:
        """
        Parse error response from UPS API.

        Args:
            response: Failed HTTP response

        Returns:
            Appropriate UPSError instance
        """
        try:
            error_data = response.json()
            return parse_ups_error(error_data)
        except Exception:
            # If JSON parsing fails, return generic error
            return UPSAPIError(
                f"HTTP {response.status_code}: {response.text[:200]}",
                details={'status_code': response.status_code}
            )
