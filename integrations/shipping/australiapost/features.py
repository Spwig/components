"""
Australia Post Product Features Module

Handles product-specific features like Authority To Leave, Safe Drop,
Dangerous Goods, SSCC barcoding, and other shipment features.

Key Features:
    - Authority To Leave (ATL)
    - Safe Drop
    - Signature on Delivery
    - Dangerous Goods declarations
    - SSCC Barcoding
    - Returns handling
    - Product-feature compatibility matrix

Author: Spwig
Version: 2.0.0
"""
import logging
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import re

logger = logging.getLogger(__name__)


class AccountType(Enum):
    """Australia Post account types."""
    EPARCEL = "eparcel"  # 10-digit, prefix 2
    STARTRACK = "startrack"  # 8-digit
    SAME_DAY = "same_day"  # 10-digit, prefix 3
    ON_DEMAND = "on_demand"  # 10-digit, prefix 1


class ProductCode(Enum):
    """Australia Post product codes."""
    # eParcel
    EPARCEL_REGULAR = "AUS_PARCEL_REGULAR"
    EPARCEL_EXPRESS = "AUS_PARCEL_EXPRESS"
    EPARCEL_COURIER = "AUS_PARCEL_COURIER"

    # StarTrack
    STARTRACK_PREMIUM = "ST_PREMIUM"
    STARTRACK_EXPRESS = "ST_EXPRESS"

    # International
    INTL_STANDARD = "INTL_PARCEL_STD"
    INTL_EXPRESS = "INTL_PARCEL_EXP"
    INTL_COURIER = "INTL_PARCEL_COR"

    # Same Day / On Demand
    SAME_DAY = "SAME_DAY_DELIVERY"
    ON_DEMAND = "ON_DEMAND_DELIVERY"


class ShipmentFeatures:
    """
    Manages shipment features and validates feature compatibility.

    Provides feature flags for shipments and ensures that features
    are only used with compatible product codes.

    Usage:
        features = ShipmentFeatures()

        # Add features to shipment
        shipment_data = features.add_authority_to_leave(
            shipment_data,
            enabled=True
        )

        # Validate features for product
        is_valid, errors = features.validate_features_for_product(
            product_code="AUS_PARCEL_EXPRESS",
            features={'authority_to_leave': True, 'safe_drop': True}
        )
    """

    # Feature compatibility matrix
    # Maps product codes to supported features
    FEATURE_COMPATIBILITY: Dict[str, Set[str]] = {
        # eParcel products
        'AUS_PARCEL_REGULAR': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'dangerous_goods',
            'returns',
            'sscc_barcode',
            'delivery_instructions'
        },
        'AUS_PARCEL_EXPRESS': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'dangerous_goods',
            'returns',
            'sscc_barcode',
            'delivery_instructions'
        },
        'AUS_PARCEL_COURIER': {
            'signature_required',
            'dangerous_goods',
            'returns',
            'sscc_barcode',
            'delivery_instructions'
        },

        # StarTrack products
        'ST_PREMIUM': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'dangerous_goods',
            'returns',
            'transfers',
            'sscc_barcode',
            'book_ins',
            'transit_cover',
            'delivery_instructions'
        },
        'ST_EXPRESS': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'dangerous_goods',
            'returns',
            'transfers',
            'sscc_barcode',
            'book_ins',
            'transit_cover',
            'delivery_instructions'
        },

        # Same Day / On Demand
        'SAME_DAY_DELIVERY': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'sscc_barcode',
            'deliver_on_date',
            'adhoc_pickup',
            'delivery_instructions'
        },
        'ON_DEMAND_DELIVERY': {
            'authority_to_leave',
            'safe_drop',
            'signature_required',
            'sscc_barcode',
            'deliver_on_date',
            'adhoc_pickup',
            'delivery_instructions'
        },

        # International
        'INTL_PARCEL_STD': {
            'signature_required',
            'returns',
            'delivery_instructions'
        },
        'INTL_PARCEL_EXP': {
            'signature_required',
            'returns',
            'delivery_instructions'
        },
        'INTL_PARCEL_COR': {
            'signature_required',
            'delivery_instructions'
        }
    }

    def __init__(self):
        """Initialize ShipmentFeatures."""
        logger.debug("ShipmentFeatures initialized")

    def add_authority_to_leave(
        self,
        shipment_data: Dict[str, Any],
        enabled: bool = True,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Authority To Leave (ATL) feature to shipment.

        Args:
            shipment_data: Shipment data dictionary
            enabled: Whether to enable ATL (default: True)
            location: Optional specific location for leaving parcel

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.add_authority_to_leave(
                shipment_data,
                enabled=True,
                location="Front porch"
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        shipment_data['features']['authority_to_leave'] = enabled

        if location and enabled:
            shipment_data['features']['atl_location'] = location

        logger.debug(f"Added ATL to shipment (enabled={enabled})")
        return shipment_data

    def add_safe_drop(
        self,
        shipment_data: Dict[str, Any],
        enabled: bool = True,
        instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Safe Drop feature to shipment.

        Args:
            shipment_data: Shipment data dictionary
            enabled: Whether to enable Safe Drop (default: True)
            instructions: Optional safe drop instructions

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.add_safe_drop(
                shipment_data,
                enabled=True,
                instructions="Leave in mailbox"
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        shipment_data['features']['safe_drop'] = enabled

        if instructions and enabled:
            shipment_data['features']['safe_drop_instructions'] = instructions

        logger.debug(f"Added Safe Drop to shipment (enabled={enabled})")
        return shipment_data

    def add_signature_required(
        self,
        shipment_data: Dict[str, Any],
        required: bool = True,
        signature_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Signature on Delivery requirement to shipment.

        Args:
            shipment_data: Shipment data dictionary
            required: Whether signature is required (default: True)
            signature_type: Type of signature ('standard', 'adult')

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.add_signature_required(
                shipment_data,
                required=True,
                signature_type='adult'
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        shipment_data['features']['signature_required'] = required

        if signature_type and required:
            shipment_data['features']['signature_type'] = signature_type

        logger.debug(f"Added signature requirement to shipment (required={required})")
        return shipment_data

    def add_dangerous_goods(
        self,
        shipment_data: Dict[str, Any],
        dg_class: str,
        un_number: Optional[str] = None,
        packing_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add Dangerous Goods declaration to shipment.

        Args:
            shipment_data: Shipment data dictionary
            dg_class: Dangerous goods class (e.g., '3', '4.1', '9')
            un_number: UN number (e.g., 'UN1090')
            packing_group: Packing group ('I', 'II', 'III')

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.add_dangerous_goods(
                shipment_data,
                dg_class='3',
                un_number='UN1090',
                packing_group='II'
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        shipment_data['features']['dangerous_goods'] = {
            'class': dg_class,
            'un_number': un_number,
            'packing_group': packing_group
        }

        logger.debug(f"Added dangerous goods declaration (class={dg_class})")
        return shipment_data

    def add_sscc_barcode(
        self,
        shipment_data: Dict[str, Any],
        sscc: Optional[str] = None,
        auto_generate: bool = False
    ) -> Dict[str, Any]:
        """
        Add SSCC barcode to shipment.

        Args:
            shipment_data: Shipment data dictionary
            sscc: 18-digit SSCC barcode (if providing your own)
            auto_generate: Whether to auto-generate SSCC (default: False)

        Returns:
            dict: Updated shipment data

        Raises:
            ValueError: If SSCC format is invalid

        Example:
            # Provide your own SSCC
            shipment = features.add_sscc_barcode(
                shipment_data,
                sscc='123456789012345678'
            )

            # Auto-generate SSCC
            shipment = features.add_sscc_barcode(
                shipment_data,
                auto_generate=True
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        if sscc:
            # Validate SSCC format
            if not self.validate_sscc(sscc):
                raise ValueError(
                    f"Invalid SSCC format: {sscc}. Must be 18 digits."
                )
            shipment_data['features']['sscc_barcode'] = sscc
        elif auto_generate:
            shipment_data['features']['sscc_barcode'] = 'auto'

        logger.debug("Added SSCC barcode to shipment")
        return shipment_data

    def add_delivery_instructions(
        self,
        shipment_data: Dict[str, Any],
        instructions: str
    ) -> Dict[str, Any]:
        """
        Add delivery instructions to shipment.

        Args:
            shipment_data: Shipment data dictionary
            instructions: Delivery instructions (max 250 characters)

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.add_delivery_instructions(
                shipment_data,
                "Ring doorbell twice. Beware of dog."
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        # Truncate if too long
        if len(instructions) > 250:
            logger.warning("Delivery instructions truncated to 250 characters")
            instructions = instructions[:250]

        shipment_data['features']['delivery_instructions'] = instructions

        logger.debug("Added delivery instructions to shipment")
        return shipment_data

    def mark_as_return(
        self,
        shipment_data: Dict[str, Any],
        return_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark shipment as a return.

        Args:
            shipment_data: Shipment data dictionary
            return_reference: Optional return reference number

        Returns:
            dict: Updated shipment data

        Example:
            shipment = features.mark_as_return(
                shipment_data,
                return_reference="RET-2025-001"
            )
        """
        if 'features' not in shipment_data:
            shipment_data['features'] = {}

        shipment_data['features']['is_return'] = True

        if return_reference:
            shipment_data['features']['return_reference'] = return_reference

        logger.debug("Marked shipment as return")
        return shipment_data

    def validate_features_for_product(
        self,
        product_code: str,
        features: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate that features are compatible with product code.

        Args:
            product_code: Product code to validate against
            features: Dictionary of features to validate

        Returns:
            tuple: (is_valid, list of error messages)

        Example:
            is_valid, errors = features.validate_features_for_product(
                product_code="AUS_PARCEL_EXPRESS",
                features={'authority_to_leave': True, 'safe_drop': True}
            )
            if not is_valid:
                print(f"Validation errors: {errors}")
        """
        errors = []

        # Check if product code is known
        if product_code not in self.FEATURE_COMPATIBILITY:
            logger.warning(f"Unknown product code: {product_code}")
            # Don't fail validation for unknown codes
            return True, []

        supported_features = self.FEATURE_COMPATIBILITY[product_code]

        # Check each enabled feature
        for feature_name, feature_value in features.items():
            # Skip if feature is disabled/false
            if not feature_value:
                continue

            # Check if feature is supported
            if feature_name not in supported_features:
                errors.append(
                    f"Feature '{feature_name}' is not supported for "
                    f"product '{product_code}'"
                )

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(
                f"Feature validation failed for {product_code}: {errors}"
            )

        return is_valid, errors

    def get_supported_features(self, product_code: str) -> Set[str]:
        """
        Get list of supported features for a product code.

        Args:
            product_code: Product code to check

        Returns:
            set: Set of supported feature names

        Example:
            supported = features.get_supported_features("AUS_PARCEL_EXPRESS")
            # Returns: {'authority_to_leave', 'safe_drop', ...}
        """
        return self.FEATURE_COMPATIBILITY.get(product_code, set())

    def is_feature_supported(
        self,
        product_code: str,
        feature_name: str
    ) -> bool:
        """
        Check if a specific feature is supported for a product.

        Args:
            product_code: Product code to check
            feature_name: Feature name to check

        Returns:
            bool: True if feature is supported

        Example:
            if features.is_feature_supported("AUS_PARCEL_EXPRESS", "authority_to_leave"):
                print("ATL is supported")
        """
        supported = self.get_supported_features(product_code)
        return feature_name in supported

    @staticmethod
    def validate_sscc(sscc: str) -> bool:
        """
        Validate SSCC barcode format.

        SSCC must be exactly 18 digits.

        Args:
            sscc: SSCC barcode to validate

        Returns:
            bool: True if valid

        Example:
            if ShipmentFeatures.validate_sscc("123456789012345678"):
                print("Valid SSCC")
        """
        if not sscc:
            return False

        # Remove spaces and dashes
        sscc = sscc.replace(' ', '').replace('-', '')

        # Must be exactly 18 digits
        if len(sscc) != 18:
            return False

        # Must be all digits
        if not sscc.isdigit():
            return False

        return True

    @staticmethod
    def format_sscc(sscc: str) -> str:
        """
        Format SSCC barcode with standard spacing.

        Args:
            sscc: SSCC barcode (18 digits)

        Returns:
            str: Formatted SSCC (e.g., "1 2345678 9012345 6 78")

        Example:
            formatted = ShipmentFeatures.format_sscc("123456789012345678")
            # Returns: "1 2345678 9012345 6 78"
        """
        # Remove existing formatting
        sscc = sscc.replace(' ', '').replace('-', '')

        if len(sscc) != 18:
            return sscc  # Return as-is if invalid

        # Format: 1 2345678 9012345 6 78
        return f"{sscc[0]} {sscc[1:8]} {sscc[8:15]} {sscc[15:17]} {sscc[17]}"
