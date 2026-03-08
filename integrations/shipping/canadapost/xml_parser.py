"""
Canada Post XML Response Parsers

Functions to parse XML responses from Canada Post REST APIs.

Author: Spwig
Version: 1.0.0
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from . import utils


logger = logging.getLogger(__name__)


# Namespace mappings for Canada Post APIs
NAMESPACES = {
    'rate': 'http://www.canadapost.ca/ws/ship/rate-v4',
    'shipment': 'http://www.canadapost.ca/ws/shipment-v8',
    'track': 'http://www.canadapost.ca/ws/track/v2',
    'messages': 'http://www.canadapost.ca/ws/messages',
}


def parse_rate_response(xml_string: str) -> List[Dict[str, Any]]:
    """
    Parse Get Rates API XML response.

    Args:
        xml_string: XML response from Canada Post

    Returns:
        List of rate dictionaries:
        [{
            'service_code': 'DOM.EP',
            'service_name': 'Expedited Parcel',
            'rate': Decimal('13.13'),
            'currency': 'CAD',
            'delivery_days': 2,
            'delivery_date': datetime(...),
            'base_price': Decimal('12.50'),
            'gst': Decimal('0.63'),
        }]

    Example XML:
        <price-quotes xmlns="http://www.canadapost.ca/ws/ship/rate-v4">
            <price-quote>
                <service-code>DOM.EP</service-code>
                <service-name>Expedited Parcel</service-name>
                <price-details>
                    <base>12.50</base>
                    <gst>0.63</gst>
                    <due>13.13</due>
                </price-details>
                <service-standard>
                    <expected-transit-time>2</expected-transit-time>
                    <expected-delivery-date>2025-10-25</expected-delivery-date>
                </service-standard>
            </price-quote>
        </price-quotes>
    """
    rates = []

    try:
        root = ET.fromstring(xml_string)
        ns = {'ns': NAMESPACES['rate']}

        # Find all price-quote elements
        price_quotes = root.findall('.//ns:price-quote', ns)
        if not price_quotes:
            # Try without namespace
            price_quotes = root.findall('.//price-quote')

        for quote in price_quotes:
            try:
                # Service code
                service_code_elem = quote.find('ns:service-code', ns) or quote.find('service-code')
                service_code = utils.extract_text_from_xml_element(service_code_elem)

                # Service name
                service_name_elem = quote.find('ns:service-name', ns) or quote.find('service-name')
                service_name = utils.extract_text_from_xml_element(
                    service_name_elem,
                    default=utils.get_service_name(service_code)
                )

                # Price details
                price_details = quote.find('ns:price-details', ns) or quote.find('price-details')
                if price_details is None:
                    logger.warning(f"No price-details found for service {service_code}")
                    continue

                # Extract price components
                base_elem = price_details.find('ns:base', ns) or price_details.find('base')
                gst_elem = price_details.find('ns:gst', ns) or price_details.find('gst')
                pst_elem = price_details.find('ns:pst', ns) or price_details.find('pst')
                hst_elem = price_details.find('ns:hst', ns) or price_details.find('hst')
                due_elem = price_details.find('ns:due', ns) or price_details.find('due')

                base = utils.extract_text_from_xml_element(base_elem, '0')
                gst = utils.extract_text_from_xml_element(gst_elem, '0')
                pst = utils.extract_text_from_xml_element(pst_elem, '0')
                hst = utils.extract_text_from_xml_element(hst_elem, '0')
                due = utils.extract_text_from_xml_element(due_elem, '0')

                # Calculate total (use 'due' if available, otherwise sum components)
                if due and due != '0':
                    total_price = Decimal(due)
                else:
                    total_price = utils.calculate_total_price(base, gst, pst, hst)

                # Service standard (delivery info)
                service_std = quote.find('ns:service-standard', ns) or quote.find('service-standard')
                delivery_days = None
                delivery_date = None

                if service_std is not None:
                    # Transit time
                    transit_elem = service_std.find('ns:expected-transit-time', ns) or service_std.find('expected-transit-time')
                    if transit_elem is not None and transit_elem.text:
                        try:
                            delivery_days = int(transit_elem.text)
                        except (ValueError, TypeError):
                            pass

                    # Delivery date
                    date_elem = service_std.find('ns:expected-delivery-date', ns) or service_std.find('expected-delivery-date')
                    if date_elem is not None and date_elem.text:
                        delivery_date = utils.parse_canada_post_date(date_elem.text)

                # Build rate dictionary
                rate = {
                    'service_code': service_code,
                    'service_name': service_name,
                    'carrier': 'Canada Post',
                    'rate': total_price,
                    'currency': 'CAD',
                    'delivery_days': delivery_days,
                    'delivery_date': delivery_date,
                    'base_price': Decimal(base) if base else Decimal('0'),
                    'gst': Decimal(gst) if gst else Decimal('0'),
                    'pst': Decimal(pst) if pst else Decimal('0'),
                    'hst': Decimal(hst) if hst else Decimal('0'),
                }

                rates.append(rate)

            except Exception as e:
                logger.warning(f"Failed to parse rate quote: {e}")
                continue

    except ET.ParseError as e:
        logger.error(f"Failed to parse rate response XML: {e}")
        raise

    return rates


def parse_shipment_response(xml_string: str) -> Dict[str, Any]:
    """
    Parse Create Shipment API XML response.

    Args:
        xml_string: XML response from Canada Post

    Returns:
        Shipment info dictionary:
        {
            'shipment_id': '545207891234567890',
            'tracking_number': '1234567890123456',
            'status': 'created',
            'label_href': 'https://soa-gw.canadapost.ca/.../label',
            'receipt_href': 'https://soa-gw.canadapost.ca/.../receipt',
            'links': [...]
        }

    Example XML:
        <shipment-info xmlns="http://www.canadapost.ca/ws/shipment-v8">
            <shipment-id>545207891234567890</shipment-id>
            <shipment-status>created</shipment-status>
            <tracking-pin>1234567890123456</tracking-pin>
            <links>
                <link rel="self" href="..." media-type="application/vnd.cpc.shipment-v8+xml"/>
                <link rel="label" href="..." media-type="application/pdf" index="0"/>
                <link rel="receipt" href="..." media-type="application/pdf"/>
            </links>
        </shipment-info>
    """
    try:
        root = ET.fromstring(xml_string)
        ns = {'ns': NAMESPACES['shipment']}

        # Extract shipment ID
        shipment_id_elem = root.find('ns:shipment-id', ns) or root.find('shipment-id')
        shipment_id = utils.extract_text_from_xml_element(shipment_id_elem)

        # Extract tracking number (called tracking-pin in Canada Post)
        tracking_elem = root.find('ns:tracking-pin', ns) or root.find('tracking-pin')
        tracking_number = utils.extract_text_from_xml_element(tracking_elem)

        # Extract status
        status_elem = root.find('ns:shipment-status', ns) or root.find('shipment-status')
        status = utils.extract_text_from_xml_element(status_elem, 'created')

        # Extract links
        links = []
        label_href = None
        receipt_href = None

        links_elem = root.find('ns:links', ns) or root.find('links')
        if links_elem is not None:
            link_elems = links_elem.findall('ns:link', ns) or links_elem.findall('link')

            for link in link_elems:
                rel = link.get('rel', '')
                href = link.get('href', '')
                media_type = link.get('media-type', '')

                links.append({
                    'rel': rel,
                    'href': href,
                    'media_type': media_type
                })

                # Extract specific links
                if rel == 'label':
                    label_href = href
                elif rel == 'receipt':
                    receipt_href = href

        return {
            'shipment_id': shipment_id,
            'tracking_number': tracking_number,
            'status': status,
            'label_href': label_href,
            'receipt_href': receipt_href,
            'links': links
        }

    except ET.ParseError as e:
        logger.error(f"Failed to parse shipment response XML: {e}")
        raise


def parse_tracking_response(xml_string: str) -> Dict[str, Any]:
    """
    Parse Tracking API XML response.

    Args:
        xml_string: XML response from Canada Post

    Returns:
        Tracking info dictionary:
        {
            'tracking_number': '1234567890123456',
            'status': 'in_transit',
            'status_description': 'Item processed',
            'service_name': 'Expedited Parcel',
            'estimated_delivery': datetime(...),
            'actual_delivery': datetime(...) or None,
            'current_location': 'Ottawa ON',
            'events': [
                {
                    'timestamp': datetime(...),
                    'status': 'in_transit',
                    'location': 'Ottawa ON',
                    'description': 'Item processed'
                },
                ...
            ]
        }

    Example XML:
        <tracking-detail xmlns="http://www.canadapost.ca/ws/track/v2">
            <tracking-number>1234567890123456</tracking-number>
            <expected-delivery-date>2025-10-25</expected-delivery-date>
            <service-name>Expedited Parcel</service-name>
            <significant-events>
                <occurrence>
                    <event-date>2025-10-23</event-date>
                    <event-time>09:15:00</event-time>
                    <event-description>Item processed</event-description>
                    <event-site>Ottawa ON</event-site>
                    <event-province>ON</event-province>
                </occurrence>
            </significant-events>
        </tracking-detail>
    """
    try:
        root = ET.fromstring(xml_string)
        ns = {'ns': NAMESPACES['track']}

        # Tracking number
        tracking_elem = root.find('ns:tracking-number', ns) or root.find('tracking-number')
        tracking_number = utils.extract_text_from_xml_element(tracking_elem)

        # Service name
        service_elem = root.find('ns:service-name', ns) or root.find('service-name')
        service_name = utils.extract_text_from_xml_element(service_elem, 'Canada Post')

        # Expected delivery date
        expected_elem = root.find('ns:expected-delivery-date', ns) or root.find('expected-delivery-date')
        estimated_delivery = None
        if expected_elem is not None and expected_elem.text:
            estimated_delivery = utils.parse_canada_post_date(expected_elem.text)

        # Actual delivery date
        actual_elem = root.find('ns:actual-delivery-date', ns) or root.find('actual-delivery-date')
        actual_delivery = None
        if actual_elem is not None and actual_elem.text:
            actual_delivery = utils.parse_canada_post_date(actual_elem.text)

        # Parse events
        events = []
        current_location = None
        latest_status = 'in_transit'
        latest_description = ''

        sig_events = root.find('ns:significant-events', ns) or root.find('significant-events')
        if sig_events is not None:
            occurrences = sig_events.findall('ns:occurrence', ns) or sig_events.findall('occurrence')

            for occurrence in occurrences:
                # Event date and time
                date_elem = occurrence.find('ns:event-date', ns) or occurrence.find('event-date')
                time_elem = occurrence.find('ns:event-time', ns) or occurrence.find('event-time')

                event_date = utils.extract_text_from_xml_element(date_elem)
                event_time = utils.extract_text_from_xml_element(time_elem, '00:00:00')

                # Combine date and time
                timestamp = None
                if event_date:
                    datetime_str = f"{event_date} {event_time}"
                    timestamp = utils.parse_canada_post_datetime(datetime_str)

                # Event description
                desc_elem = occurrence.find('ns:event-description', ns) or occurrence.find('event-description')
                description = utils.extract_text_from_xml_element(desc_elem, 'Event')

                # Event location
                site_elem = occurrence.find('ns:event-site', ns) or occurrence.find('event-site')
                prov_elem = occurrence.find('ns:event-province', ns) or occurrence.find('event-province')

                site = utils.extract_text_from_xml_element(site_elem)
                province = utils.extract_text_from_xml_element(prov_elem)

                location = f"{site} {province}".strip() if site or province else ''

                # Map status
                event_status = utils.map_canada_post_status(description)

                events.append({
                    'timestamp': timestamp,
                    'status': event_status,
                    'location': location,
                    'description': description
                })

            # Get latest event info (first in list is most recent)
            if events:
                latest_event = events[0]
                latest_status = latest_event['status']
                latest_description = latest_event['description']
                current_location = latest_event['location']

        # Sort events oldest to newest
        events.sort(key=lambda e: e['timestamp'] if e['timestamp'] else utils.parse_canada_post_datetime('1970-01-01'))

        return {
            'tracking_number': tracking_number,
            'status': latest_status,
            'status_description': latest_description,
            'carrier': 'Canada Post',
            'service': service_name,
            'estimated_delivery': estimated_delivery,
            'actual_delivery': actual_delivery,
            'current_location': current_location,
            'events': events
        }

    except ET.ParseError as e:
        logger.error(f"Failed to parse tracking response XML: {e}")
        raise
