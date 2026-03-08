"""
Canada Post Provider Utilities

Helper functions for Canada Post API integration including service code mappings,
formatters, validators, and status mappers.

Author: Spwig
Version: 1.0.0
"""

import re
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from django.utils import timezone


# Service code mappings
SERVICE_CODES = {
    # Domestic Services (Canada)
    'DOM.RP': 'Regular Parcel',
    'DOM.EP': 'Expedited Parcel',
    'DOM.XP': 'Xpresspost',
    'DOM.XP.CERT': 'Xpresspost Certified',
    'DOM.PC': 'Priority',
    'DOM.LW': 'Library Materials',

    # USA Services
    'USA.EP': 'Expedited Parcel USA',
    'USA.PW.ENV': 'Priority Worldwide Envelope USA',
    'USA.PW.PAK': 'Priority Worldwide Pak USA',
    'USA.PW.PARCEL': 'Priority Worldwide Parcel USA',
    'USA.XP': 'Xpresspost USA',

    # International Services
    'INT.XP': 'Xpresspost International',
    'INT.TP': 'Tracked Packet International',
    'INT.IP.AIR': 'International Parcel Air',
    'INT.IP.SURF': 'International Parcel Surface',
    'INT.PW.ENV': 'Priority Worldwide Envelope Int\'l',
    'INT.PW.PAK': 'Priority Worldwide Pak Int\'l',
    'INT.PW.PARCEL': 'Priority Worldwide Parcel Int\'l',
}


# Options code mappings
OPTIONS_CODES = {
    # Delivery Options
    'SO': 'Signature Required',
    'D2PO': 'Deliver to Post Office',
    'LAD': 'Leave at Door',
    'DNS': 'Do Not Safe Drop',
    'PA18': 'Proof of Age 18',
    'PA19': 'Proof of Age 19',
    'HFP': 'Card for Pickup',
    'DC': 'Delivery Confirmation',

    # Insurance & Protection
    'COV': 'Coverage/Insurance',
    'COD': 'Cash on Delivery',

    # Special Handling
    'RASE': 'Return at Sender\'s Expense',
    'RTS': 'Return to Sender',
}


def format_canadian_postal_code(code: str) -> str:
    """
    Format Canadian postal code to standard format (A1A 1A1).

    Args:
        code: Postal code (with or without space)

    Returns:
        Formatted postal code with space

    Example:
        >>> format_canadian_postal_code('K1A0B1')
        'K1A 0B1'
        >>> format_canadian_postal_code('k1a 0b1')
        'K1A 0B1'
    """
    # Remove spaces and convert to uppercase
    code = code.replace(' ', '').replace('-', '').upper()

    # Validate format (basic check)
    if len(code) != 6:
        return code  # Return as-is if invalid

    # Insert space after 3rd character
    return f"{code[:3]} {code[3:]}"


def format_us_zip_code(code: str) -> str:
    """
    Format US ZIP code to standard format.

    Args:
        code: ZIP code (5 or 9 digits)

    Returns:
        Formatted ZIP code

    Example:
        >>> format_us_zip_code('12345')
        '12345'
        >>> format_us_zip_code('123456789')
        '12345-6789'
    """
    # Remove any existing formatting
    code = code.replace('-', '').replace(' ', '').strip()

    # Format based on length
    if len(code) == 9:
        return f"{code[:5]}-{code[5:]}"
    else:
        return code


def validate_customer_number(number: str) -> bool:
    """
    Validate Canada Post customer number format.

    Customer numbers are exactly 10 digits.

    Args:
        number: Customer number to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_customer_number('1234567890')
        True
        >>> validate_customer_number('123456')
        False
    """
    if not number:
        return False

    # Remove any spaces or dashes
    cleaned = number.replace(' ', '').replace('-', '')

    # Must be exactly 10 digits
    return cleaned.isdigit() and len(cleaned) == 10


def validate_postal_code(code: str, country: str = 'CA') -> bool:
    """
    Validate postal/ZIP code format.

    Args:
        code: Postal code to validate
        country: Country code ('CA', 'US', etc.)

    Returns:
        True if valid format

    Example:
        >>> validate_postal_code('K1A 0B1', 'CA')
        True
        >>> validate_postal_code('12345', 'US')
        True
    """
    if not code:
        return False

    code = code.strip()

    if country == 'CA':
        # Canadian postal code: A1A 1A1 or A1A1A1
        pattern = r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$'
        return bool(re.match(pattern, code.upper()))
    elif country == 'US':
        # US ZIP: 12345 or 12345-6789
        code_clean = code.replace('-', '').replace(' ', '')
        return code_clean.isdigit() and len(code_clean) in (5, 9)
    else:
        # For other countries, just check it's not empty
        return len(code) > 0


def convert_weight_to_kg(grams: float) -> float:
    """
    Convert weight from grams to kilograms.

    Canada Post API expects weight in kilograms with 3 decimal places.

    Args:
        grams: Weight in grams

    Returns:
        Weight in kilograms

    Example:
        >>> convert_weight_to_kg(5000)
        5.0
        >>> convert_weight_to_kg(250)
        0.25
    """
    return round(grams / 1000.0, 3)


def convert_dimensions_to_cm(mm: float) -> float:
    """
    Convert dimensions from millimeters to centimeters.

    Canada Post API expects dimensions in centimeters with 1 decimal place.

    Args:
        mm: Dimension in millimeters

    Returns:
        Dimension in centimeters

    Example:
        >>> convert_dimensions_to_cm(300)
        30.0
        >>> convert_dimensions_to_cm(125)
        12.5
    """
    return round(mm / 10.0, 1)


def detect_customer_type(customer_number: str, contract_id: Optional[str]) -> str:
    """
    Detect whether customer is contract or non-contract.

    Args:
        customer_number: 10-digit customer number
        contract_id: Optional contract ID

    Returns:
        'contract' or 'non_contract'

    Example:
        >>> detect_customer_type('1234567890', '12345678')
        'contract'
        >>> detect_customer_type('1234567890', None)
        'non_contract'
        >>> detect_customer_type('1234567890', '')
        'non_contract'
    """
    if contract_id and contract_id.strip():
        return 'contract'
    else:
        return 'non_contract'


def map_canada_post_status(status_text: str) -> str:
    """
    Map Canada Post tracking status to platform status codes.

    Platform statuses:
    - pending: Label created, not yet in system
    - in_transit: Package moving through network
    - out_for_delivery: Out with courier
    - delivered: Successfully delivered
    - failed: Delivery failed
    - returned: Returned to sender
    - cancelled: Shipment cancelled

    Args:
        status_text: Canada Post status description

    Returns:
        Platform status code

    Example:
        >>> map_canada_post_status('Item processed')
        'in_transit'
        >>> map_canada_post_status('Delivered')
        'delivered'
    """
    status_lower = status_text.lower().strip()

    # Delivered
    if any(keyword in status_lower for keyword in ['delivered', 'delivery confirmed']):
        return 'delivered'

    # Out for delivery
    if any(keyword in status_lower for keyword in ['out for delivery', 'on vehicle']):
        return 'out_for_delivery'

    # Failed delivery
    if any(keyword in status_lower for keyword in ['delivery failure', 'attempted', 'notice card left']):
        return 'failed'

    # Returned to sender
    if any(keyword in status_lower for keyword in ['returned', 'return to sender', 'rts']):
        return 'returned'

    # In transit
    if any(keyword in status_lower for keyword in [
        'in transit', 'processed', 'arrived', 'departed',
        'sorting', 'forwarded', 'customs'
    ]):
        return 'in_transit'

    # Pending/Created
    if any(keyword in status_lower for keyword in ['electronic info submitted', 'info received']):
        return 'pending'

    # Cancelled
    if any(keyword in status_lower for keyword in ['cancelled', 'void']):
        return 'cancelled'

    # Default to in_transit for unknown statuses
    return 'in_transit'


def parse_canada_post_date(date_str: str) -> Optional[datetime]:
    """
    Parse Canada Post date string to datetime.

    Canada Post uses format: YYYY-MM-DD

    Args:
        date_str: Date string from Canada Post

    Returns:
        Datetime object or None if parsing fails

    Example:
        >>> parse_canada_post_date('2025-10-23')
        datetime.datetime(2025, 10, 23, 0, 0)
    """
    if not date_str:
        return None

    try:
        # Parse YYYY-MM-DD format
        dt = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        # Make timezone aware
        return timezone.make_aware(dt)
    except (ValueError, AttributeError):
        return None


def parse_canada_post_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse Canada Post datetime string to datetime.

    Canada Post uses format: YYYY-MM-DD HH:MM:SS

    Args:
        datetime_str: Datetime string from Canada Post

    Returns:
        Datetime object or None if parsing fails

    Example:
        >>> parse_canada_post_datetime('2025-10-23 14:30:00')
        datetime.datetime(2025, 10, 23, 14, 30)
    """
    if not datetime_str:
        return None

    try:
        # Try with time first
        if ' ' in datetime_str:
            dt = datetime.strptime(datetime_str.strip(), '%Y-%m-%d %H:%M:%S')
        else:
            # Fallback to date only
            dt = datetime.strptime(datetime_str.strip(), '%Y-%m-%d')

        # Make timezone aware
        return timezone.make_aware(dt)
    except (ValueError, AttributeError):
        # Try parsing date only
        return parse_canada_post_date(datetime_str)


def get_service_name(service_code: str) -> str:
    """
    Get human-readable service name from service code.

    Args:
        service_code: Canada Post service code

    Returns:
        Service name or code if not found

    Example:
        >>> get_service_name('DOM.EP')
        'Expedited Parcel'
        >>> get_service_name('UNKNOWN')
        'UNKNOWN'
    """
    return SERVICE_CODES.get(service_code, service_code)


def get_option_name(option_code: str) -> str:
    """
    Get human-readable option name from option code.

    Args:
        option_code: Canada Post option code

    Returns:
        Option name or code if not found

    Example:
        >>> get_option_name('SO')
        'Signature Required'
        >>> get_option_name('UNKNOWN')
        'UNKNOWN'
    """
    return OPTIONS_CODES.get(option_code, option_code)


def format_parcel_for_api(parcel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parcel data for Canada Post API.

    Converts platform parcel format to Canada Post expected format.

    Args:
        parcel: Platform parcel dictionary with:
            - weight: Weight in grams
            - length: Length in mm
            - width: Width in mm
            - height: Height in mm

    Returns:
        Formatted parcel dictionary for API:
            - weight: Weight in kg
            - length: Length in cm
            - width: Width in cm
            - height: Height in cm

    Example:
        >>> parcel = {'weight': 5000, 'length': 300, 'width': 200, 'height': 150}
        >>> format_parcel_for_api(parcel)
        {'weight': 5.0, 'length': 30.0, 'width': 20.0, 'height': 15.0}
    """
    formatted = {}

    # Convert weight from grams to kg
    if 'weight' in parcel:
        formatted['weight'] = convert_weight_to_kg(parcel['weight'])

    # Convert dimensions from mm to cm
    if 'length' in parcel:
        formatted['length'] = convert_dimensions_to_cm(parcel['length'])

    if 'width' in parcel:
        formatted['width'] = convert_dimensions_to_cm(parcel['width'])

    if 'height' in parcel:
        formatted['height'] = convert_dimensions_to_cm(parcel['height'])

    return formatted


def extract_text_from_xml_element(element, default: str = '') -> str:
    """
    Safely extract text from XML element.

    Args:
        element: XML element or None
        default: Default value if element is None or has no text

    Returns:
        Element text or default value
    """
    if element is None:
        return default
    return element.text if element.text else default


def calculate_total_price(base: str, gst: str = '0', pst: str = '0', hst: str = '0') -> Decimal:
    """
    Calculate total price from Canada Post price components.

    Args:
        base: Base price
        gst: GST amount
        pst: PST amount
        hst: HST amount

    Returns:
        Total price as Decimal

    Example:
        >>> calculate_total_price('12.50', '0.63', '0', '0')
        Decimal('13.13')
    """
    total = Decimal('0.00')

    try:
        total += Decimal(base)
    except (ValueError, TypeError):
        pass

    try:
        total += Decimal(gst)
    except (ValueError, TypeError):
        pass

    try:
        total += Decimal(pst)
    except (ValueError, TypeError):
        pass

    try:
        total += Decimal(hst)
    except (ValueError, TypeError):
        pass

    return total
