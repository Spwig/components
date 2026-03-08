"""
Australia Post HTTP Basic Authentication

Handles HTTP Basic Authentication for Australia Post API using API Key and password.
API Key is in UUID format (e.g., 601a4032-6dbd-46aa-9c6c-8c6dacca5e61).
"""

import base64
import logging
from typing import Dict, Optional

from django.utils.translation import gettext_lazy as _

from .exceptions import (
    AustraliaPostAuthenticationError,
    AustraliaPostValidationError
)


logger = logging.getLogger(__name__)


class AustraliaPostAuthClient:
    """
    HTTP Basic Authentication client for Australia Post API.

    Australia Post uses HTTP Basic Authentication with:
    - API Key (UUID format) as username
    - Password chosen during API key generation
    - Account-Number header for charge account

    Example:
        Authorization: Basic NjAxYTQwMzItNmRiZC00NmFhLTljNmMtOGM2ZGFjY2E1ZTYxOnBhc3N3b3JkCg==
        (Base64 encoded: 601a4032-6dbd-46aa-9c6c-8c6dacca5e61:password)
    """

    def __init__(self, api_key: str, api_password: str, account_number: Optional[str] = None):
        """
        Initialize authentication client.

        Args:
            api_key: Australia Post API Key (UUID format)
            api_password: Password associated with API Key
            account_number: Charge account number (8-10 digits)

        Raises:
            AustraliaPostValidationError: If credentials are invalid
        """
        self.api_key = api_key
        self.api_password = api_password
        self.account_number = account_number

        # Validate API key format
        self._validate_api_key()

        # Validate account number format if provided
        if self.account_number:
            self._validate_account_number()

        logger.debug("Initialized Australia Post auth client")

    def _validate_api_key(self) -> None:
        """
        Validate API key format (UUID).

        Raises:
            AustraliaPostValidationError: If API key format is invalid
        """
        if not self.api_key:
            raise AustraliaPostValidationError(
                _("API key is required"),
                error_code="MISSING_API_KEY"
            )

        # UUID format: 8-4-4-4-12 hexadecimal characters
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

        if not re.match(uuid_pattern, self.api_key.lower()):
            raise AustraliaPostValidationError(
                _("API key must be in UUID format (e.g., 601a4032-6dbd-46aa-9c6c-8c6dacca5e61)"),
                error_code="INVALID_API_KEY_FORMAT"
            )

    def _validate_account_number(self) -> None:
        """
        Validate account number format.

        Australia Post: 10 digits (left-padded with zeros)
        StarTrack: 8 digits (no padding needed)

        Raises:
            AustraliaPostValidationError: If account number format is invalid
        """
        if not self.account_number:
            return

        # Remove any spaces or dashes
        clean_number = self.account_number.replace(' ', '').replace('-', '')

        # Check if all digits
        if not clean_number.isdigit():
            raise AustraliaPostValidationError(
                _("Account number must contain only digits"),
                error_code="INVALID_ACCOUNT_NUMBER"
            )

        # Check length (8 or 10 digits)
        length = len(clean_number)
        if length not in [8, 10]:
            raise AustraliaPostValidationError(
                _("Account number must be 8 digits (StarTrack) or 10 digits (Australia Post)"),
                error_code="INVALID_ACCOUNT_NUMBER_LENGTH"
            )

    def get_auth_header(self) -> str:
        """
        Generate HTTP Basic Authentication header value.

        Returns:
            str: Base64 encoded 'api_key:password' for Authorization header

        Example:
            >>> client = AustraliaPostAuthClient('601a4032-6dbd-46aa-9c6c-8c6dacca5e61', 'password')
            >>> client.get_auth_header()
            'Basic NjAxYTQwMzItNmRiZC00NmFhLTljNmMtOGM2ZGFjY2E1ZTYxOnBhc3N3b3Jk'
        """
        # Format: api_key:password
        credentials = f"{self.api_key}:{self.api_password}"

        # Base64 encode
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

        return f"Basic {encoded}"

    def get_account_header(self, account_number: Optional[str] = None) -> str:
        """
        Generate Account-Number header value with proper padding.

        Australia Post account numbers are 10 digits and must be left-padded with zeros.
        StarTrack account numbers are 8 digits and don't need padding.

        Args:
            account_number: Optional override for account number

        Returns:
            str: Properly formatted account number

        Example:
            >>> client = AustraliaPostAuthClient('api-key', 'password', '123456')
            >>> client.get_account_header()
            '0000123456'  # 10-digit Australia Post
            >>> client2 = AustraliaPostAuthClient('api-key', 'password', '12345678')
            >>> client2.get_account_header()
            '12345678'  # 8-digit StarTrack
        """
        number = account_number or self.account_number

        if not number:
            raise AustraliaPostValidationError(
                _("Account number is required for this operation"),
                error_code="MISSING_ACCOUNT_NUMBER"
            )

        # Remove any spaces or dashes
        clean_number = number.replace(' ', '').replace('-', '')

        # Pad to 10 digits if needed (Australia Post)
        # StarTrack accounts (8 digits) are not padded
        if len(clean_number) < 10 and clean_number[0] == '0':
            # Already starts with 0, likely needs padding to 10 digits
            return clean_number.zfill(10)
        elif len(clean_number) <= 6:
            # Short number, pad to 10 digits for Australia Post
            return clean_number.zfill(10)
        else:
            # 8-digit StarTrack or already 10-digit Australia Post
            return clean_number

    def get_headers(self, include_account: bool = False) -> Dict[str, str]:
        """
        Get complete set of authentication headers for Australia Post API.

        Args:
            include_account: Include Account-Number header

        Returns:
            dict: Headers dictionary

        Example:
            {
                "Authorization": "Basic NjAxYTQwMz...",
                "Account-Number": "0000123456",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        """
        headers = {
            'Authorization': self.get_auth_header(),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if include_account and self.account_number:
            headers['Account-Number'] = self.get_account_header()

        return headers

    def test_authentication(self) -> bool:
        """
        Test if API key and password are valid.

        Note: This only validates format. Actual authentication
        is tested by making an API call.

        Returns:
            bool: True if credentials are valid format
        """
        try:
            self._validate_api_key()
            if self.account_number:
                self._validate_account_number()
            return True
        except AustraliaPostValidationError:
            return False


def pad_account_number(account_number: str) -> str:
    """
    Pad account number to appropriate length.

    Australia Post: 10 digits (left-padded)
    StarTrack: 8 digits (no padding)

    Args:
        account_number: Raw account number

    Returns:
        str: Properly formatted account number

    Example:
        >>> pad_account_number('123456')
        '0000123456'
        >>> pad_account_number('12345678')
        '12345678'
    """
    # Remove any spaces or dashes
    clean = account_number.replace(' ', '').replace('-', '')

    # If 8 digits and first digit is non-zero, it's StarTrack (no padding)
    if len(clean) == 8 and clean[0] != '0':
        return clean

    # Otherwise pad to 10 digits for Australia Post
    return clean.zfill(10)


def detect_service_type(account_number: str) -> str:
    """
    Detect service type from account number.

    Args:
        account_number: Account number (8 or 10 digits)

    Returns:
        str: 'australia_post' or 'startrack'

    Example:
        >>> detect_service_type('0000123456')
        'australia_post'
        >>> detect_service_type('12345678')
        'startrack'
    """
    clean = account_number.replace(' ', '').replace('-', '')

    # StarTrack: 8 digits, left-most digit is always non-zero
    if len(clean) == 8 and clean[0] != '0':
        return 'startrack'

    # Australia Post: 10 digits
    return 'australia_post'


def create_auth_client(credentials: Dict[str, str]) -> AustraliaPostAuthClient:
    """
    Factory function to create auth client from credentials dict.

    Args:
        credentials: Dict with keys: api_key, api_password, account_number

    Returns:
        AustraliaPostAuthClient: Configured auth client

    Raises:
        ValueError: If required credentials are missing

    Example:
        credentials = {
            'api_key': '601a4032-6dbd-46aa-9c6c-8c6dacca5e61',
            'api_password': 'my_secure_password',
            'account_number': '0000123456'
        }
        client = create_auth_client(credentials)
    """
    required_fields = ['api_key', 'api_password']

    missing_fields = [field for field in required_fields if not credentials.get(field)]
    if missing_fields:
        raise ValueError(
            f"Missing required credentials: {', '.join(missing_fields)}"
        )

    return AustraliaPostAuthClient(
        api_key=credentials['api_key'],
        api_password=credentials['api_password'],
        account_number=credentials.get('account_number')
    )
