"""
Australia Post Provider Exceptions

Custom exception hierarchy for Australia Post API errors with specific error code mappings.
Implements error handling for account errors, authentication failures, and API-specific issues.
"""

from typing import Optional, Dict, Any


class AustraliaPostError(Exception):
    """Base exception for all Australia Post provider errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class AustraliaPostAuthenticationError(AustraliaPostError):
    """Raised when API key authentication fails (401 errors)."""
    pass


class AustraliaPostAuthorizationError(AustraliaPostError):
    """Raised when access is denied (403 errors)."""
    pass


class AustraliaPostValidationError(AustraliaPostError):
    """Raised when request validation fails (400 errors)."""
    pass


class AustraliaPostAccountError(AustraliaPostError):
    """
    Raised when account/contract issues occur.

    Specific error codes:
    - 40001 (JSON_NO_CONTRACT_ID): Charge account not found
    - 41001 (CUSTOMER_NOT_FOUND): Location with account number not found
    - 41002 (ACCOUNT_NOT_FOUND): Account with ID not found
    - 41003 (CONTRACT_NOT_VALID_ERROR): Contract expired or not yet valid
    """
    pass


class AustraliaPostShipmentError(AustraliaPostError):
    """
    Raised when shipment/label generation fails.

    Specific error codes:
    - 44013: Shipment creation issues
    """
    pass


class AustraliaPostRateLimitError(AustraliaPostError):
    """
    Raised when API rate limit is exceeded (429 errors).

    Tracking API has a limit of 10 requests per 60 seconds.
    """

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AustraliaPostServiceUnavailableError(AustraliaPostError):
    """Raised when Australia Post API service is unavailable (503 errors)."""
    pass


class AustraliaPostAPIError(AustraliaPostError):
    """Raised for general API errors not covered by specific exceptions (500 errors)."""
    pass


class AustraliaPostNetworkError(AustraliaPostError):
    """Raised when network connectivity issues occur."""
    pass


class AustraliaPostTimeoutError(AustraliaPostError):
    """Raised when API request times out."""
    pass


class AustraliaPostTrackingError(AustraliaPostError):
    """Raised when tracking lookup fails."""
    pass


class AustraliaPostLabelError(AustraliaPostError):
    """Raised when label generation or retrieval fails."""
    pass


class AustraliaPostOrderError(AustraliaPostError):
    """
    Raised when order creation or management fails.

    v2.0.0 addition for order management functionality.
    Covers errors in:
    - Order creation from shipments
    - Order retrieval
    - Order summary/manifest generation
    - Order size validation (>2,000 items)
    """
    pass


class AustraliaPostBasketError(AustraliaPostError):
    """
    Raised when basket operations fail.

    v2.0.0 addition for basket management functionality.
    Covers errors in:
    - Basket size limit exceeded (>10,000 items)
    - Basket state issues
    - Shipment not found in basket
    """
    pass


class AustraliaPostPickupError(AustraliaPostError):
    """
    Raised when pickup scheduling fails.

    v2.0.0 addition for adhoc pickup functionality.
    Covers errors in:
    - Pickup creation
    - Pickup cancellation
    - Invalid pickup date/time
    """
    pass


# Error code to exception mapping based on Australia Post API documentation
ERROR_CODE_MAP = {
    # Authentication errors (401)
    '401': AustraliaPostAuthenticationError,
    'UNAUTHORIZED': AustraliaPostAuthenticationError,
    'INVALID_API_KEY': AustraliaPostAuthenticationError,

    # Authorization errors (403)
    '403': AustraliaPostAuthorizationError,
    'FORBIDDEN': AustraliaPostAuthorizationError,
    'ACCESS_DENIED': AustraliaPostAuthorizationError,

    # Validation errors (400)
    '400': AustraliaPostValidationError,
    'BAD_REQUEST': AustraliaPostValidationError,
    'INVALID_REQUEST': AustraliaPostValidationError,
    'JSON_MANDATORY_FIELD_MISSING': AustraliaPostValidationError,
    '40002': AustraliaPostValidationError,

    # Account errors (40001, 41001, 41002, 41003)
    'JSON_NO_CONTRACT_ID': AustraliaPostAccountError,
    '40001': AustraliaPostAccountError,
    'CUSTOMER_NOT_FOUND': AustraliaPostAccountError,
    '41001': AustraliaPostAccountError,
    'ACCOUNT_NOT_FOUND': AustraliaPostAccountError,
    '41002': AustraliaPostAccountError,
    'CONTRACT_NOT_VALID_ERROR': AustraliaPostAccountError,
    '41003': AustraliaPostAccountError,

    # Shipment errors (44013)
    '44013': AustraliaPostShipmentError,
    'SHIPMENT_CREATION_FAILED': AustraliaPostShipmentError,
    'LABEL_GENERATION_FAILED': AustraliaPostLabelError,

    # Rate limit errors (429)
    '429': AustraliaPostRateLimitError,
    'TOO_MANY_REQUESTS': AustraliaPostRateLimitError,
    'RATE_LIMIT_EXCEEDED': AustraliaPostRateLimitError,

    # Service errors (503, 500)
    '503': AustraliaPostServiceUnavailableError,
    'SERVICE_UNAVAILABLE': AustraliaPostServiceUnavailableError,
    '500': AustraliaPostAPIError,
    'INTERNAL_SERVER_ERROR': AustraliaPostAPIError,
    '502': AustraliaPostAPIError,
    'BAD_GATEWAY': AustraliaPostAPIError,
    '504': AustraliaPostTimeoutError,
    'GATEWAY_TIMEOUT': AustraliaPostTimeoutError,

    # Not Acceptable
    '406': AustraliaPostValidationError,
    'NOT_ACCEPTABLE': AustraliaPostValidationError,

    # v2.0.0 additions - Order management errors
    'ORDER_CREATION_FAILED': AustraliaPostOrderError,
    'ORDER_NOT_FOUND': AustraliaPostOrderError,
    'ORDER_SIZE_EXCEEDED': AustraliaPostOrderError,
    'ORDER_SPLIT_FAILED': AustraliaPostOrderError,
    'MANIFEST_GENERATION_FAILED': AustraliaPostOrderError,

    # v2.0.0 additions - Basket management errors
    'BASKET_LIMIT_EXCEEDED': AustraliaPostBasketError,
    'BASKET_LOCKED': AustraliaPostBasketError,
    'SHIPMENT_NOT_IN_BASKET': AustraliaPostBasketError,
    'BASKET_OVERFLOW': AustraliaPostBasketError,

    # v2.0.0 additions - Pickup errors
    'PICKUP_CREATION_FAILED': AustraliaPostPickupError,
    'PICKUP_NOT_FOUND': AustraliaPostPickupError,
    'INVALID_PICKUP_DATE': AustraliaPostPickupError,
    'INVALID_TIME_SLOT': AustraliaPostPickupError,
    'PICKUP_CANCELLATION_FAILED': AustraliaPostPickupError,
    'PAST_DATE': AustraliaPostPickupError,
    'DATE_TOO_FAR': AustraliaPostPickupError,

    # v2.0.0 additions - Validation errors
    'INVALID_SUBURB': AustraliaPostValidationError,
    'INVALID_POSTCODE': AustraliaPostValidationError,
    'ADDRESS_NOT_SERVICEABLE': AustraliaPostValidationError,
    'INVALID_DATE_FORMAT': AustraliaPostValidationError,
}


def parse_error_response(response_data: Optional[Dict[str, Any]] = None) -> tuple[Optional[str], str]:
    """
    Parse error information from Australia Post JSON response.

    Australia Post API returns errors in JSON format with various structures:
    - {error: {code, message}}
    - {errorCode, errorMessage}
    - {code, message}
    - {errors: [{code, message}]}

    Args:
        response_data: Response JSON data

    Returns:
        Tuple of (error_code, error_message)

    Example:
        >>> data = {"error": {"code": "41001", "message": "Customer not found"}}
        >>> parse_error_response(data)
        ('41001', 'Customer not found')
    """
    if not response_data or not isinstance(response_data, dict):
        return None, "Unknown error"

    error_code = None
    message = "Unknown error"

    # Format 1: {error: {code, message}}
    if 'error' in response_data:
        error_info = response_data['error']
        if isinstance(error_info, dict):
            error_code = error_info.get('code') or error_info.get('errorCode')
            message = error_info.get('message') or error_info.get('errorMessage', 'Unknown error')
        elif isinstance(error_info, str):
            message = error_info

    # Format 2: {errorCode, errorMessage}
    elif 'errorCode' in response_data or 'error_code' in response_data:
        error_code = response_data.get('errorCode') or response_data.get('error_code')
        message = response_data.get('errorMessage') or response_data.get('error_message', 'Unknown error')

    # Format 3: {code, message}
    elif 'code' in response_data:
        error_code = response_data.get('code')
        message = response_data.get('message', 'Unknown error')

    # Format 4: {errors: [{code, message}]}
    elif 'errors' in response_data and isinstance(response_data['errors'], list):
        if response_data['errors']:
            first_error = response_data['errors'][0]
            if isinstance(first_error, dict):
                error_code = first_error.get('code')
                message = first_error.get('message', 'Unknown error')

    return error_code, message


def create_exception_from_response(
    response_status: int,
    response_data: Optional[Dict[str, Any]] = None,
    default_message: str = "Australia Post API error"
) -> AustraliaPostError:
    """
    Create appropriate exception from API response.

    Args:
        response_status: HTTP status code
        response_data: Response JSON data
        default_message: Default error message if none found in response

    Returns:
        Appropriate AustraliaPostError subclass instance

    Example:
        >>> exception = create_exception_from_response(
        ...     401,
        ...     {"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}}
        ... )
        >>> isinstance(exception, AustraliaPostAuthenticationError)
        True
    """
    response_data = response_data or {}

    # Parse error information from response
    error_code, message = parse_error_response(response_data)
    if message == "Unknown error":
        message = default_message

    # Determine exception class from status code first
    status_str = str(response_status)
    exception_class = ERROR_CODE_MAP.get(status_str, AustraliaPostAPIError)

    # Override with error code if more specific
    if error_code:
        exception_class = ERROR_CODE_MAP.get(str(error_code), exception_class)

    # Handle rate limit with retry-after
    if response_status == 429 or exception_class == AustraliaPostRateLimitError:
        retry_after = response_data.get('retryAfter') or response_data.get('retry_after')
        return exception_class(message, error_code=error_code, response_data=response_data, retry_after=retry_after)

    return exception_class(message, error_code=error_code, response_data=response_data)


def handle_request_exception(exception: Exception, operation: str = "API request") -> AustraliaPostError:
    """
    Convert requests library exceptions to Australia Post exceptions.

    Args:
        exception: Original exception from requests
        operation: Description of the operation that failed

    Returns:
        Appropriate AustraliaPostError subclass instance

    Example:
        >>> import requests
        >>> try:
        ...     response = requests.get('http://example.com', timeout=1)
        ... except requests.exceptions.Timeout as e:
        ...     error = handle_request_exception(e, "fetch rates")
        >>> isinstance(error, AustraliaPostTimeoutError)
        True
    """
    import requests

    if isinstance(exception, requests.exceptions.Timeout):
        return AustraliaPostTimeoutError(
            f"{operation} timed out",
            error_code="TIMEOUT"
        )
    elif isinstance(exception, requests.exceptions.ConnectionError):
        return AustraliaPostNetworkError(
            f"Network error during {operation}: {str(exception)}",
            error_code="CONNECTION_ERROR"
        )
    elif isinstance(exception, requests.exceptions.HTTPError):
        return AustraliaPostAPIError(
            f"HTTP error during {operation}: {str(exception)}",
            error_code="HTTP_ERROR"
        )
    elif isinstance(exception, requests.exceptions.RequestException):
        return AustraliaPostNetworkError(
            f"Request failed during {operation}: {str(exception)}",
            error_code="REQUEST_ERROR"
        )
    else:
        return AustraliaPostError(
            f"Unexpected error during {operation}: {str(exception)}",
            error_code="UNKNOWN_ERROR"
        )
