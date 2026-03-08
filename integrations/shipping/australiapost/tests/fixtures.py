"""
Test Fixtures and Mock Data for Australia Post Provider v2.0.0

Provides reusable test data, mock responses, and fixtures for all test suites.

Author: Spwig
Version: 2.0.0
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock


# =============================================================================
# Account Test Data
# =============================================================================

# eParcel account (10-digit, prefix 2)
EPARCEL_CREDENTIALS = {
    'api_key': '601a4032-6dbd-46aa-9c6c-8c6dacca5e61',
    'api_password': 'test_password',
    'account_number': '2004952470',
    'account_type': 'eparcel',
    'environment': 'test'
}

# StarTrack account (8-digit)
STARTRACK_CREDENTIALS = {
    'api_key': '701b5043-7dcf-57bb-9d7d-9d7ebcdb6f72',
    'api_password': 'test_password',
    'account_number': '12345678',
    'account_type': 'startrack',
    'environment': 'test'
}

# Same Day account (10-digit, prefix 3)
SAME_DAY_CREDENTIALS = {
    'api_key': '801c6154-8eeg-68cc-0e8e-0e8fcdec7g83',
    'api_password': 'test_password',
    'account_number': '3005063581',
    'account_type': 'same_day',
    'environment': 'test'
}

# On Demand account (10-digit, prefix 1)
ON_DEMAND_CREDENTIALS = {
    'api_key': '901d7265-9ffh-79dd-1f9f-1f9gdeed8h94',
    'api_password': 'test_password',
    'account_number': '1006174692',
    'account_type': 'on_demand',
    'environment': 'test'
}


# =============================================================================
# Address Test Data
# =============================================================================

MELBOURNE_ADDRESS = {
    'street': '123 Collins Street',
    'suburb': 'Melbourne',
    'state': 'VIC',
    'postcode': '3000',
    'country': 'AU'
}

SYDNEY_ADDRESS = {
    'street': '456 George Street',
    'suburb': 'Sydney',
    'state': 'NSW',
    'postcode': '2000',
    'country': 'AU'
}

BRISBANE_ADDRESS = {
    'street': '789 Queen Street',
    'suburb': 'Brisbane',
    'state': 'QLD',
    'postcode': '4000',
    'country': 'AU'
}

PERTH_ADDRESS = {
    'street': '321 Murray Street',
    'suburb': 'Perth',
    'state': 'WA',
    'postcode': '6000',
    'country': 'AU'
}

ADELAIDE_ADDRESS = {
    'street': '654 King William Street',
    'suburb': 'Adelaide',
    'state': 'SA',
    'postcode': '5000',
    'country': 'AU'
}


# =============================================================================
# Item/Parcel Test Data
# =============================================================================

def create_test_item(
    weight: float = 1.5,
    length: int = 20,
    width: int = 15,
    height: int = 10,
    item_reference: str = 'TEST-ITEM-001'
) -> Dict[str, Any]:
    """Create a test item/parcel."""
    return {
        'weight': weight,
        'length': length,
        'width': width,
        'height': height,
        'item_reference': item_reference,
        'item_description': 'Test Item'
    }


STANDARD_ITEM = create_test_item()

HEAVY_ITEM = create_test_item(weight=15.0, length=50, width=40, height=30)

LARGE_ITEM = create_test_item(weight=5.0, length=100, width=60, height=50)


# =============================================================================
# Shipment Test Data
# =============================================================================

def create_test_shipment_data(
    from_address: Dict[str, str] = MELBOURNE_ADDRESS,
    to_address: Dict[str, str] = SYDNEY_ADDRESS,
    items: List[Dict[str, Any]] = None,
    service_code: str = 'AUS_PARCEL_EXPRESS',
    reference: str = 'TEST-SHIP-001'
) -> Dict[str, Any]:
    """Create test shipment data."""
    if items is None:
        items = [STANDARD_ITEM]

    return {
        'from': from_address,
        'to': to_address,
        'items': items,
        'service_code': service_code,
        'shipment_reference': reference,
        'customer_reference_1': 'CUST-REF-001',
        'customer_reference_2': 'ORDER-12345'
    }


# =============================================================================
# Mock API Responses
# =============================================================================

def create_mock_shipment_response(
    shipment_id: str = 'SHIP-12345',
    tracking_number: str = 'AA123456789AU',
    status: str = 'created'
) -> Dict[str, Any]:
    """Create mock shipment API response."""
    return {
        'shipment_id': shipment_id,
        'tracking_number': tracking_number,
        'status': status,
        'created_at': datetime.utcnow().isoformat(),
        'items': [
            {
                'item_id': 'ITEM-001',
                'weight': 1.5,
                'dimensions': {
                    'length': 20,
                    'width': 15,
                    'height': 10
                }
            }
        ],
        'from_address': MELBOURNE_ADDRESS,
        'to_address': SYDNEY_ADDRESS,
        'total_charge': 12.50,
        'currency': 'AUD'
    }


def create_mock_order_response(
    order_id: str = 'ORDER-12345',
    shipment_ids: List[str] = None,
    status: str = 'created'
) -> Dict[str, Any]:
    """Create mock order API response."""
    if shipment_ids is None:
        shipment_ids = ['SHIP-001', 'SHIP-002']

    return {
        'order_id': order_id,
        'status': status,
        'created_at': datetime.utcnow().isoformat(),
        'shipment_ids': shipment_ids,
        'shipment_count': len(shipment_ids),
        'total_items': len(shipment_ids) * 5,  # Assume 5 items per shipment
        'order_reference': 'TEST-ORDER-001',
        'manifest_url': f'https://api.auspost.com.au/manifests/{order_id}.pdf'
    }


def create_mock_pickup_response(
    pickup_id: str = 'PICKUP-12345',
    pickup_date: str = None,
    time_slot: str = 'morning'
) -> Dict[str, Any]:
    """Create mock pickup API response."""
    if pickup_date is None:
        pickup_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    return {
        'pickup_id': pickup_id,
        'status': 'scheduled',
        'pickup_date': pickup_date,
        'time_slot': time_slot,
        'time_window': '08:00-12:00' if time_slot == 'morning' else '12:00-17:00',
        'pickup_address': MELBOURNE_ADDRESS,
        'shipment_ids': ['SHIP-001', 'SHIP-002'],
        'created_at': datetime.utcnow().isoformat()
    }


def create_mock_validation_response(
    valid: bool = True,
    suburb: str = 'MELBOURNE',
    state: str = 'VIC',
    postcode: str = '3000'
) -> Dict[str, Any]:
    """Create mock suburb validation response."""
    response = {
        'valid': valid,
        'suburb': suburb.upper(),
        'state': state.upper(),
        'postcode': postcode,
        'suggestions': []
    }

    if not valid:
        response['suggestions'] = [
            {'suburb': 'MELBOURNE', 'state': 'VIC', 'postcode': '3000'},
            {'suburb': 'MELBOURNE', 'state': 'VIC', 'postcode': '3001'}
        ]

    return response


def create_mock_serviceability_response(
    serviceable: bool = True,
    service_code: str = 'AUS_PARCEL_EXPRESS'
) -> Dict[str, Any]:
    """Create mock serviceability response."""
    return {
        'serviceable': serviceable,
        'address': SYDNEY_ADDRESS,
        'service_code': service_code,
        'restrictions': [],
        'alternatives': [] if serviceable else ['AUS_PARCEL_REGULAR'],
        'delivery_days': 1 if serviceable else None
    }


def create_mock_price_response(
    base_price: float = 10.00,
    service_code: str = 'AUS_PARCEL_EXPRESS'
) -> Dict[str, Any]:
    """Create mock pricing response."""
    surcharges_total = base_price * 0.1  # 10% surcharge
    tax_total = (base_price + surcharges_total) * 0.1  # 10% GST
    total = base_price + surcharges_total + tax_total

    return {
        'base_price': base_price,
        'surcharges': [
            {'type': 'fuel', 'name': 'Fuel Surcharge', 'amount': surcharges_total}
        ],
        'surcharges_total': surcharges_total,
        'taxes': {'gst': tax_total},
        'tax_total': tax_total,
        'total': total,
        'currency': 'AUD',
        'service_code': service_code,
        'service_name': 'Parcel Post Express'
    }


def create_mock_eta_response(
    estimated_days: int = 1,
    service_code: str = 'AUS_PARCEL_EXPRESS'
) -> Dict[str, Any]:
    """Create mock ETA response."""
    delivery_date = (datetime.now() + timedelta(days=estimated_days)).strftime('%Y-%m-%d')

    return {
        'estimated_delivery_date': delivery_date,
        'estimated_days': estimated_days,
        'service_code': service_code,
        'delivery_window': '9:00-17:00',
        'guarantees': ['next_day'] if estimated_days == 1 else [],
        'cutoff_time': '15:00',
        'business_days': True
    }


# =============================================================================
# Mock Auth Client
# =============================================================================

class MockAuthClient:
    """Mock authentication client for testing."""

    def __init__(self, credentials: Dict[str, Any]):
        """Initialize mock auth client."""
        self.credentials = credentials
        self.api_key = credentials.get('api_key')
        self.api_password = credentials.get('api_password')
        self.account_number = credentials.get('account_number')

    def get_headers(self, include_account: bool = True) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.api_key}:{self.api_password}'
        }

        if include_account:
            headers['Account-Number'] = self.account_number

        return headers

    def test_authentication(self) -> bool:
        """Test authentication."""
        return True

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Mock API request.

        Returns mock responses based on endpoint.
        """
        # Return different mock responses based on endpoint
        if '/shipments' in endpoint and method == 'POST':
            return create_mock_shipment_response()
        elif '/orders' in endpoint and method == 'POST':
            return create_mock_order_response()
        elif '/pickups' in endpoint and method == 'POST':
            return create_mock_pickup_response()
        elif '/postcode/validate' in endpoint:
            return create_mock_validation_response()
        elif '/serviceability' in endpoint:
            return create_mock_serviceability_response()
        elif '/prices/items' in endpoint:
            return create_mock_price_response()
        elif '/eta' in endpoint:
            return create_mock_eta_response()
        else:
            return {}


def create_mock_auth_client(credentials: Dict[str, Any] = None) -> MockAuthClient:
    """Create mock auth client for testing."""
    if credentials is None:
        credentials = EPARCEL_CREDENTIALS
    return MockAuthClient(credentials)


# =============================================================================
# Test Helpers
# =============================================================================

def generate_shipment_ids(count: int, prefix: str = 'SHIP') -> List[str]:
    """Generate list of test shipment IDs."""
    return [f'{prefix}-{str(i).zfill(5)}' for i in range(1, count + 1)]


def generate_item_ids(count: int, prefix: str = 'ITEM') -> List[str]:
    """Generate list of test item IDs."""
    return [f'{prefix}-{str(i).zfill(3)}' for i in range(1, count + 1)]


def create_large_shipment_batch(item_count: int) -> List[Dict[str, Any]]:
    """
    Create a large batch of test shipments.

    Useful for testing order splitting and basket limits.
    """
    shipments = []

    for i in range(item_count):
        shipment = create_test_shipment_data(
            reference=f'BATCH-SHIP-{str(i).zfill(5)}'
        )
        shipments.append(shipment)

    return shipments
