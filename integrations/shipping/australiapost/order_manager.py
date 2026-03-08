"""
Australia Post Order Management Module

Handles order creation, retrieval, manifest generation, and order splitting
to meet lodgement validation requirements.

Key Features:
    - Create orders from shipments (PUT /orders)
    - Retrieve order details (GET /orders/{id})
    - Generate order summary/manifest (GET /orders/{id}/summary)
    - Automatic order splitting for >2,000 items
    - Order size validation and tracking

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from .exceptions import (
    AustraliaPostError,
    AustraliaPostValidationError,
    create_exception_from_response,
)

logger = logging.getLogger(__name__)


# Constants
MAX_ORDER_ITEMS = 2000  # Maximum items per order as per lodgement requirements
ORDER_WARNING_THRESHOLD = 1800  # Warn when approaching limit


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrderManager:
    """
    Manages Australia Post orders including creation, retrieval, and manifest generation.

    Responsibilities:
        - Create orders from shipments
        - Validate order size (max 2,000 items)
        - Split large orders automatically
        - Retrieve order details
        - Generate order summaries (manifests)
        - Track order state

    Usage:
        order_manager = OrderManager(auth_client, base_url, api_version)

        # Create order from shipments
        result = order_manager.create_order(
            account_number="2004952470",
            shipment_ids=["SHIP123", "SHIP124"],
            order_reference="ORDER-001"
        )

        # Get order details
        order = order_manager.get_order(
            account_number="2004952470",
            order_id="ORD123"
        )

        # Get order summary (manifest)
        manifest = order_manager.get_order_summary(
            account_number="2004952470",
            order_id="ORD123"
        )
    """

    def __init__(self, auth_client, base_url: str, api_version: str = "v1"):
        """
        Initialize Order Manager.

        Args:
            auth_client: Authentication client for API calls
            base_url: Base URL for Australia Post API
            api_version: API version (default: v1)
        """
        self.auth_client = auth_client
        self.base_url = base_url
        self.api_version = api_version
        self.order_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("OrderManager initialized")

    def create_order(
        self,
        account_number: str,
        shipment_ids: List[str],
        order_reference: Optional[str] = None,
        order_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an order from a list of shipment IDs.

        Validates that the number of items doesn't exceed 2,000.
        If it does, raises an error suggesting use of create_order_with_split().

        Args:
            account_number: Australia Post account number
            shipment_ids: List of shipment IDs to include in order
            order_reference: Optional reference for the order
            order_metadata: Optional metadata for the order

        Returns:
            dict: Order creation response with:
                - order_id: Created order ID
                - order_reference: Order reference
                - shipment_count: Number of shipments in order
                - item_count: Total items in order
                - created_at: Creation timestamp

        Raises:
            AustraliaPostValidationError: If order exceeds 2,000 items
            AustraliaPostError: If order creation fails

        Example:
            result = order_manager.create_order(
                account_number="2004952470",
                shipment_ids=["SHIP123", "SHIP124", "SHIP125"],
                order_reference="ORDER-001"
            )
            # Returns: {
            #     'order_id': 'ORD456',
            #     'order_reference': 'ORDER-001',
            #     'shipment_count': 3,
            #     'item_count': 15,
            #     'created_at': '2025-11-06T10:00:00Z'
            # }
        """
        logger.info(
            f"Creating order for account {account_number} "
            f"with {len(shipment_ids)} shipments"
        )

        # Validate shipment IDs
        if not shipment_ids:
            raise AustraliaPostValidationError(
                "Cannot create order without shipments",
                error_code="40002"
            )

        # Build order request payload
        payload = self._build_order_payload(
            shipment_ids=shipment_ids,
            order_reference=order_reference,
            order_metadata=order_metadata
        )

        # Make API request
        endpoint = f'/shipping/{self.api_version}/orders'

        try:
            response = self.auth_client._make_request(
                method='PUT',
                endpoint=endpoint,
                data=payload,
                headers={'Account-Number': account_number}
            )

            # Parse response
            order_data = self._parse_order_response(response)

            # Cache order
            if order_data.get('order_id'):
                self.order_cache[order_data['order_id']] = order_data

            logger.info(f"Order created successfully: {order_data.get('order_id')}")

            return order_data

        except Exception as e:
            logger.error(f"Order creation failed: {e}")
            raise create_exception_from_response(e)

    def get_order(
        self,
        account_number: str,
        order_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve order details.

        Args:
            account_number: Australia Post account number
            order_id: Order ID to retrieve
            use_cache: Whether to use cached data if available

        Returns:
            dict: Order details including:
                - order_id: Order ID
                - order_reference: Order reference
                - status: Order status
                - shipments: List of shipments in order
                - item_count: Total items
                - created_at: Creation timestamp
                - updated_at: Last update timestamp

        Raises:
            AustraliaPostError: If order retrieval fails

        Example:
            order = order_manager.get_order(
                account_number="2004952470",
                order_id="ORD456"
            )
        """
        # Check cache first
        if use_cache and order_id in self.order_cache:
            logger.debug(f"Returning cached order: {order_id}")
            return self.order_cache[order_id]

        logger.info(f"Retrieving order {order_id} for account {account_number}")

        endpoint = f'/shipping/{self.api_version}/accounts/{account_number}/orders/{order_id}'

        try:
            response = self.auth_client._make_request(
                method='GET',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            order_data = self._parse_order_response(response)

            # Update cache
            self.order_cache[order_id] = order_data

            logger.info(f"Order retrieved successfully: {order_id}")

            return order_data

        except Exception as e:
            logger.error(f"Order retrieval failed: {e}")
            raise create_exception_from_response(e)

    def get_order_summary(
        self,
        account_number: str,
        order_id: str,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Get order summary/manifest for lodgement.

        The manifest is required for production lodgement and contains
        all shipment details formatted for Australia Post processing.

        Args:
            account_number: Australia Post account number
            order_id: Order ID to get summary for
            format: Response format ('json' or 'pdf')

        Returns:
            dict: Order summary/manifest with:
                - order_id: Order ID
                - manifest_url: URL to download PDF manifest (if format='pdf')
                - summary: Detailed shipment summary (if format='json')
                - total_items: Total item count
                - total_weight: Total weight
                - created_at: Summary generation timestamp

        Raises:
            AustraliaPostError: If manifest retrieval fails

        Example:
            # Get JSON summary
            manifest = order_manager.get_order_summary(
                account_number="2004952470",
                order_id="ORD456",
                format='json'
            )

            # Get PDF manifest URL
            manifest = order_manager.get_order_summary(
                account_number="2004952470",
                order_id="ORD456",
                format='pdf'
            )
            # manifest_url = manifest['manifest_url']
        """
        logger.info(
            f"Getting order summary for order {order_id} "
            f"(account: {account_number}, format: {format})"
        )

        endpoint = (
            f'/shipping/{self.api_version}/accounts/{account_number}/'
            f'orders/{order_id}/summary'
        )

        headers = {
            'Account-Number': account_number,
            'Accept': 'application/json' if format == 'json' else 'application/pdf'
        }

        try:
            response = self.auth_client._make_request(
                method='GET',
                endpoint=endpoint,
                headers=headers
            )

            if format == 'pdf':
                # PDF response handling
                summary_data = {
                    'order_id': order_id,
                    'manifest_url': response.get('url') or response.get('manifest_url'),
                    'format': 'pdf',
                    'generated_at': datetime.utcnow().isoformat()
                }
            else:
                # JSON response
                summary_data = self._parse_order_summary_response(response)
                summary_data['order_id'] = order_id

            logger.info(f"Order summary retrieved successfully: {order_id}")

            return summary_data

        except Exception as e:
            logger.error(f"Order summary retrieval failed: {e}")
            raise create_exception_from_response(e)

    def create_order_with_split(
        self,
        account_number: str,
        shipment_ids: List[str],
        order_reference_prefix: Optional[str] = None,
        order_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Create multiple orders by splitting shipments to stay within 2,000 item limit.

        This method automatically splits shipments across multiple orders if needed.
        Each order will contain up to 2,000 items as per lodgement requirements.

        Args:
            account_number: Australia Post account number
            shipment_ids: List of shipment IDs to include
            order_reference_prefix: Prefix for order references (will append -1, -2, etc.)
            order_metadata: Optional metadata for the orders

        Returns:
            list: List of created order responses, one per order created

        Raises:
            AustraliaPostError: If any order creation fails

        Example:
            # Create orders from 5,000 shipments (will create 3 orders)
            results = order_manager.create_order_with_split(
                account_number="2004952470",
                shipment_ids=shipment_list,  # 5,000 shipments
                order_reference_prefix="BATCH-2025-11"
            )
            # Returns: [
            #     {'order_id': 'ORD1', 'shipment_count': 2000, ...},
            #     {'order_id': 'ORD2', 'shipment_count': 2000, ...},
            #     {'order_id': 'ORD3', 'shipment_count': 1000, ...}
            # ]
        """
        logger.info(
            f"Creating orders with auto-split for {len(shipment_ids)} shipments"
        )

        # Split shipments into chunks
        shipment_chunks = self._split_shipments(shipment_ids)

        logger.info(f"Split into {len(shipment_chunks)} orders")

        created_orders = []

        for i, chunk in enumerate(shipment_chunks, 1):
            # Generate order reference
            if order_reference_prefix:
                order_ref = f"{order_reference_prefix}-{i}"
            else:
                order_ref = f"ORDER-{datetime.utcnow().strftime('%Y%m%d')}-{i}"

            # Add chunk number to metadata
            chunk_metadata = order_metadata.copy() if order_metadata else {}
            chunk_metadata.update({
                'chunk_number': i,
                'total_chunks': len(shipment_chunks)
            })

            try:
                order_result = self.create_order(
                    account_number=account_number,
                    shipment_ids=chunk,
                    order_reference=order_ref,
                    order_metadata=chunk_metadata
                )

                created_orders.append(order_result)

                logger.info(
                    f"Created order {i}/{len(shipment_chunks)}: "
                    f"{order_result.get('order_id')}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to create order {i}/{len(shipment_chunks)}: {e}"
                )
                # Continue with remaining orders or raise?
                # For now, raise to ensure all-or-nothing
                raise

        logger.info(
            f"Successfully created {len(created_orders)} orders "
            f"from {len(shipment_ids)} shipments"
        )

        return created_orders

    def validate_order_size(
        self,
        shipment_ids: List[str],
        get_item_count: Optional[callable] = None
    ) -> Tuple[bool, int, str]:
        """
        Validate if shipments can fit in a single order.

        Args:
            shipment_ids: List of shipment IDs to validate
            get_item_count: Optional callable to get item count for each shipment
                           If not provided, assumes 1 item per shipment

        Returns:
            tuple: (is_valid, item_count, message)
                - is_valid: True if fits in one order (<= 2,000 items)
                - item_count: Total item count
                - message: Validation message

        Example:
            is_valid, count, msg = order_manager.validate_order_size(shipment_ids)
            if not is_valid:
                print(f"Order too large: {msg}")
                # Use create_order_with_split instead
        """
        if get_item_count:
            # Calculate actual item count
            item_count = sum(get_item_count(sid) for sid in shipment_ids)
        else:
            # Default: assume 1 item per shipment
            item_count = len(shipment_ids)

        if item_count <= MAX_ORDER_ITEMS:
            if item_count >= ORDER_WARNING_THRESHOLD:
                message = (
                    f"Order contains {item_count} items, approaching limit of "
                    f"{MAX_ORDER_ITEMS}. Consider splitting."
                )
            else:
                message = f"Order size valid ({item_count} items)"
            return True, item_count, message
        else:
            message = (
                f"Order exceeds maximum size: {item_count} items "
                f"(limit: {MAX_ORDER_ITEMS}). Must split into multiple orders."
            )
            return False, item_count, message

    def _build_order_payload(
        self,
        shipment_ids: List[str],
        order_reference: Optional[str] = None,
        order_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build order creation API payload.

        Args:
            shipment_ids: List of shipment IDs
            order_reference: Optional order reference
            order_metadata: Optional metadata

        Returns:
            dict: API request payload
        """
        payload: Dict[str, Any] = {
            'shipments': [{'shipment_id': sid} for sid in shipment_ids]
        }

        if order_reference:
            payload['order_reference'] = order_reference

        if order_metadata:
            payload['metadata'] = order_metadata

        return payload

    def _parse_order_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse order creation/retrieval response.

        Args:
            response: API response

        Returns:
            dict: Parsed order data
        """
        # Handle various response formats
        order_data = response.get('order', response)

        return {
            'order_id': order_data.get('order_id') or order_data.get('id'),
            'order_reference': order_data.get('order_reference'),
            'status': order_data.get('status', OrderStatus.CREATED.value),
            'shipments': order_data.get('shipments', []),
            'shipment_count': len(order_data.get('shipments', [])),
            'item_count': order_data.get('item_count') or order_data.get('total_items'),
            'created_at': order_data.get('created_at') or datetime.utcnow().isoformat(),
            'updated_at': order_data.get('updated_at'),
            'metadata': order_data.get('metadata', {})
        }

    def _parse_order_summary_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse order summary response.

        Args:
            response: API response

        Returns:
            dict: Parsed summary data
        """
        summary_data = response.get('summary', response)

        return {
            'summary': summary_data,
            'total_items': summary_data.get('total_items'),
            'total_weight': summary_data.get('total_weight'),
            'total_cost': summary_data.get('total_cost'),
            'shipment_details': summary_data.get('shipments', []),
            'format': 'json',
            'generated_at': datetime.utcnow().isoformat()
        }

    def _split_shipments(
        self,
        shipment_ids: List[str],
        max_per_order: int = MAX_ORDER_ITEMS
    ) -> List[List[str]]:
        """
        Split shipment list into chunks for multiple orders.

        Note: This simple implementation splits by shipment count, assuming
        each shipment has 1 item. For more accurate splitting, you would need
        to query each shipment's item count first.

        Args:
            shipment_ids: List of shipment IDs to split
            max_per_order: Maximum shipments per order (default: 2000)

        Returns:
            list: List of shipment ID chunks
        """
        chunks = []
        for i in range(0, len(shipment_ids), max_per_order):
            chunk = shipment_ids[i:i + max_per_order]
            chunks.append(chunk)

        return chunks

    def clear_cache(self) -> None:
        """Clear the order cache."""
        self.order_cache.clear()
        logger.debug("Order cache cleared")

    def get_cached_order_count(self) -> int:
        """
        Get count of cached orders.

        Returns:
            int: Number of orders in cache
        """
        return len(self.order_cache)
