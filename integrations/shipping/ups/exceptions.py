"""
UPS Provider Custom Exceptions

Defines exception hierarchy for UPS-specific errors.
Maps UPS API error codes to appropriate exception types.
"""
from typing import Optional, Dict, Any


class UPSError(Exception):
    """Base exception for all UPS provider errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize UPS error.

        Args:
            message: Human-readable error message
            error_code: UPS API error code (if available)
            details: Additional error details
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class UPSAuthenticationError(UPSError):
    """Raised when authentication fails (401 errors)."""
    pass


class UPSAuthorizationError(UPSError):
    """Raised when access is forbidden (403 errors)."""
    pass


class UPSValidationError(UPSError):
    """Raised when request validation fails (400 errors)."""
    pass


class UPSRateLimitError(UPSError):
    """Raised when rate limit is exceeded (429 errors)."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            **kwargs: Additional arguments for UPSError
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class UPSServiceUnavailableError(UPSError):
    """Raised when UPS API is temporarily unavailable (503 errors)."""
    pass


class UPSAccountError(UPSError):
    """Raised when there are account-related issues."""
    pass


class UPSShipmentError(UPSError):
    """Raised when shipment/label operations fail."""
    pass


class UPSTrackingError(UPSError):
    """Raised when tracking lookup fails."""
    pass


class UPSAPIError(UPSError):
    """Raised for general API errors."""
    pass


# Error code to exception mapping
ERROR_CODE_MAP = {
    # Authentication errors
    '250003': UPSAuthenticationError,  # Invalid Access License number
    '250004': UPSAuthenticationError,  # Invalid User Id
    '250005': UPSAuthenticationError,  # Invalid Password
    '250006': UPSAuthenticationError,  # Invalid Access License Number

    # Authorization errors
    '250007': UPSAuthorizationError,  # Insufficient privilege
    '250008': UPSAuthorizationError,  # User ID is disabled

    # Validation errors
    '110208': UPSValidationError,  # Invalid postal code
    '110210': UPSValidationError,  # Invalid address
    '110920': UPSValidationError,  # Invalid package weight
    '110971': UPSValidationError,  # Invalid package dimensions
    '111210': UPSValidationError,  # Invalid service code

    # Account errors
    '111057': UPSAccountError,  # Invalid shipper number
    '111100': UPSAccountError,  # Account not authorized
    '111500': UPSAccountError,  # Billing account issue

    # Shipment errors
    '120100': UPSShipmentError,  # Shipment creation failed
    '120200': UPSShipmentError,  # Label generation failed
    '120300': UPSShipmentError,  # Void/cancellation failed

    # Tracking errors
    '151018': UPSTrackingError,  # Invalid tracking number
    '151022': UPSTrackingError,  # Tracking number not found
    '151044': UPSTrackingError,  # No tracking information available
}


def get_exception_for_error_code(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> UPSError:
    """
    Get appropriate exception instance for UPS error code.

    Args:
        error_code: UPS API error code
        message: Error message
        details: Additional error details

    Returns:
        Appropriate UPSError subclass instance
    """
    exception_class = ERROR_CODE_MAP.get(error_code, UPSAPIError)
    return exception_class(message, error_code=error_code, details=details)


def parse_ups_error(response_data: Dict[str, Any]) -> UPSError:
    """
    Parse UPS API error response and create appropriate exception.

    UPS error response format:
    {
        "response": {
            "errors": [
                {
                    "code": "250003",
                    "message": "Invalid Access License number"
                }
            ]
        }
    }

    Args:
        response_data: UPS API error response JSON

    Returns:
        Appropriate UPSError instance
    """
    try:
        # Extract error information
        response = response_data.get('response', {})
        errors = response.get('errors', [])

        if not errors:
            # No structured errors, return generic error
            return UPSAPIError(
                message="UPS API error occurred",
                details=response_data
            )

        # Use first error
        error = errors[0]
        error_code = error.get('code', 'UNKNOWN')
        error_message = error.get('message', 'Unknown error')

        # Get appropriate exception
        return get_exception_for_error_code(
            error_code=error_code,
            message=error_message,
            details={'response': response_data}
        )

    except Exception:
        # If parsing fails, return generic error
        return UPSAPIError(
            message="Failed to parse UPS error response",
            details={'raw_response': response_data}
        )
