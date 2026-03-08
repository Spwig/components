# Australia Post Shipping Provider v2.0.0

**Version:** 2.0.0
**Author:** Spwig
**License:** Proprietary

## Overview

The Australia Post Shipping Provider v2.0.0 is a production-ready, comprehensive integration with the Australia Post Shipping REST API. This version meets full Australia Post lodgement validation requirements and provides complete order management, basket management, validation services, and all product features for all four account types: eParcel, StarTrack, Same Day, and On Demand services.

## What's New in v2.0.0

### Production Workflow Compliance
- **Order Management**: Create orders from shipments with automatic splitting (>2,000 items per order)
- **Basket Management**: Track up to 10,000 items before order creation
- **Manifest Generation**: Generate order summaries and manifests for lodgement
- **Complete Validation**: Pre-flight validation for addresses, suburbs, and shipments

### Enhanced Features
- **Validation Services**: Suburb/postcode validation, serviceability checks with caching
- **Enhanced Pricing**: Individual shipment pricing, ETA calculations, service comparisons
- **Product Features**: Authority To Leave, Safe Drop, Signature requirements, Dangerous Goods, SSCC barcoding
- **Adhoc Pickups**: Schedule pickups with time slot management (morning, afternoon, all day)
- **Shipment Management**: Enhanced retrieval, filtering, pagination, updates, and deletion
- **Feature Validation**: Product-feature compatibility matrix for all services

### Four Account Type Support
1. **eParcel** (10-digit, prefix 2): Standard Australia Post services
2. **StarTrack** (8-digit): Premium express services
3. **Same Day** (10-digit, prefix 3): Same day delivery services
4. **On Demand** (10-digit, prefix 1): On-demand delivery services

## Production Workflow

Australia Post requires a specific workflow for production lodgement:

### Complete Workflow
```python
# 1. Validate address before creating shipments
result = provider.validate_suburb('Melbourne', 'VIC', '3000')
if result['valid']:
    print("Address is valid!")

# 2. Create shipments and add to basket
for order_item in order_items:
    shipment = provider._create_shipment(shipment_data)
    provider.add_to_basket(
        shipment_id=shipment['shipment_id'],
        item_count=len(order_item['items'])
    )

# 3. Check basket status
basket_status = provider.get_basket_status()
print(f"Basket: {basket_status['total_items']} items in {basket_status['total_shipments']} shipments")

# 4. Create order from basket (auto-splits if >2,000 items)
orders = provider.create_order_with_split(
    shipment_ids=basket_status['shipment_ids'],
    order_reference_prefix='ORDER-2025-001'
)

# 5. Generate labels for shipments
for order in orders:
    for shipment_id in order['shipment_ids']:
        labels = provider._create_labels(shipment_id, synchronous=True)

# 6. Get order summary/manifest
manifest = provider.get_order_summary(orders[0]['order_id'], format='json')

# 7. Track shipments
tracking = provider.get_tracking(['AA123456789AU'])
```

### Order Size Limits
- **Maximum order size**: 2,000 items per order
- **Automatic splitting**: Provider automatically splits orders exceeding 2,000 items
- **Basket capacity**: Up to 10,000 items before creating orders
- **Warning thresholds**: Warnings at 1,800 items (order) and 8,000 items (basket)

## Key Features

### Core Features (v1.0.1)
- **API Key Authentication**: HTTP Basic Auth using UUID-format API Key
- **Four Account Types**: eParcel (10-digit, prefix 2), StarTrack (8-digit), Same Day (prefix 3), On Demand (prefix 1)
- **Two-Step Label Generation**: Create shipment, then create labels
- **Rate Limiting**: Automatic rate limiting for tracking API (10 requests/60 seconds)
- **JSON Format**: Modern JSON request/response format
- **Comprehensive Error Handling**: Detailed error code parsing and exception hierarchy
- **Exponential Backoff**: Retry logic with backoff policy
- **International Support**: Customs declarations and international shipping

### v2.0.0 Enhancements

#### Order Management
- Create orders from shipments (POST /orders)
- Automatic order splitting when exceeding 2,000 items
- Order retrieval with caching
- Manifest generation (JSON, PDF, CSV formats)
- Order summary with shipment details

#### Basket Management
- Track up to 10,000 items before order creation
- Add/remove shipments from basket
- Basket locking mechanism
- State persistence with snapshots
- Real-time capacity monitoring
- Statistics and analytics

#### Validation Services
- Suburb and postcode validation (POST /postcode/validate)
- Address serviceability lookups (POST /serviceability)
- Pre-flight shipment validation (POST /shipments/validate)
- Postcode and state format validation
- Result caching with 1-hour TTL
- Validation suggestions for corrections

#### Enhanced Pricing
- Individual shipment pricing with surcharge breakdown (POST /prices/items)
- ETA calculations (POST /eta)
- Service price comparisons
- Decimal precision for accurate pricing
- Delivery date estimates

#### Product Features
- **Authority To Leave (ATL)**: Leave parcels at specified locations
- **Safe Drop**: Contactless delivery with instructions
- **Signature Requirements**: Standard or adult signature options
- **Dangerous Goods**: Full DG declaration support (class, UN number, packing group)
- **SSCC Barcoding**: 18-digit barcode support with validation
- **Delivery Instructions**: Custom delivery instructions (max 250 chars)
- **Returns Handling**: Mark shipments as returns with references
- **Feature Compatibility Matrix**: Validate features against product codes

#### Adhoc Pickup Scheduling
- Schedule pickups with address and date (POST /pickups)
- Three time slots: morning (8-12), afternoon (12-17), all day (8-17)
- Pickup retrieval and cancellation
- Date validation (not in past, max 30 days future)
- Contact information support

#### Shipment Management
- Enhanced shipment retrieval with caching (GET /shipments/{id})
- List shipments with filtering and pagination (GET /shipments)
- Update shipment details (PUT /shipments/{id})
- Delete shipments (DELETE /shipments/{id})
- Individual item operations (update/delete items)

## Account Types and Authentication

### Account Number Format by Type

#### 1. eParcel Accounts (Standard Australia Post)
- **Format**: 10 digits, prefix 2 (e.g., 2004952470)
- **Detection**: 10 digits starting with '2'
- **Services**: AUS_PARCEL_REGULAR, AUS_PARCEL_EXPRESS, AUS_PARCEL_COURIER
- **Features**: ATL, Safe Drop, Signature, DG, SSCC, Returns

#### 2. StarTrack Accounts (Premium Express)
- **Format**: 8 digits, first digit non-zero (e.g., 12345678)
- **Detection**: Exactly 8 digits, first digit ≠ '0'
- **Services**: ST_PREMIUM, ST_EXPRESS, ST_FIXED_PRICE
- **Features**: ATL, Safe Drop, Signature, DG, Transfers, Book-ins, Transit Cover, SSCC

#### 3. Same Day Accounts (Same Day Delivery)
- **Format**: 10 digits, prefix 3 (e.g., 3005063581)
- **Detection**: 10 digits starting with '3'
- **Services**: SAME_DAY_DELIVERY
- **Features**: ATL, Safe Drop, Signature, SSCC, Deliver on Date, Adhoc Pickup

#### 4. On Demand Accounts (On-Demand Delivery)
- **Format**: 10 digits, prefix 1 (e.g., 1006174692)
- **Detection**: 10 digits starting with '1'
- **Services**: ON_DEMAND_DELIVERY
- **Features**: ATL, Safe Drop, Signature, SSCC, Deliver on Date, Adhoc Pickup

### API Key Format

**IMPORTANT**: Australia Post uses API Keys in UUID format:

```
601a4032-6dbd-46aa-9c6c-8c6dacca5e61
```

UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### Authentication

HTTP Basic Authentication:
```
Authorization: Basic {base64(api_key:password)}
```

### Required Headers
```http
Authorization: Basic {base64(api_key:password)}
Account-Number: {account_number}
Content-Type: application/json
Accept: application/json
```

## Installation & Setup

### 1. Configure Credentials

```python
# eParcel Account
credentials = {
    'api_key': '601a4032-6dbd-46aa-9c6c-8c6dacca5e61',
    'api_password': 'my_secure_password',
    'account_number': '2004952470',
    'account_type': 'eparcel',
    'environment': 'test'  # or 'production'
}

# StarTrack Account
credentials = {
    'api_key': '701b5043-7dcf-57bb-9d7d-9d7ebcdb6f72',
    'api_password': 'my_secure_password',
    'account_number': '12345678',
    'account_type': 'startrack',
    'environment': 'test'
}
```

### 2. Initialize Provider

```python
from australiapost.provider import AustraliaPostProvider

provider = AustraliaPostProvider(
    credentials=credentials,
    config={
        'basket_max_size': 10000,  # Maximum basket capacity
        'validation_cache_ttl': 3600  # 1 hour validation cache
    }
)
```

### 3. Test Connection

```python
result = provider.test_connection()

if result['success']:
    print("Connected successfully!")
    print(f"Account: {result['account_info']}")
else:
    print(f"Connection failed: {result['message']}")
```

## Usage Examples

### Order Management

#### Create Order with Auto-Split
```python
# Create order from shipments (auto-splits if >2,000 items)
orders = provider.create_order_with_split(
    shipment_ids=['SHIP-001', 'SHIP-002', 'SHIP-003'],
    order_reference_prefix='ORDER-2025-001'
)

for order in orders:
    print(f"Order {order['order_id']}: {order['shipment_count']} shipments")
```

#### Get Order and Manifest
```python
# Get order details
order = provider.get_order('ORDER-12345')

# Get manifest
manifest = provider.get_order_summary('ORDER-12345', format='json')
print(f"Manifest: {manifest['total_shipments']} shipments")
```

### Basket Management

#### Add Shipments to Basket
```python
# Add shipments
status = provider.add_to_basket('SHIP-001', item_count=5)
status = provider.add_to_basket('SHIP-002', item_count=10)

# Get basket status
basket = provider.get_basket_status()
print(f"Basket: {basket['total_items']} items, {basket['remaining_capacity']} remaining")

# Get statistics
stats = provider.get_basket_statistics()
print(f"Average: {stats['average_items_per_shipment']} items per shipment")

# Clear basket
provider.clear_basket()
```

### Validation Services

#### Validate Suburb and Postcode
```python
result = provider.validate_suburb('Melbourne', 'VIC', '3000')

if result['valid']:
    print(f"Valid: {result['suburb']}, {result['state']} {result['postcode']}")
else:
    print(f"Invalid. Suggestions: {result['suggestions']}")
```

#### Check Address Serviceability
```python
result = provider.lookup_serviceability(
    address={
        'suburb': 'Sydney',
        'state': 'NSW',
        'postcode': '2000'
    },
    service_code='AUS_PARCEL_EXPRESS'
)

if result['serviceable']:
    print(f"Serviceable! Delivery days: {result['delivery_days']}")
else:
    print(f"Not serviceable. Alternatives: {result['alternatives']}")
```

#### Pre-Flight Validation
```python
result = provider.validate_shipments([
    {
        'from': {'suburb': 'Melbourne', 'state': 'VIC', 'postcode': '3000'},
        'to': {'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
        'items': [{'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}]
    }
])

if result['valid']:
    print("All shipments valid!")
else:
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
```

### Enhanced Pricing

#### Get Individual Shipment Price
```python
price = provider.get_shipment_price(
    from_address={'suburb': 'Melbourne', 'state': 'VIC', 'postcode': '3000'},
    to_address={'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
    items=[{'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}],
    service_code='AUS_PARCEL_EXPRESS'
)

print(f"Base: ${price['base_price']}")
print(f"Surcharges: ${price['surcharges_total']}")
print(f"Tax: ${price['tax_total']}")
print(f"Total: ${price['total']} {price['currency']}")
```

#### Calculate ETA
```python
eta = provider.calculate_eta(
    from_postcode='3000',
    to_postcode='2000',
    service_code='AUS_PARCEL_EXPRESS'
)

print(f"Estimated delivery: {eta['estimated_delivery_date']}")
print(f"Transit days: {eta['estimated_days']}")
print(f"Delivery window: {eta['delivery_window']}")
```

#### Compare Service Prices
```python
comparisons = provider.compare_service_prices(
    from_address={'suburb': 'Melbourne', 'state': 'VIC', 'postcode': '3000'},
    to_address={'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
    items=[{'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}]
)

for comparison in comparisons:
    print(f"{comparison['service_name']}: ${comparison['total']}")
```

### Product Features

#### Authority To Leave (ATL)
```python
shipment = provider.add_authority_to_leave(
    shipment_data,
    enabled=True,
    location='Front porch'
)
```

#### Safe Drop
```python
shipment = provider.add_safe_drop(
    shipment_data,
    enabled=True,
    instructions='Leave in mailbox'
)
```

#### Signature Required
```python
shipment = provider.add_signature_required(
    shipment_data,
    required=True,
    signature_type='adult'
)
```

#### Dangerous Goods
```python
shipment = provider.add_dangerous_goods(
    shipment_data,
    dg_class='3',
    un_number='UN1090',
    packing_group='II'
)
```

#### SSCC Barcode
```python
# Manual SSCC
shipment = provider.add_sscc_barcode(
    shipment_data,
    sscc='123456789012345678'
)

# Auto-generated SSCC
shipment = provider.add_sscc_barcode(
    shipment_data,
    auto_generate=True
)
```

#### Validate Features for Product
```python
is_valid, errors = provider.validate_features_for_product(
    'AUS_PARCEL_EXPRESS',
    {
        'authority_to_leave': True,
        'safe_drop': True,
        'signature_required': True
    }
)

if not is_valid:
    print(f"Invalid features: {errors}")
```

### Adhoc Pickup Scheduling

#### Schedule Pickup
```python
pickup = provider.schedule_pickup(
    pickup_address={
        'street': '123 Main St',
        'suburb': 'Melbourne',
        'state': 'VIC',
        'postcode': '3000'
    },
    pickup_date='2025-11-08',
    time_slot='morning',
    shipment_ids=['SHIP-001', 'SHIP-002'],
    instructions='Ring doorbell',
    contact_name='John Smith',
    contact_phone='+61 3 9999 8888'
)

print(f"Pickup scheduled: {pickup['pickup_id']}")
print(f"Time: {pickup['time_window']}")
```

#### Get Available Time Slots
```python
slots = provider.get_available_time_slots('2025-11-08')

for slot in slots:
    print(f"{slot['slot']}: {slot['start']}-{slot['end']}")
```

#### Cancel Pickup
```python
result = provider.cancel_pickup('PICKUP-12345')
print(f"Pickup cancelled: {result['message']}")
```

### Shipment Management

#### Get Shipments with Filtering
```python
shipments = provider.get_shipments(
    status='created',
    created_after='2025-11-01',
    limit=50,
    offset=0
)

print(f"Found {shipments['total']} shipments")
for shipment in shipments['items']:
    print(f"  {shipment['shipment_id']}: {shipment['status']}")
```

#### Update Shipment
```python
updated = provider.update_shipment(
    'SHIP-12345',
    {'shipment_reference': 'NEW-REF-001'}
)
```

#### Delete Shipment
```python
result = provider.delete_shipment('SHIP-12345')
print(f"Deleted: {result['success']}")
```

### Original Features (v1.0.1)

#### Get Rates
```python
rates = provider.get_rates(
    origin={'postal_code': '3000', 'country_code': 'AU'},
    destination={'postal_code': '2000', 'country_code': 'AU'},
    parcels=[{'weight_kg': 2.5, 'length_cm': 30, 'width_cm': 20, 'height_cm': 15}]
)

for rate in rates:
    print(f"{rate['service_name']}: ${rate['total_charge']}")
```

#### Buy Label (Two-Step Process)
```python
label = provider.buy_label({
    'origin': {
        'name': 'John Smith',
        'street_line1': '123 Main St',
        'city': 'Melbourne',
        'state_code': 'VIC',
        'postal_code': '3000',
        'country_code': 'AU'
    },
    'destination': {
        'name': 'Jane Doe',
        'street_line1': '456 High St',
        'city': 'Sydney',
        'state_code': 'NSW',
        'postal_code': '2000',
        'country_code': 'AU'
    },
    'parcels': [{'weight_kg': 2.5, 'length_cm': 30, 'width_cm': 20, 'height_cm': 15}],
    'service_code': 'AUS_PARCEL_EXPRESS'
})

print(f"Label URL: {label['label_url']}")
print(f"Tracking: {label['tracking_number']}")
```

#### Track Shipments
```python
tracking = provider.get_tracking(['AA123456789AU'])

for t in tracking:
    print(f"Status: {t['status']}")
    for event in t['events']:
        print(f"  {event['timestamp']}: {event['description']}")
```

## Service Codes by Account Type

### eParcel Services
| Code | Name | ATL | Safe Drop | Signature | DG | SSCC |
|------|------|-----|-----------|-----------|----|----- |
| `AUS_PARCEL_REGULAR` | Regular Parcel | ✓ | ✓ | ✓ | ✓ | ✓ |
| `AUS_PARCEL_EXPRESS` | Express Post | ✓ | ✓ | ✓ | ✓ | ✓ |
| `AUS_PARCEL_COURIER` | Courier Post | ✗ | ✗ | ✓ | ✓ | ✓ |

### StarTrack Services
| Code | Name | ATL | Safe Drop | Signature | DG | Transfers | SSCC |
|------|------|-----|-----------|-----------|-----|-----------|------|
| `ST_PREMIUM` | StarTrack Premium | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ST_EXPRESS` | StarTrack Express | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Same Day / On Demand Services
| Code | Name | ATL | Safe Drop | Deliver on Date | Adhoc Pickup |
|------|------|-----|-----------|-----------------|--------------|
| `SAME_DAY_DELIVERY` | Same Day | ✓ | ✓ | ✓ | ✓ |
| `ON_DEMAND_DELIVERY` | On Demand | ✓ | ✓ | ✓ | ✓ |

### International Services
| Code | Name | Signature | Returns |
|------|------|-----------|---------|
| `INTL_PARCEL_STD` | International Standard | ✓ | ✓ |
| `INTL_PARCEL_EXP` | International Express | ✓ | ✓ |
| `INTL_PARCEL_COR` | International Courier | ✓ | ✗ |

## Provider Capabilities

The provider exposes 24 capabilities in v2.0.0:

### Core Capabilities
- `rates`: Rate calculation
- `labels`: Two-step label generation
- `tracking`: Real-time tracking with rate limiting
- `international`: International shipping
- `returns`: Return label support
- `pickup`: Pickup scheduling
- `insurance`: Insurance coverage
- `signature`: Signature confirmation
- `dangerous_goods`: Dangerous goods support

### v2.0.0 Capabilities
- `orders`: Order creation and management
- `order_summary`: Manifest generation
- `order_splitting`: Automatic order splitting
- `basket_management`: Basket tracking
- `shipment_update`: Shipment updates
- `item_operations`: Item-level operations
- `validation`: Pre-flight validation
- `address_validation`: Suburb/postcode validation
- `serviceability`: Address serviceability
- `authority_to_leave`: ATL feature
- `safe_drop`: Safe drop feature
- `sscc_barcoding`: SSCC barcode support
- `adhoc_pickups`: Adhoc pickup scheduling
- `eta_calculation`: ETA calculations
- `enhanced_pricing`: Individual shipment pricing

## Error Handling

### Exception Hierarchy

| Exception | Description | HTTP Status |
|-----------|-------------|-------------|
| `AustraliaPostError` | Base exception | - |
| `AustraliaPostAuthenticationError` | Invalid API key/password | 401 |
| `AustraliaPostAccountError` | Account issues | 40001, 41001-41003 |
| `AustraliaPostValidationError` | Invalid request data | 400, 40002 |
| `AustraliaPostShipmentError` | Shipment creation failed | 44013 |
| `AustraliaPostOrderError` | Order management failed (v2.0.0) | - |
| `AustraliaPostBasketError` | Basket operations failed (v2.0.0) | - |
| `AustraliaPostPickupError` | Pickup scheduling failed (v2.0.0) | - |
| `AustraliaPostRateLimitError` | Rate limit exceeded | 429 |
| `AustraliaPostServiceUnavailableError` | Service unavailable | 503 |
| `AustraliaPostAPIError` | Server error | 500, 502 |

### Error Handling Example
```python
from australiapost.exceptions import (
    AustraliaPostValidationError,
    AustraliaPostBasketError,
    AustraliaPostOrderError
)

try:
    provider.add_to_basket('SHIP-001', item_count=15000)
except AustraliaPostBasketError as e:
    print(f"Basket error: {e.message}")
    print(f"Error code: {e.error_code}")
```

## Rate Limiting

The Tracking API has strict rate limits enforced by token bucket algorithm:

- **Limit**: 10 requests per 60 seconds
- **Implementation**: Automatic waiting when limit reached
- **Behavior**: Non-blocking, provider handles automatically

```python
# Rate limiting is automatic for tracking
tracking = provider.get_tracking(['AA123456789AU'])  # Automatically rate limited
```

## Best Practices

### 1. Production Workflow
- Always validate addresses before creating shipments
- Use basket for batch processing
- Create orders before generating labels
- Generate manifests for lodgement

### 2. Order Management
- Use `create_order_with_split()` for large batches
- Monitor basket capacity (10,000 item limit)
- Keep orders under 2,000 items (automatic splitting available)

### 3. Validation
- Pre-validate suburbs and postcodes
- Check serviceability for destinations
- Use pre-flight validation for complex shipments
- Leverage validation caching (1-hour TTL)

### 4. Features
- Validate feature compatibility with product codes
- Use ATL/Safe Drop for contactless delivery
- Mark dangerous goods correctly with proper UN numbers
- Validate SSCC barcodes before submission

### 5. Performance
- Use caching for validation and orders
- Batch shipments in basket before creating orders
- Use synchronous label generation for <250 parcels
- Leverage connection pooling (built-in)

### 6. Security
- Store API keys securely
- Never commit credentials to version control
- Use environment-specific credentials
- Rotate passwords regularly

## API Endpoints Reference

### v2.0.0 Endpoints
- `POST /shipping/v1/orders` - Create order from shipments
- `GET /shipping/v1/orders/{order_id}` - Get order details
- `GET /shipping/v1/orders/{order_id}/summary` - Get manifest
- `POST /shipping/v1/postcode/validate` - Validate suburb/postcode
- `POST /shipping/v1/serviceability` - Check address serviceability
- `POST /shipping/v1/shipments/validate` - Pre-flight validation
- `POST /shipping/v1/prices/items` - Individual shipment pricing
- `POST /shipping/v1/eta` - Calculate ETA
- `POST /shipping/v1/pickups` - Schedule adhoc pickup
- `GET /shipping/v1/pickups/{pickup_id}` - Get pickup details
- `DELETE /shipping/v1/pickups/{pickup_id}` - Cancel pickup
- `GET /shipping/v1/shipments` - List shipments
- `GET /shipping/v1/shipments/{id}` - Get shipment
- `PUT /shipping/v1/shipments/{id}` - Update shipment
- `DELETE /shipping/v1/shipments/{id}` - Delete shipment

### v1.0.1 Endpoints
- `POST /shipping/v1/prices/shipments` - Get rates
- `POST /shipping/v1/shipments` - Create shipment
- `POST /shipping/v1/labels` - Generate labels
- `GET /shipping/v1/track` - Track shipment
- `DELETE /shipping/v1/shipments/{id}` - Void shipment

## Support & Documentation

- **API Documentation**: https://developers.auspost.com.au/apis/shipping
- **Developer Portal**: https://developers.auspost.com.au/
- **Test Credentials**: See `.claude_code/shipping/providers/australia_post/development_credentials.md`
- **Provider Issues**: https://github.com/spwig/shop/issues

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Version 2.0.0 (2025-11-06)
- Complete order management system
- Basket management (10,000 item capacity)
- Enhanced validation services with caching
- Product feature management and validation
- Adhoc pickup scheduling
- Enhanced pricing and ETA calculations
- Shipment management enhancements
- Four account type support (eParcel, StarTrack, Same Day, On Demand)
- Production-ready lodgement compliance

### Version 1.0.1 (2025-10-24)
- Initial release
- Rate calculation
- Two-step label generation
- Tracking with rate limiting
- Basic error handling

## License

Proprietary - Copyright Spwig 2025

All rights reserved. This software is proprietary and confidential.
