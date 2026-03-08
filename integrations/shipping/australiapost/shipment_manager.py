"""
Australia Post Shipment Management Module

Enhanced shipment operations including retrieval, updates, and item-level management.
Supports basket workflow before order creation.

Key Features:
    - Get shipment details (GET /shipments/{id})
    - List and filter shipments (GET /shipments)
    - Update shipments before order creation (PUT /shipments/{id})
    - Delete items from shipments
    - Update individual items

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .exceptions import (
    AustraliaPostError,
    AustraliaPostValidationError,
    AustraliaPostShipmentError,
    create_exception_from_response,
)

logger = logging.getLogger(__name__)


class ShipmentManager:
    """
    Manages enhanced shipment operations for basket management workflow.

    Provides methods to retrieve, update, and manage shipments and their items
    before they are converted into orders.

    Responsibilities:
        - Retrieve individual shipment details
        - List and filter shipments
        - Update shipment data
        - Manage items within shipments (add, update, delete)
        - Track shipment state

    Usage:
        shipment_manager = ShipmentManager(auth_client, base_url, api_version)

        # Get shipment details
        shipment = shipment_manager.get_shipment(
            account_number="2004952470",
            shipment_id="SHIP123"
        )

        # List shipments
        shipments = shipment_manager.get_shipments(
            account_number="2004952470",
            status="pending"
        )

        # Update shipment
        shipment_manager.update_shipment(
            account_number="2004952470",
            shipment_id="SHIP123",
            updates={'reference': 'NEW-REF-001'}
        )

        # Delete item from shipment
        shipment_manager.delete_item(
            account_number="2004952470",
            shipment_id="SHIP123",
            item_id="ITEM456"
        )
    """

    def __init__(self, auth_client, base_url: str, api_version: str = "v1"):
        """
        Initialize Shipment Manager.

        Args:
            auth_client: Authentication client for API calls
            base_url: Base URL for Australia Post API
            api_version: API version (default: v1)
        """
        self.auth_client = auth_client
        self.base_url = base_url
        self.api_version = api_version
        self.shipment_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("ShipmentManager initialized")

    def get_shipment(
        self,
        account_number: str,
        shipment_id: str,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve shipment details.

        Args:
            account_number: Australia Post account number
            shipment_id: Shipment ID to retrieve
            use_cache: Whether to use cached data if available

        Returns:
            dict: Shipment details including:
                - shipment_id: Shipment ID
                - items: List of items in shipment
                - from_address: Origin address
                - to_address: Destination address
                - status: Shipment status
                - created_at: Creation timestamp
                - metadata: Additional shipment data

        Raises:
            AustraliaPostShipmentError: If shipment not found
            AustraliaPostError: If retrieval fails

        Example:
            shipment = shipment_manager.get_shipment(
                account_number="2004952470",
                shipment_id="SHIP123"
            )
        """
        # Check cache
        if use_cache and shipment_id in self.shipment_cache:
            logger.debug(f"Returning cached shipment: {shipment_id}")
            return self.shipment_cache[shipment_id]

        logger.info(f"Retrieving shipment {shipment_id} for account {account_number}")

        endpoint = f'/shipping/{self.api_version}/shipments/{shipment_id}'

        try:
            response = self.auth_client._make_request(
                method='GET',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            shipment_data = self._parse_shipment_response(response)

            # Update cache
            self.shipment_cache[shipment_id] = shipment_data

            logger.info(f"Shipment retrieved successfully: {shipment_id}")

            return shipment_data

        except Exception as e:
            logger.error(f"Shipment retrieval failed: {e}")
            raise create_exception_from_response(e)

    def get_shipments(
        self,
        account_number: str,
        status: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        reference: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List and filter shipments.

        Args:
            account_number: Australia Post account number
            status: Filter by status (e.g., 'pending', 'created', 'in_order')
            created_after: Filter shipments created after this date (ISO format)
            created_before: Filter shipments created before this date (ISO format)
            reference: Filter by reference string
            limit: Maximum number of shipments to return (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            dict: Shipments list with:
                - shipments: List of shipment objects
                - total: Total count
                - limit: Request limit
                - offset: Request offset
                - has_more: Whether more results available

        Raises:
            AustraliaPostError: If listing fails

        Example:
            results = shipment_manager.get_shipments(
                account_number="2004952470",
                status="pending",
                limit=50
            )
            # Returns: {
            #     'shipments': [...],
            #     'total': 127,
            #     'limit': 50,
            #     'offset': 0,
            #     'has_more': True
            # }
        """
        logger.info(
            f"Listing shipments for account {account_number} "
            f"(status={status}, limit={limit}, offset={offset})"
        )

        # Build query parameters
        params = {
            'limit': limit,
            'offset': offset
        }

        if status:
            params['status'] = status
        if created_after:
            params['created_after'] = created_after
        if created_before:
            params['created_before'] = created_before
        if reference:
            params['reference'] = reference

        endpoint = f'/shipping/{self.api_version}/shipments'

        try:
            response = self.auth_client._make_request(
                method='GET',
                endpoint=endpoint,
                params=params,
                headers={'Account-Number': account_number}
            )

            results = self._parse_shipments_list_response(response)

            logger.info(
                f"Retrieved {len(results['shipments'])} shipments "
                f"(total: {results.get('total', 'unknown')})"
            )

            return results

        except Exception as e:
            logger.error(f"Shipments listing failed: {e}")
            raise create_exception_from_response(e)

    def update_shipment(
        self,
        account_number: str,
        shipment_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update shipment data before order creation.

        Can update shipment metadata, references, and certain fields.
        Cannot update shipments that are already in an order.

        Args:
            account_number: Australia Post account number
            shipment_id: Shipment ID to update
            updates: Dictionary of fields to update

        Returns:
            dict: Updated shipment data

        Raises:
            AustraliaPostShipmentError: If shipment is locked or in order
            AustraliaPostValidationError: If updates are invalid
            AustraliaPostError: If update fails

        Example:
            updated = shipment_manager.update_shipment(
                account_number="2004952470",
                shipment_id="SHIP123",
                updates={
                    'reference': 'NEW-REF-001',
                    'metadata': {'customer_id': '12345'}
                }
            )
        """
        logger.info(
            f"Updating shipment {shipment_id} for account {account_number}"
        )

        endpoint = f'/shipping/{self.api_version}/shipments/{shipment_id}'

        try:
            response = self.auth_client._make_request(
                method='PUT',
                endpoint=endpoint,
                data=updates,
                headers={'Account-Number': account_number}
            )

            shipment_data = self._parse_shipment_response(response)

            # Update cache
            self.shipment_cache[shipment_id] = shipment_data

            logger.info(f"Shipment updated successfully: {shipment_id}")

            return shipment_data

        except Exception as e:
            logger.error(f"Shipment update failed: {e}")
            raise create_exception_from_response(e)

    def delete_item(
        self,
        account_number: str,
        shipment_id: str,
        item_id: str
    ) -> Dict[str, Any]:
        """
        Delete an item from a shipment.

        Removes a single item from the shipment. If this is the last item,
        consider deleting the entire shipment instead.

        Args:
            account_number: Australia Post account number
            shipment_id: Shipment containing the item
            item_id: Item ID to delete

        Returns:
            dict: Updated shipment data

        Raises:
            AustraliaPostShipmentError: If item not found or shipment locked
            AustraliaPostError: If deletion fails

        Example:
            result = shipment_manager.delete_item(
                account_number="2004952470",
                shipment_id="SHIP123",
                item_id="ITEM456"
            )
        """
        logger.info(
            f"Deleting item {item_id} from shipment {shipment_id} "
            f"(account: {account_number})"
        )

        endpoint = (
            f'/shipping/{self.api_version}/shipments/{shipment_id}/'
            f'items/{item_id}'
        )

        try:
            response = self.auth_client._make_request(
                method='DELETE',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            # Response might be updated shipment or confirmation
            if response and isinstance(response, dict):
                result = self._parse_shipment_response(response)

                # Update cache
                if shipment_id in self.shipment_cache:
                    del self.shipment_cache[shipment_id]  # Invalidate cache

                logger.info(f"Item {item_id} deleted successfully")

                return result
            else:
                logger.info(f"Item {item_id} deleted successfully")
                return {'success': True, 'message': 'Item deleted'}

        except Exception as e:
            logger.error(f"Item deletion failed: {e}")
            raise create_exception_from_response(e)

    def update_item(
        self,
        account_number: str,
        shipment_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an item within a shipment.

        Modifies item data such as quantity, weight, dimensions, or metadata.

        Args:
            account_number: Australia Post account number
            shipment_id: Shipment containing the item
            item_id: Item ID to update
            updates: Dictionary of item fields to update

        Returns:
            dict: Updated item data or updated shipment data

        Raises:
            AustraliaPostShipmentError: If item not found or shipment locked
            AustraliaPostValidationError: If updates are invalid
            AustraliaPostError: If update fails

        Example:
            updated = shipment_manager.update_item(
                account_number="2004952470",
                shipment_id="SHIP123",
                item_id="ITEM456",
                updates={
                    'quantity': 2,
                    'weight': 1.5
                }
            )
        """
        logger.info(
            f"Updating item {item_id} in shipment {shipment_id} "
            f"(account: {account_number})"
        )

        endpoint = (
            f'/shipping/{self.api_version}/shipments/{shipment_id}/'
            f'items/{item_id}'
        )

        try:
            response = self.auth_client._make_request(
                method='PUT',
                endpoint=endpoint,
                data=updates,
                headers={'Account-Number': account_number}
            )

            result = self._parse_item_response(response)

            # Invalidate shipment cache
            if shipment_id in self.shipment_cache:
                del self.shipment_cache[shipment_id]

            logger.info(f"Item {item_id} updated successfully")

            return result

        except Exception as e:
            logger.error(f"Item update failed: {e}")
            raise create_exception_from_response(e)

    def delete_shipment(
        self,
        account_number: str,
        shipment_id: str
    ) -> Dict[str, Any]:
        """
        Delete an entire shipment from basket.

        This is an alias for the void_label functionality but specifically
        for shipments that haven't been added to an order yet.

        Args:
            account_number: Australia Post account number
            shipment_id: Shipment ID to delete

        Returns:
            dict: Deletion confirmation

        Raises:
            AustraliaPostShipmentError: If shipment is in an order
            AustraliaPostError: If deletion fails

        Example:
            result = shipment_manager.delete_shipment(
                account_number="2004952470",
                shipment_id="SHIP123"
            )
        """
        logger.info(
            f"Deleting shipment {shipment_id} (account: {account_number})"
        )

        endpoint = f'/shipping/{self.api_version}/shipments/{shipment_id}'

        try:
            response = self.auth_client._make_request(
                method='DELETE',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            # Remove from cache
            if shipment_id in self.shipment_cache:
                del self.shipment_cache[shipment_id]

            logger.info(f"Shipment {shipment_id} deleted successfully")

            return {
                'success': True,
                'shipment_id': shipment_id,
                'message': 'Shipment deleted successfully'
            }

        except Exception as e:
            logger.error(f"Shipment deletion failed: {e}")
            raise create_exception_from_response(e)

    def count_shipment_items(self, shipment: Dict[str, Any]) -> int:
        """
        Count items in a shipment.

        Args:
            shipment: Shipment data dictionary

        Returns:
            int: Number of items in shipment
        """
        items = shipment.get('items', [])
        return len(items)

    def _parse_shipment_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse shipment response.

        Args:
            response: API response

        Returns:
            dict: Parsed shipment data
        """
        # Handle various response formats
        shipment_data = response.get('shipment', response)

        return {
            'shipment_id': shipment_data.get('shipment_id') or shipment_data.get('id'),
            'items': shipment_data.get('items', []),
            'item_count': len(shipment_data.get('items', [])),
            'from_address': shipment_data.get('from') or shipment_data.get('from_address'),
            'to_address': shipment_data.get('to') or shipment_data.get('to_address'),
            'status': shipment_data.get('status'),
            'reference': shipment_data.get('shipment_reference') or shipment_data.get('reference'),
            'created_at': shipment_data.get('created_at'),
            'updated_at': shipment_data.get('updated_at'),
            'metadata': shipment_data.get('metadata', {}),
            'order_id': shipment_data.get('order_id'),  # If already in an order
            'label_url': shipment_data.get('label_url')
        }

    def _parse_shipments_list_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse shipments list response.

        Args:
            response: API response

        Returns:
            dict: Parsed list with pagination info
        """
        shipments_data = response.get('shipments', [])
        parsed_shipments = [
            self._parse_shipment_response({'shipment': s})
            for s in shipments_data
        ]

        total = response.get('total', len(parsed_shipments))
        limit = response.get('limit', len(parsed_shipments))
        offset = response.get('offset', 0)

        return {
            'shipments': parsed_shipments,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + len(parsed_shipments)) < total
        }

    def _parse_item_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse item response.

        Args:
            response: API response

        Returns:
            dict: Parsed item data
        """
        item_data = response.get('item', response)

        return {
            'item_id': item_data.get('item_id') or item_data.get('id'),
            'description': item_data.get('description'),
            'quantity': item_data.get('quantity', 1),
            'weight': item_data.get('weight'),
            'length': item_data.get('length'),
            'width': item_data.get('width'),
            'height': item_data.get('height'),
            'product_id': item_data.get('product_id'),
            'metadata': item_data.get('metadata', {})
        }

    def clear_cache(self) -> None:
        """Clear the shipment cache."""
        self.shipment_cache.clear()
        logger.debug("Shipment cache cleared")

    def get_cached_shipment_count(self) -> int:
        """
        Get count of cached shipments.

        Returns:
            int: Number of shipments in cache
        """
        return len(self.shipment_cache)
