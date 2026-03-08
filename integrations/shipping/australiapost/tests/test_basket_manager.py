"""
Unit Tests for BasketManager

Tests basket management functionality including:
- Adding/removing shipments
- Size limits
- Locking mechanism
- State persistence
- Validation

Author: Spwig
Version: 2.0.0
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import modules from parent directory
import basket_manager
import exceptions

BasketManager = basket_manager.BasketManager
AustraliaPostBasketError = exceptions.AustraliaPostBasketError


class TestBasketManager(unittest.TestCase):
    """Test cases for BasketManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.basket = BasketManager(max_size=10000)

    def tearDown(self):
        """Clean up after tests."""
        self.basket.clear()

    # =========================================================================
    # Initialization Tests
    # =========================================================================

    def test_initialization(self):
        """Test basket manager initialization."""
        self.assertEqual(self.basket.max_size, 10000)
        self.assertEqual(self.basket.total_items, 0)
        self.assertEqual(self.basket.total_shipments, 0)
        self.assertFalse(self.basket.is_locked)

    def test_initialization_with_custom_size(self):
        """Test initialization with custom max size."""
        basket = BasketManager(max_size=5000)
        self.assertEqual(basket.max_size, 5000)

    # =========================================================================
    # Add Shipment Tests
    # =========================================================================

    def test_add_single_shipment(self):
        """Test adding a single shipment to basket."""
        result = self.basket.add_shipment('SHIP-001', item_count=5)

        self.assertEqual(self.basket.total_items, 5)
        self.assertEqual(self.basket.total_shipments, 1)
        self.assertIn('SHIP-001', self.basket.shipments)
        self.assertEqual(result['total_items'], 5)
        self.assertEqual(result['total_shipments'], 1)

    def test_add_multiple_shipments(self):
        """Test adding multiple shipments to basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)
        self.basket.add_shipment('SHIP-003', item_count=3)

        self.assertEqual(self.basket.total_items, 18)
        self.assertEqual(self.basket.total_shipments, 3)

    def test_add_shipment_with_metadata(self):
        """Test adding shipment with metadata."""
        metadata = {'reference': 'TEST-001', 'weight': 2.5}
        self.basket.add_shipment('SHIP-001', item_count=5, shipment_data=metadata)

        shipment = self.basket.shipments['SHIP-001']
        self.assertEqual(shipment['shipment_data'], metadata)

    def test_add_duplicate_shipment_raises_error(self):
        """Test adding duplicate shipment ID raises error."""
        self.basket.add_shipment('SHIP-001', item_count=5)

        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.add_shipment('SHIP-001', item_count=3)

        self.assertIn('already in basket', str(context.exception))

    def test_add_shipment_exceeding_limit_raises_error(self):
        """Test adding shipment that exceeds limit raises error."""
        # Fill basket to near capacity
        self.basket.add_shipment('SHIP-001', item_count=9999)

        # Try to add one more shipment that would exceed limit
        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.add_shipment('SHIP-002', item_count=2)

        self.assertIn('would exceed maximum', str(context.exception))

    def test_add_shipment_zero_items_raises_error(self):
        """Test adding shipment with zero items raises error."""
        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.add_shipment('SHIP-001', item_count=0)

        self.assertIn('at least 1 item', str(context.exception))

    def test_add_shipment_negative_items_raises_error(self):
        """Test adding shipment with negative items raises error."""
        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.add_shipment('SHIP-001', item_count=-5)

        self.assertIn('at least 1 item', str(context.exception))

    def test_add_shipment_to_locked_basket_raises_error(self):
        """Test adding shipment to locked basket raises error."""
        self.basket.lock()

        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.add_shipment('SHIP-001', item_count=5)

        self.assertIn('locked', str(context.exception))

    # =========================================================================
    # Remove Shipment Tests
    # =========================================================================

    def test_remove_shipment(self):
        """Test removing a shipment from basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        result = self.basket.remove_shipment('SHIP-001')

        self.assertEqual(self.basket.total_items, 10)
        self.assertEqual(self.basket.total_shipments, 1)
        self.assertNotIn('SHIP-001', self.basket.shipments)
        self.assertEqual(result['total_items'], 10)

    def test_remove_nonexistent_shipment_raises_error(self):
        """Test removing nonexistent shipment raises error."""
        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.remove_shipment('SHIP-999')

        self.assertIn('not found', str(context.exception))

    def test_remove_shipment_from_locked_basket_raises_error(self):
        """Test removing shipment from locked basket raises error."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.lock()

        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.remove_shipment('SHIP-001')

        self.assertIn('locked', str(context.exception))

    # =========================================================================
    # Clear Basket Tests
    # =========================================================================

    def test_clear_basket(self):
        """Test clearing basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        result = self.basket.clear()

        self.assertEqual(self.basket.total_items, 0)
        self.assertEqual(self.basket.total_shipments, 0)
        self.assertEqual(len(self.basket.shipments), 0)
        self.assertEqual(result['total_items'], 0)

    def test_clear_locked_basket_raises_error(self):
        """Test clearing locked basket raises error."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.lock()

        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.clear()

        self.assertIn('locked', str(context.exception))

    # =========================================================================
    # Status Tests
    # =========================================================================

    def test_get_status(self):
        """Test getting basket status."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        status = self.basket.get_status()

        self.assertEqual(status['total_items'], 15)
        self.assertEqual(status['total_shipments'], 2)
        self.assertEqual(status['max_size'], 10000)
        self.assertEqual(status['remaining_capacity'], 9985)
        self.assertFalse(status['is_locked'])
        self.assertEqual(len(status['shipment_ids']), 2)
        self.assertIn('SHIP-001', status['shipment_ids'])

    def test_get_status_empty_basket(self):
        """Test getting status of empty basket."""
        status = self.basket.get_status()

        self.assertEqual(status['total_items'], 0)
        self.assertEqual(status['total_shipments'], 0)
        self.assertEqual(status['remaining_capacity'], 10000)

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_statistics(self):
        """Test getting basket statistics."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)
        self.basket.add_shipment('SHIP-003', item_count=15)

        stats = self.basket.get_statistics()

        self.assertEqual(stats['total_items'], 30)
        self.assertEqual(stats['total_shipments'], 3)
        self.assertEqual(stats['average_items_per_shipment'], 10.0)
        self.assertEqual(stats['largest_shipment_items'], 15)
        self.assertEqual(stats['smallest_shipment_items'], 5)

    def test_get_statistics_single_shipment(self):
        """Test statistics with single shipment."""
        self.basket.add_shipment('SHIP-001', item_count=5)

        stats = self.basket.get_statistics()

        self.assertEqual(stats['average_items_per_shipment'], 5.0)
        self.assertEqual(stats['largest_shipment_items'], 5)
        self.assertEqual(stats['smallest_shipment_items'], 5)

    def test_get_statistics_empty_basket(self):
        """Test statistics for empty basket."""
        stats = self.basket.get_statistics()

        self.assertEqual(stats['total_items'], 0)
        self.assertEqual(stats['total_shipments'], 0)
        self.assertIsNone(stats['average_items_per_shipment'])
        self.assertIsNone(stats['largest_shipment_items'])
        self.assertIsNone(stats['smallest_shipment_items'])

    # =========================================================================
    # Lock/Unlock Tests
    # =========================================================================

    def test_lock_basket(self):
        """Test locking basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.lock()

        self.assertTrue(self.basket.is_locked)

    def test_unlock_basket(self):
        """Test unlocking basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.lock()
        self.basket.unlock()

        self.assertFalse(self.basket.is_locked)

    def test_lock_empty_basket_raises_error(self):
        """Test locking empty basket raises error."""
        with self.assertRaises(AustraliaPostBasketError) as context:
            self.basket.lock()

        self.assertIn('Cannot lock empty basket', str(context.exception))

    # =========================================================================
    # Validation Tests
    # =========================================================================

    def test_validate_basket_valid(self):
        """Test validating a valid basket."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        is_valid, errors = self.basket.validate()

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_empty_basket(self):
        """Test validating empty basket returns error."""
        is_valid, errors = self.basket.validate()

        self.assertFalse(is_valid)
        self.assertIn('Basket is empty', errors)

    def test_validate_basket_near_limit(self):
        """Test validating basket near capacity limit."""
        # Add to warning threshold (8000 items)
        self.basket.add_shipment('SHIP-001', item_count=8500)

        is_valid, errors = self.basket.validate()

        self.assertTrue(is_valid)
        self.assertIn('approaching capacity limit', errors[0])

    # =========================================================================
    # Snapshot Tests
    # =========================================================================

    def test_get_snapshot(self):
        """Test getting basket snapshot."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        snapshot = self.basket.get_snapshot()

        self.assertEqual(snapshot['total_items'], 15)
        self.assertEqual(snapshot['total_shipments'], 2)
        self.assertEqual(len(snapshot['shipments']), 2)
        self.assertIn('timestamp', snapshot)

    def test_restore_from_snapshot(self):
        """Test restoring basket from snapshot."""
        # Create initial state
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)

        # Get snapshot
        snapshot = self.basket.get_snapshot()

        # Modify basket
        self.basket.add_shipment('SHIP-003', item_count=20)
        self.assertEqual(self.basket.total_items, 35)

        # Restore from snapshot
        self.basket.restore_from_snapshot(snapshot)

        self.assertEqual(self.basket.total_items, 15)
        self.assertEqual(self.basket.total_shipments, 2)
        self.assertIn('SHIP-001', self.basket.shipments)
        self.assertNotIn('SHIP-003', self.basket.shipments)

    def test_restore_from_snapshot_with_locked_basket(self):
        """Test restoring locked basket from snapshot."""
        # Create snapshot
        self.basket.add_shipment('SHIP-001', item_count=5)
        snapshot = self.basket.get_snapshot()

        # Lock basket
        self.basket.lock()

        # Restore should work even when locked
        self.basket.restore_from_snapshot(snapshot)

        self.assertEqual(self.basket.total_items, 5)

    # =========================================================================
    # Capacity Tests
    # =========================================================================

    def test_fill_basket_to_capacity(self):
        """Test filling basket to exactly max capacity."""
        # Add shipments totaling 10,000 items
        for i in range(1, 101):
            self.basket.add_shipment(f'SHIP-{i:03d}', item_count=100)

        self.assertEqual(self.basket.total_items, 10000)
        self.assertEqual(self.basket.total_shipments, 100)

    def test_cannot_exceed_capacity(self):
        """Test that basket cannot exceed maximum capacity."""
        self.basket.add_shipment('SHIP-001', item_count=10000)

        with self.assertRaises(AustraliaPostBasketError):
            self.basket.add_shipment('SHIP-002', item_count=1)

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_add_shipment_with_empty_id(self):
        """Test adding shipment with empty ID raises error."""
        with self.assertRaises(AustraliaPostBasketError):
            self.basket.add_shipment('', item_count=5)

    def test_remove_shipment_with_empty_id(self):
        """Test removing shipment with empty ID raises error."""
        with self.assertRaises(AustraliaPostBasketError):
            self.basket.remove_shipment('')

    def test_get_shipment_ids(self):
        """Test getting list of shipment IDs."""
        self.basket.add_shipment('SHIP-001', item_count=5)
        self.basket.add_shipment('SHIP-002', item_count=10)
        self.basket.add_shipment('SHIP-003', item_count=3)

        shipment_ids = self.basket.get_shipment_ids()

        self.assertEqual(len(shipment_ids), 3)
        self.assertIn('SHIP-001', shipment_ids)
        self.assertIn('SHIP-002', shipment_ids)
        self.assertIn('SHIP-003', shipment_ids)


if __name__ == '__main__':
    unittest.main()
