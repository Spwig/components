"""
Australia Post Pickup Service Module

Handles adhoc pickup scheduling for Australia Post shipments.

Key Features:
    - Schedule adhoc pickups (POST /pickups)
    - Pickup address validation
    - Time slot selection
    - Cancel pickups

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, time

from .exceptions import (
    AustraliaPostError,
    AustraliaPostValidationError,
    create_exception_from_response,
)

logger = logging.getLogger(__name__)


class PickupService:
    """
    Handles pickup scheduling operations for Australia Post.

    Provides methods to create, retrieve, and cancel adhoc pickups.

    Responsibilities:
        - Schedule adhoc pickups
        - Validate pickup addresses
        - Manage time slots
        - Cancel pickups

    Usage:
        pickup_service = PickupService(auth_client, base_url, api_version)

        # Schedule pickup
        pickup = pickup_service.create_adhoc_pickup(
            account_number="2004952470",
            pickup_address={...},
            pickup_date="2025-11-08",
            time_slot="morning",
            shipment_ids=["SHIP123", "SHIP124"]
        )

        # Cancel pickup
        pickup_service.cancel_pickup(
            account_number="2004952470",
            pickup_id="PICKUP123"
        )
    """

    # Available time slots
    TIME_SLOTS = {
        'morning': {'start': '08:00', 'end': '12:00'},
        'afternoon': {'start': '12:00', 'end': '17:00'},
        'all_day': {'start': '08:00', 'end': '17:00'}
    }

    def __init__(
        self,
        auth_client,
        base_url: str,
        api_version: str = "v1"
    ):
        """
        Initialize Pickup Service.

        Args:
            auth_client: Authentication client for API calls
            base_url: Base URL for Australia Post API
            api_version: API version (default: v1)
        """
        self.auth_client = auth_client
        self.base_url = base_url
        self.api_version = api_version

        logger.info("PickupService initialized")

    def create_adhoc_pickup(
        self,
        account_number: str,
        pickup_address: Dict[str, str],
        pickup_date: str,
        time_slot: str = 'all_day',
        shipment_ids: Optional[List[str]] = None,
        instructions: Optional[str] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule an adhoc pickup.

        Args:
            account_number: Australia Post account number
            pickup_address: Pickup location address
            pickup_date: Pickup date (ISO format YYYY-MM-DD)
            time_slot: Time slot ('morning', 'afternoon', 'all_day')
            shipment_ids: Optional list of shipment IDs to be picked up
            instructions: Optional pickup instructions
            contact_name: Optional contact person name
            contact_phone: Optional contact phone number

        Returns:
            dict: Pickup confirmation with:
                - pickup_id: Pickup confirmation ID
                - pickup_date: Scheduled pickup date
                - time_slot: Scheduled time slot
                - status: Pickup status
                - tracking_url: URL to track pickup (if available)

        Raises:
            AustraliaPostValidationError: If pickup data is invalid
            AustraliaPostError: If pickup creation fails

        Example:
            pickup = pickup_service.create_adhoc_pickup(
                account_number="2004952470",
                pickup_address={
                    'street': '123 Business St',
                    'suburb': 'Melbourne',
                    'state': 'VIC',
                    'postcode': '3000',
                    'country': 'AU'
                },
                pickup_date="2025-11-08",
                time_slot="morning",
                shipment_ids=["SHIP123", "SHIP124"],
                instructions="Ring front doorbell",
                contact_name="John Smith",
                contact_phone="+61 3 9999 8888"
            )
            # Returns: {
            #     'pickup_id': 'PICKUP456',
            #     'pickup_date': '2025-11-08',
            #     'time_slot': 'morning',
            #     'time_window': '08:00-12:00',
            #     'status': 'scheduled'
            # }
        """
        logger.info(
            f"Creating adhoc pickup for {pickup_date} "
            f"({time_slot}) at {pickup_address.get('postcode')}"
        )

        # Validate time slot
        if time_slot not in self.TIME_SLOTS:
            raise AustraliaPostValidationError(
                f"Invalid time slot: {time_slot}. "
                f"Must be one of: {', '.join(self.TIME_SLOTS.keys())}",
                error_code="INVALID_TIME_SLOT"
            )

        # Validate pickup date
        self._validate_pickup_date(pickup_date)

        # Build request payload
        payload = {
            'pickup_address': pickup_address,
            'pickup_date': pickup_date,
            'time_slot': time_slot,
            'time_window': self.TIME_SLOTS[time_slot]
        }

        if shipment_ids:
            payload['shipment_ids'] = shipment_ids

        if instructions:
            payload['instructions'] = instructions

        if contact_name:
            payload['contact_name'] = contact_name

        if contact_phone:
            payload['contact_phone'] = contact_phone

        endpoint = f'/shipping/{self.api_version}/pickups'

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload,
                headers={'Account-Number': account_number}
            )

            pickup_data = self._parse_pickup_response(response)

            logger.info(
                f"Adhoc pickup scheduled: {pickup_data.get('pickup_id')} "
                f"on {pickup_date} ({time_slot})"
            )

            return pickup_data

        except Exception as e:
            logger.error(f"Adhoc pickup creation failed: {e}")
            raise create_exception_from_response(e)

    def get_pickup(
        self,
        account_number: str,
        pickup_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve pickup details.

        Args:
            account_number: Australia Post account number
            pickup_id: Pickup ID to retrieve

        Returns:
            dict: Pickup details

        Raises:
            AustraliaPostError: If retrieval fails

        Example:
            pickup = pickup_service.get_pickup(
                account_number="2004952470",
                pickup_id="PICKUP456"
            )
        """
        logger.info(f"Retrieving pickup {pickup_id}")

        endpoint = f'/shipping/{self.api_version}/pickups/{pickup_id}'

        try:
            response = self.auth_client._make_request(
                method='GET',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            pickup_data = self._parse_pickup_response(response)

            logger.info(f"Pickup retrieved: {pickup_id}")

            return pickup_data

        except Exception as e:
            logger.error(f"Pickup retrieval failed: {e}")
            raise create_exception_from_response(e)

    def cancel_pickup(
        self,
        account_number: str,
        pickup_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a scheduled pickup.

        Args:
            account_number: Australia Post account number
            pickup_id: Pickup ID to cancel

        Returns:
            dict: Cancellation confirmation

        Raises:
            AustraliaPostError: If cancellation fails

        Example:
            result = pickup_service.cancel_pickup(
                account_number="2004952470",
                pickup_id="PICKUP456"
            )
        """
        logger.info(f"Cancelling pickup {pickup_id}")

        endpoint = f'/shipping/{self.api_version}/pickups/{pickup_id}'

        try:
            response = self.auth_client._make_request(
                method='DELETE',
                endpoint=endpoint,
                headers={'Account-Number': account_number}
            )

            logger.info(f"Pickup cancelled: {pickup_id}")

            return {
                'success': True,
                'pickup_id': pickup_id,
                'status': 'cancelled',
                'message': 'Pickup cancelled successfully'
            }

        except Exception as e:
            logger.error(f"Pickup cancellation failed: {e}")
            raise create_exception_from_response(e)

    def get_available_time_slots(
        self,
        pickup_date: str
    ) -> List[Dict[str, str]]:
        """
        Get available time slots for a pickup date.

        Args:
            pickup_date: Pickup date (ISO format)

        Returns:
            list: Available time slots with time windows

        Example:
            slots = pickup_service.get_available_time_slots("2025-11-08")
            # Returns: [
            #     {'slot': 'morning', 'start': '08:00', 'end': '12:00'},
            #     {'slot': 'afternoon', 'start': '12:00', 'end': '17:00'},
            #     {'slot': 'all_day', 'start': '08:00', 'end': '17:00'}
            # ]
        """
        # For now, return all standard time slots
        # In a real implementation, this might query the API for available slots
        return [
            {
                'slot': slot_name,
                'start': slot_times['start'],
                'end': slot_times['end']
            }
            for slot_name, slot_times in self.TIME_SLOTS.items()
        ]

    def _validate_pickup_date(self, pickup_date: str) -> None:
        """
        Validate pickup date.

        Args:
            pickup_date: Date string to validate (YYYY-MM-DD)

        Raises:
            AustraliaPostValidationError: If date is invalid
        """
        try:
            date_obj = datetime.fromisoformat(pickup_date)
        except ValueError:
            raise AustraliaPostValidationError(
                f"Invalid pickup date format: {pickup_date}. "
                "Use ISO format: YYYY-MM-DD",
                error_code="INVALID_DATE_FORMAT"
            )

        # Check if date is in the past
        today = datetime.now().date()
        if date_obj.date() < today:
            raise AustraliaPostValidationError(
                f"Pickup date cannot be in the past: {pickup_date}",
                error_code="PAST_DATE"
            )

        # Check if date is too far in the future (e.g., > 30 days)
        max_future_date = today + timedelta(days=30)
        if date_obj.date() > max_future_date:
            raise AustraliaPostValidationError(
                f"Pickup date too far in future: {pickup_date}. "
                "Maximum 30 days from today.",
                error_code="DATE_TOO_FAR"
            )

    def _parse_pickup_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse pickup response."""
        pickup_data = response.get('pickup', response)

        return {
            'pickup_id': pickup_data.get('pickup_id') or pickup_data.get('id'),
            'pickup_date': pickup_data.get('pickup_date'),
            'time_slot': pickup_data.get('time_slot'),
            'time_window': pickup_data.get('time_window'),
            'status': pickup_data.get('status', 'scheduled'),
            'pickup_address': pickup_data.get('pickup_address'),
            'shipment_ids': pickup_data.get('shipment_ids', []),
            'contact_name': pickup_data.get('contact_name'),
            'contact_phone': pickup_data.get('contact_phone'),
            'instructions': pickup_data.get('instructions'),
            'tracking_url': pickup_data.get('tracking_url'),
            'created_at': pickup_data.get('created_at')
        }
