"""
Australia Post Validation Service Module

Provides pre-flight validation for addresses, suburbs, and shipments.
Includes caching for performance optimization.

Key Features:
    - Validate Australian suburbs and postcodes (POST /postcode/validate)
    - Pre-flight shipment validation (POST /shipments/validate)
    - Address serviceability lookup (POST /serviceability)
    - Validation result caching
    - Automatic validation in workflow

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json

from .exceptions import (
    AustraliaPostError,
    AustraliaPostValidationError,
    create_exception_from_response,
)

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Handles validation operations for Australia Post.

    Provides validation for addresses, suburbs, postcodes, and shipments
    before creating orders. Includes caching to reduce API calls and
    improve performance.

    Responsibilities:
        - Validate Australian suburbs and postcodes
        - Check address serviceability
        - Pre-flight shipment validation
        - Cache validation results
        - Provide validation suggestions

    Usage:
        validation_service = ValidationService(auth_client, base_url, api_version)

        # Validate suburb
        result = validation_service.validate_suburb(
            suburb="Sydney",
            state="NSW",
            postcode="2000"
        )

        # Check serviceability
        serviceable = validation_service.lookup_serviceability(
            address={
                'street': '123 Main St',
                'suburb': 'Sydney',
                'state': 'NSW',
                'postcode': '2000'
            }
        )

        # Validate shipment data
        validation = validation_service.validate_shipments([
            {'from': {...}, 'to': {...}, 'items': [...]}
        ])
    """

    def __init__(
        self,
        auth_client,
        base_url: str,
        api_version: str = "v1",
        cache_ttl: int = 3600  # 1 hour default
    ):
        """
        Initialize Validation Service.

        Args:
            auth_client: Authentication client for API calls
            base_url: Base URL for Australia Post API
            api_version: API version (default: v1)
            cache_ttl: Cache time-to-live in seconds (default: 3600)
        """
        self.auth_client = auth_client
        self.base_url = base_url
        self.api_version = api_version
        self.cache_ttl = cache_ttl

        # Validation caches
        self.suburb_cache: Dict[str, Dict[str, Any]] = {}
        self.serviceability_cache: Dict[str, Dict[str, Any]] = {}
        self.shipment_validation_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(f"ValidationService initialized (cache_ttl={cache_ttl}s)")

    def validate_suburb(
        self,
        suburb: str,
        state: str,
        postcode: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Validate Australian suburb and postcode combination.

        Checks if the suburb, state, and postcode combination is valid
        according to Australia Post data.

        Args:
            suburb: Suburb name
            state: State code (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
            postcode: 4-digit postcode
            use_cache: Whether to use cached results (default: True)

        Returns:
            dict: Validation result with:
                - valid: Boolean indicating if combination is valid
                - suburb: Normalized suburb name
                - state: State code
                - postcode: Postcode
                - suggestions: List of suggested corrections (if invalid)
                - cached: Whether result was from cache

        Raises:
            AustraliaPostValidationError: If validation fails
            AustraliaPostError: If API call fails

        Example:
            result = validation_service.validate_suburb(
                suburb="Sydney",
                state="NSW",
                postcode="2000"
            )
            # Returns: {
            #     'valid': True,
            #     'suburb': 'SYDNEY',
            #     'state': 'NSW',
            #     'postcode': '2000',
            #     'suggestions': [],
            #     'cached': False
            # }
        """
        # Create cache key
        cache_key = self._create_suburb_cache_key(suburb, state, postcode)

        # Check cache
        if use_cache and cache_key in self.suburb_cache:
            cached_result = self.suburb_cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug(f"Returning cached suburb validation: {suburb}, {postcode}")
                cached_result['cached'] = True
                return cached_result

        logger.info(f"Validating suburb: {suburb}, {state}, {postcode}")

        endpoint = f'/shipping/{self.api_version}/postcode/validate'

        payload = {
            'suburb': suburb,
            'state': state,
            'postcode': postcode
        }

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload
            )

            result = self._parse_suburb_validation_response(response)
            result['cached'] = False

            # Cache result
            if use_cache:
                result['cached_at'] = datetime.utcnow().isoformat()
                self.suburb_cache[cache_key] = result

            logger.info(
                f"Suburb validation: {suburb}, {postcode} - "
                f"{'valid' if result['valid'] else 'invalid'}"
            )

            return result

        except Exception as e:
            logger.error(f"Suburb validation failed: {e}")
            raise create_exception_from_response(e)

    def lookup_serviceability(
        self,
        address: Dict[str, str],
        service_code: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Check if an address is serviceable by Australia Post.

        Determines if the given address can receive deliveries for the
        specified service code.

        Args:
            address: Address dictionary with keys:
                - street: Street address
                - suburb: Suburb name
                - state: State code
                - postcode: Postcode
            service_code: Optional service code to check (e.g., 'AUS_PARCEL_EXPRESS')
            use_cache: Whether to use cached results (default: True)

        Returns:
            dict: Serviceability result with:
                - serviceable: Boolean indicating if address is serviceable
                - address: Normalized address
                - service_code: Service code checked
                - restrictions: Any delivery restrictions
                - alternatives: Alternative services if not serviceable
                - cached: Whether result was from cache

        Raises:
            AustraliaPostError: If API call fails

        Example:
            result = validation_service.lookup_serviceability(
                address={
                    'street': '123 Main St',
                    'suburb': 'Sydney',
                    'state': 'NSW',
                    'postcode': '2000'
                },
                service_code='AUS_PARCEL_EXPRESS'
            )
            # Returns: {
            #     'serviceable': True,
            #     'address': {...},
            #     'service_code': 'AUS_PARCEL_EXPRESS',
            #     'restrictions': [],
            #     'alternatives': [],
            #     'cached': False
            # }
        """
        # Create cache key
        cache_key = self._create_serviceability_cache_key(address, service_code)

        # Check cache
        if use_cache and cache_key in self.serviceability_cache:
            cached_result = self.serviceability_cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug(f"Returning cached serviceability: {address.get('postcode')}")
                cached_result['cached'] = True
                return cached_result

        logger.info(
            f"Checking serviceability: {address.get('suburb')}, "
            f"{address.get('postcode')}"
        )

        endpoint = f'/shipping/{self.api_version}/serviceability'

        payload = {
            'to_address': address
        }

        if service_code:
            payload['service_code'] = service_code

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload
            )

            result = self._parse_serviceability_response(response)
            result['cached'] = False

            # Cache result
            if use_cache:
                result['cached_at'] = datetime.utcnow().isoformat()
                self.serviceability_cache[cache_key] = result

            logger.info(
                f"Serviceability check: {address.get('postcode')} - "
                f"{'serviceable' if result['serviceable'] else 'not serviceable'}"
            )

            return result

        except Exception as e:
            logger.error(f"Serviceability lookup failed: {e}")
            raise create_exception_from_response(e)

    def validate_shipments(
        self,
        shipments: List[Dict[str, Any]],
        account_number: str
    ) -> Dict[str, Any]:
        """
        Pre-flight validation for shipment data.

        Validates shipment data before creating the actual shipments.
        Checks for errors in addresses, items, weights, dimensions, etc.

        Args:
            shipments: List of shipment dictionaries to validate
            account_number: Australia Post account number

        Returns:
            dict: Validation results with:
                - valid: Boolean indicating if all shipments are valid
                - shipment_results: List of validation results per shipment
                - errors: List of validation errors
                - warnings: List of validation warnings
                - total_shipments: Total number of shipments validated

        Raises:
            AustraliaPostValidationError: If validation request is malformed
            AustraliaPostError: If API call fails

        Example:
            result = validation_service.validate_shipments(
                shipments=[
                    {
                        'from': {'suburb': 'Melbourne', 'state': 'VIC', 'postcode': '3000'},
                        'to': {'suburb': 'Sydney', 'state': 'NSW', 'postcode': '2000'},
                        'items': [{'weight': 1.5, 'length': 20, 'width': 15, 'height': 10}]
                    }
                ],
                account_number="2004952470"
            )
            # Returns: {
            #     'valid': True,
            #     'shipment_results': [{...}],
            #     'errors': [],
            #     'warnings': [],
            #     'total_shipments': 1
            # }
        """
        logger.info(f"Validating {len(shipments)} shipments")

        endpoint = f'/shipping/{self.api_version}/shipments/validate'

        payload = {
            'shipments': shipments
        }

        try:
            response = self.auth_client._make_request(
                method='POST',
                endpoint=endpoint,
                data=payload,
                headers={'Account-Number': account_number}
            )

            result = self._parse_shipment_validation_response(response)

            logger.info(
                f"Shipment validation complete: "
                f"{'valid' if result['valid'] else 'invalid'} "
                f"({len(result['errors'])} errors, {len(result['warnings'])} warnings)"
            )

            return result

        except Exception as e:
            logger.error(f"Shipment validation failed: {e}")
            raise create_exception_from_response(e)

    def validate_postcode_format(self, postcode: str) -> Tuple[bool, str]:
        """
        Validate Australian postcode format.

        Args:
            postcode: Postcode to validate

        Returns:
            tuple: (is_valid, message)

        Example:
            is_valid, msg = validation_service.validate_postcode_format("2000")
            # Returns: (True, "Valid postcode")

            is_valid, msg = validation_service.validate_postcode_format("12345")
            # Returns: (False, "Postcode must be 4 digits")
        """
        if not postcode:
            return False, "Postcode is required"

        # Remove spaces
        postcode = postcode.strip()

        # Check length
        if len(postcode) != 4:
            return False, "Postcode must be 4 digits"

        # Check if numeric
        if not postcode.isdigit():
            return False, "Postcode must contain only digits"

        # Valid range is 0200-9999
        postcode_int = int(postcode)
        if postcode_int < 200 or postcode_int > 9999:
            return False, "Postcode must be between 0200 and 9999"

        return True, "Valid postcode"

    def validate_state_code(self, state: str) -> Tuple[bool, str]:
        """
        Validate Australian state/territory code.

        Args:
            state: State code to validate

        Returns:
            tuple: (is_valid, message)

        Example:
            is_valid, msg = validation_service.validate_state_code("NSW")
            # Returns: (True, "Valid state code")
        """
        valid_states = {'NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'}

        if not state:
            return False, "State is required"

        state = state.strip().upper()

        if state not in valid_states:
            return False, f"Invalid state code. Must be one of: {', '.join(valid_states)}"

        return True, "Valid state code"

    def _parse_suburb_validation_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse suburb validation API response."""
        # Handle various response formats
        result_data = response.get('result', response)

        return {
            'valid': result_data.get('valid', False),
            'suburb': result_data.get('suburb', '').upper(),
            'state': result_data.get('state', '').upper(),
            'postcode': result_data.get('postcode', ''),
            'suggestions': result_data.get('suggestions', []),
            'locality': result_data.get('locality'),
            'delivery_area': result_data.get('delivery_area')
        }

    def _parse_serviceability_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse serviceability lookup API response."""
        result_data = response.get('result', response)

        return {
            'serviceable': result_data.get('serviceable', False),
            'address': result_data.get('address', {}),
            'service_code': result_data.get('service_code'),
            'restrictions': result_data.get('restrictions', []),
            'alternatives': result_data.get('alternative_services', []),
            'delivery_days': result_data.get('delivery_days'),
            'delivery_area': result_data.get('delivery_area')
        }

    def _parse_shipment_validation_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse shipment validation API response."""
        result_data = response.get('result', response)

        shipment_results = result_data.get('shipments', [])
        all_errors = []
        all_warnings = []

        for shipment in shipment_results:
            all_errors.extend(shipment.get('errors', []))
            all_warnings.extend(shipment.get('warnings', []))

        return {
            'valid': len(all_errors) == 0,
            'shipment_results': shipment_results,
            'errors': all_errors,
            'warnings': all_warnings,
            'total_shipments': len(shipment_results)
        }

    def _create_suburb_cache_key(
        self,
        suburb: str,
        state: str,
        postcode: str
    ) -> str:
        """Create cache key for suburb validation."""
        key_data = f"{suburb.lower()}:{state.upper()}:{postcode}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _create_serviceability_cache_key(
        self,
        address: Dict[str, str],
        service_code: Optional[str]
    ) -> str:
        """Create cache key for serviceability lookup."""
        key_data = json.dumps({
            'suburb': address.get('suburb', '').lower(),
            'state': address.get('state', '').upper(),
            'postcode': address.get('postcode', ''),
            'service_code': service_code or ''
        }, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid based on TTL."""
        if 'cached_at' not in cached_data:
            return False

        cached_at = datetime.fromisoformat(cached_data['cached_at'])
        age = (datetime.utcnow() - cached_at).total_seconds()

        return age < self.cache_ttl

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Clear validation caches.

        Args:
            cache_type: Type of cache to clear ('suburb', 'serviceability', 'shipment')
                       If None, clears all caches
        """
        if cache_type == 'suburb' or cache_type is None:
            self.suburb_cache.clear()
            logger.debug("Suburb cache cleared")

        if cache_type == 'serviceability' or cache_type is None:
            self.serviceability_cache.clear()
            logger.debug("Serviceability cache cleared")

        if cache_type == 'shipment' or cache_type is None:
            self.shipment_validation_cache.clear()
            logger.debug("Shipment validation cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including:
                - suburb_cache_size: Number of cached suburb validations
                - serviceability_cache_size: Number of cached serviceability lookups
                - shipment_cache_size: Number of cached shipment validations
                - cache_ttl: Cache TTL in seconds
        """
        return {
            'suburb_cache_size': len(self.suburb_cache),
            'serviceability_cache_size': len(self.serviceability_cache),
            'shipment_cache_size': len(self.shipment_validation_cache),
            'cache_ttl': self.cache_ttl,
            'total_cached_items': (
                len(self.suburb_cache) +
                len(self.serviceability_cache) +
                len(self.shipment_validation_cache)
            )
        }

    def set_cache_ttl(self, ttl: int) -> None:
        """
        Set cache time-to-live.

        Args:
            ttl: Cache TTL in seconds
        """
        self.cache_ttl = ttl
        logger.info(f"Cache TTL updated to {ttl}s")
