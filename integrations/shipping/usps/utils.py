"""
USPS Provider Utilities

Helper functions for data transformation, validation, and formatting.
"""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from dateutil import parser as date_parser
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


# USPS Mail Class mappings
MAIL_CLASSES = {
    'USPS_GROUND_ADVANTAGE': _('USPS Ground Advantage™'),
    'PRIORITY_MAIL': _('Priority Mail®'),
    'PRIORITY_MAIL_EXPRESS': _('Priority Mail Express®'),
    'PARCEL_SELECT': _('Parcel Select®'),
    'PARCEL_SELECT_LIGHTWEIGHT': _('Parcel Select Lightweight®'),
    'USPS_CONNECT_LOCAL': _('USPS Connect® Local'),
    'USPS_CONNECT_MAIL': _('USPS Connect® Mail'),
    'USPS_CONNECT_REGIONAL': _('USPS Connect® Regional'),
    'MEDIA_MAIL': _('Media Mail®'),
    'LIBRARY_MAIL': _('Library Mail'),
    'BOUND_PRINTED_MATTER': _('Bound Printed Matter'),
    'USPS_GROUND_ADVANTAGE_RETURN_SERVICE': _('Ground Advantage Return'),
    'PRIORITY_MAIL_RETURN_SERVICE': _('Priority Mail Return'),
    'PRIORITY_MAIL_EXPRESS_RETURN_SERVICE': _('Priority Mail Express Return'),
    # Deprecated
    'FIRST-CLASS_PACKAGE_SERVICE': _('First-Class Package Service'),
    'USPS_RETAIL_GROUND': _('USPS Retail Ground'),
}


# Processing categories
PROCESSING_CATEGORIES = {
    'MACHINABLE': 'Machinable',
    'NONSTANDARD': 'Non-machinable'
}


# Price types
PRICE_TYPES = {
    'RETAIL': 'Retail',
    'COMMERCIAL': 'Commercial',
    'COMMERCIAL_PLUS': 'Commercial Plus'
}


# Status text patterns to platform status mapping
STATUS_PATTERNS = {
    'delivered': 'delivered',
    'out for delivery': 'out_for_delivery',
    'in transit': 'in_transit',
    'accepted': 'in_transit',
    'arrived': 'in_transit',
    'departed': 'in_transit',
    'sorting': 'in_transit',
    'notice left': 'exception',
    'alert': 'exception',
    'return': 'exception',
    'available for pickup': 'available_for_pickup',
    'held': 'exception',
    'refused': 'exception',
    'undeliverable': 'exception',
}


def map_usps_status(status_text: str) -> str:
    """
    Map USPS status text to platform status code.

    USPS uses descriptive text (not codes) for status.
    This function matches text patterns to standardized platform statuses.

    Args:
        status_text: USPS status description

    Returns:
        str: Platform status code (delivered, in_transit, exception, etc.)

    Example:
        >>> map_usps_status("Your item was delivered")
        'delivered'
        >>> map_usps_status("Out for Delivery")
        'out_for_delivery'
    """
    if not status_text:
        return 'in_transit'

    status_lower = status_text.lower()

    # Check each pattern
    for pattern, platform_status in STATUS_PATTERNS.items():
        if pattern in status_lower:
            return platform_status

    # Default to in_transit if no pattern matches
    return 'in_transit'


def format_address(address: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format address dict to USPS API format.

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
        dict: USPS-formatted address

    Example:
        {
            "streetAddress": "123 Main St",
            "streetAddressAbbreviation": "Apt 4",
            "city": "Springfield",
            "state": "IL",
            "ZIPCode": "62701"
        }
    """
    usps_address = {}

    # Name/Company
    if address.get('company'):
        usps_address['firm'] = address['company'][:50]  # Max 50 chars
    elif address.get('name'):
        usps_address['firm'] = address['name'][:50]

    # Street address
    if address.get('street_line1'):
        usps_address['streetAddress'] = address['street_line1'][:50]

    if address.get('street_line2'):
        usps_address['streetAddressAbbreviation'] = address['street_line2'][:50]

    if address.get('street_line3'):
        # USPS doesn't have line3, append to line2 if space permits
        if 'streetAddressAbbreviation' in usps_address:
            combined = f"{usps_address['streetAddressAbbreviation']}, {address['street_line3']}"
            usps_address['streetAddressAbbreviation'] = combined[:50]
        else:
            usps_address['streetAddressAbbreviation'] = address['street_line3'][:50]

    # City
    if address.get('city'):
        usps_address['city'] = address['city'][:50]

    # State (2-letter code)
    if address.get('state_code'):
        usps_address['state'] = address['state_code'][:2].upper()

    # ZIP Code (5 or 9 digits)
    if address.get('postal_code'):
        zip_code = clean_zip_code(address['postal_code'])
        usps_address['ZIPCode'] = zip_code

    return usps_address


def clean_zip_code(zip_code: str) -> str:
    """
    Clean and format ZIP code for USPS API.

    Accepts formats:
    - 12345
    - 12345-6789
    - 12345 6789

    Returns:
        str: Cleaned ZIP code (5 or 9 digits)

    Example:
        >>> clean_zip_code("12345-6789")
        '12345-6789'
        >>> clean_zip_code("12345 6789")
        '12345-6789'
    """
    # Remove all non-digit characters except hyphen
    cleaned = re.sub(r'[^\d-]', '', str(zip_code))

    # If no hyphen but has 9 digits, add hyphen
    if '-' not in cleaned and len(cleaned) == 9:
        cleaned = f"{cleaned[:5]}-{cleaned[5:]}"

    return cleaned


def format_parcel(parcel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parcel dict to USPS API format.

    Args:
        parcel: Platform parcel dict with keys:
            - weight_oz (or weight_lb)
            - length_in
            - width_in
            - height_in

    Returns:
        dict: USPS-formatted package description

    Example:
        {
            "weight": 10.5,
            "length": 12.0,
            "width": 8.0,
            "height": 6.0
        }
    """
    package = {}

    # Weight (convert to pounds)
    weight_lb = parcel.get('weight_lb', 0)
    weight_oz = parcel.get('weight_oz', 0)
    total_weight = weight_lb + (weight_oz / 16.0)

    if total_weight > 0:
        package['weight'] = round(total_weight, 2)

    # Dimensions (in inches)
    if parcel.get('length_in'):
        package['length'] = round(float(parcel['length_in']), 2)

    if parcel.get('width_in'):
        package['width'] = round(float(parcel['width_in']), 2)

    if parcel.get('height_in'):
        package['height'] = round(float(parcel['height_in']), 2)

    return package


def determine_processing_category(length: float, width: float, height: float, weight: float) -> str:
    """
    Determine if package is MACHINABLE or NONSTANDARD based on dimensions.

    Based on USPS DMM 201 specifications.

    Args:
        length: Length in inches
        width: Width in inches
        height: Height (thickness) in inches
        weight: Weight in pounds

    Returns:
        str: 'MACHINABLE' or 'NONSTANDARD'
    """
    # Irregular shapes or very large/small dimensions = NONSTANDARD
    if any([
        length > 27,  # Over 27 inches long
        width > 17,   # Over 17 inches wide
        height > 17,  # Over 17 inches high
        weight > 35,  # Over 35 lbs
        length < 5,   # Under 5 inches
        width < 3.5,  # Under 3.5 inches
        height < 0.007,  # Too thin
    ]):
        return 'NONSTANDARD'

    return 'MACHINABLE'


def parse_usps_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse USPS date string to Python date object.

    Args:
        date_str: Date string in various formats

    Returns:
        date: Parsed date or None

    Example:
        >>> parse_usps_date("2025-10-23")
        datetime.date(2025, 10, 23)
    """
    if not date_str:
        return None

    try:
        parsed = date_parser.parse(date_str)
        return parsed.date()
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None


def parse_usps_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parse USPS datetime string to Python datetime object.

    Args:
        datetime_str: Datetime string in various formats

    Returns:
        datetime: Parsed datetime or None

    Example:
        >>> parse_usps_datetime("2025-10-23T14:30:00Z")
        datetime.datetime(2025, 10, 23, 14, 30, 0)
    """
    if not datetime_str:
        return None

    try:
        return date_parser.parse(datetime_str)
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
        return None


def validate_zip_code(zip_code: str) -> bool:
    """
    Validate ZIP code format.

    Accepts:
    - 5-digit: 12345
    - 9-digit: 12345-6789

    Args:
        zip_code: ZIP code string

    Returns:
        bool: True if valid format
    """
    pattern = r'^\d{5}(-\d{4})?$'
    return bool(re.match(pattern, str(zip_code)))


def validate_tracking_number(tracking_number: str) -> bool:
    """
    Validate USPS tracking number format.

    USPS uses various formats:
    - 20 digits: 12345678901234567890
    - 22 digits: 9400100000000000000000
    - Various service-specific formats

    Args:
        tracking_number: Tracking number string

    Returns:
        bool: True if valid format
    """
    # Remove spaces and convert to uppercase
    tracking = str(tracking_number).replace(' ', '').upper()

    # Check if all digits and reasonable length (20-34 chars)
    if tracking.isdigit() and 20 <= len(tracking) <= 34:
        return True

    # Check for alphanumeric formats (some USPS services)
    if re.match(r'^[A-Z0-9]{20,34}$', tracking):
        return True

    return False


def get_mail_class_name(mail_class_code: str) -> str:
    """
    Get human-readable name for mail class code.

    Args:
        mail_class_code: USPS mail class code

    Returns:
        str: Display name

    Example:
        >>> get_mail_class_name('USPS_GROUND_ADVANTAGE')
        'USPS Ground Advantage™'
    """
    return str(MAIL_CLASSES.get(mail_class_code, mail_class_code))


def format_money(amount: float, currency: str = 'USD') -> str:
    """
    Format money amount for display.

    Args:
        amount: Dollar amount
        currency: Currency code (default USD)

    Returns:
        str: Formatted amount

    Example:
        >>> format_money(12.50)
        '$12.50'
    """
    if currency == 'USD':
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency}"


def pounds_to_ounces(pounds: float) -> float:
    """Convert pounds to ounces."""
    return pounds * 16


def ounces_to_pounds(ounces: float) -> float:
    """Convert ounces to pounds."""
    return ounces / 16
