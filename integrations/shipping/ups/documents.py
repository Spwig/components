"""
UPS Document Handling Module

Functions for handling shipping labels and documents.
Supports PDF, PNG, and ZPL formats.
"""
import base64
import logging
from typing import Optional
from pathlib import Path

import requests


logger = logging.getLogger(__name__)


def decode_label(label_data: str, format: str = 'PDF') -> bytes:
    """
    Decode base64-encoded label data to bytes.

    UPS returns labels as base64-encoded strings.

    Args:
        label_data: Base64-encoded label string
        format: Label format (PDF, PNG, ZPL, EPL)

    Returns:
        Decoded label bytes

    Raises:
        ValueError: If label_data is invalid
    """
    if not label_data:
        raise ValueError("Label data is empty")

    try:
        # Decode base64 string to bytes
        label_bytes = base64.b64decode(label_data)
        logger.debug(f"Decoded {len(label_bytes)} bytes of {format} label data")
        return label_bytes

    except Exception as e:
        logger.error(f"Failed to decode label data: {e}")
        raise ValueError(f"Invalid base64 label data: {str(e)}")


def save_label_to_file(label_data: bytes, file_path: str) -> None:
    """
    Save label data to file.

    Args:
        label_data: Label bytes
        file_path: Destination file path

    Raises:
        IOError: If file write fails
    """
    try:
        path = Path(file_path)

        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write label data
        with open(path, 'wb') as f:
            f.write(label_data)

        logger.info(f"Label saved to: {file_path} ({len(label_data)} bytes)")

    except Exception as e:
        logger.error(f"Failed to save label to file: {e}")
        raise IOError(f"Failed to save label: {str(e)}")


def get_label_from_url(url: str, timeout: int = 30) -> bytes:
    """
    Download label from URL.

    Some UPS responses include label URLs instead of base64 data.

    Args:
        url: Label URL
        timeout: Request timeout in seconds

    Returns:
        Label data bytes

    Raises:
        ConnectionError: If download fails
    """
    if not url:
        raise ValueError("URL is empty")

    try:
        logger.debug(f"Downloading label from: {url}")

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        label_data = response.content
        logger.info(f"Downloaded {len(label_data)} bytes from {url}")

        return label_data

    except requests.exceptions.Timeout:
        logger.error(f"Label download timed out: {url}")
        raise ConnectionError("Label download timeout")

    except requests.exceptions.RequestException as e:
        logger.error(f"Label download failed: {e}")
        raise ConnectionError(f"Failed to download label: {str(e)}")


def validate_label_format(format: str) -> bool:
    """
    Validate label format string.

    Args:
        format: Label format to validate

    Returns:
        True if format is supported
    """
    supported_formats = ['PDF', 'PNG', 'GIF', 'ZPL', 'EPL']
    return format.upper() in supported_formats


def get_label_extension(format: str) -> str:
    """
    Get file extension for label format.

    Args:
        format: Label format (PDF, PNG, ZPL, etc.)

    Returns:
        File extension with dot (e.g., '.pdf')
    """
    format = format.upper()

    extension_map = {
        'PDF': '.pdf',
        'PNG': '.png',
        'GIF': '.gif',
        'ZPL': '.zpl',
        'EPL': '.epl'
    }

    return extension_map.get(format, '.bin')


def get_label_mime_type(format: str) -> str:
    """
    Get MIME type for label format.

    Args:
        format: Label format

    Returns:
        MIME type string
    """
    format = format.upper()

    mime_map = {
        'PDF': 'application/pdf',
        'PNG': 'image/png',
        'GIF': 'image/gif',
        'ZPL': 'application/zpl',
        'EPL': 'application/epl'
    }

    return mime_map.get(format, 'application/octet-stream')
