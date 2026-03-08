"""
Australia Post Basket Management Module

Manages the "basket" of shipments before they are converted into orders.
Tracks basket size to ensure compliance with the 10,000 item limit.

Key Features:
    - Track basket size (10,000 item limit)
    - Basket state persistence and recovery
    - Basket overflow warnings
    - Shipment tracking before order creation
    - Clear completed shipments

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from enum import Enum

from .exceptions import (
    AustraliaPostError,
    AustraliaPostValidationError,
)

logger = logging.getLogger(__name__)


# Constants
MAX_BASKET_SIZE = 10000  # Maximum items in basket before order creation
BASKET_WARNING_THRESHOLD = 8000  # Warn when approaching limit


class BasketStatus(Enum):
    """Basket status enumeration."""
    ACTIVE = "active"
    READY = "ready"  # Ready to create order
    WARNING = "warning"  # Approaching limit
    FULL = "full"  # At or over limit
    LOCKED = "locked"  # Locked for order creation


class BasketManager:
    """
    Manages the basket of shipments before order creation.

    The basket is a temporary holding area for shipments that have been created
    but not yet converted into an order. Australia Post requires that baskets
    contain no more than 10,000 items before creating an order.

    Responsibilities:
        - Track basket size (item count)
        - Enforce 10,000 item limit
        - Provide warnings at 8,000 items
        - Track shipment IDs in basket
        - Clear completed/cancelled shipments
        - Provide basket status and statistics

    Usage:
        basket_manager = BasketManager()

        # Add shipments to basket
        basket_manager.add_shipment("SHIP123", item_count=5)
        basket_manager.add_shipment("SHIP124", item_count=3)

        # Check basket status
        status = basket_manager.get_status()
        # {'status': 'active', 'item_count': 8, 'shipment_count': 2}

        # Get all shipments ready for order
        shipments = basket_manager.get_all_shipments()

        # Clear basket after order creation
        basket_manager.clear()
    """

    def __init__(self, max_size: int = MAX_BASKET_SIZE):
        """
        Initialize Basket Manager.

        Args:
            max_size: Maximum basket size (default: 10,000)
        """
        self.max_size = max_size
        self.warning_threshold = BASKET_WARNING_THRESHOLD

        # Basket data structures
        self.shipments: Dict[str, Dict[str, Any]] = {}  # shipment_id -> shipment_data
        self.item_count = 0
        self.status = BasketStatus.ACTIVE
        self.locked = False

        # Statistics
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()

        logger.info(f"BasketManager initialized (max_size={max_size})")

    def add_shipment(
        self,
        shipment_id: str,
        item_count: int = 1,
        shipment_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a shipment to the basket.

        Args:
            shipment_id: Unique shipment identifier
            item_count: Number of items in this shipment (default: 1)
            shipment_data: Optional additional shipment data

        Returns:
            dict: Updated basket status

        Raises:
            AustraliaPostValidationError: If adding would exceed basket limit
            ValueError: If basket is locked

        Example:
            result = basket_manager.add_shipment(
                shipment_id="SHIP123",
                item_count=5,
                shipment_data={'reference': 'ORDER-001-ITEM-1'}
            )
        """
        if self.locked:
            raise ValueError("Basket is locked for order creation")

        # Check if adding would exceed limit
        new_total = self.item_count + item_count
        if new_total > self.max_size:
            raise AustraliaPostValidationError(
                f"Adding {item_count} items would exceed basket limit "
                f"({new_total} > {self.max_size}). Create an order first.",
                error_code="BASKET_LIMIT_EXCEEDED"
            )

        # Check if shipment already exists
        if shipment_id in self.shipments:
            logger.warning(f"Shipment {shipment_id} already in basket, updating...")
            # Update existing shipment
            old_count = self.shipments[shipment_id]['item_count']
            self.item_count -= old_count

        # Add shipment
        self.shipments[shipment_id] = {
            'shipment_id': shipment_id,
            'item_count': item_count,
            'added_at': datetime.utcnow().isoformat(),
            'data': shipment_data or {}
        }

        self.item_count += item_count
        self.last_updated = datetime.utcnow()

        # Update status
        self._update_status()

        logger.info(
            f"Added shipment {shipment_id} with {item_count} items "
            f"(basket: {self.item_count}/{self.max_size})"
        )

        return self.get_status()

    def remove_shipment(self, shipment_id: str) -> Dict[str, Any]:
        """
        Remove a shipment from the basket.

        Args:
            shipment_id: Shipment ID to remove

        Returns:
            dict: Updated basket status

        Raises:
            ValueError: If basket is locked or shipment not found

        Example:
            result = basket_manager.remove_shipment("SHIP123")
        """
        if self.locked:
            raise ValueError("Basket is locked for order creation")

        if shipment_id not in self.shipments:
            raise ValueError(f"Shipment {shipment_id} not found in basket")

        # Remove shipment
        removed = self.shipments.pop(shipment_id)
        self.item_count -= removed['item_count']
        self.last_updated = datetime.utcnow()

        # Update status
        self._update_status()

        logger.info(
            f"Removed shipment {shipment_id} with {removed['item_count']} items "
            f"(basket: {self.item_count}/{self.max_size})"
        )

        return self.get_status()

    def get_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get shipment data from basket.

        Args:
            shipment_id: Shipment ID to retrieve

        Returns:
            dict: Shipment data or None if not found
        """
        return self.shipments.get(shipment_id)

    def has_shipment(self, shipment_id: str) -> bool:
        """
        Check if shipment is in basket.

        Args:
            shipment_id: Shipment ID to check

        Returns:
            bool: True if shipment is in basket
        """
        return shipment_id in self.shipments

    def get_all_shipments(self) -> List[str]:
        """
        Get all shipment IDs in basket.

        Returns:
            list: List of shipment IDs
        """
        return list(self.shipments.keys())

    def get_shipment_count(self) -> int:
        """
        Get number of shipments in basket.

        Returns:
            int: Shipment count
        """
        return len(self.shipments)

    def get_item_count(self) -> int:
        """
        Get total item count in basket.

        Returns:
            int: Total items across all shipments
        """
        return self.item_count

    def get_available_capacity(self) -> int:
        """
        Get remaining capacity in basket.

        Returns:
            int: Number of items that can still be added
        """
        return max(0, self.max_size - self.item_count)

    def can_add_items(self, item_count: int) -> bool:
        """
        Check if items can be added without exceeding limit.

        Args:
            item_count: Number of items to check

        Returns:
            bool: True if items can be added
        """
        return (self.item_count + item_count) <= self.max_size

    def get_status(self) -> Dict[str, Any]:
        """
        Get current basket status.

        Returns:
            dict: Basket status including:
                - status: Current basket status
                - item_count: Total items
                - shipment_count: Total shipments
                - capacity: Remaining capacity
                - utilization: Percentage full
                - locked: Whether basket is locked
                - warnings: List of warnings (if any)
        """
        utilization = (self.item_count / self.max_size * 100) if self.max_size > 0 else 0

        warnings = []
        if self.status == BasketStatus.WARNING:
            warnings.append(
                f"Basket approaching limit: {self.item_count}/{self.max_size} items "
                f"({utilization:.1f}%)"
            )
        elif self.status == BasketStatus.FULL:
            warnings.append(
                f"Basket at capacity: {self.item_count}/{self.max_size} items. "
                "Create an order to continue."
            )

        return {
            'status': self.status.value,
            'item_count': self.item_count,
            'shipment_count': len(self.shipments),
            'max_size': self.max_size,
            'capacity': self.get_available_capacity(),
            'utilization_percent': round(utilization, 2),
            'locked': self.locked,
            'warnings': warnings,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed basket statistics.

        Returns:
            dict: Detailed statistics including:
                - avg_items_per_shipment: Average items per shipment
                - largest_shipment: Largest shipment item count
                - smallest_shipment: Smallest shipment item count
                - total_shipments: Total shipment count
                - total_items: Total item count
        """
        if not self.shipments:
            return {
                'total_shipments': 0,
                'total_items': 0,
                'avg_items_per_shipment': 0,
                'largest_shipment': 0,
                'smallest_shipment': 0
            }

        item_counts = [s['item_count'] for s in self.shipments.values()]

        return {
            'total_shipments': len(self.shipments),
            'total_items': self.item_count,
            'avg_items_per_shipment': round(self.item_count / len(self.shipments), 2),
            'largest_shipment': max(item_counts),
            'smallest_shipment': min(item_counts),
            'capacity_remaining': self.get_available_capacity(),
            'utilization_percent': round(
                (self.item_count / self.max_size * 100) if self.max_size > 0 else 0,
                2
            )
        }

    def clear(self) -> None:
        """
        Clear all shipments from basket.

        This is typically called after successfully creating an order.
        """
        if self.locked:
            logger.warning("Attempting to clear locked basket")

        shipment_count = len(self.shipments)
        item_count = self.item_count

        self.shipments.clear()
        self.item_count = 0
        self.status = BasketStatus.ACTIVE
        self.locked = False
        self.last_updated = datetime.utcnow()

        logger.info(
            f"Basket cleared: removed {shipment_count} shipments "
            f"({item_count} items)"
        )

    def lock(self) -> None:
        """
        Lock basket for order creation.

        Prevents modifications while an order is being created.
        """
        self.locked = True
        self.status = BasketStatus.LOCKED
        logger.info("Basket locked for order creation")

    def unlock(self) -> None:
        """
        Unlock basket.

        Allows modifications after order creation completes or fails.
        """
        self.locked = False
        self._update_status()
        logger.info("Basket unlocked")

    def is_locked(self) -> bool:
        """
        Check if basket is locked.

        Returns:
            bool: True if basket is locked
        """
        return self.locked

    def is_empty(self) -> bool:
        """
        Check if basket is empty.

        Returns:
            bool: True if basket contains no shipments
        """
        return len(self.shipments) == 0

    def is_full(self) -> bool:
        """
        Check if basket is at capacity.

        Returns:
            bool: True if basket is at or over limit
        """
        return self.item_count >= self.max_size

    def _update_status(self) -> None:
        """Update basket status based on current item count."""
        if self.locked:
            self.status = BasketStatus.LOCKED
        elif self.item_count >= self.max_size:
            self.status = BasketStatus.FULL
        elif self.item_count >= self.warning_threshold:
            self.status = BasketStatus.WARNING
        elif self.item_count > 0:
            self.status = BasketStatus.READY
        else:
            self.status = BasketStatus.ACTIVE

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate basket state.

        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []

        if self.item_count > self.max_size:
            errors.append(
                f"Basket exceeds maximum size: {self.item_count} > {self.max_size}"
            )

        if self.item_count < 0:
            errors.append(f"Invalid item count: {self.item_count}")

        if len(self.shipments) == 0 and self.item_count != 0:
            errors.append("Item count mismatch: no shipments but item_count > 0")

        # Verify item count matches sum of shipment counts
        calculated_count = sum(s['item_count'] for s in self.shipments.values())
        if calculated_count != self.item_count:
            errors.append(
                f"Item count mismatch: calculated={calculated_count}, "
                f"stored={self.item_count}"
            )

        return (len(errors) == 0, errors)

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a complete snapshot of basket state for persistence.

        Returns:
            dict: Complete basket state that can be used to restore basket
        """
        return {
            'shipments': self.shipments.copy(),
            'item_count': self.item_count,
            'max_size': self.max_size,
            'status': self.status.value,
            'locked': self.locked,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'snapshot_at': datetime.utcnow().isoformat()
        }

    def restore_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore basket from a snapshot.

        Args:
            snapshot: Snapshot data from get_snapshot()
        """
        self.shipments = snapshot['shipments'].copy()
        self.item_count = snapshot['item_count']
        self.max_size = snapshot.get('max_size', MAX_BASKET_SIZE)
        self.locked = snapshot.get('locked', False)

        # Restore timestamps if available
        if 'created_at' in snapshot:
            self.created_at = datetime.fromisoformat(snapshot['created_at'])
        if 'last_updated' in snapshot:
            self.last_updated = datetime.fromisoformat(snapshot['last_updated'])

        self._update_status()

        logger.info(
            f"Basket restored from snapshot: {len(self.shipments)} shipments, "
            f"{self.item_count} items"
        )

    def __repr__(self) -> str:
        """String representation of basket."""
        return (
            f"<BasketManager status={self.status.value} "
            f"items={self.item_count}/{self.max_size} "
            f"shipments={len(self.shipments)}>"
        )
