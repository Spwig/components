"""
NinjaVan Webhook Management

Handles webhook subscription management and webhook event processing
for NinjaVan tracking updates.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.utils.translation import gettext_lazy as _

from .exceptions import (
    NinjaVanError,
    NinjaVanWebhookError,
    NinjaVanAuthenticationError,
    parse_error_response,
)
from . import utils


logger = logging.getLogger(__name__)


# NinjaVan Webhook Events V2
WEBHOOK_EVENTS_V2 = [
    "Pending Pickup",
    "On Hold",
    "In Transit",
    "Out for Delivery",
    "Delivered, Received by Customer",
    "Delivery Fail",
    "Cancelled",
    "Returned to Sender",
]


class WebhookSubscriptionManager:
    """
    Manages webhook subscriptions with NinjaVan API.

    Handles creating, listing, and deleting webhook subscriptions
    for tracking event notifications.
    """

    def __init__(
        self,
        base_url: str,
        access_token: str,
        timeout: int = 30,
    ):
        """
        Initialize webhook subscription manager.

        Args:
            base_url: NinjaVan API base URL (with country code)
            access_token: OAuth access token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.access_token = access_token
        self.timeout = timeout

    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """
        List all active webhook subscriptions.

        Returns:
            List of subscription dictionaries:
            [{
                'id': 'sub_123',
                'event': 'Delivered, Received by Customer',
                'uri': 'https://myshop.com/webhooks/',
                'created_at': '2025-10-23T10:30:00Z'
            }]

        Raises:
            NinjaVanAuthenticationError: If authentication fails
            NinjaVanError: If API request fails
        """
        logger.info("Listing webhook subscriptions")

        endpoint = "/plugins/2.1/shippers/webhooks"
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                subscriptions = response.json()
                logger.info(f"Found {len(subscriptions)} webhook subscriptions")
                return subscriptions

            # Handle error
            error = parse_error_response(response)
            logger.error(f"Failed to list subscriptions: {error}")
            raise error

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error listing subscriptions: {e}")
            raise NinjaVanError(f"Failed to list subscriptions: {str(e)}")

    def subscribe(self, event_type: str, uri: str) -> Dict[str, Any]:
        """
        Subscribe to a webhook event.

        Args:
            event_type: Event type to subscribe to (e.g., "Delivered, Received by Customer")
            uri: Webhook endpoint URL (HTTPS required)

        Returns:
            Subscription details:
            {
                'id': 'sub_123',
                'event': 'Delivered, Received by Customer',
                'uri': 'https://myshop.com/webhooks/',
                'created_at': '2025-10-23T10:30:00Z'
            }

        Raises:
            NinjaVanValidationError: If event type or URI is invalid
            NinjaVanAuthenticationError: If authentication fails
            NinjaVanError: If API request fails
        """
        logger.info(f"Subscribing to webhook event: {event_type}")

        # Validate event type
        if event_type not in WEBHOOK_EVENTS_V2:
            logger.warning(f"Unknown event type: {event_type}")

        # Validate URI (must be HTTPS)
        if not uri.startswith('https://'):
            raise NinjaVanWebhookError(
                "Webhook URI must use HTTPS protocol",
                status_code=400,
            )

        endpoint = "/plugins/2.1/shippers/webhooks"
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json',
        }

        payload = {
            'event': event_type,
            'uri': uri,
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code in [200, 201]:
                subscription = response.json()
                logger.info(f"Subscribed to {event_type}: {subscription.get('id')}")
                return subscription

            # Handle error
            error = parse_error_response(response)
            logger.error(f"Failed to subscribe to {event_type}: {error}")
            raise error

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error subscribing to webhook: {e}")
            raise NinjaVanError(f"Failed to subscribe to webhook: {str(e)}")

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from a webhook event.

        Args:
            subscription_id: Subscription ID to delete

        Returns:
            True if unsubscribed successfully

        Raises:
            NinjaVanAuthenticationError: If authentication fails
            NinjaVanError: If API request fails
        """
        logger.info(f"Unsubscribing from webhook: {subscription_id}")

        endpoint = f"/plugins/2.1/shippers/webhooks/{subscription_id}"
        url = f"{self.base_url}{endpoint}"

        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json',
        }

        try:
            response = requests.delete(
                url,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code in [200, 204]:
                logger.info(f"Unsubscribed from {subscription_id}")
                return True

            # Handle error
            error = parse_error_response(response)
            logger.error(f"Failed to unsubscribe from {subscription_id}: {error}")
            raise error

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error unsubscribing from webhook: {e}")
            raise NinjaVanError(f"Failed to unsubscribe from webhook: {str(e)}")

    def subscribe_to_all_events(self, base_uri: str) -> List[Dict[str, Any]]:
        """
        Subscribe to all tracking events.

        Creates subscriptions for all events in WEBHOOK_EVENTS_V2.

        Args:
            base_uri: Base webhook URI (e.g., 'https://myshop.com/webhooks/')

        Returns:
            List of created subscriptions

        Raises:
            NinjaVanError: If any subscription fails
        """
        logger.info("Subscribing to all webhook events")

        subscriptions = []
        errors = []

        for event_type in WEBHOOK_EVENTS_V2:
            try:
                subscription = self.subscribe(event_type, base_uri)
                subscriptions.append(subscription)
            except Exception as e:
                logger.error(f"Failed to subscribe to {event_type}: {e}")
                errors.append({
                    'event': event_type,
                    'error': str(e),
                })

        if errors and not subscriptions:
            # All subscriptions failed
            raise NinjaVanWebhookError(
                f"Failed to subscribe to any events. Errors: {errors}",
                status_code=None,
            )

        if errors:
            # Some subscriptions failed
            logger.warning(
                f"Subscribed to {len(subscriptions)}/{len(WEBHOOK_EVENTS_V2)} events. "
                f"{len(errors)} failed: {errors}"
            )

        logger.info(f"Successfully subscribed to {len(subscriptions)} events")

        return subscriptions

    def cleanup_subscriptions(self) -> int:
        """
        Remove all webhook subscriptions.

        Useful for cleanup when disconnecting NinjaVan account.

        Returns:
            Number of subscriptions removed

        Raises:
            NinjaVanError: If cleanup fails
        """
        logger.info("Cleaning up all webhook subscriptions")

        try:
            # List all subscriptions
            subscriptions = self.list_subscriptions()

            removed_count = 0
            for subscription in subscriptions:
                subscription_id = subscription.get('id')
                if subscription_id:
                    try:
                        self.unsubscribe(subscription_id)
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to remove subscription {subscription_id}: {e}")

            logger.info(f"Removed {removed_count} webhook subscriptions")
            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup subscriptions: {e}")
            raise NinjaVanError(f"Failed to cleanup subscriptions: {str(e)}")


class WebhookReceiver:
    """
    Receives and processes webhook events from NinjaVan.

    Handles signature verification and event storage.
    """

    def __init__(self, client_secret: str):
        """
        Initialize webhook receiver.

        Args:
            client_secret: Client secret for signature verification
        """
        self.client_secret = client_secret

    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw webhook payload (JSON string)
            signature: Signature from X-Ninjavan-Hmac-Sha256 header

        Returns:
            True if signature is valid, False otherwise
        """
        return utils.verify_webhook_signature(payload, signature, self.client_secret)

    def process_webhook(self, request: Any) -> Dict[str, Any]:
        """
        Process incoming webhook request.

        Args:
            request: Django/Flask request object with headers and body

        Returns:
            Dictionary with processed event data:
            {
                'success': True,
                'tracking_number': 'NVSG123',
                'event_type': 'Delivered, Received by Customer',
                'status': 'delivered',
                'timestamp': datetime(...)
            }

        Raises:
            NinjaVanWebhookError: If signature is invalid or payload is malformed
        """
        # Get raw body
        if hasattr(request, 'body'):
            # Django request
            raw_body = request.body.decode('utf-8')
        elif hasattr(request, 'data'):
            # Flask request
            raw_body = request.data.decode('utf-8')
        else:
            raise NinjaVanWebhookError("Unable to read request body")

        # Get signature header
        signature = request.headers.get('X-Ninjavan-Hmac-Sha256')
        if not signature:
            raise NinjaVanWebhookError(
                "Missing X-Ninjavan-Hmac-Sha256 header",
                status_code=400,
            )

        # Verify signature
        if not self.verify_signature(raw_body, signature):
            logger.warning("Webhook signature verification failed")
            raise NinjaVanWebhookError(
                "Invalid webhook signature",
                status_code=401,
            )

        logger.info("Webhook signature verified")

        # Parse payload
        try:
            import json
            payload = json.loads(raw_body)
        except Exception as e:
            raise NinjaVanWebhookError(
                f"Invalid JSON payload: {str(e)}",
                status_code=400,
            )

        # Extract event data
        tracking_number = payload.get('tracking_number')
        event_type = payload.get('status')  # Event type in 'status' field
        timestamp_str = payload.get('timestamp')

        if not tracking_number:
            raise NinjaVanWebhookError(
                "Webhook payload missing tracking_number",
                status_code=400,
            )

        if not event_type:
            raise NinjaVanWebhookError(
                "Webhook payload missing status/event_type",
                status_code=400,
            )

        # Parse timestamp
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        # Map to platform status
        platform_status = utils.map_ninjavan_status(event_type)

        # Build event data
        event_data = {
            'tracking_number': tracking_number,
            'event_type': event_type,
            'status': platform_status,
            'timestamp': timestamp,
            'location': payload.get('location'),
            'shipper_id': payload.get('shipper_id'),
            'delivery_address': payload.get('delivery_address'),
            'proof_of_delivery_url': payload.get('proof_of_delivery_url'),
        }

        # Store event in database
        self._store_event(event_data)

        logger.info(
            f"Webhook processed: {tracking_number} - {event_type} ({platform_status})"
        )

        return {
            'success': True,
            'tracking_number': tracking_number,
            'event_type': event_type,
            'status': platform_status,
            'timestamp': timestamp,
        }

    def _store_event(self, event_data: Dict[str, Any]) -> None:
        """
        Store webhook event in database.

        This would interact with the platform's database models
        to store tracking events. Implementation depends on the
        platform's data layer.

        Args:
            event_data: Event data to store
        """
        # TODO: Implement database storage
        # This would use Django ORM or similar to store:
        # - tracking_number
        # - event_type
        # - status
        # - timestamp
        # - location
        # - additional metadata

        logger.debug(f"Storing webhook event: {event_data['tracking_number']}")

        # Example (pseudo-code):
        # TrackingEvent.objects.create(
        #     tracking_number=event_data['tracking_number'],
        #     event_type=event_data['event_type'],
        #     status=event_data['status'],
        #     timestamp=event_data['timestamp'],
        #     location=event_data.get('location'),
        #     metadata=event_data
        # )

    def get_tracking_events(self, tracking_number: str) -> List[Dict[str, Any]]:
        """
        Query stored tracking events for a shipment.

        This would query the platform's database for webhook events
        stored for the given tracking number.

        Args:
            tracking_number: NinjaVan tracking number

        Returns:
            List of event dictionaries, ordered by timestamp (newest first)

        Example:
            [
                {
                    'timestamp': datetime(2025, 10, 23, 16, 45),
                    'status': 'delivered',
                    'location': 'Singapore',
                    'description': 'Delivered, Received by Customer',
                    'raw_status': 'Delivered, Received by Customer',
                    'proof_of_delivery_url': 'https://...'
                },
                {
                    'timestamp': datetime(2025, 10, 23, 10, 30),
                    'status': 'out_for_delivery',
                    'location': 'Singapore',
                    'description': 'Out for Delivery',
                    'raw_status': 'Out for Delivery'
                }
            ]
        """
        # TODO: Implement database query
        # This would use Django ORM or similar to query:
        # TrackingEvent.objects.filter(
        #     tracking_number=tracking_number
        # ).order_by('-timestamp')

        logger.debug(f"Querying tracking events for {tracking_number}")

        # Example (pseudo-code):
        # events = TrackingEvent.objects.filter(
        #     tracking_number=tracking_number
        # ).order_by('-timestamp').values()
        # return list(events)

        # For now, return empty list (no events stored yet)
        return []


class WebhookEventProcessor:
    """
    Processes webhook events and updates shipment status.

    Higher-level processor that coordinates between webhook receiver
    and shipment tracking updates.
    """

    def __init__(self, receiver: WebhookReceiver):
        """
        Initialize event processor.

        Args:
            receiver: WebhookReceiver instance
        """
        self.receiver = receiver

    def process_event(self, request: Any) -> Dict[str, Any]:
        """
        Process webhook event and update shipment tracking.

        Args:
            request: Webhook request object

        Returns:
            Processing result dictionary

        Raises:
            NinjaVanWebhookError: If processing fails
        """
        # Process webhook
        result = self.receiver.process_webhook(request)

        # Extract data
        tracking_number = result['tracking_number']
        platform_status = result['status']
        event_type = result['event_type']

        # Update shipment status in platform
        # This would trigger platform-specific logic:
        # - Update order status
        # - Send customer notifications
        # - Trigger workflows
        # - Update analytics

        logger.info(f"Updated shipment {tracking_number} to status: {platform_status}")

        return result

    def handle_delivery_confirmation(self, tracking_number: str, event_data: Dict[str, Any]) -> None:
        """
        Handle delivery confirmation event.

        Special handling for delivered status:
        - Send delivery notification to customer
        - Update order status to completed
        - Trigger post-delivery workflows

        Args:
            tracking_number: Tracking number
            event_data: Event data
        """
        logger.info(f"Handling delivery confirmation for {tracking_number}")

        # Extract proof of delivery
        pod_url = event_data.get('proof_of_delivery_url')

        # TODO: Implement delivery confirmation logic
        # - Send customer email with POD
        # - Update order status
        # - Trigger review request
        # - Update analytics

    def handle_delivery_failure(self, tracking_number: str, event_data: Dict[str, Any]) -> None:
        """
        Handle delivery failure event.

        Special handling for failed delivery:
        - Send notification to customer
        - Create support ticket
        - Attempt redelivery

        Args:
            tracking_number: Tracking number
            event_data: Event data
        """
        logger.info(f"Handling delivery failure for {tracking_number}")

        # TODO: Implement delivery failure logic
        # - Send notification
        # - Create support ticket
        # - Schedule redelivery


def setup_webhooks(
    provider: Any,
    webhook_uri: str,
    force_recreate: bool = False
) -> List[Dict[str, Any]]:
    """
    Setup webhook subscriptions for a NinjaVan provider.

    Convenience function to subscribe to all tracking events.

    Args:
        provider: NinjaVanProvider instance
        webhook_uri: Webhook endpoint URI
        force_recreate: If True, delete existing subscriptions first

    Returns:
        List of created subscriptions

    Example:
        >>> from .provider import NinjaVanProvider
        >>> provider = NinjaVanProvider(credentials)
        >>> subscriptions = setup_webhooks(
        ...     provider,
        ...     'https://myshop.com/shipping/ninjavan/webhooks/'
        ... )
    """
    logger.info(f"Setting up webhooks for {webhook_uri}")

    # Create subscription manager
    manager = WebhookSubscriptionManager(
        base_url=provider.base_url,
        access_token=provider.access_token,
        timeout=provider.REQUEST_TIMEOUT,
    )

    # Cleanup existing subscriptions if requested
    if force_recreate:
        logger.info("Cleaning up existing subscriptions")
        manager.cleanup_subscriptions()

    # Subscribe to all events
    subscriptions = manager.subscribe_to_all_events(webhook_uri)

    logger.info(f"Webhook setup complete: {len(subscriptions)} subscriptions created")

    return subscriptions


def cleanup_webhooks(provider: Any) -> int:
    """
    Remove all webhook subscriptions for a NinjaVan provider.

    Convenience function for cleanup when disconnecting account.

    Args:
        provider: NinjaVanProvider instance

    Returns:
        Number of subscriptions removed

    Example:
        >>> from .provider import NinjaVanProvider
        >>> provider = NinjaVanProvider(credentials)
        >>> count = cleanup_webhooks(provider)
    """
    logger.info("Cleaning up webhooks")

    # Create subscription manager
    manager = WebhookSubscriptionManager(
        base_url=provider.base_url,
        access_token=provider.access_token,
        timeout=provider.REQUEST_TIMEOUT,
    )

    # Cleanup subscriptions
    count = manager.cleanup_subscriptions()

    logger.info(f"Webhook cleanup complete: {count} subscriptions removed")

    return count
