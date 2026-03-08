"""
Integration Tests for Australia Post Provider v2.0.0

Tests complete workflows for all 4 account types:
- eParcel (account: 2004952470, 10-digit prefix 2)
- StarTrack (account: 12345678, 8-digit)
- Same Day (account: 3005063581, 10-digit prefix 3)
- On Demand (account: 1006174692, 10-digit prefix 1)

Tests the production workflow:
1. Validate address
2. Create shipments and add to basket
3. Manage basket
4. Create order (with auto-split if needed)
5. Generate labels
6. Get order summary
7. Track shipments
8. Schedule pickups

Author: Spwig
Version: 2.0.0
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import test fixtures
from tests.fixtures import (
    EPARCEL_CREDENTIALS,
    STARTRACK_CREDENTIALS,
    SAME_DAY_CREDENTIALS,
    ON_DEMAND_CREDENTIALS,
    MELBOURNE_ADDRESS,
    SYDNEY_ADDRESS,
    BRISBANE_ADDRESS,
    PERTH_ADDRESS,
    ADELAIDE_ADDRESS,
    STANDARD_ITEM,
    HEAVY_ITEM,
    LARGE_ITEM,
    create_test_shipment_data,
    create_test_item,
    create_mock_auth_client,
    create_mock_shipment_response,
    create_mock_order_response,
    create_mock_pickup_response,
    create_mock_validation_response,
    create_mock_serviceability_response,
    create_mock_price_response,
    create_mock_eta_response,
    generate_shipment_ids,
)

# Import provider and modules
from provider import AustraliaPostProvider
from auth import detect_service_type, pad_account_number
from order_manager import OrderManager
from basket_manager import BasketManager
from validation_service import ValidationService
from pricing_service import PricingService
from features import ShipmentFeatures
from pickup_service import PickupService
import exceptions


class TestAccountTypeDetection(unittest.TestCase):
    """Test account type detection and validation."""

    def test_detect_eparcel_account(self):
        """Test detecting eParcel account (10-digit, prefix 2)."""
        account = EPARCEL_CREDENTIALS['account_number']
        service_type = detect_service_type(account)
        self.assertEqual(service_type, 'eparcel')

    def test_detect_startrack_account(self):
        """Test detecting StarTrack account (8-digit)."""
        account = STARTRACK_CREDENTIALS['account_number']
        service_type = detect_service_type(account)
        self.assertEqual(service_type, 'startrack')

    def test_detect_same_day_account(self):
        """Test detecting Same Day account (10-digit, prefix 3)."""
        account = SAME_DAY_CREDENTIALS['account_number']
        service_type = detect_service_type(account)
        self.assertEqual(service_type, 'same_day')

    def test_detect_on_demand_account(self):
        """Test detecting On Demand account (10-digit, prefix 1)."""
        account = ON_DEMAND_CREDENTIALS['account_number']
        service_type = detect_service_type(account)
        self.assertEqual(service_type, 'on_demand')

    def test_pad_eparcel_account(self):
        """Test padding eParcel account number."""
        account = EPARCEL_CREDENTIALS['account_number']
        padded = pad_account_number(account)
        self.assertEqual(len(padded), 10)
        self.assertTrue(padded.startswith('2'))

    def test_pad_startrack_account(self):
        """Test padding StarTrack account number."""
        account = STARTRACK_CREDENTIALS['account_number']
        padded = pad_account_number(account)
        self.assertEqual(len(padded), 8)


class TestEParcelWorkflow(unittest.TestCase):
    """Integration tests for eParcel account workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.credentials = EPARCEL_CREDENTIALS.copy()
        self.mock_auth_client = create_mock_auth_client(self.credentials)

        # Initialize managers
        self.order_manager = OrderManager(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.basket_manager = BasketManager(max_size=10000)

        self.validation_service = ValidationService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1',
            cache_ttl=3600
        )

        self.pricing_service = PricingService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.features = ShipmentFeatures()

        self.pickup_service = PickupService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

    def tearDown(self):
        """Clean up after tests."""
        self.basket_manager.clear() if not self.basket_manager.is_locked else None

    def test_complete_eparcel_workflow(self):
        """Test complete eParcel workflow: validate -> create -> basket -> order -> manifest."""

        # Step 1: Validate address
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_validation_response(
                valid=True,
                suburb='SYDNEY',
                state='NSW',
                postcode='2000'
            )

            validation_result = self.validation_service.validate_suburb(
                suburb='Sydney',
                state='NSW',
                postcode='2000'
            )

            self.assertTrue(validation_result['valid'])
            self.assertEqual(validation_result['suburb'], 'SYDNEY')

        # Step 2: Create test shipments
        shipment_ids = []
        for i in range(5):
            shipment_data = create_test_shipment_data(
                from_address=MELBOURNE_ADDRESS,
                to_address=SYDNEY_ADDRESS,
                service_code='AUS_PARCEL_EXPRESS',
                reference=f'EPARCEL-SHIP-{i+1:03d}'
            )

            # Add features for eParcel
            shipment_data = self.features.add_authority_to_leave(
                shipment_data,
                enabled=True,
                location='Front porch'
            )
            shipment_data = self.features.add_delivery_instructions(
                shipment_data,
                'Ring doorbell twice'
            )

            # Mock shipment creation
            shipment_id = f'SHIP-EPARCEL-{i+1:05d}'
            shipment_ids.append(shipment_id)

        # Step 3: Add shipments to basket
        for shipment_id in shipment_ids:
            result = self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=3,  # 3 items per shipment
                shipment_data={'reference': shipment_id}
            )

            self.assertEqual(result['total_shipments'], shipment_ids.index(shipment_id) + 1)

        # Verify basket status
        status = self.basket_manager.get_status()
        self.assertEqual(status['total_shipments'], 5)
        self.assertEqual(status['total_items'], 15)  # 5 shipments × 3 items
        self.assertEqual(status['remaining_capacity'], 9985)

        # Step 4: Create order from basket
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_order_response(
                order_id='ORD-EPARCEL-001',
                shipment_ids=shipment_ids,
                status='created'
            )

            order = self.order_manager.create_order(
                account_number=self.credentials['account_number'],
                shipment_ids=shipment_ids,
                order_reference='EPARCEL-ORDER-001'
            )

            self.assertEqual(order['order_id'], 'ORD-EPARCEL-001')
            self.assertEqual(order['shipment_count'], 5)

        # Step 5: Get order summary (manifest)
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = {
                'order_id': 'ORD-EPARCEL-001',
                'manifest_url': 'https://api.auspost.com.au/manifests/ORD-EPARCEL-001.pdf',
                'shipment_ids': shipment_ids,
                'created_at': datetime.utcnow().isoformat()
            }

            summary = self.order_manager.get_order_summary(
                account_number=self.credentials['account_number'],
                order_id='ORD-EPARCEL-001'
            )

            self.assertIn('manifest_url', summary)
            self.assertEqual(len(summary['shipment_ids']), 5)

    def test_eparcel_service_codes(self):
        """Test eParcel service codes and features."""
        # eParcel Regular supports ATL, Safe Drop
        eparcel_regular_features = self.features.get_supported_features('AUS_PARCEL_REGULAR')
        self.assertIn('authority_to_leave', eparcel_regular_features)
        self.assertIn('safe_drop', eparcel_regular_features)
        self.assertIn('signature_required', eparcel_regular_features)

        # eParcel Express supports ATL, Safe Drop
        eparcel_express_features = self.features.get_supported_features('AUS_PARCEL_EXPRESS')
        self.assertIn('authority_to_leave', eparcel_express_features)
        self.assertIn('safe_drop', eparcel_express_features)

        # eParcel Courier does NOT support ATL or Safe Drop
        eparcel_courier_features = self.features.get_supported_features('AUS_PARCEL_COURIER')
        self.assertNotIn('authority_to_leave', eparcel_courier_features)
        self.assertNotIn('safe_drop', eparcel_courier_features)
        self.assertIn('signature_required', eparcel_courier_features)

    def test_eparcel_pricing(self):
        """Test eParcel pricing calculation."""
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_price_response(
                base_price=12.50,
                service_code='AUS_PARCEL_EXPRESS'
            )

            price = self.pricing_service.get_shipment_price(
                account_number=self.credentials['account_number'],
                from_address=MELBOURNE_ADDRESS,
                to_address=SYDNEY_ADDRESS,
                items=[STANDARD_ITEM],
                service_code='AUS_PARCEL_EXPRESS'
            )

            self.assertIsInstance(price['base_price'], (float, Decimal))
            self.assertIn('total', price)
            self.assertEqual(price['currency'], 'AUD')

    def test_eparcel_adhoc_pickup(self):
        """Test adhoc pickup scheduling for eParcel."""
        pickup_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_pickup_response(
                pickup_id='PICKUP-EPARCEL-001',
                pickup_date=pickup_date,
                time_slot='morning'
            )

            pickup = self.pickup_service.schedule_pickup(
                account_number=self.credentials['account_number'],
                pickup_date=pickup_date,
                time_slot='morning',
                pickup_address=MELBOURNE_ADDRESS,
                shipment_ids=['SHIP-001', 'SHIP-002']
            )

            self.assertEqual(pickup['status'], 'scheduled')
            self.assertEqual(pickup['time_slot'], 'morning')
            self.assertEqual(pickup['pickup_date'], pickup_date)


class TestStarTrackWorkflow(unittest.TestCase):
    """Integration tests for StarTrack account workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.credentials = STARTRACK_CREDENTIALS.copy()
        self.mock_auth_client = create_mock_auth_client(self.credentials)

        self.order_manager = OrderManager(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.basket_manager = BasketManager(max_size=10000)
        self.features = ShipmentFeatures()

    def tearDown(self):
        """Clean up after tests."""
        self.basket_manager.clear() if not self.basket_manager.is_locked else None

    def test_complete_startrack_workflow(self):
        """Test complete StarTrack workflow."""

        # Create shipments for StarTrack
        shipment_ids = []
        for i in range(3):
            shipment_data = create_test_shipment_data(
                from_address=BRISBANE_ADDRESS,
                to_address=PERTH_ADDRESS,
                service_code='ST_PREMIUM',
                reference=f'STARTRACK-SHIP-{i+1:03d}'
            )

            # Add StarTrack-specific features
            shipment_data = self.features.add_authority_to_leave(
                shipment_data,
                enabled=True
            )

            # StarTrack Premium supports transfers and book-ins
            if 'features' not in shipment_data:
                shipment_data['features'] = {}
            shipment_data['features']['transfers'] = True
            shipment_data['features']['book_ins'] = True

            shipment_id = f'SHIP-ST-{i+1:05d}'
            shipment_ids.append(shipment_id)

        # Add to basket
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=5,
                shipment_data={'reference': shipment_id}
            )

        # Create order
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_order_response(
                order_id='ORD-ST-001',
                shipment_ids=shipment_ids,
                status='created'
            )

            order = self.order_manager.create_order(
                account_number=self.credentials['account_number'],
                shipment_ids=shipment_ids,
                order_reference='STARTRACK-ORDER-001'
            )

            self.assertEqual(order['order_id'], 'ORD-ST-001')
            self.assertEqual(order['shipment_count'], 3)

    def test_startrack_service_codes(self):
        """Test StarTrack service codes and features."""
        # StarTrack Premium supports ATL, Safe Drop, Transfers, Book-ins
        st_premium_features = self.features.get_supported_features('ST_PREMIUM')
        self.assertIn('authority_to_leave', st_premium_features)
        self.assertIn('safe_drop', st_premium_features)
        self.assertIn('transfers', st_premium_features)
        self.assertIn('book_ins', st_premium_features)
        self.assertIn('transit_cover', st_premium_features)

        # StarTrack Express
        st_express_features = self.features.get_supported_features('ST_EXPRESS')
        self.assertIn('signature_required', st_express_features)

    def test_startrack_feature_validation(self):
        """Test StarTrack feature compatibility validation."""
        # Valid features for StarTrack Premium
        valid_features = {
            'authority_to_leave': True,
            'safe_drop': True,
            'transfers': True,
            'book_ins': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'ST_PREMIUM',
            valid_features
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestSameDayWorkflow(unittest.TestCase):
    """Integration tests for Same Day delivery account workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.credentials = SAME_DAY_CREDENTIALS.copy()
        self.mock_auth_client = create_mock_auth_client(self.credentials)

        self.order_manager = OrderManager(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.basket_manager = BasketManager(max_size=10000)
        self.features = ShipmentFeatures()
        self.pickup_service = PickupService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

    def tearDown(self):
        """Clean up after tests."""
        self.basket_manager.clear() if not self.basket_manager.is_locked else None

    def test_complete_same_day_workflow(self):
        """Test complete Same Day delivery workflow."""

        # Create Same Day shipments (metro only, same day delivery)
        shipment_ids = []
        for i in range(2):
            shipment_data = create_test_shipment_data(
                from_address=SYDNEY_ADDRESS,
                to_address=SYDNEY_ADDRESS,  # Same Day is metro-to-metro
                service_code='SAME_DAY_DELIVERY',
                reference=f'SAMEDAY-SHIP-{i+1:03d}'
            )

            # Same Day features
            shipment_data = self.features.add_authority_to_leave(
                shipment_data,
                enabled=True
            )

            if 'features' not in shipment_data:
                shipment_data['features'] = {}
            shipment_data['features']['deliver_on_date'] = datetime.now().strftime('%Y-%m-%d')
            shipment_data['features']['adhoc_pickup'] = True

            shipment_id = f'SHIP-SD-{i+1:05d}'
            shipment_ids.append(shipment_id)

        # Add to basket
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=2,
                shipment_data={'reference': shipment_id}
            )

        # Create order
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_order_response(
                order_id='ORD-SD-001',
                shipment_ids=shipment_ids,
                status='created'
            )

            order = self.order_manager.create_order(
                account_number=self.credentials['account_number'],
                shipment_ids=shipment_ids,
                order_reference='SAMEDAY-ORDER-001'
            )

            self.assertEqual(order['order_id'], 'ORD-SD-001')
            self.assertEqual(order['shipment_count'], 2)

    def test_same_day_adhoc_pickup(self):
        """Test adhoc pickup for Same Day delivery."""
        pickup_date = datetime.now().strftime('%Y-%m-%d')  # Same day pickup

        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_pickup_response(
                pickup_id='PICKUP-SD-001',
                pickup_date=pickup_date,
                time_slot='morning'
            )

            pickup = self.pickup_service.schedule_pickup(
                account_number=self.credentials['account_number'],
                pickup_date=pickup_date,
                time_slot='morning',
                pickup_address=SYDNEY_ADDRESS,
                shipment_ids=['SHIP-SD-001']
            )

            self.assertEqual(pickup['status'], 'scheduled')
            self.assertEqual(pickup['pickup_date'], pickup_date)

    def test_same_day_service_codes(self):
        """Test Same Day service codes and features."""
        same_day_features = self.features.get_supported_features('SAME_DAY_DELIVERY')
        self.assertIn('authority_to_leave', same_day_features)
        self.assertIn('deliver_on_date', same_day_features)
        self.assertIn('adhoc_pickup', same_day_features)


class TestOnDemandWorkflow(unittest.TestCase):
    """Integration tests for On Demand account workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.credentials = ON_DEMAND_CREDENTIALS.copy()
        self.mock_auth_client = create_mock_auth_client(self.credentials)

        self.order_manager = OrderManager(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.basket_manager = BasketManager(max_size=10000)
        self.features = ShipmentFeatures()

    def tearDown(self):
        """Clean up after tests."""
        self.basket_manager.clear() if not self.basket_manager.is_locked else None

    def test_complete_on_demand_workflow(self):
        """Test complete On Demand workflow."""

        # Create On Demand shipments
        shipment_ids = []
        for i in range(4):
            shipment_data = create_test_shipment_data(
                from_address=ADELAIDE_ADDRESS,
                to_address=MELBOURNE_ADDRESS,
                service_code='ON_DEMAND_DELIVERY',
                reference=f'ONDEMAND-SHIP-{i+1:03d}'
            )

            # On Demand features
            shipment_data = self.features.add_authority_to_leave(
                shipment_data,
                enabled=True
            )
            shipment_data = self.features.add_safe_drop(
                shipment_data,
                enabled=True,
                instructions='Leave in safe place'
            )

            shipment_id = f'SHIP-OD-{i+1:05d}'
            shipment_ids.append(shipment_id)

        # Add to basket
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=4,
                shipment_data={'reference': shipment_id}
            )

        # Create order
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_order_response(
                order_id='ORD-OD-001',
                shipment_ids=shipment_ids,
                status='created'
            )

            order = self.order_manager.create_order(
                account_number=self.credentials['account_number'],
                shipment_ids=shipment_ids,
                order_reference='ONDEMAND-ORDER-001'
            )

            self.assertEqual(order['order_id'], 'ORD-OD-001')
            self.assertEqual(order['shipment_count'], 4)

    def test_on_demand_service_codes(self):
        """Test On Demand service codes and features."""
        on_demand_features = self.features.get_supported_features('ON_DEMAND_DELIVERY')
        self.assertIn('authority_to_leave', on_demand_features)
        self.assertIn('safe_drop', on_demand_features)
        self.assertIn('signature_required', on_demand_features)


class TestOrderSplitting(unittest.TestCase):
    """Test automatic order splitting for all account types."""

    def setUp(self):
        """Set up test fixtures."""
        self.eparcel_credentials = EPARCEL_CREDENTIALS.copy()
        self.mock_auth_client = create_mock_auth_client(self.eparcel_credentials)

        self.order_manager = OrderManager(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

        self.basket_manager = BasketManager(max_size=10000)

    def tearDown(self):
        """Clean up after tests."""
        self.basket_manager.clear() if not self.basket_manager.is_locked else None

    def test_order_splitting_at_2000_items(self):
        """Test automatic order splitting when exceeding 2,000 items."""

        # Create 500 shipments with 5 items each = 2,500 items total
        # Should split into 2 orders: 2,000 items + 500 items
        shipment_ids = generate_shipment_ids(500, prefix='SPLIT-SHIP')

        # Add to basket
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=5,
                shipment_data={'reference': shipment_id}
            )

        # Verify basket has all items
        status = self.basket_manager.get_status()
        self.assertEqual(status['total_items'], 2500)
        self.assertEqual(status['total_shipments'], 500)

        # Mock order creation with splitting
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            # First order: 400 shipments (2,000 items)
            # Second order: 100 shipments (500 items)
            mock_request.side_effect = [
                create_mock_order_response(
                    order_id='ORD-SPLIT-001',
                    shipment_ids=shipment_ids[:400],
                    status='created'
                ),
                create_mock_order_response(
                    order_id='ORD-SPLIT-002',
                    shipment_ids=shipment_ids[400:],
                    status='created'
                )
            ]

            # This should create 2 orders automatically
            orders = self.order_manager.create_order_with_split(
                account_number=self.eparcel_credentials['account_number'],
                shipment_ids=shipment_ids,
                order_reference_prefix='SPLIT-ORDER'
            )

            # Should have created 2 orders
            self.assertEqual(len(orders), 2)
            self.assertEqual(orders[0]['order_id'], 'ORD-SPLIT-001')
            self.assertEqual(orders[1]['order_id'], 'ORD-SPLIT-002')

    def test_order_warning_at_1800_items(self):
        """Test warning when approaching 2,000 item limit."""

        # Create 360 shipments with 5 items each = 1,800 items (warning threshold)
        shipment_ids = generate_shipment_ids(360, prefix='WARN-SHIP')

        # Add to basket
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=5
            )

        # Validate order size
        is_valid, total_items, errors = self.order_manager.validate_order_size(
            shipment_ids=shipment_ids,
            get_item_count=lambda sid: 5
        )

        self.assertTrue(is_valid)
        self.assertEqual(total_items, 1800)
        # Should have warning about approaching limit
        self.assertGreater(len(errors), 0)
        self.assertIn('approaching', errors[0].lower())

    def test_basket_capacity_limit(self):
        """Test basket capacity limit of 10,000 items."""

        # Fill basket to capacity
        shipment_ids = generate_shipment_ids(2000, prefix='CAPACITY-SHIP')

        # Add 2000 shipments with 5 items each = 10,000 items
        for shipment_id in shipment_ids:
            self.basket_manager.add_shipment(
                shipment_id=shipment_id,
                item_count=5
            )

        # Verify basket is at capacity
        status = self.basket_manager.get_status()
        self.assertEqual(status['total_items'], 10000)
        self.assertEqual(status['remaining_capacity'], 0)

        # Try to add one more shipment (should fail)
        with self.assertRaises(exceptions.AustraliaPostBasketError) as context:
            self.basket_manager.add_shipment(
                shipment_id='OVERFLOW-SHIP',
                item_count=1
            )

        self.assertIn('exceed', str(context.exception).lower())


class TestValidationServices(unittest.TestCase):
    """Test validation services across all account types."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_auth_client = create_mock_auth_client(EPARCEL_CREDENTIALS)

        self.validation_service = ValidationService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1',
            cache_ttl=3600
        )

    def test_validate_australian_suburbs(self):
        """Test validating Australian suburbs and postcodes."""
        test_cases = [
            ('Sydney', 'NSW', '2000', True),
            ('Melbourne', 'VIC', '3000', True),
            ('Brisbane', 'QLD', '4000', True),
            ('Perth', 'WA', '6000', True),
            ('Adelaide', 'SA', '5000', True),
        ]

        for suburb, state, postcode, expected_valid in test_cases:
            with patch.object(self.mock_auth_client, '_make_request') as mock_request:
                mock_request.return_value = create_mock_validation_response(
                    valid=expected_valid,
                    suburb=suburb.upper(),
                    state=state,
                    postcode=postcode
                )

                result = self.validation_service.validate_suburb(
                    suburb=suburb,
                    state=state,
                    postcode=postcode
                )

                self.assertEqual(result['valid'], expected_valid)
                self.assertEqual(result['state'], state)

    def test_validation_caching(self):
        """Test validation result caching."""
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_validation_response(
                valid=True,
                suburb='SYDNEY',
                state='NSW',
                postcode='2000'
            )

            # First call - should hit API
            result1 = self.validation_service.validate_suburb(
                suburb='Sydney',
                state='NSW',
                postcode='2000'
            )

            self.assertEqual(mock_request.call_count, 1)

            # Second call - should use cache
            result2 = self.validation_service.validate_suburb(
                suburb='Sydney',
                state='NSW',
                postcode='2000',
                use_cache=True
            )

            # API should not be called again
            self.assertEqual(mock_request.call_count, 1)
            self.assertTrue(result2.get('cached', False))

    def test_serviceability_lookup(self):
        """Test address serviceability lookup."""
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_serviceability_response(
                serviceable=True,
                service_code='AUS_PARCEL_EXPRESS'
            )

            result = self.validation_service.lookup_serviceability(
                address=SYDNEY_ADDRESS,
                service_code='AUS_PARCEL_EXPRESS'
            )

            self.assertTrue(result['serviceable'])
            self.assertEqual(result['service_code'], 'AUS_PARCEL_EXPRESS')


class TestFeatureCompatibility(unittest.TestCase):
    """Test product feature compatibility across account types."""

    def setUp(self):
        """Set up test fixtures."""
        self.features = ShipmentFeatures()

    def test_eparcel_feature_compatibility(self):
        """Test eParcel feature compatibility."""
        # eParcel Regular - supports ATL, Safe Drop
        features = {
            'authority_to_leave': True,
            'safe_drop': True,
            'signature_required': False
        }

        is_valid, errors = self.features.validate_features_for_product(
            'AUS_PARCEL_REGULAR',
            features
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # eParcel Courier - does NOT support ATL or Safe Drop
        features = {
            'authority_to_leave': True,
            'safe_drop': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'AUS_PARCEL_COURIER',
            features
        )

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 2)  # Both features not supported

    def test_startrack_feature_compatibility(self):
        """Test StarTrack feature compatibility."""
        # StarTrack Premium - supports ATL, Safe Drop, Transfers, Book-ins
        features = {
            'authority_to_leave': True,
            'safe_drop': True,
            'transfers': True,
            'book_ins': True,
            'transit_cover': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'ST_PREMIUM',
            features
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_international_feature_compatibility(self):
        """Test international service feature compatibility."""
        # International services have limited features
        features = {
            'authority_to_leave': True,  # Not supported for international
            'signature_required': True,  # Supported
            'returns': True  # Supported
        }

        is_valid, errors = self.features.validate_features_for_product(
            'INTL_PARCEL_STD',
            features
        )

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_dangerous_goods_declaration(self):
        """Test dangerous goods declaration."""
        shipment_data = create_test_shipment_data()

        result = self.features.add_dangerous_goods(
            shipment_data,
            dg_class='3',
            un_number='UN1090',
            packing_group='II'
        )

        self.assertIn('dangerous_goods', result['features'])
        self.assertEqual(result['features']['dangerous_goods']['class'], '3')
        self.assertEqual(result['features']['dangerous_goods']['un_number'], 'UN1090')
        self.assertEqual(result['features']['dangerous_goods']['packing_group'], 'II')

    def test_sscc_barcode_validation(self):
        """Test SSCC barcode validation."""
        # Valid SSCC (18 digits)
        valid_sscc = '123456789012345678'
        self.assertTrue(ShipmentFeatures.validate_sscc(valid_sscc))

        # Invalid SSCC (too short)
        short_sscc = '12345678901234567'
        self.assertFalse(ShipmentFeatures.validate_sscc(short_sscc))

        # Invalid SSCC (too long)
        long_sscc = '1234567890123456789'
        self.assertFalse(ShipmentFeatures.validate_sscc(long_sscc))

        # Invalid SSCC (non-numeric)
        invalid_sscc = '12345678901234567A'
        self.assertFalse(ShipmentFeatures.validate_sscc(invalid_sscc))


class TestPickupScheduling(unittest.TestCase):
    """Test pickup scheduling across account types."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_auth_client = create_mock_auth_client(EPARCEL_CREDENTIALS)

        self.pickup_service = PickupService(
            auth_client=self.mock_auth_client,
            base_url='https://test.auspost.com.au/api',
            api_version='v1'
        )

    def test_schedule_pickup_morning_slot(self):
        """Test scheduling pickup with morning time slot."""
        pickup_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_pickup_response(
                pickup_id='PICKUP-001',
                pickup_date=pickup_date,
                time_slot='morning'
            )

            pickup = self.pickup_service.schedule_pickup(
                account_number=EPARCEL_CREDENTIALS['account_number'],
                pickup_date=pickup_date,
                time_slot='morning',
                pickup_address=MELBOURNE_ADDRESS,
                shipment_ids=['SHIP-001', 'SHIP-002']
            )

            self.assertEqual(pickup['status'], 'scheduled')
            self.assertEqual(pickup['time_slot'], 'morning')
            self.assertEqual(pickup['time_window'], '08:00-12:00')

    def test_schedule_pickup_afternoon_slot(self):
        """Test scheduling pickup with afternoon time slot."""
        pickup_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_pickup_response(
                pickup_id='PICKUP-002',
                pickup_date=pickup_date,
                time_slot='afternoon'
            )

            pickup = self.pickup_service.schedule_pickup(
                account_number=EPARCEL_CREDENTIALS['account_number'],
                pickup_date=pickup_date,
                time_slot='afternoon',
                pickup_address=MELBOURNE_ADDRESS,
                shipment_ids=['SHIP-003']
            )

            self.assertEqual(pickup['time_slot'], 'afternoon')
            self.assertEqual(pickup['time_window'], '12:00-17:00')

    def test_schedule_pickup_all_day_slot(self):
        """Test scheduling pickup with all-day time slot."""
        pickup_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = create_mock_pickup_response(
                pickup_id='PICKUP-003',
                pickup_date=pickup_date,
                time_slot='all_day'
            )

            pickup = self.pickup_service.schedule_pickup(
                account_number=EPARCEL_CREDENTIALS['account_number'],
                pickup_date=pickup_date,
                time_slot='all_day',
                pickup_address=MELBOURNE_ADDRESS,
                shipment_ids=['SHIP-004', 'SHIP-005', 'SHIP-006']
            )

            self.assertEqual(pickup['time_slot'], 'all_day')

    def test_cancel_pickup(self):
        """Test cancelling scheduled pickup."""
        with patch.object(self.mock_auth_client, '_make_request') as mock_request:
            mock_request.return_value = {
                'pickup_id': 'PICKUP-001',
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow().isoformat()
            }

            result = self.pickup_service.cancel_pickup(
                account_number=EPARCEL_CREDENTIALS['account_number'],
                pickup_id='PICKUP-001'
            )

            self.assertEqual(result['status'], 'cancelled')


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
