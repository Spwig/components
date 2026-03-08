"""
Canada Post Provider Exceptions

Custom exception hierarchy for Canada Post API errors with XML error response parsing.

Author: Spwig
Version: 1.0.0
"""

from typing import Optional, Dict, Any
import xml.etree.ElementTree as ET


class CanadaPostError(Exception):
    """Base exception for all Canada Post provider errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class CanadaPostAuthenticationError(CanadaPostError):
    """Raised when Basic Authentication fails (401 errors)."""
    pass


class CanadaPostAuthorizationError(CanadaPostError):
    """Raised when access is denied or service code not authorized (403 errors)."""
    pass


class CanadaPostValidationError(CanadaPostError):
    """Raised when request validation fails (400 errors)."""
    pass


class CanadaPostRateLimitError(CanadaPostError):
    """Raised when API rate limit is exceeded (429 errors)."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class CanadaPostServiceUnavailableError(CanadaPostError):
    """Raised when Canada Post API service is unavailable (503 errors)."""
    pass


class CanadaPostShipmentError(CanadaPostError):
    """Raised when shipment creation or management fails."""
    pass


class CanadaPostTrackingError(CanadaPostError):
    """Raised when tracking lookup fails."""
    pass


class CanadaPostAddressError(CanadaPostError):
    """Raised when address validation fails."""
    pass


class CanadaPostAPIError(CanadaPostError):
    """Raised for general API errors not covered by specific exceptions."""
    pass


class CanadaPostNetworkError(CanadaPostError):
    """Raised when network connectivity issues occur."""
    pass


class CanadaPostTimeoutError(CanadaPostError):
    """Raised when API request times out."""
    pass


class CanadaPostManifestError(CanadaPostError):
    """Raised when manifest creation or management fails."""
    pass


# Error code to exception mapping
ERROR_CODE_MAP = {
    # Authentication errors
    '401': CanadaPostAuthenticationError,
    'UNAUTHORIZED': CanadaPostAuthenticationError,
    'INVALID_CREDENTIALS': CanadaPostAuthenticationError,

    # Authorization errors
    '403': CanadaPostAuthorizationError,
    'FORBIDDEN': CanadaPostAuthorizationError,
    'AA004': CanadaPostAuthorizationError,  # Not authorized for service code
    'ACCESS_DENIED': CanadaPostAuthorizationError,

    # Validation errors
    '400': CanadaPostValidationError,
    'BAD_REQUEST': CanadaPostValidationError,
    'Client.InvalidData': CanadaPostValidationError,
    'INVALID_REQUEST': CanadaPostValidationError,
    'INVALID_PARAMETER': CanadaPostValidationError,
    'MISSING_PARAMETER': CanadaPostValidationError,
    'INVALID_POSTAL_CODE': CanadaPostValidationError,
    'INVALID_TRACKING_NUMBER': CanadaPostTrackingError,

    # Rate limit errors
    '429': CanadaPostRateLimitError,
    'TOO_MANY_REQUESTS': CanadaPostRateLimitError,
    'RATE_LIMIT_EXCEEDED': CanadaPostRateLimitError,

    # Service errors
    '503': CanadaPostServiceUnavailableError,
    'SERVICE_UNAVAILABLE': CanadaPostServiceUnavailableError,
    '500': CanadaPostAPIError,
    'INTERNAL_SERVER_ERROR': CanadaPostAPIError,
    'Server.SystemError': CanadaPostAPIError,
    '502': CanadaPostAPIError,
    'BAD_GATEWAY': CanadaPostAPIError,
    '504': CanadaPostTimeoutError,
    'GATEWAY_TIMEOUT': CanadaPostTimeoutError,

    # Shipping/label errors
    'LABEL_GENERATION_FAILED': CanadaPostShipmentError,
    'INVALID_SERVICE_CODE': CanadaPostShipmentError,
    'INVALID_PACKAGE_DIMENSIONS': CanadaPostShipmentError,
    'INVALID_WEIGHT': CanadaPostShipmentError,
    'SERVICE_NOT_AVAILABLE': CanadaPostShipmentError,
    'DESTINATION_NOT_SERVICEABLE': CanadaPostShipmentError,

    # Tracking errors
    'TRACKING_NOT_FOUND': CanadaPostTrackingError,
    'TRACKING_NUMBER_NOT_FOUND': CanadaPostTrackingError,
    'INVALID_TRACKING_FORMAT': CanadaPostTrackingError,

    # Address errors
    'ADDRESS_NOT_FOUND': CanadaPostAddressError,
    'INVALID_ADDRESS': CanadaPostAddressError,
    'ADDRESS_VALIDATION_FAILED': CanadaPostAddressError,

    # Manifest errors
    'MANIFEST_CREATION_FAILED': CanadaPostManifestError,
    'INVALID_MANIFEST': CanadaPostManifestError,
}


def parse_xml_error_response(response) -> Dict[str, Any]:
    """
    Parse Canada Post XML error response.

    Canada Post returns errors in XML format:
    <?xml version="1.0" encoding="UTF-8"?>
    <messages xmlns="http://www.canadapost.ca/ws/messages">
        <message>
            <code>AA004</code>
            <description>You are not authorized to use the requested service code</description>
        </message>
    </messages>

    Args:
        response: HTTP response object with XML content

    Returns:
        Dictionary with parsed error information:
        {
            'error_code': 'AA004',
            'message': 'You are not authorized...',
            'messages': [...] (all messages if multiple)
        }
    """
    error_info = {
        'error_code': None,
        'message': None,
        'messages': []
    }

    try:
        # Try to parse XML response
        xml_content = response.text
        if not xml_content or not xml_content.strip():
            return error_info

        # Parse XML
        root = ET.fromstring(xml_content)

        # Define namespace (Canada Post uses this for error responses)
        ns = {'ns': 'http://www.canadapost.ca/ws/messages'}

        # Find all message elements
        messages = root.findall('.//ns:message', ns)
        if not messages:
            # Try without namespace
            messages = root.findall('.//message')

        if messages:
            # Extract all error messages
            for msg in messages:
                code_elem = msg.find('ns:code', ns) or msg.find('code')
                desc_elem = msg.find('ns:description', ns) or msg.find('description')

                code = code_elem.text if code_elem is not None else None
                description = desc_elem.text if desc_elem is not None else None

                error_info['messages'].append({
                    'code': code,
                    'description': description
                })

            # Use first message as primary error
            if error_info['messages']:
                error_info['error_code'] = error_info['messages'][0]['code']
                error_info['message'] = error_info['messages'][0]['description']

    except ET.ParseError:
        # Not valid XML, try to extract plain text error
        try:
            error_info['message'] = response.text[:500]  # Limit length
        except Exception:
            pass
    except Exception:
        # Other parsing errors
        pass

    return error_info


def create_exception_from_response(
    response_status: int,
    response,
    default_message: str = "Canada Post API error"
) -> CanadaPostError:
    """
    Create appropriate exception from API response.

    Args:
        response_status: HTTP status code
        response: HTTP response object
        default_message: Default error message if none found in response

    Returns:
        Appropriate CanadaPostError subclass instance
    """
    # Parse XML error response
    error_info = parse_xml_error_response(response)

    error_code = error_info.get('error_code')
    message = error_info.get('message') or default_message

    # Determine exception class from status code first
    status_str = str(response_status)
    exception_class = ERROR_CODE_MAP.get(status_str, CanadaPostAPIError)

    # Override with error code if more specific
    if error_code:
        exception_class = ERROR_CODE_MAP.get(error_code, exception_class)

    # Handle rate limit with retry-after
    if response_status == 429 or exception_class == CanadaPostRateLimitError:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                retry_after = int(retry_after)
            except (ValueError, TypeError):
                retry_after = None
        return exception_class(
            message,
            error_code=error_code,
            response_data=error_info,
            retry_after=retry_after
        )

    return exception_class(message, error_code=error_code, response_data=error_info)


def handle_request_exception(exception: Exception, operation: str = "API request") -> CanadaPostError:
    """
    Convert requests library exceptions to Canada Post exceptions.

    Args:
        exception: Original exception from requests
        operation: Description of the operation that failed

    Returns:
        Appropriate CanadaPostError subclass instance
    """
    import requests

    if isinstance(exception, requests.exceptions.Timeout):
        return CanadaPostTimeoutError(
            f"{operation} timed out",
            error_code="TIMEOUT"
        )
    elif isinstance(exception, requests.exceptions.ConnectionError):
        return CanadaPostNetworkError(
            f"Network error during {operation}: {str(exception)}",
            error_code="CONNECTION_ERROR"
        )
    elif isinstance(exception, requests.exceptions.HTTPError):
        return CanadaPostAPIError(
            f"HTTP error during {operation}: {str(exception)}",
            error_code="HTTP_ERROR"
        )
    elif isinstance(exception, requests.exceptions.RequestException):
        return CanadaPostNetworkError(
            f"Request failed during {operation}: {str(exception)}",
            error_code="REQUEST_ERROR"
        )
    else:
        return CanadaPostError(
            f"Unexpected error during {operation}: {str(exception)}",
            error_code="UNKNOWN_ERROR"
        )
