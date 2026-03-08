"""
USPS Document Handling

Handles multipart label responses, document parsing, and file management.
USPS returns labels in multipart/form-data format (not JSON with base64).
"""

import base64
import logging
import email
from email import policy
from typing import Dict, Any, Optional
from pathlib import Path
import json

from django.utils.translation import gettext_lazy as _

from .exceptions import USPSShipmentError


logger = logging.getLogger(__name__)


def parse_multipart_label_response(response) -> Dict[str, Any]:
    """
    Parse USPS multipart/form-data label response.

    USPS returns labels in multipart format with separate parts:
    1. labelMetadata (JSON) - tracking number, postage, etc.
    2. labelImage (binary, base64) - shipping label
    3. receiptImage (binary, base64) - postal receipt
    4. returnLabelMetadata (optional JSON) - return label info
    5. returnLabelImage (optional binary, base64) - return label

    Args:
        response: requests.Response object with multipart content

    Returns:
        dict: Parsed label data with keys:
            - metadata: Label metadata dict
            - label: Label image binary data
            - receipt: Receipt image binary data (optional)
            - return_metadata: Return label metadata (optional)
            - return_label: Return label image binary data (optional)

    Raises:
        USPSShipmentError: If parsing fails

    Example:
        result = parse_multipart_label_response(response)
        tracking_number = result['metadata']['trackingNumber']
        label_pdf = result['label']
    """
    try:
        # Parse multipart message using email library
        msg = email.message_from_bytes(
            response.content,
            policy=policy.default
        )

        result = {}

        # Iterate through all parts
        for part in msg.iter_parts():
            content_disposition = part.get('Content-Disposition', '')
            name = part.get_param('name', header='content-disposition')

            if not name:
                continue

            # Extract based on part name
            if name == 'labelMetadata':
                # JSON metadata
                content = part.get_content()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                result['metadata'] = json.loads(content)
                logger.debug("Parsed label metadata")

            elif name == 'labelImage':
                # Base64-encoded label image
                content = part.get_content()
                if isinstance(content, str):
                    content = content.encode('utf-8')

                # Decode base64
                try:
                    result['label'] = base64.b64decode(content)
                    logger.debug(f"Parsed label image ({len(result['label'])} bytes)")
                except Exception as e:
                    logger.error(f"Failed to decode label image: {e}")
                    raise

            elif name == 'receiptImage':
                # Base64-encoded receipt image
                content = part.get_content()
                if isinstance(content, str):
                    content = content.encode('utf-8')

                try:
                    result['receipt'] = base64.b64decode(content)
                    logger.debug(f"Parsed receipt image ({len(result['receipt'])} bytes)")
                except Exception as e:
                    logger.warning(f"Failed to decode receipt image: {e}")
                    # Receipt is optional, continue

            elif name == 'returnLabelMetadata':
                # JSON return label metadata
                content = part.get_content()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                result['return_metadata'] = json.loads(content)
                logger.debug("Parsed return label metadata")

            elif name == 'returnLabelImage':
                # Base64-encoded return label image
                content = part.get_content()
                if isinstance(content, str):
                    content = content.encode('utf-8')

                try:
                    result['return_label'] = base64.b64decode(content)
                    logger.debug(f"Parsed return label image ({len(result['return_label'])} bytes)")
                except Exception as e:
                    logger.warning(f"Failed to decode return label image: {e}")

            elif name == 'returnReceiptImage':
                # Base64-encoded return receipt image
                content = part.get_content()
                if isinstance(content, str):
                    content = content.encode('utf-8')

                try:
                    result['return_receipt'] = base64.b64decode(content)
                    logger.debug(f"Parsed return receipt image ({len(result['return_receipt'])} bytes)")
                except Exception as e:
                    logger.warning(f"Failed to decode return receipt image: {e}")

        # Validate required fields
        if 'metadata' not in result:
            raise USPSShipmentError(
                _("Label response missing metadata"),
                error_code="MISSING_LABEL_METADATA"
            )

        if 'label' not in result:
            raise USPSShipmentError(
                _("Label response missing label image"),
                error_code="MISSING_LABEL_IMAGE"
            )

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse label metadata JSON: {e}")
        raise USPSShipmentError(
            _("Invalid label metadata JSON"),
            error_code="INVALID_LABEL_JSON"
        )

    except Exception as e:
        logger.error(f"Failed to parse multipart label response: {e}")
        raise USPSShipmentError(
            _("Failed to parse label response: {error}").format(error=str(e)),
            error_code="LABEL_PARSE_ERROR"
        )


def save_label_to_file(label_data: bytes, file_path: str, create_dirs: bool = True) -> None:
    """
    Save label binary data to file.

    Args:
        label_data: Label image binary data
        file_path: Destination file path
        create_dirs: Create parent directories if they don't exist

    Raises:
        OSError: If file write fails
    """
    path = Path(file_path)

    # Create parent directories if needed
    if create_dirs and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {path.parent}")

    # Write binary data
    with open(path, 'wb') as f:
        f.write(label_data)

    logger.info(f"Saved label to {file_path} ({len(label_data)} bytes)")


def get_file_extension_from_content_type(content_type: str) -> str:
    """
    Get file extension from MIME content type.

    Args:
        content_type: MIME type (e.g., 'application/pdf')

    Returns:
        str: File extension with dot (e.g., '.pdf')
    """
    extensions = {
        'application/pdf': '.pdf',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/tiff': '.tiff',
        'image/svg+xml': '.svg',
        'application/octet-stream': '.bin',
    }

    return extensions.get(content_type.lower(), '.bin')


def decode_base64_image(base64_data: str) -> bytes:
    """
    Decode base64-encoded image data.

    Args:
        base64_data: Base64-encoded string

    Returns:
        bytes: Decoded binary data

    Raises:
        ValueError: If decoding fails
    """
    try:
        if isinstance(base64_data, str):
            base64_data = base64_data.encode('utf-8')

        return base64.b64decode(base64_data)

    except Exception as e:
        logger.error(f"Failed to decode base64 image: {e}")
        raise ValueError(f"Invalid base64 data: {e}")


def extract_tracking_number(label_metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extract tracking number from label metadata.

    Args:
        label_metadata: Parsed label metadata dict

    Returns:
        str: Tracking number or None
    """
    # Try various possible field names
    tracking_fields = [
        'trackingNumber',
        'tracking_number',
        'trackingNbr',
        'TRACKING_NUMBER'
    ]

    for field in tracking_fields:
        if field in label_metadata:
            return str(label_metadata[field])

    logger.warning("Could not find tracking number in label metadata")
    return None


def extract_postage_amount(label_metadata: Dict[str, Any]) -> Optional[float]:
    """
    Extract postage amount from label metadata.

    Args:
        label_metadata: Parsed label metadata dict

    Returns:
        float: Postage amount or None
    """
    # Try various possible field names
    postage_fields = [
        'postage',
        'postageAmount',
        'price',
        'cost'
    ]

    for field in postage_fields:
        if field in label_metadata:
            try:
                return float(label_metadata[field])
            except (ValueError, TypeError):
                continue

    logger.warning("Could not find postage amount in label metadata")
    return None


def get_label_format_from_metadata(label_metadata: Dict[str, Any]) -> str:
    """
    Determine label format from metadata.

    Args:
        label_metadata: Parsed label metadata dict

    Returns:
        str: Format name ('PDF', 'PNG', 'ZPL', etc.)
    """
    # Check for explicit format field
    if 'imageInfo' in label_metadata:
        image_info = label_metadata['imageInfo']
        if 'imageType' in image_info:
            return image_info['imageType'].upper()

    if 'labelFormat' in label_metadata:
        return label_metadata['labelFormat'].upper()

    if 'format' in label_metadata:
        return label_metadata['format'].upper()

    # Default to PDF (most common)
    return 'PDF'
