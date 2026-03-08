"""
NinjaVan Provider Utility Functions

Helper functions for URL construction, webhook verification, status mapping,
address formatting, and data transformation.
"""

import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


# NinjaVan supported countries
NINJAVAN_COUNTRIES = {
    'SG': _('Singapore'),
    'MY': _('Malaysia'),
    'TH': _('Thailand'),
    'ID': _('Indonesia'),
    'VN': _('Vietnam'),
    'PH': _('Philippines'),
    'MM': _('Myanmar'),
}


# NinjaVan service types
SERVICE_TYPES = {
    'Parcel': _('Standard Parcel'),
    'Return': _('Return Service'),
    'Marketplace': _('Marketplace'),
    'Corporate': _('Corporate'),
    'International': _('International'),
    'Cold Chain': _('Cold Chain (Temperature Controlled)'),
}


# NinjaVan webhook events V2 to platform status mapping
WEBHOOK_STATUS_MAP = {
    # Standard delivery flow
    "Pending Pickup": "pending",
    "On Hold": "on_hold",
    "In Transit": "in_transit",
    "Out for Delivery": "out_for_delivery",
    "Delivered, Received by Customer": "delivered",

    # Exceptions
    "Delivery Fail": "delivery_failed",
    "Cancelled": "cancelled",
    "Returned to Sender": "returned",
}


# NinjaVan API endpoints
SANDBOX_BASE_URL = "https://api-sandbox.ninjavan.co"
PRODUCTION_BASE_URL = "https://api.ninjavan.co"


def get_base_url(environment: str, country_code: str) -> str:
    """
    Construct API base URL based on environment and country code.

    Important: Sandbox ALWAYS uses /sg endpoint regardless of actual country_code.
    Production uses /{country_code} endpoint.

    Args:
        environment: 'sandbox' or 'production'
        country_code: Two-letter country code (SG, MY, TH, ID, VN, PH, MM)

    Returns:
        Base URL with country path (e.g., 'https://api-sandbox.ninjavan.co/sg')

    Example:
        >>> get_base_url('sandbox', 'MY')
        'https://api-sandbox.ninjavan.co/sg'
        >>> get_base_url('production', 'MY')
        'https://api.ninjavan.co/my'
    """
    # Normalize inputs
    environment = environment.lower()
    country_code = country_code.lower()

    # Select base URL
    if environment == 'production':
        base_url = PRODUCTION_BASE_URL
    else:
        base_url = SANDBOX_BASE_URL
        # Sandbox always uses /sg
        country_code = 'sg'

    return f"{base_url}/{country_code}"


def verify_webhook_signature(
    payload: str,
    signature: str,
    client_secret: str
) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.

    NinjaVan signs webhook payloads with HMAC-SHA256 using the client_secret
    as the key. The signature is sent in the X-Ninjavan-Hmac-Sha256 header.

    Args:
        payload: Raw webhook payload (JSON string)
        signature: Signature from X-Ninjavan-Hmac-Sha256 header
        client_secret: Client secret used as HMAC key

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> payload = '{"tracking_number": "TEST123"}'
        >>> signature = "abc123..."
        >>> verify_webhook_signature(payload, signature, "my_secret")
        True
    """
    try:
        # Compute expected signature
        expected_signature = hmac.new(
            client_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)

        if not is_valid:
            logger.warning(
                f"Webhook signature verification failed. "
                f"Expected: {expected_signature[:8]}..., Got: {signature[:8]}..."
            )

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


def map_ninjavan_status(event_type: str) -> str:
    """
    Map NinjaVan webhook event type to platform status code.

    Args:
        event_type: NinjaVan event type (e.g., "Delivered, Received by Customer")

    Returns:
        Platform status code (e.g., 'delivered', 'in_transit', 'pending')

    Example:
        >>> map_ninjavan_status("Delivered, Received by Customer")
        'delivered'
        >>> map_ninjavan_status("Out for Delivery")
        'out_for_delivery'
    """
    # Get mapped status, default to 'in_transit' for unknown statuses
    platform_status = WEBHOOK_STATUS_MAP.get(event_type, 'in_transit')

    if event_type not in WEBHOOK_STATUS_MAP:
        logger.warning(
            f"Unknown NinjaVan event type: {event_type}. "
            f"Mapping to 'in_transit'"
        )

    return platform_status


def format_address(address_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform platform address format to NinjaVan API format.

    Args:
        address_data: Platform address dictionary containing:
            - name: Full name
            - company: Company name (optional)
            - address1: Street address line 1
            - address2: Street address line 2 (optional)
            - city: City
            - state: State/province
            - postal_code: Postal/ZIP code
            - country: Country code (2-letter)
            - phone: Phone number
            - email: Email address

    Returns:
        NinjaVan address format dictionary

    Example:
        >>> platform_address = {
        ...     'name': 'John Doe',
        ...     'address1': '123 Main St',
        ...     'city': 'Singapore',
        ...     'postal_code': '123456',
        ...     'country': 'SG',
        ...     'phone': '+6512345678',
        ...     'email': 'john@example.com'
        ... }
        >>> format_address(platform_address)
        {
            'name': 'John Doe',
            'address': {
                'address1': '123 Main St',
                'address2': '',
                'city': 'Singapore',
                'state': '',
                'postcode': '123456',
                'country': 'SG'
            },
            'phone_number': '+6512345678',
            'email': 'john@example.com'
        }
    """
    # Extract data with defaults
    name = address_data.get('name', '')
    company = address_data.get('company', '')
    address1 = address_data.get('address1', '')
    address2 = address_data.get('address2', '')
    city = address_data.get('city', '')
    state = address_data.get('state', '')
    postal_code = address_data.get('postal_code', '')
    country = address_data.get('country', '').upper()
    phone = address_data.get('phone', '')
    email = address_data.get('email', '')

    # Use company name if provided and no name
    if not name and company:
        name = company

    # Build NinjaVan address format
    ninjavan_address = {
        'name': name,
        'address': {
            'address1': address1,
            'address2': address2,
            'city': city,
            'state': state,
            'postcode': postal_code,
            'country': country,
        },
        'phone_number': phone,
        'email': email,
    }

    return ninjavan_address


def format_parcel(parcel_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform platform parcel format to NinjaVan parcel_job format.

    Args:
        parcel_data: Platform parcel dictionary containing:
            - weight: Weight in grams
            - length: Length in cm (optional)
            - width: Width in cm (optional)
            - height: Height in cm (optional)
            - description: Item description
            - value: Declared value/insurance amount (optional)
            - currency: Currency code (optional)

    Returns:
        NinjaVan parcel_job format dictionary

    Example:
        >>> platform_parcel = {
        ...     'weight': 1000,
        ...     'length': 20,
        ...     'width': 15,
        ...     'height': 10,
        ...     'description': 'Electronics',
        ...     'value': 100.00
        ... }
        >>> format_parcel(platform_parcel)
        {
            'dimensions': {
                'weight': 1.0,
                'length': 20,
                'width': 15,
                'height': 10
            },
            'description': 'Electronics',
            'insurance_details': {
                'insured_value': 100.00,
                'currency': 'SGD'
            }
        }
    """
    # Extract data with defaults
    weight_grams = parcel_data.get('weight', 0)
    length_cm = parcel_data.get('length')
    width_cm = parcel_data.get('width')
    height_cm = parcel_data.get('height')
    description = parcel_data.get('description', 'Package')
    value = parcel_data.get('value')
    currency = parcel_data.get('currency', 'SGD')

    # Convert weight from grams to kilograms
    weight_kg = round(weight_grams / 1000.0, 2)

    # Build dimensions (weight is required, dimensions are optional)
    dimensions = {
        'weight': weight_kg,
    }

    # Add dimensions if provided
    if length_cm and width_cm and height_cm:
        dimensions['length'] = float(length_cm)
        dimensions['width'] = float(width_cm)
        dimensions['height'] = float(height_cm)

    # Build parcel_job format
    parcel_job = {
        'dimensions': dimensions,
        'description': description,
    }

    # Add insurance details if value provided
    if value:
        parcel_job['insurance_details'] = {
            'insured_value': float(value),
            'currency': currency,
        }

    return parcel_job


def parse_waybill_response(response: Any) -> Dict[str, Any]:
    """
    Parse NinjaVan waybill (label) API response.

    The waybill endpoint returns a PDF file directly (not JSON).
    This function processes the response and returns the label data.

    Args:
        response: requests.Response object from waybill endpoint

    Returns:
        Dictionary containing:
            - label_data: Base64-encoded PDF data
            - label_format: 'pdf'
            - label_size: Size of PDF in bytes

    Example:
        >>> response = requests.get(waybill_url)
        >>> label = parse_waybill_response(response)
        >>> label['label_format']
        'pdf'
    """
    # Check if response is PDF
    content_type = response.headers.get('Content-Type', '')
    if 'application/pdf' not in content_type:
        logger.warning(
            f"Unexpected waybill content type: {content_type}. "
            f"Expected application/pdf"
        )

    # Get PDF data
    pdf_bytes = response.content
    pdf_size = len(pdf_bytes)

    # Encode to base64 for storage/transmission
    label_data = base64.b64encode(pdf_bytes).decode('utf-8')

    logger.info(f"Parsed waybill PDF: {pdf_size} bytes")

    return {
        'label_data': label_data,
        'label_format': 'pdf',
        'label_size': pdf_size,
    }


def validate_country_code(country_code: str) -> bool:
    """
    Validate NinjaVan country code.

    Args:
        country_code: Two-letter country code

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_country_code('SG')
        True
        >>> validate_country_code('US')
        False
    """
    return country_code.upper() in NINJAVAN_COUNTRIES


def format_tracking_number(tracking_number: str) -> str:
    """
    Format tracking number for display (removes extra whitespace).

    Args:
        tracking_number: Raw tracking number

    Returns:
        Cleaned tracking number

    Example:
        >>> format_tracking_number(' NVSGTEST123 ')
        'NVSGTEST123'
    """
    return tracking_number.strip()


def parse_error_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse NinjaVan API error response and extract useful details.

    Args:
        response_data: JSON response data from API error

    Returns:
        Dictionary with parsed error information:
            - message: Error message
            - code: Error code (if available)
            - details: Additional error details (if available)

    Example:
        >>> error_response = {
        ...     'error': {
        ...         'code': '127014',
        ...         'message': 'Invalid charset',
        ...         'details': [{'field': 'address', 'message': 'Invalid format'}]
        ...     }
        ... }
        >>> parse_error_response(error_response)
        {
            'message': 'Invalid charset',
            'code': '127014',
            'details': [{'field': 'address', 'message': 'Invalid format'}]
        }
    """
    if not response_data:
        return {
            'message': 'Unknown error',
            'code': None,
            'details': None,
        }

    # Handle different error response formats
    error_obj = response_data.get('error', {})

    # Format 1: error is a string (OAuth errors)
    if isinstance(error_obj, str):
        return {
            'message': response_data.get('error_description', error_obj),
            'code': error_obj,
            'details': None,
        }

    # Format 2: error is an object (API errors)
    if isinstance(error_obj, dict):
        return {
            'message': error_obj.get('message', 'Unknown error'),
            'code': error_obj.get('code'),
            'details': error_obj.get('details'),
        }

    # Format 3: no error object
    return {
        'message': response_data.get('message', 'Unknown error'),
        'code': None,
        'details': None,
    }


def build_redirect_uri(shop_domain: str, protocol: str = 'https') -> str:
    """
    Build OAuth redirect URI for merchant's shop.

    Args:
        shop_domain: Merchant's shop domain (e.g., 'myshop.example.com')
        protocol: Protocol to use ('https' or 'http', default: 'https')

    Returns:
        Full redirect URI

    Example:
        >>> build_redirect_uri('myshop.example.com')
        'https://myshop.example.com/shipping/ninjavan/oauth/callback/'
    """
    return f"{protocol}://{shop_domain}/shipping/ninjavan/oauth/callback/"


def build_webhook_uri(shop_domain: str, protocol: str = 'https') -> str:
    """
    Build webhook endpoint URI for merchant's shop.

    Args:
        shop_domain: Merchant's shop domain (e.g., 'myshop.example.com')
        protocol: Protocol to use ('https' or 'http', default: 'https')

    Returns:
        Full webhook URI

    Example:
        >>> build_webhook_uri('myshop.example.com')
        'https://myshop.example.com/shipping/ninjavan/webhooks/'
    """
    return f"{protocol}://{shop_domain}/shipping/ninjavan/webhooks/"


def get_service_type_name(service_type: str) -> str:
    """
    Get human-readable service type name.

    Args:
        service_type: NinjaVan service type code

    Returns:
        Translated service type name

    Example:
        >>> get_service_type_name('Parcel')
        'Standard Parcel'
    """
    return SERVICE_TYPES.get(service_type, service_type)
