"""
Australia Post Pricing Service Module

Enhanced pricing operations including individual shipment pricing and ETA calculations.

Key Features:
    - Get individual shipment pricing (POST /prices/items)
    - Calculate estimated time of arrival (POST /eta)
    - Compare pricing across services
    - Price caching for performance

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .exceptions import (
    AustraliaPostError,
    create_exception_from_response,
)

logger = logging.getLogger(__name__)


class PricingService:
    """
    Handles enhanced pricing operations for Australia Post.

    Provides methods to get individual shipment pricing, calculate ETAs,
    and compare prices across different services.

    Responsibilities:
        - Get individual shipment pricing
        - Calculate estimated delivery times
        - Compare service options
        - Cache pricing results

    Usage:
        pricing_service = PricingService(auth_client, base_url, api_version)

        # Get shipment price
        price = pricing_service.get_shipment_price(
            account_number="2004952470",
            from_address={...},
            to_address={...},
            items=[...]
        )

        # Calculate ETA
        eta = pricing_service.calculate_eta(
            from_postcode="3000",
            to_postcode="2000",
            service_code="AUS_PARCEL_EXPRESS"
        )
    """

    def __init__(
        self,
        auth_client,
        base_url: str,
        api_version: str = "v1"
    ):
        """
        Initialize Pricing Service.

        Args:
            auth_client: Authentication client for API calls
            base_url: Base URL for Australia Post API
            api_version: API version (default: v1)
        """
        self.auth_client = auth_client
        self.base_url = base_url
        self.api_version = api_version
        self.price_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("PricingService initialized")

    def get_shipment_price(
        self,
        account_number: str,
        from_address: Dict[str, str],
        to_address: Dict[str, str],
        items: List[Dict[str, Any]],
        service_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get pricing for an individual shipment.

        This is different from the standard rates endpoint - it provides
        detailed pricing breakdown for a specific shipment configuration.

        Args:
            account_number: Australia Post account number
            from_address: Origin address
            to_address: Destination address
            items: List of items in shipment
            service_code: Optional specific service code

        Returns:
            dict: Pricing details with:
                - base_price: Base shipping price
                - surcharges: List of surcharges
                - taxes: Tax breakdown
                - total: Total price
                - currency: Currency code (AUD)
                - service_code: Service used for pricing

        Raises:
            AustraliaPostError: If pricing request fails

        Example:
            price = pricing_service.get_shipment_price(
                account_number="2004952470",
                from_address={
                    'suburb': 'Melbourne',
                    'state': 'VIC',
                    'postcode': '3000'
                },
                to_address={
                    'suburb': 'Sydney',
                    'state': 'NSW',
                    'postcode': '2000'
                },
                items=[
                    {'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}
                ],
                service_code='AUS_PARCEL_EXPRESS'
            )
            # Returns: {
            #     'base_price': 12.50,
            #     'surcharges': [{'type': 'fuel', 'amount': 1.25}],
            #     'taxes': {'gst': 1.38},
            #     'total': 15.13,
            #     'currency': 'AUD',
            #     'service_code': 'AUS_PARCEL_EXPRESS'
            # }
        """
        logger.info(
            f"Getting shipment price for route: "
            f"{from_address.get('postcode')} -> {to_address.get('postcode')}"
        )

        endpoint = f'/shipping/{self.api_version}/prices/items'

        payload = {
            'from': from_address,
            'to': to_address,
            'items': items
        }

        if service_code:
            payload['service_code'] = service_code

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload,
                headers={'Account-Number': account_number}
            )

            price_data = self._parse_price_response(response)

            logger.info(
                f"Shipment price calculated: {price_data.get('total')} "
                f"{price_data.get('currency')}"
            )

            return price_data

        except Exception as e:
            logger.error(f"Shipment pricing failed: {e}")
            raise create_exception_from_response(e)

    def calculate_eta(
        self,
        from_postcode: str,
        to_postcode: str,
        service_code: str,
        ship_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate estimated time of arrival for a shipment.

        Args:
            from_postcode: Origin postcode
            to_postcode: Destination postcode
            service_code: Service code to calculate ETA for
            ship_date: Optional ship date (ISO format), defaults to today

        Returns:
            dict: ETA information with:
                - estimated_delivery_date: Expected delivery date
                - estimated_days: Number of business days
                - service_code: Service used for calculation
                - delivery_window: Delivery time window (if available)
                - guarantees: Service guarantees (if any)

        Raises:
            AustraliaPostError: If ETA calculation fails

        Example:
            eta = pricing_service.calculate_eta(
                from_postcode="3000",
                to_postcode="2000",
                service_code="AUS_PARCEL_EXPRESS",
                ship_date="2025-11-07"
            )
            # Returns: {
            #     'estimated_delivery_date': '2025-11-08',
            #     'estimated_days': 1,
            #     'service_code': 'AUS_PARCEL_EXPRESS',
            #     'delivery_window': '9:00-17:00',
            #     'guarantees': ['next_day']
            # }
        """
        logger.info(
            f"Calculating ETA for {service_code}: "
            f"{from_postcode} -> {to_postcode}"
        )

        endpoint = f'/shipping/{self.api_version}/eta'

        payload = {
            'from_postcode': from_postcode,
            'to_postcode': to_postcode,
            'service_code': service_code
        }

        if ship_date:
            payload['ship_date'] = ship_date
        else:
            payload['ship_date'] = datetime.now().strftime('%Y-%m-%d')

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload
            )

            eta_data = self._parse_eta_response(response)

            logger.info(
                f"ETA calculated: {eta_data.get('estimated_days')} days "
                f"(delivery: {eta_data.get('estimated_delivery_date')})"
            )

            return eta_data

        except Exception as e:
            logger.error(f"ETA calculation failed: {e}")
            raise create_exception_from_response(e)

    def compare_service_prices(
        self,
        account_number: str,
        from_address: Dict[str, str],
        to_address: Dict[str, str],
        items: List[Dict[str, Any]],
        service_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Compare pricing across multiple services.

        Gets pricing for the same shipment across different service levels
        to help merchants choose the best option.

        Args:
            account_number: Australia Post account number
            from_address: Origin address
            to_address: Destination address
            items: List of items
            service_codes: List of service codes to compare (if None, gets all available)

        Returns:
            list: List of price comparisons, sorted by total price (ascending)

        Example:
            comparisons = pricing_service.compare_service_prices(
                account_number="2004952470",
                from_address={...},
                to_address={...},
                items=[...]
            )
            # Returns: [
            #     {'service_code': 'AUS_PARCEL_REGULAR', 'total': 10.00, ...},
            #     {'service_code': 'AUS_PARCEL_EXPRESS', 'total': 15.00, ...}
            # ]
        """
        logger.info(
            f"Comparing service prices: "
            f"{from_address.get('postcode')} -> {to_address.get('postcode')}"
        )

        comparisons = []

        if service_codes:
            codes_to_check = service_codes
        else:
            # Use common service codes if none specified
            codes_to_check = [
                'AUS_PARCEL_REGULAR',
                'AUS_PARCEL_EXPRESS',
                'ST_PREMIUM',
                'ST_EXPRESS'
            ]

        for service_code in codes_to_check:
            try:
                price_data = self.get_shipment_price(
                    account_number=account_number,
                    from_address=from_address,
                    to_address=to_address,
                    items=items,
                    service_code=service_code
                )
                comparisons.append(price_data)
            except Exception as e:
                logger.warning(
                    f"Could not get price for {service_code}: {e}"
                )
                continue

        # Sort by total price
        comparisons.sort(key=lambda x: x.get('total', float('inf')))

        logger.info(
            f"Price comparison complete: {len(comparisons)} services compared"
        )

        return comparisons

    def _parse_price_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse price response."""
        price_data = response.get('price', response)

        # Extract surcharges
        surcharges = []
        for surcharge in price_data.get('surcharges', []):
            surcharges.append({
                'type': surcharge.get('type'),
                'name': surcharge.get('name'),
                'amount': self._to_decimal(surcharge.get('amount'))
            })

        # Extract taxes
        taxes = {}
        for tax in price_data.get('taxes', []):
            tax_type = tax.get('type', 'gst')
            taxes[tax_type] = self._to_decimal(tax.get('amount'))

        return {
            'base_price': self._to_decimal(price_data.get('base_price')),
            'surcharges': surcharges,
            'surcharges_total': self._to_decimal(price_data.get('surcharges_total')),
            'taxes': taxes,
            'tax_total': self._to_decimal(price_data.get('tax_total')),
            'total': self._to_decimal(price_data.get('total')),
            'currency': price_data.get('currency', 'AUD'),
            'service_code': price_data.get('service_code'),
            'service_name': price_data.get('service_name')
        }

    def _parse_eta_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ETA response."""
        eta_data = response.get('eta', response)

        return {
            'estimated_delivery_date': eta_data.get('estimated_delivery_date'),
            'estimated_days': eta_data.get('estimated_days') or eta_data.get('transit_days'),
            'service_code': eta_data.get('service_code'),
            'delivery_window': eta_data.get('delivery_window'),
            'guarantees': eta_data.get('guarantees', []),
            'cutoff_time': eta_data.get('cutoff_time'),
            'business_days': eta_data.get('business_days', True)
        }

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal safely."""
        if value is None:
            return None

        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to Decimal")
            return None
