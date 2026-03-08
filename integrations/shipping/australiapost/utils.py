"""
Australia Post Provider Utilities

Helper functions for data transformation, validation, and formatting.
Includes address formatting, tracking status mapping, and product code mappings.
"""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from dateutil import parser as date_parser
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


# Australia Post product/service code mappings
PRODUCT_CODES = {
    # Domestic services
    'AUS_PARCEL_REGULAR': _('Regular Parcel'),
    'AUS_PARCEL_EXPRESS': _('Express Post'),
    'AUS_PARCEL_COURIER': _('Courier Post'),
    'AUS_LETTER_REGULAR': _('Regular Letter'),
    'AUS_LETTER_EXPRESS': _('Express Letter'),
    'AUS_PARCEL_STANDARD': _('Standard Parcel'),

    # International services
    'INTL_PARCEL_STD': _('International Standard'),
    'INTL_PARCEL_EXP': _('International Express'),
    'INTL_PARCEL_COR': _('International Courier'),
    'INTL_LETTER_AIR': _('International Letter Airmail'),

    # StarTrack services
    'ST_PREMIUM': _('StarTrack Premium'),
    'ST_EXPRESS': _('StarTrack Express'),
    'ST_FIXED_PRICE': _('StarTrack Fixed Price Premium'),
}


# Tracking event status mappings
# Maps Australia Post event descriptions to platform status codes
STATUS_PATTERNS = {
    'delivered': 'delivered',
    'delivery attempted': 'exception',
    'out for delivery': 'out_for_delivery',
    'on board for delivery': 'out_for_delivery',
    'in transit': 'in_transit',
    'arrived at facility': 'in_transit',
    'departed facility': 'in_transit',
    'processed': 'in_transit',
    'received': 'in_transit',
    'collected': 'in_transit',
    'lodged': 'in_transit',
    'shipping information received': 'pending',
    'awaiting collection': 'available_for_pickup',
    'held': 'exception',
    'delayed': 'exception',
    'return to sender': 'exception',
    'unsuccessful delivery': 'exception',
    'damaged': 'exception',
}


def pad_account_number(account_number: str) -> str:
    """
    Pad account number to appropriate length.

    Australia Post: 10 digits (left-padded with zeros)
    StarTrack: 8 digits (no padding needed)

    Args:
        account_number: Raw account number

    Returns:
        str: Properly formatted account number

    Example:
        >>> pad_account_number('123456')
        '0000123456'
        >>> pad_account_number('12345678')
        '12345678'
    """
    # Remove any spaces or dashes
    clean = account_number.replace(' ', '').replace('-', '')

    # If 8 digits and first digit is non-zero, it's StarTrack (no padding)
    if len(clean) == 8 and clean[0] != '0':
        return clean

    # Otherwise pad to 10 digits for Australia Post
    return clean.zfill(10)


def detect_service_type(account_number: str) -> str:
    """
    Detect service type from account number.

    Args:
        account_number: Account number (8 or 10 digits)

    Returns:
        str: 'australia_post' or 'startrack'

    Example:
        >>> detect_service_type('0000123456')
        'australia_post'
        >>> detect_service_type('12345678')
        'startrack'
    """
    clean = account_number.replace(' ', '').replace('-', '')

    # StarTrack: 8 digits, left-most digit is always non-zero
    if len(clean) == 8 and clean[0] != '0':
        return 'startrack'

    # Australia Post: 10 digits
    return 'australia_post'


def format_address(address: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format address dict to Australia Post API format.

    Args:
        address: Platform address dict with keys:
            - name (optional)
            - company (optional)
            - street_line1
            - street_line2 (optional)
            - street_line3 (optional)
            - city
            - state_code
            - postal_code
            - country_code
            - phone (optional)
            - email (optional)

    Returns:
        dict: Australia Post-formatted address

    Example:
        {
            "name": "John Smith",
            "lines": ["123 Main Street", "Suite 100"],
            "suburb": "Sydney",
            "state": "NSW",
            "postcode": "2000",
            "country": "AU",
            "phone": "0412345678",
            "email": "john@example.com"
        }
    """
    auspost_address = {}

    # Name/Company
    if address.get('company'):
        auspost_address['business_name'] = address['company'][:40]
        if address.get('name'):
            auspost_address['name'] = address['name'][:40]
    elif address.get('name'):
        auspost_address['name'] = address['name'][:40]

    # Street lines
    lines = []
    if address.get('street_line1'):
        lines.append(address['street_line1'][:40])
    if address.get('street_line2'):
        lines.append(address['street_line2'][:40])
    if address.get('street_line3'):
        lines.append(address['street_line3'][:40])

    if lines:
        auspost_address['lines'] = lines

    # Suburb (city)
    if address.get('city'):
        auspost_address['suburb'] = address['city'][:40]

    # State
    if address.get('state_code'):
        auspost_address['state'] = address['state_code'][:3].upper()

    # Postcode
    if address.get('postal_code'):
        auspost_address['postcode'] = clean_postcode(address['postal_code'])

    # Country
    if address.get('country_code'):
        auspost_address['country'] = address['country_code'][:2].upper()

    # Phone
    if address.get('phone'):
        auspost_address['phone'] = clean_phone(address['phone'])

    # Email
    if address.get('email'):
        auspost_address['email'] = address['email'][:80]

    return auspost_address


def clean_postcode(postcode: str) -> str:
    """
    Clean and format Australian postcode.

    Australian postcodes are 4 digits.

    Args:
        postcode: Raw postcode

    Returns:
        str: Cleaned postcode

    Example:
        >>> clean_postcode('2000')
        '2000'
        >>> clean_postcode('NSW 2000')
        '2000'
    """
    # Extract digits only
    digits = re.sub(r'\D', '', str(postcode))

    # Australian postcodes are 4 digits
    if len(digits) >= 4:
        return digits[:4]

    return digits


def clean_phone(phone: str) -> str:
    """
    Clean and format phone number.

    Args:
        phone: Raw phone number

    Returns:
        str: Cleaned phone number

    Example:
        >>> clean_phone('+61 412 345 678')
        '0412345678'
        >>> clean_phone('(02) 1234-5678')
        '0212345678'
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))

    # If starts with 61 (Australia country code), replace with 0
    if digits.startswith('61'):
        digits = '0' + digits[2:]

    # Limit to 15 digits
    return digits[:15]


def format_parcel(parcel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parcel dict to Australia Post API format.

    Args:
        parcel: Platform parcel dict with keys:
            - weight_kg (or weight_lb/weight_oz)
            - length_cm (or length_in)
            - width_cm (or width_in)
            - height_cm (or height_in)

    Returns:
        dict: Australia Post-formatted package

    Example:
        {
            "weight": 2.5,
            "length": 30,
            "width": 20,
            "height": 15
        }
    """
    package = {}

    # Weight (convert to kilograms)
    weight_kg = parcel.get('weight_kg', 0)
    weight_lb = parcel.get('weight_lb', 0)
    weight_oz = parcel.get('weight_oz', 0)

    total_weight = weight_kg + (weight_lb * 0.453592) + (weight_oz * 0.0283495)

    if total_weight > 0:
        package['weight'] = round(total_weight, 3)

    # Dimensions (convert to centimeters)
    length_cm = parcel.get('length_cm', 0) or (parcel.get('length_in', 0) * 2.54)
    width_cm = parcel.get('width_cm', 0) or (parcel.get('width_in', 0) * 2.54)
    height_cm = parcel.get('height_cm', 0) or (parcel.get('height_in', 0) * 2.54)

    if length_cm > 0:
        package['length'] = round(length_cm, 1)

    if width_cm > 0:
        package['width'] = round(width_cm, 1)

    if height_cm > 0:
        package['height'] = round(height_cm, 1)

    return package


def map_tracking_status(event_description: str) -> str:
    """
    Map Australia Post tracking event description to platform status code.

    Australia Post uses descriptive text for tracking events.
    This function matches text patterns to standardized platform statuses.

    Args:
        event_description: Australia Post event description

    Returns:
        str: Platform status code (delivered, in_transit, exception, etc.)

    Example:
        >>> map_tracking_status("Item delivered")
        'delivered'
        >>> map_tracking_status("Out for delivery")
        'out_for_delivery'
        >>> map_tracking_status("Delivery attempted - left card")
        'exception'
    """
    if not event_description:
        return 'in_transit'

    description_lower = event_description.lower()

    # Check each pattern
    for pattern, platform_status in STATUS_PATTERNS.items():
        if pattern in description_lower:
            return platform_status

    # Default to in_transit if no pattern matches
    return 'in_transit'


def parse_auspost_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse Australia Post date string to Python date object.

    Args:
        date_str: Date string in various formats

    Returns:
        date: Parsed date or None

    Example:
        >>> parse_auspost_date("2025-10-24")
        datetime.date(2025, 10, 24)
    """
    if not date_str:
        return None

    try:
        parsed = date_parser.parse(date_str)
        return parsed.date()
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None


def parse_auspost_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Australia Post datetime string to Python datetime object.

    Args:
        datetime_str: Datetime string in various formats

    Returns:
        datetime: Parsed datetime or None

    Example:
        >>> parse_auspost_datetime("2025-10-24T14:30:00+11:00")
        datetime.datetime(2025, 10, 24, 14, 30, 0, tzinfo=...)
    """
    if not datetime_str:
        return None

    try:
        return date_parser.parse(datetime_str)
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
        return None


def validate_postcode(postcode: str, country_code: str = 'AU') -> bool:
    """
    Validate postcode format.

    Australia: 4 digits

    Args:
        postcode: Postcode string
        country_code: Country code (default AU)

    Returns:
        bool: True if valid format
    """
    if country_code == 'AU':
        # Australian postcodes are 4 digits
        pattern = r'^\d{4}$'
        return bool(re.match(pattern, str(postcode)))

    # For other countries, basic validation
    return len(str(postcode)) >= 3


def validate_tracking_number(tracking_number: str) -> bool:
    """
    Validate Australia Post tracking number format.

    Australia Post tracking numbers are typically:
    - 13 characters alphanumeric
    - Format: 2 letters + 9 digits + 2 letters (e.g., AA123456789AU)

    Args:
        tracking_number: Tracking number string

    Returns:
        bool: True if valid format
    """
    # Remove spaces and convert to uppercase
    tracking = str(tracking_number).replace(' ', '').upper()

    # Standard format: 2 letters + 9 digits + 2 letters (13 chars)
    if re.match(r'^[A-Z]{2}\d{9}[A-Z]{2}$', tracking):
        return True

    # Alternative formats (numeric only)
    if tracking.isdigit() and 10 <= len(tracking) <= 20:
        return True

    return False


def get_product_name(product_code: str) -> str:
    """
    Get human-readable name for product code.

    Args:
        product_code: Australia Post product code

    Returns:
        str: Display name

    Example:
        >>> get_product_name('AUS_PARCEL_EXPRESS')
        'Express Post'
    """
    return str(PRODUCT_CODES.get(product_code, product_code))


def format_money(amount: float, currency: str = 'AUD') -> str:
    """
    Format money amount for display.

    Args:
        amount: Dollar amount
        currency: Currency code (default AUD)

    Returns:
        str: Formatted amount

    Example:
        >>> format_money(12.50)
        '$12.50'
    """
    if currency in ['AUD', 'USD']:
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency}"


def kg_to_grams(kg: float) -> float:
    """Convert kilograms to grams."""
    return kg * 1000


def grams_to_kg(grams: float) -> float:
    """Convert grams to kilograms."""
    return grams / 1000


def cm_to_mm(cm: float) -> float:
    """Convert centimeters to millimeters."""
    return cm * 10


def mm_to_cm(mm: float) -> float:
    """Convert millimeters to centimeters."""
    return mm / 10


def pounds_to_kg(pounds: float) -> float:
    """Convert pounds to kilograms."""
    return pounds * 0.453592


def kg_to_pounds(kg: float) -> float:
    """Convert kilograms to pounds."""
    return kg / 0.453592


def inches_to_cm(inches: float) -> float:
    """Convert inches to centimeters."""
    return inches * 2.54


def cm_to_inches(cm: float) -> float:
    """Convert centimeters to inches."""
    return cm / 2.54


def extract_error_message(response_data: Dict[str, Any]) -> str:
    """
    Extract human-readable error message from API response.

    Args:
        response_data: Response JSON data

    Returns:
        str: Error message

    Example:
        >>> data = {"error": {"message": "Invalid account number"}}
        >>> extract_error_message(data)
        'Invalid account number'
    """
    if not response_data:
        return "Unknown error"

    # Try various error message locations
    if isinstance(response_data, dict):
        # Format 1: {error: {message}}
        if 'error' in response_data:
            error = response_data['error']
            if isinstance(error, dict):
                return error.get('message', str(error))
            return str(error)

        # Format 2: {errorMessage}
        if 'errorMessage' in response_data:
            return response_data['errorMessage']

        # Format 3: {message}
        if 'message' in response_data:
            return response_data['message']

        # Format 4: {errors: [{message}]}
        if 'errors' in response_data and isinstance(response_data['errors'], list):
            if response_data['errors']:
                first_error = response_data['errors'][0]
                if isinstance(first_error, dict):
                    return first_error.get('message', str(first_error))

    return str(response_data)
