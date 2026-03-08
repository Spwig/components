"""
UPS Provider Utility Functions

Helper functions for data transformation, parsing, and validation.
"""
import re
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from dateutil import parser as date_parser


def parse_ups_date(date_string: str) -> Optional[datetime]:
    """
    Parse UPS date string to datetime object.

    UPS uses various date formats:
    - ISO 8601: "2025-10-23T14:30:00"
    - YYYYMMDD: "20251023"

    Args:
        date_string: Date string from UPS API

    Returns:
        Parsed datetime object, or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Try ISO 8601 format first
        return date_parser.parse(date_string)
    except Exception:
        try:
            # Try YYYYMMDD format
            return datetime.strptime(date_string, '%Y%m%d')
        except Exception:
            return None


def format_address(address: Dict[str, str]) -> Dict[str, Any]:
    """
    Format address dictionary for UPS API request.

    Args:
        address: Address dictionary with keys:
            - name: Recipient/sender name
            - company: Company name (optional)
            - street1: Address line 1
            - street2: Address line 2 (optional)
            - city: City
            - state: State/province code
            - postal_code: Postal/ZIP code
            - country: Country code (ISO 2-letter)
            - phone: Phone number (optional)

    Returns:
        UPS-formatted address dictionary
    """
    ups_address = {
        'AddressLine': []
    }

    # Add street address lines (max 3)
    if address.get('street1'):
        ups_address['AddressLine'].append(address['street1'])
    if address.get('street2'):
        ups_address['AddressLine'].append(address['street2'])
    if address.get('street3'):
        ups_address['AddressLine'].append(address['street3'])

    # Add city, state, postal code
    if address.get('city'):
        ups_address['City'] = address['city']
    if address.get('state'):
        ups_address['StateProvinceCode'] = address['state']
    if address.get('postal_code'):
        ups_address['PostalCode'] = address['postal_code']
    if address.get('country'):
        ups_address['CountryCode'] = address['country']

    return ups_address


def format_parcel(parcel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parcel dictionary for UPS API request.

    Args:
        parcel: Parcel dictionary with keys:
            - weight: Weight in grams
            - length: Length in cm
            - width: Width in cm
            - height: Height in cm
            - value: Declared value (Decimal)
            - currency: Currency code (optional)

    Returns:
        UPS-formatted package dictionary
    """
    ups_package = {
        'PackagingType': {
            'Code': '02',  # Customer Supplied Package
            'Description': 'Package'
        },
        'Dimensions': {
            'UnitOfMeasurement': {
                'Code': 'CM',
                'Description': 'Centimeters'
            },
            'Length': str(int(parcel.get('length', 10))),
            'Width': str(int(parcel.get('width', 10))),
            'Height': str(int(parcel.get('height', 10)))
        },
        'PackageWeight': {
            'UnitOfMeasurement': {
                'Code': 'KGS',
                'Description': 'Kilograms'
            },
            # Convert grams to kilograms
            'Weight': str(round(parcel.get('weight', 1000) / 1000, 2))
        }
    }

    # Add declared value if provided
    if parcel.get('value'):
        ups_package['PackageServiceOptions'] = {
            'DeclaredValue': {
                'CurrencyCode': parcel.get('currency', 'USD'),
                'MonetaryValue': str(parcel['value'])
            }
        }

    return ups_package


def map_ups_status(ups_status: str) -> str:
    """
    Map UPS tracking status code to platform status.

    UPS Status Codes:
    - M: Manifest Pickup
    - I: In Transit
    - X: Exception
    - D: Delivered
    - P: Pickup
    - O: Out for Delivery

    Platform Statuses:
    - created
    - in_transit
    - out_for_delivery
    - delivered
    - exception
    - returned

    Args:
        ups_status: UPS status code

    Returns:
        Platform status string
    """
    status_map = {
        'M': 'created',           # Manifest Pickup
        'MP': 'created',          # Manifest Pickup
        'I': 'in_transit',        # In Transit
        'P': 'in_transit',        # Pickup
        'O': 'out_for_delivery',  # Out for Delivery
        'D': 'delivered',         # Delivered
        'X': 'exception',         # Exception
        'RS': 'returned',         # Return to Sender
    }

    return status_map.get(ups_status, 'in_transit')


def validate_tracking_number(tracking_number: str) -> bool:
    """
    Validate UPS tracking number format.

    UPS tracking numbers follow the format:
    - 1Z + 6 alphanumeric + 10 digits (18 characters total)
    - Example: 1Z999AA10123456784

    Args:
        tracking_number: Tracking number to validate

    Returns:
        True if valid, False otherwise
    """
    if not tracking_number:
        return False

    # UPS 1Z tracking number pattern
    pattern = r'^1Z[A-Z0-9]{6}\d{10}$'

    return bool(re.match(pattern, tracking_number, re.IGNORECASE))


def calculate_billable_weight(parcels: list) -> Decimal:
    """
    Calculate total billable weight for parcels.

    Uses dimensional weight if greater than actual weight.
    Dimensional weight = (L x W x H) / 5000 (for cm to kg)

    Args:
        parcels: List of parcel dictionaries

    Returns:
        Total billable weight in kilograms
    """
    total_billable = Decimal('0')

    for parcel in parcels:
        # Actual weight in kg
        actual_weight = Decimal(str(parcel.get('weight', 1000))) / 1000

        # Dimensional weight
        length = Decimal(str(parcel.get('length', 10)))
        width = Decimal(str(parcel.get('width', 10)))
        height = Decimal(str(parcel.get('height', 10)))

        dim_weight = (length * width * height) / 5000

        # Use greater of actual or dimensional weight
        billable = max(actual_weight, dim_weight)
        total_billable += billable

    return total_billable


def parse_rate_response(rate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse UPS rate quote response into standardized format.

    Args:
        rate_data: UPS rate quote data

    Returns:
        Standardized rate dictionary
    """
    service = rate_data.get('Service', {})
    total_charges = rate_data.get('TotalCharges', {})
    service_options_charges = rate_data.get('ServiceOptionsCharges', {})

    # Parse service information
    service_code = service.get('Code', '')
    service_description = service.get('Description', '')

    # Parse charges
    currency = total_charges.get('CurrencyCode', 'USD')
    total_amount = Decimal(str(total_charges.get('MonetaryValue', '0')))

    # Parse delivery time
    delivery_time = None
    if 'TimeInTransit' in rate_data:
        delivery_time = rate_data['TimeInTransit'].get('BusinessDaysInTransit')

    return {
        'service_code': service_code,
        'service_name': service_description,
        'carrier': 'UPS',
        'rate': total_amount,
        'currency': currency,
        'delivery_days': int(delivery_time) if delivery_time else None,
        'billable_weight': None,  # Set by caller if available
    }


def parse_tracking_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse UPS tracking event into standardized format.

    Args:
        event: UPS tracking event data

    Returns:
        Standardized tracking event dictionary
    """
    # Parse timestamp
    date = event.get('Date', '')
    time = event.get('Time', '')
    timestamp_str = f"{date} {time}" if date and time else None
    timestamp = parse_ups_date(timestamp_str) if timestamp_str else None

    # Parse location
    location_parts = []
    if event.get('ActivityLocation'):
        loc = event['ActivityLocation'].get('Address', {})
        if loc.get('City'):
            location_parts.append(loc['City'])
        if loc.get('StateProvinceCode'):
            location_parts.append(loc['StateProvinceCode'])
        if loc.get('CountryCode'):
            location_parts.append(loc['CountryCode'])

    location = ', '.join(location_parts) if location_parts else None

    # Parse status
    status_type = event.get('Status', {}).get('Type', 'I')
    status = map_ups_status(status_type)

    # Parse description
    description = event.get('Status', {}).get('Description', '')

    return {
        'timestamp': timestamp,
        'status': status,
        'location': location,
        'description': description
    }
