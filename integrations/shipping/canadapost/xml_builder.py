"""
Canada Post XML Request Builders

Functions to build XML request payloads for Canada Post REST APIs.

Author: Spwig
Version: 1.0.0
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from decimal import Decimal


def build_rate_request(
    origin_postal_code: str,
    destination: Dict[str, str],
    parcel: Dict[str, Any],
    customer_number: str,
    contract_id: Optional[str] = None
) -> str:
    """
    Build XML request for Get Rates API.

    Args:
        origin_postal_code: Origin Canadian postal code (e.g., 'K1A 0B1')
        destination: Destination address dict with:
            - country: 'CA', 'US', or international code
            - postal_code: Destination postal/ZIP code
        parcel: Parcel dict with:
            - weight: Weight in kg
            - length: Length in cm
            - width: Width in cm
            - height: Height in cm
        customer_number: 10-digit customer number
        contract_id: Optional contract ID for contract customers

    Returns:
        XML string ready to POST to API

    Example XML:
        <?xml version="1.0" encoding="UTF-8"?>
        <mailing-scenario xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
            <customer-number>1234567890</customer-number>
            <contract-id>12345678</contract-id>
            <parcel-characteristics>
                <weight>5.0</weight>
                <dimensions>
                    <length>30.0</length>
                    <width>20.0</width>
                    <height>15.0</height>
                </dimensions>
            </parcel-characteristics>
            <origin-postal-code>K1A0B1</origin-postal-code>
            <destination>
                <domestic>
                    <postal-code>M5H2N2</postal-code>
                </domestic>
            </destination>
        </mailing-scenario>
    """
    # Create root element with namespace
    root = ET.Element('mailing-scenario')
    root.set('xmlns', 'http://www.canadapost.ca/ws/ship/rate-v4')

    # Customer number (required)
    customer_elem = ET.SubElement(root, 'customer-number')
    customer_elem.text = customer_number.strip()

    # Contract ID (optional, for contract customers)
    if contract_id and contract_id.strip():
        contract_elem = ET.SubElement(root, 'contract-id')
        contract_elem.text = contract_id.strip()

    # Parcel characteristics
    parcel_chars = ET.SubElement(root, 'parcel-characteristics')

    # Weight (in kg)
    weight_elem = ET.SubElement(parcel_chars, 'weight')
    weight_elem.text = str(parcel['weight'])

    # Dimensions (in cm)
    if all(k in parcel for k in ['length', 'width', 'height']):
        dimensions = ET.SubElement(parcel_chars, 'dimensions')

        length_elem = ET.SubElement(dimensions, 'length')
        length_elem.text = str(parcel['length'])

        width_elem = ET.SubElement(dimensions, 'width')
        width_elem.text = str(parcel['width'])

        height_elem = ET.SubElement(dimensions, 'height')
        height_elem.text = str(parcel['height'])

    # Origin postal code
    origin_elem = ET.SubElement(root, 'origin-postal-code')
    origin_elem.text = origin_postal_code.replace(' ', '').replace('-', '')

    # Destination
    dest_elem = ET.SubElement(root, 'destination')
    country = destination.get('country', 'CA').upper()

    if country == 'CA':
        # Domestic (Canada)
        domestic = ET.SubElement(dest_elem, 'domestic')
        postal_elem = ET.SubElement(domestic, 'postal-code')
        postal_elem.text = destination['postal_code'].replace(' ', '').replace('-', '')
    elif country == 'US':
        # United States
        us_dest = ET.SubElement(dest_elem, 'united-states')
        zip_elem = ET.SubElement(us_dest, 'zip-code')
        zip_elem.text = destination['postal_code'].replace(' ', '').replace('-', '')
    else:
        # International
        intl_dest = ET.SubElement(dest_elem, 'international')
        country_elem = ET.SubElement(intl_dest, 'country-code')
        country_elem.text = country

    # Convert to XML string
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return xml_str.decode('utf-8')


def build_shipment_request(
    sender: Dict[str, str],
    recipient: Dict[str, str],
    parcel: Dict[str, Any],
    service_code: str,
    options: List[Dict[str, Any]],
    customer_number: str,
    mobo: Optional[str] = None,
    group_id_or_transmit: str = 'transmit',
    customs: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build XML request for Create Shipment API.

    Args:
        sender: Sender address dict with:
            - name: Full name
            - company: Company name (optional)
            - phone: Phone number
            - address_line_1: Street address
            - address_line_2: Apt/Suite (optional)
            - city: City
            - province: Province/state code
            - postal_code: Postal code
            - country: Country code
        recipient: Recipient address (same format as sender)
        parcel: Parcel dict with weight and dimensions (in kg/cm)
        service_code: Service code (e.g., 'DOM.EP')
        options: List of option dicts:
            [{'code': 'SO'}, {'code': 'COV', 'amount': '500.00'}]
        customer_number: 10-digit customer number
        mobo: Mailed On Behalf Of number (defaults to customer_number)
        group_id_or_transmit: Either 'transmit' or a group ID string
        customs: Optional customs data for international shipments

    Returns:
        XML string ready to POST to API

    Example XML:
        <?xml version="1.0" encoding="UTF-8"?>
        <shipment xmlns="http://www.canadapost.ca/ws/shipment-v8">
            <transmit-shipment/>
            <requested-shipping-point>K1A0B1</requested-shipping-point>
            <delivery-spec>
                <service-code>DOM.EP</service-code>
                <sender>...</sender>
                <destination>...</destination>
                <options>...</options>
                <parcel-characteristics>...</parcel-characteristics>
            </delivery-spec>
        </shipment>
    """
    # Create root element with namespace
    root = ET.Element('shipment')
    root.set('xmlns', 'http://www.canadapost.ca/ws/shipment-v8')

    # Group ID or transmit shipment
    if group_id_or_transmit.lower() == 'transmit':
        ET.SubElement(root, 'transmit-shipment')
    else:
        group_elem = ET.SubElement(root, 'group-id')
        group_elem.text = group_id_or_transmit

    # Requested shipping point (origin postal code)
    shipping_point = ET.SubElement(root, 'requested-shipping-point')
    shipping_point.text = sender['postal_code'].replace(' ', '').replace('-', '')

    # Delivery spec
    delivery_spec = ET.SubElement(root, 'delivery-spec')

    # Service code
    service_elem = ET.SubElement(delivery_spec, 'service-code')
    service_elem.text = service_code

    # Sender
    sender_elem = ET.SubElement(delivery_spec, 'sender')
    _add_address_to_element(sender_elem, sender)

    # Destination/Recipient
    dest_elem = ET.SubElement(delivery_spec, 'destination')
    _add_address_to_element(dest_elem, recipient)

    # Options
    if options:
        options_elem = ET.SubElement(delivery_spec, 'options')
        for option in options:
            option_elem = ET.SubElement(options_elem, 'option')

            code_elem = ET.SubElement(option_elem, 'option-code')
            code_elem.text = option['code']

            if 'amount' in option:
                amount_elem = ET.SubElement(option_elem, 'option-amount')
                amount_elem.text = str(option['amount'])

    # Parcel characteristics
    parcel_chars = ET.SubElement(delivery_spec, 'parcel-characteristics')

    weight_elem = ET.SubElement(parcel_chars, 'weight')
    weight_elem.text = str(parcel['weight'])

    if all(k in parcel for k in ['length', 'width', 'height']):
        dimensions = ET.SubElement(parcel_chars, 'dimensions')

        length_elem = ET.SubElement(dimensions, 'length')
        length_elem.text = str(parcel['length'])

        width_elem = ET.SubElement(dimensions, 'width')
        width_elem.text = str(parcel['width'])

        height_elem = ET.SubElement(dimensions, 'height')
        height_elem.text = str(parcel['height'])

    # Customs (for international shipments)
    if customs:
        customs_elem = ET.SubElement(delivery_spec, 'customs')
        _add_customs_to_element(customs_elem, customs)

    # Preferences
    preferences = ET.SubElement(delivery_spec, 'preferences')
    packing_elem = ET.SubElement(preferences, 'show-packing-instructions')
    packing_elem.text = 'true'

    # Convert to XML string
    xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    return xml_str.decode('utf-8')


def build_customs_declaration(
    sku_list: List[Dict[str, Any]],
    reason: str = 'SOG',  # Sale of Goods
    currency: str = 'CAD'
) -> Dict[str, Any]:
    """
    Build customs declaration data for international shipments.

    Args:
        sku_list: List of SKU dicts:
            [{
                'description': 'Product name',
                'quantity': 2,
                'unit_value': 25.00,
                'weight': 0.5,  # kg per unit
                'country_of_origin': 'CA',
                'hs_tariff': '123456'  # Optional
            }]
        reason: Reason for export:
            - 'SOG': Sale of Goods (default)
            - 'DOC': Documents
            - 'SAM': Commercial Sample
            - 'REP': Repair/Warranty
            - 'OTH': Other
        currency: Currency code (CAD, USD, etc.)

    Returns:
        Customs dict ready for build_shipment_request()
    """
    return {
        'currency': currency,
        'reason_for_export': reason,
        'sku_list': sku_list
    }


def _add_address_to_element(parent: ET.Element, address: Dict[str, str]) -> None:
    """
    Helper to add address details to XML element.

    Args:
        parent: Parent XML element
        address: Address dictionary
    """
    # Name
    name_elem = ET.SubElement(parent, 'name')
    name_elem.text = address['name']

    # Company (optional)
    if address.get('company'):
        company_elem = ET.SubElement(parent, 'company')
        company_elem.text = address['company']

    # Contact phone
    phone_elem = ET.SubElement(parent, 'contact-phone')
    phone_elem.text = address['phone']

    # Address details
    addr_details = ET.SubElement(parent, 'address-details')

    line1_elem = ET.SubElement(addr_details, 'address-line-1')
    line1_elem.text = address['address_line_1']

    if address.get('address_line_2'):
        line2_elem = ET.SubElement(addr_details, 'address-line-2')
        line2_elem.text = address['address_line_2']

    city_elem = ET.SubElement(addr_details, 'city')
    city_elem.text = address['city']

    prov_elem = ET.SubElement(addr_details, 'prov-state')
    prov_elem.text = address['province']

    # Country code (for international)
    if address.get('country') and address['country'] != 'CA':
        country_elem = ET.SubElement(addr_details, 'country-code')
        country_elem.text = address['country']

    postal_elem = ET.SubElement(addr_details, 'postal-zip-code')
    postal_elem.text = address['postal_code'].replace(' ', '').replace('-', '')


def _add_customs_to_element(parent: ET.Element, customs: Dict[str, Any]) -> None:
    """
    Helper to add customs declaration to XML element.

    Args:
        parent: Parent XML element (customs)
        customs: Customs dictionary
    """
    # Currency
    currency_elem = ET.SubElement(parent, 'currency')
    currency_elem.text = customs.get('currency', 'CAD')

    # Reason for export
    reason_elem = ET.SubElement(parent, 'reason-for-export')
    reason_elem.text = customs.get('reason_for_export', 'SOG')

    # SKU list
    sku_list = customs.get('sku_list', [])
    if sku_list:
        for sku in sku_list:
            sku_elem = ET.SubElement(parent, 'sku')

            # Customs description
            desc_elem = ET.SubElement(sku_elem, 'customs-description')
            desc_elem.text = sku['description']

            # Quantity
            qty_elem = ET.SubElement(sku_elem, 'quantity')
            qty_elem.text = str(sku['quantity'])

            # Unit weight (kg)
            weight_elem = ET.SubElement(sku_elem, 'unit-weight')
            weight_elem.text = str(sku['weight'])

            # Unit value
            value_elem = ET.SubElement(sku_elem, 'customs-value-per-unit')
            value_elem.text = str(sku['unit_value'])

            # Country of origin
            origin_elem = ET.SubElement(sku_elem, 'country-of-origin')
            origin_elem.text = sku.get('country_of_origin', 'CA')

            # HS tariff code (optional)
            if sku.get('hs_tariff'):
                tariff_elem = ET.SubElement(sku_elem, 'hs-tariff-code')
                tariff_elem.text = sku['hs_tariff']
