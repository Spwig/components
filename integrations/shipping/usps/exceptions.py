"""
USPS Provider Exceptions

Custom exception hierarchy for USPS API errors with specific error code mappings.
"""

from typing import Optional, Dict, Any


class USPSError(Exception):
    """Base exception for all USPS provider errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class USPSAuthenticationError(USPSError):
    """Raised when OAuth authentication fails (401 errors)."""
    pass


class USPSAuthorizationError(USPSError):
    """Raised when access is denied (403 errors)."""
    pass


class USPSValidationError(USPSError):
    """Raised when request validation fails (400 errors)."""
    pass


class USPSRateLimitError(USPSError):
    """Raised when API rate limit is exceeded (429 errors)."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class USPSServiceUnavailableError(USPSError):
    """Raised when USPS API service is unavailable (503 errors)."""
    pass


class USPSPaymentError(USPSError):
    """Raised when payment authorization issues occur."""
    pass


class USPSShipmentError(USPSError):
    """Raised when shipment/label generation fails."""
    pass


class USPSTrackingError(USPSError):
    """Raised when tracking lookup fails."""
    pass


class USPSAddressError(USPSError):
    """Raised when address validation fails."""
    pass


class USPSAPIError(USPSError):
    """Raised for general API errors not covered by specific exceptions."""
    pass


class USPSNetworkError(USPSError):
    """Raised when network connectivity issues occur."""
    pass


class USPSTimeoutError(USPSError):
    """Raised when API request times out."""
    pass


# Error code to exception mapping
ERROR_CODE_MAP = {
    # Authentication errors
    '401': USPSAuthenticationError,
    'UNAUTHORIZED': USPSAuthenticationError,
    'INVALID_TOKEN': USPSAuthenticationError,
    'TOKEN_EXPIRED': USPSAuthenticationError,
    'INVALID_CLIENT': USPSAuthenticationError,

    # Authorization errors
    '403': USPSAuthorizationError,
    'FORBIDDEN': USPSAuthorizationError,
    'ACCESS_DENIED': USPSAuthorizationError,
    'INSUFFICIENT_SCOPE': USPSAuthorizationError,

    # Validation errors
    '400': USPSValidationError,
    'BAD_REQUEST': USPSValidationError,
    'INVALID_REQUEST': USPSValidationError,
    'INVALID_PARAMETER': USPSValidationError,
    'MISSING_PARAMETER': USPSValidationError,
    'INVALID_ZIP_CODE': USPSValidationError,
    'INVALID_TRACKING_NUMBER': USPSTrackingError,

    # Rate limit errors
    '429': USPSRateLimitError,
    'TOO_MANY_REQUESTS': USPSRateLimitError,
    'RATE_LIMIT_EXCEEDED': USPSRateLimitError,

    # Service errors
    '503': USPSServiceUnavailableError,
    'SERVICE_UNAVAILABLE': USPSServiceUnavailableError,
    '500': USPSAPIError,
    'INTERNAL_SERVER_ERROR': USPSAPIError,
    '502': USPSAPIError,
    'BAD_GATEWAY': USPSAPIError,
    '504': USPSTimeoutError,
    'GATEWAY_TIMEOUT': USPSTimeoutError,

    # Payment errors
    'PAYMENT_AUTHORIZATION_REQUIRED': USPSPaymentError,
    'INVALID_PAYMENT_TOKEN': USPSPaymentError,
    'PAYMENT_ACCOUNT_NOT_FOUND': USPSPaymentError,
    'INSUFFICIENT_FUNDS': USPSPaymentError,
    'INVALID_ACCOUNT_NUMBER': USPSPaymentError,

    # Shipping/label errors
    'LABEL_GENERATION_FAILED': USPSShipmentError,
    'INVALID_MAIL_CLASS': USPSShipmentError,
    'INVALID_PACKAGE_DIMENSIONS': USPSShipmentError,
    'INVALID_WEIGHT': USPSShipmentError,
    'SERVICE_NOT_AVAILABLE': USPSShipmentError,
    'DESTINATION_NOT_SERVICEABLE': USPSShipmentError,

    # Tracking errors
    'TRACKING_NOT_FOUND': USPSTrackingError,
    'TRACKING_NUMBER_NOT_FOUND': USPSTrackingError,
    'INVALID_TRACKING_FORMAT': USPSTrackingError,

    # Address errors
    'ADDRESS_NOT_FOUND': USPSAddressError,
    'INVALID_ADDRESS': USPSAddressError,
    'ADDRESS_VALIDATION_FAILED': USPSAddressError,
}


def create_exception_from_response(
    response_status: int,
    response_data: Optional[Dict[str, Any]] = None,
    default_message: str = "USPS API error"
) -> USPSError:
    """
    Create appropriate exception from API response.

    Args:
        response_status: HTTP status code
        response_data: Response JSON data
        default_message: Default error message if none found in response

    Returns:
        Appropriate USPSError subclass instance
    """
    response_data = response_data or {}

    # Extract error information from response
    error_code = None
    message = default_message

    # Try different response formats USPS might use
    if isinstance(response_data, dict):
        # Format 1: {error: {code, message}}
        if 'error' in response_data:
            error_info = response_data['error']
            if isinstance(error_info, dict):
                error_code = error_info.get('code') or error_info.get('errorCode')
                message = error_info.get('message') or error_info.get('errorMessage', default_message)
            elif isinstance(error_info, str):
                message = error_info

        # Format 2: {errorCode, errorMessage}
        elif 'errorCode' in response_data or 'error_code' in response_data:
            error_code = response_data.get('errorCode') or response_data.get('error_code')
            message = response_data.get('errorMessage') or response_data.get('error_message', default_message)

        # Format 3: {code, message}
        elif 'code' in response_data:
            error_code = response_data.get('code')
            message = response_data.get('message', default_message)

        # Format 4: {errors: [{code, message}]}
        elif 'errors' in response_data and isinstance(response_data['errors'], list):
            if response_data['errors']:
                first_error = response_data['errors'][0]
                error_code = first_error.get('code')
                message = first_error.get('message', default_message)

    # Determine exception class from status code first
    status_str = str(response_status)
    exception_class = ERROR_CODE_MAP.get(status_str, USPSAPIError)

    # Override with error code if more specific
    if error_code:
        exception_class = ERROR_CODE_MAP.get(error_code, exception_class)

    # Handle rate limit with retry-after
    if response_status == 429 or exception_class == USPSRateLimitError:
        retry_after = response_data.get('retryAfter') or response_data.get('retry_after')
        return exception_class(message, error_code=error_code, response_data=response_data, retry_after=retry_after)

    return exception_class(message, error_code=error_code, response_data=response_data)


def handle_request_exception(exception: Exception, operation: str = "API request") -> USPSError:
    """
    Convert requests library exceptions to USPS exceptions.

    Args:
        exception: Original exception from requests
        operation: Description of the operation that failed

    Returns:
        Appropriate USPSError subclass instance
    """
    import requests

    if isinstance(exception, requests.exceptions.Timeout):
        return USPSTimeoutError(
            f"{operation} timed out",
            error_code="TIMEOUT"
        )
    elif isinstance(exception, requests.exceptions.ConnectionError):
        return USPSNetworkError(
            f"Network error during {operation}: {str(exception)}",
            error_code="CONNECTION_ERROR"
        )
    elif isinstance(exception, requests.exceptions.HTTPError):
        return USPSAPIError(
            f"HTTP error during {operation}: {str(exception)}",
            error_code="HTTP_ERROR"
        )
    elif isinstance(exception, requests.exceptions.RequestException):
        return USPSNetworkError(
            f"Request failed during {operation}: {str(exception)}",
            error_code="REQUEST_ERROR"
        )
    else:
        return USPSError(
            f"Unexpected error during {operation}: {str(exception)}",
            error_code="UNKNOWN_ERROR"
        )
