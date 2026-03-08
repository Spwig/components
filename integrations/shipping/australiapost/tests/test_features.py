"""
Unit Tests for ShipmentFeatures

Tests product feature management including:
- Authority To Leave (ATL)
- Safe Drop
- Signature requirements
- Dangerous Goods
- SSCC barcoding
- Feature-product compatibility validation

Author: Spwig
Version: 2.0.0
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features import ShipmentFeatures, ProductCode
from tests.fixtures import create_test_shipment_data


class TestShipmentFeatures(unittest.TestCase):
    """Test cases for ShipmentFeatures."""

    def setUp(self):
        """Set up test fixtures."""
        self.features = ShipmentFeatures()
        self.shipment_data = create_test_shipment_data()

    # =========================================================================
    # Authority To Leave Tests
    # =========================================================================

    def test_add_authority_to_leave_enabled(self):
        """Test adding Authority To Leave feature."""
        result = self.features.add_authority_to_leave(
            self.shipment_data,
            enabled=True
        )

        self.assertTrue(result['features']['authority_to_leave'])

    def test_add_authority_to_leave_with_location(self):
        """Test adding ATL with specific location."""
        result = self.features.add_authority_to_leave(
            self.shipment_data,
            enabled=True,
            location='Front porch'
        )

        self.assertTrue(result['features']['authority_to_leave'])
        self.assertEqual(result['features']['atl_location'], 'Front porch')

    def test_add_authority_to_leave_disabled(self):
        """Test disabling Authority To Leave."""
        result = self.features.add_authority_to_leave(
            self.shipment_data,
            enabled=False
        )

        self.assertFalse(result['features']['authority_to_leave'])
        self.assertNotIn('atl_location', result['features'])

    # =========================================================================
    # Safe Drop Tests
    # =========================================================================

    def test_add_safe_drop_enabled(self):
        """Test adding Safe Drop feature."""
        result = self.features.add_safe_drop(
            self.shipment_data,
            enabled=True
        )

        self.assertTrue(result['features']['safe_drop'])

    def test_add_safe_drop_with_instructions(self):
        """Test adding Safe Drop with instructions."""
        result = self.features.add_safe_drop(
            self.shipment_data,
            enabled=True,
            instructions='Leave in mailbox'
        )

        self.assertTrue(result['features']['safe_drop'])
        self.assertEqual(result['features']['safe_drop_instructions'], 'Leave in mailbox')

    def test_add_safe_drop_disabled(self):
        """Test disabling Safe Drop."""
        result = self.features.add_safe_drop(
            self.shipment_data,
            enabled=False
        )

        self.assertFalse(result['features']['safe_drop'])

    # =========================================================================
    # Signature Required Tests
    # =========================================================================

    def test_add_signature_required_standard(self):
        """Test adding standard signature requirement."""
        result = self.features.add_signature_required(
            self.shipment_data,
            required=True
        )

        self.assertTrue(result['features']['signature_required'])

    def test_add_signature_required_adult(self):
        """Test adding adult signature requirement."""
        result = self.features.add_signature_required(
            self.shipment_data,
            required=True,
            signature_type='adult'
        )

        self.assertTrue(result['features']['signature_required'])
        self.assertEqual(result['features']['signature_type'], 'adult')

    def test_add_signature_not_required(self):
        """Test disabling signature requirement."""
        result = self.features.add_signature_required(
            self.shipment_data,
            required=False
        )

        self.assertFalse(result['features']['signature_required'])

    # =========================================================================
    # Dangerous Goods Tests
    # =========================================================================

    def test_add_dangerous_goods_basic(self):
        """Test adding basic dangerous goods declaration."""
        result = self.features.add_dangerous_goods(
            self.shipment_data,
            dg_class='3'
        )

        self.assertIn('dangerous_goods', result['features'])
        self.assertEqual(result['features']['dangerous_goods']['class'], '3')

    def test_add_dangerous_goods_complete(self):
        """Test adding complete dangerous goods declaration."""
        result = self.features.add_dangerous_goods(
            self.shipment_data,
            dg_class='3',
            un_number='UN1090',
            packing_group='II'
        )

        dg = result['features']['dangerous_goods']
        self.assertEqual(dg['class'], '3')
        self.assertEqual(dg['un_number'], 'UN1090')
        self.assertEqual(dg['packing_group'], 'II')

    # =========================================================================
    # SSCC Barcode Tests
    # =========================================================================

    def test_validate_sscc_valid(self):
        """Test validating valid SSCC."""
        valid_sscc = '123456789012345678'
        self.assertTrue(ShipmentFeatures.validate_sscc(valid_sscc))

    def test_validate_sscc_with_spaces(self):
        """Test validating SSCC with spaces."""
        sscc_with_spaces = '1234 5678 9012 3456 78'
        self.assertTrue(ShipmentFeatures.validate_sscc(sscc_with_spaces))

    def test_validate_sscc_with_dashes(self):
        """Test validating SSCC with dashes."""
        sscc_with_dashes = '123456-789012-345678'
        self.assertTrue(ShipmentFeatures.validate_sscc(sscc_with_dashes))

    def test_validate_sscc_too_short(self):
        """Test validating SSCC that's too short."""
        short_sscc = '12345678901234567'  # 17 digits
        self.assertFalse(ShipmentFeatures.validate_sscc(short_sscc))

    def test_validate_sscc_too_long(self):
        """Test validating SSCC that's too long."""
        long_sscc = '1234567890123456789'  # 19 digits
        self.assertFalse(ShipmentFeatures.validate_sscc(long_sscc))

    def test_validate_sscc_non_numeric(self):
        """Test validating SSCC with non-numeric characters."""
        invalid_sscc = '12345678901234567A'
        self.assertFalse(ShipmentFeatures.validate_sscc(invalid_sscc))

    def test_validate_sscc_empty(self):
        """Test validating empty SSCC."""
        self.assertFalse(ShipmentFeatures.validate_sscc(''))
        self.assertFalse(ShipmentFeatures.validate_sscc(None))

    def test_format_sscc(self):
        """Test formatting SSCC."""
        sscc = '123456789012345678'
        formatted = ShipmentFeatures.format_sscc(sscc)

        # Check formatting matches expected pattern
        self.assertEqual(len(formatted.replace(' ', '')), 18)
        self.assertIn(' ', formatted)

    def test_add_sscc_barcode_manual(self):
        """Test adding manual SSCC barcode."""
        result = self.features.add_sscc_barcode(
            self.shipment_data,
            sscc='123456789012345678'
        )

        self.assertEqual(result['features']['sscc_barcode'], '123456789012345678')

    def test_add_sscc_barcode_auto_generate(self):
        """Test adding auto-generated SSCC barcode."""
        result = self.features.add_sscc_barcode(
            self.shipment_data,
            auto_generate=True
        )

        self.assertEqual(result['features']['sscc_barcode'], 'auto')

    def test_add_sscc_barcode_invalid_raises_error(self):
        """Test adding invalid SSCC raises error."""
        with self.assertRaises(ValueError) as context:
            self.features.add_sscc_barcode(
                self.shipment_data,
                sscc='12345'  # Too short
            )

        self.assertIn('Invalid SSCC format', str(context.exception))

    # =========================================================================
    # Delivery Instructions Tests
    # =========================================================================

    def test_add_delivery_instructions(self):
        """Test adding delivery instructions."""
        result = self.features.add_delivery_instructions(
            self.shipment_data,
            'Ring doorbell twice'
        )

        self.assertEqual(
            result['features']['delivery_instructions'],
            'Ring doorbell twice'
        )

    def test_add_delivery_instructions_truncation(self):
        """Test delivery instructions are truncated to 250 chars."""
        long_instructions = 'A' * 300

        result = self.features.add_delivery_instructions(
            self.shipment_data,
            long_instructions
        )

        instructions = result['features']['delivery_instructions']
        self.assertEqual(len(instructions), 250)

    # =========================================================================
    # Returns Tests
    # =========================================================================

    def test_mark_as_return(self):
        """Test marking shipment as return."""
        result = self.features.mark_as_return(self.shipment_data)

        self.assertTrue(result['features']['is_return'])

    def test_mark_as_return_with_reference(self):
        """Test marking shipment as return with reference."""
        result = self.features.mark_as_return(
            self.shipment_data,
            return_reference='RET-2025-001'
        )

        self.assertTrue(result['features']['is_return'])
        self.assertEqual(result['features']['return_reference'], 'RET-2025-001')

    # =========================================================================
    # Feature Compatibility Tests
    # =========================================================================

    def test_validate_features_for_eparcel_regular(self):
        """Test feature validation for eParcel Regular."""
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

    def test_validate_features_for_eparcel_courier(self):
        """Test feature validation for eParcel Courier."""
        # eParcel Courier doesn't support ATL or Safe Drop
        features = {
            'authority_to_leave': True,
            'safe_drop': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'AUS_PARCEL_COURIER',
            features
        )

        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 2)  # Both ATL and Safe Drop not supported

    def test_validate_features_for_startrack_premium(self):
        """Test feature validation for StarTrack Premium."""
        features = {
            'authority_to_leave': True,
            'safe_drop': True,
            'transfers': True,
            'book_ins': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'ST_PREMIUM',
            features
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_features_for_same_day(self):
        """Test feature validation for Same Day delivery."""
        features = {
            'deliver_on_date': True,
            'adhoc_pickup': True,
            'authority_to_leave': True
        }

        is_valid, errors = self.features.validate_features_for_product(
            'SAME_DAY_DELIVERY',
            features
        )

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_features_for_international(self):
        """Test feature validation for international service."""
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

    def test_validate_features_disabled_features_ignored(self):
        """Test that disabled features are ignored in validation."""
        features = {
            'authority_to_leave': False,  # Disabled
            'safe_drop': False,  # Disabled
            'signature_required': True  # Enabled and supported
        }

        is_valid, errors = self.features.validate_features_for_product(
            'INTL_PARCEL_STD',
            features
        )

        # Should be valid because disabled features are ignored
        self.assertTrue(is_valid)

    def test_validate_features_unknown_product(self):
        """Test feature validation for unknown product code."""
        features = {'authority_to_leave': True}

        is_valid, errors = self.features.validate_features_for_product(
            'UNKNOWN_PRODUCT',
            features
        )

        # Should pass validation for unknown products
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    # =========================================================================
    # Get Supported Features Tests
    # =========================================================================

    def test_get_supported_features_eparcel_regular(self):
        """Test getting supported features for eParcel Regular."""
        supported = self.features.get_supported_features('AUS_PARCEL_REGULAR')

        self.assertIn('authority_to_leave', supported)
        self.assertIn('safe_drop', supported)
        self.assertIn('signature_required', supported)
        self.assertIn('dangerous_goods', supported)

    def test_get_supported_features_startrack(self):
        """Test getting supported features for StarTrack."""
        supported = self.features.get_supported_features('ST_PREMIUM')

        self.assertIn('transfers', supported)
        self.assertIn('book_ins', supported)
        self.assertIn('transit_cover', supported)

    def test_get_supported_features_unknown_product(self):
        """Test getting supported features for unknown product."""
        supported = self.features.get_supported_features('UNKNOWN_PRODUCT')

        self.assertEqual(len(supported), 0)

    # =========================================================================
    # Is Feature Supported Tests
    # =========================================================================

    def test_is_feature_supported_true(self):
        """Test checking if feature is supported (true case)."""
        is_supported = self.features.is_feature_supported(
            'AUS_PARCEL_EXPRESS',
            'authority_to_leave'
        )

        self.assertTrue(is_supported)

    def test_is_feature_supported_false(self):
        """Test checking if feature is supported (false case)."""
        is_supported = self.features.is_feature_supported(
            'AUS_PARCEL_COURIER',
            'authority_to_leave'
        )

        self.assertFalse(is_supported)

    def test_is_feature_supported_unknown_product(self):
        """Test checking feature support for unknown product."""
        is_supported = self.features.is_feature_supported(
            'UNKNOWN_PRODUCT',
            'authority_to_leave'
        )

        self.assertFalse(is_supported)

    # =========================================================================
    # Multiple Features Tests
    # =========================================================================

    def test_add_multiple_features(self):
        """Test adding multiple features to shipment."""
        result = self.shipment_data.copy()

        # Add ATL
        result = self.features.add_authority_to_leave(result, enabled=True)

        # Add Safe Drop
        result = self.features.add_safe_drop(result, enabled=True)

        # Add Signature
        result = self.features.add_signature_required(result, required=True)

        # Add instructions
        result = self.features.add_delivery_instructions(
            result,
            'Ring doorbell'
        )

        # Verify all features are present
        self.assertTrue(result['features']['authority_to_leave'])
        self.assertTrue(result['features']['safe_drop'])
        self.assertTrue(result['features']['signature_required'])
        self.assertEqual(result['features']['delivery_instructions'], 'Ring doorbell')

    def test_conflicting_features(self):
        """Test that conflicting features can be detected via validation."""
        # ATL and Signature are typically conflicting
        features = {
            'authority_to_leave': True,
            'signature_required': True
        }

        # For eParcel Express, both are supported but may conflict
        is_valid, errors = self.features.validate_features_for_product(
            'AUS_PARCEL_EXPRESS',
            features
        )

        # Both are technically supported, validation passes
        # (Business logic would need to prevent this combination)
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main()
