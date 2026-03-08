"""
NinjaVan Plugin API Exception Hierarchy

This module defines all exceptions specific to NinjaVan Plugin API integration,
including OAuth errors, scope errors, and general API errors.
"""

from typing import Optional, Dict, Any


class NinjaVanError(Exception):
    """
    Base exception for all NinjaVan provider errors.

    All NinjaVan-specific exceptions inherit from this class,
    allowing for easy exception handling at the provider level.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize NinjaVan error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code from API response
            error_code: NinjaVan error code (if provided)
            request_id: Request ID for debugging (from X-Request-ID header)
            details: Additional error details from API response
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error message with all available details."""
        parts = [self.message]
        if self.error_code:
            parts.append(f"Error Code: {self.error_code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        return " | ".join(parts)


class NinjaVanOAuthError(NinjaVanError):
    """
    Raised when OAuth authorization flow fails.

    This includes errors during:
    - Authorization code exchange
    - Token refresh
    - Invalid grant errors
    - Client credential mismatches
    """
    pass


class NinjaVanScopeError(NinjaVanError):
    """
    Raised when attempting to access an API without required scope.

    Example: Trying to create orders without SHIPPER_PUBLIC_APIS_CREATE_ORDER scope.
    """

    def __init__(
        self,
        message: str,
        required_scope: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize scope error.

        Args:
            message: Human-readable error message
            required_scope: The OAuth scope required for this operation
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.required_scope = required_scope

    def __str__(self) -> str:
        """Return formatted error message with required scope."""
        msg = super().__str__()
        if self.required_scope:
            msg += f" | Required Scope: {self.required_scope}"
        return msg


class NinjaVanAuthenticationError(NinjaVanError):
    """
    Raised when authentication fails (401 errors).

    Common causes:
    - Expired access token
    - Invalid access token
    - Missing access token
    - Revoked access token

    Should trigger token refresh attempt.
    """
    pass


class NinjaVanValidationError(NinjaVanError):
    """
    Raised when request validation fails (400 errors).

    Common causes:
    - Missing required fields
    - Invalid field formats
    - Invalid service level for shipper account
    - Duplicate tracking numbers
    - Invalid time slots
    - Invalid dimensions
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            validation_errors: List of field-specific validation errors
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []

    def get_field_errors(self) -> Dict[str, list]:
        """
        Extract field-specific validation errors.

        Returns:
            Dict mapping field names to list of error messages
        """
        field_errors = {}
        for error in self.validation_errors:
            if isinstance(error, dict):
                field = error.get('field', 'non_field_errors')
                msg = error.get('message', str(error))
                if field not in field_errors:
                    field_errors[field] = []
                field_errors[field].append(msg)
        return field_errors


class NinjaVanForbiddenError(NinjaVanError):
    """
    Raised when access is forbidden (403 errors).

    Common causes:
    - Using sandbox URL for production requests (or vice versa)
    - Integration audit not passed
    - Accessing waybill endpoint without prior request approval
    - Shipper account frozen due to outstanding fees
    """
    pass


class NinjaVanNotFoundError(NinjaVanError):
    """
    Raised when requested resource is not found (404 errors).

    Common causes:
    - Invalid tracking number
    - Order doesn't exist
    - Webhook subscription not found
    """
    pass


class NinjaVanRateLimitError(NinjaVanError):
    """
    Raised when API rate limit is exceeded (429 errors).

    The client should wait a few hours before retrying.
    Rate-limited endpoints:
    - OAuth API (token generation)
    - Waybill API (label generation)
    """

    def __init__(
        self,
        message: str = "API rate limit exceeded. Please retry after a few hours.",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize rate limit error.

        Args:
            message: Human-readable error message
            retry_after: Seconds to wait before retrying (from Retry-After header)
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class NinjaVanAPIError(NinjaVanError):
    """
    Raised for general API errors (5xx errors).

    These are server-side errors that should be retried with exponential backoff.
    """
    pass


class NinjaVanWebhookError(NinjaVanError):
    """
    Raised when webhook processing fails.

    This includes:
    - Signature verification failures
    - Invalid webhook payloads
    - Webhook subscription errors
    """
    pass


class NinjaVanNetworkError(NinjaVanError):
    """
    Raised when network communication fails.

    This includes:
    - Connection timeouts
    - Connection refused
    - DNS resolution failures

    Should be retried with exponential backoff.
    """
    pass


# Error code mapping for NinjaVan API responses
ERROR_CODE_MAP = {
    # OAuth errors
    'invalid_grant': NinjaVanOAuthError,
    'invalid_client': NinjaVanOAuthError,
    'unauthorized_client': NinjaVanOAuthError,
    'unsupported_grant_type': NinjaVanOAuthError,

    # Order API errors
    '109201': NinjaVanValidationError,  # Duplicate tracking ID
    '127014': NinjaVanValidationError,  # UTF extended charset not supported
}


def parse_error_response(response) -> NinjaVanError:
    """
    Parse NinjaVan API error response and return appropriate exception.

    Args:
        response: requests.Response object with error status code

    Returns:
        Appropriate NinjaVanError subclass instance

    Example error response formats:

    Format 1 (OAuth errors):
    {
        "error": "invalid_grant",
        "error_description": "The provided authorization grant is invalid"
    }

    Format 2 (Validation errors):
    {
        "error": {
            "code": "127014",
            "request_id": "1ba6da4f-0709-416e-9e30-a5546130b4d2",
            "title": "Bad Request",
            "message": "Invalid charset! UTF Extended charset is not supported",
            "details": [
                {
                    "reason": "Validation Error",
                    "field": "to.address.address1",
                    "message": "Invalid address format"
                }
            ]
        }
    }

    Format 3 (Simple errors):
    {
        "error": {
            "message": "Service Level is not supported for this shipper account."
        }
    }
    """
    status_code = response.status_code
    request_id = response.headers.get('X-Request-ID')

    try:
        data = response.json()
    except Exception:
        # If response is not JSON, create generic error
        return _create_error_from_status_code(
            status_code,
            response.text or response.reason,
            request_id=request_id
        )

    # Handle OAuth errors (format 1)
    if 'error' in data and isinstance(data['error'], str):
        error_type = data['error']
        error_message = data.get('error_description', data['error'])

        exception_class = ERROR_CODE_MAP.get(error_type, NinjaVanOAuthError)
        return exception_class(
            message=error_message,
            status_code=status_code,
            error_code=error_type,
            request_id=request_id
        )

    # Handle structured errors (formats 2 and 3)
    if 'error' in data and isinstance(data['error'], dict):
        error_obj = data['error']
        error_code = error_obj.get('code')
        error_message = error_obj.get('message', error_obj.get('title', 'Unknown error'))
        error_details = error_obj.get('details', [])

        # Check if we have a specific exception for this error code
        if error_code and error_code in ERROR_CODE_MAP:
            exception_class = ERROR_CODE_MAP[error_code]
            if exception_class == NinjaVanValidationError:
                return exception_class(
                    message=error_message,
                    status_code=status_code,
                    error_code=error_code,
                    request_id=request_id or error_obj.get('request_id'),
                    validation_errors=error_details
                )

        # Create error based on status code
        return _create_error_from_status_code(
            status_code,
            error_message,
            error_code=error_code,
            request_id=request_id or error_obj.get('request_id'),
            details={'errors': error_details} if error_details else None
        )

    # If we can't parse the error, create generic error based on status code
    return _create_error_from_status_code(
        status_code,
        data.get('message', str(data)),
        request_id=request_id
    )


def _create_error_from_status_code(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> NinjaVanError:
    """
    Create appropriate exception class based on HTTP status code.

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Optional error code
        request_id: Optional request ID
        details: Optional additional details

    Returns:
        Appropriate NinjaVanError subclass instance
    """
    exception_map = {
        400: NinjaVanValidationError,
        401: NinjaVanAuthenticationError,
        403: NinjaVanForbiddenError,
        404: NinjaVanNotFoundError,
        429: NinjaVanRateLimitError,
    }

    # 5xx errors map to NinjaVanAPIError
    if status_code >= 500:
        exception_class = NinjaVanAPIError
    else:
        exception_class = exception_map.get(status_code, NinjaVanError)

    return exception_class(
        message=message,
        status_code=status_code,
        error_code=error_code,
        request_id=request_id,
        details=details
    )
