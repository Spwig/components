"""
Canada Post Authentication Client

Implements HTTP Basic Authentication for Canada Post REST APIs.

Author: Spwig
Version: 1.0.0
"""

import base64
import logging
from typing import Dict, Any

from .exceptions import CanadaPostAuthenticationError


logger = logging.getLogger(__name__)


class CanadaPostAuthClient:
    """
    Canada Post Basic Authentication client.

    Handles HTTP Basic Authentication for Canada Post REST API requests.
    Simpler than OAuth - uses API key and secret with base64 encoding.

    Usage:
        client = CanadaPostAuthClient(username='api_key', password='api_secret')
        headers = {'Authorization': client.get_auth_header()}
        response = requests.post(url, headers=headers, data=xml_data)
    """

    def __init__(self, username: str, password: str):
        """
        Initialize authentication client.

        Args:
            username: Canada Post API key (username for Basic Auth)
            password: Canada Post API secret (password for Basic Auth)

        Raises:
            CanadaPostAuthenticationError: If credentials are missing or invalid
        """
        if not username or not password:
            raise CanadaPostAuthenticationError(
                "Canada Post API credentials are required (username and password)"
            )

        self.username = username.strip()
        self.password = password.strip()

        if not self.username or not self.password:
            raise CanadaPostAuthenticationError(
                "Canada Post API credentials cannot be empty"
            )

        logger.debug("Canada Post auth client initialized")

    def get_auth_header(self) -> str:
        """
        Generate Basic Authentication header value.

        Creates base64-encoded credentials string in format:
        "Basic {base64(username:password)}"

        Returns:
            Authorization header value ready to use

        Example:
            >>> client = CanadaPostAuthClient('mykey', 'mysecret')
            >>> client.get_auth_header()
            'Basic bXlrZXk6bXlzZWNyZXQ='
        """
        # Combine username and password with colon
        credentials = f"{self.username}:{self.password}"

        # Encode to bytes, then base64, then decode to string
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

        # Return with Basic prefix
        return f"Basic {encoded}"

    def get_headers(self, content_type: str = None, accept: str = None) -> Dict[str, str]:
        """
        Get complete headers dict including authentication.

        Args:
            content_type: Optional Content-Type header value
            accept: Optional Accept header value

        Returns:
            Dictionary of headers ready for requests

        Example:
            >>> client = CanadaPostAuthClient('mykey', 'mysecret')
            >>> headers = client.get_headers(
            ...     content_type='application/vnd.cpc.ship.rate-v4+xml',
            ...     accept='application/vnd.cpc.ship.rate-v4+xml'
            ... )
            >>> requests.post(url, headers=headers, data=xml)
        """
        headers = {
            'Authorization': self.get_auth_header(),
        }

        if content_type:
            headers['Content-Type'] = content_type

        if accept:
            headers['Accept'] = accept

        return headers

    def validate(self) -> bool:
        """
        Validate that credentials are properly formatted.

        Note: This only validates format, not whether credentials are actually valid.
        Use provider's test_connection() method to verify credentials with API.

        Returns:
            True if credentials appear valid

        Raises:
            CanadaPostAuthenticationError: If credentials are invalid
        """
        if not self.username or len(self.username) < 8:
            raise CanadaPostAuthenticationError(
                "Canada Post API username must be at least 8 characters"
            )

        if not self.password or len(self.password) < 8:
            raise CanadaPostAuthenticationError(
                "Canada Post API password must be at least 8 characters"
            )

        return True


def create_auth_client(credentials: Dict[str, Any]) -> CanadaPostAuthClient:
    """
    Factory function to create CanadaPostAuthClient from credentials dict.

    Args:
        credentials: Dictionary containing:
            - username: API key
            - password: API secret

    Returns:
        Configured CanadaPostAuthClient instance

    Raises:
        CanadaPostAuthenticationError: If credentials are missing or invalid

    Example:
        >>> credentials = {
        ...     'username': 'your_api_key',
        ...     'password': 'your_api_secret'
        ... }
        >>> client = create_auth_client(credentials)
    """
    username = credentials.get('username') or credentials.get('api_key')
    password = credentials.get('password') or credentials.get('api_secret')

    if not username or not password:
        raise CanadaPostAuthenticationError(
            "Missing required credentials: username/api_key and password/api_secret"
        )

    return CanadaPostAuthClient(username=username, password=password)
