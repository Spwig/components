"""
UPS OAuth 2.0 Authentication Module

Handles OAuth 2.0 client credentials flow for UPS API authentication.
Implements token acquisition, caching, and automatic refresh.

References:
- UPS OAuth Documentation: https://developer.ups.com/api/reference/oauth
- Token Endpoint: POST /security/v1/oauth/token
- Token Lifetime: 60 minutes (3600 seconds)
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

import requests
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class UPSOAuthClient:
    """
    OAuth 2.0 client for UPS API authentication.

    Handles token acquisition using client credentials grant type,
    token caching with expiration, and thread-safe token refresh.
    """

    # Token endpoint URLs
    SANDBOX_TOKEN_URL = 'https://wwwcie.ups.com/security/v1/oauth/token'
    PRODUCTION_TOKEN_URL = 'https://onlinetools.ups.com/security/v1/oauth/token'

    # Token lifetime (55 minutes - 5 minute buffer before 60 min expiration)
    TOKEN_LIFETIME_SECONDS = 3300

    # Cache key prefix
    CACHE_KEY_PREFIX = 'ups_oauth_token'

    def __init__(self, client_id: str, client_secret: str, environment: str = 'test'):
        """
        Initialize UPS OAuth client.

        Args:
            client_id: UPS API Client ID
            client_secret: UPS API Client Secret
            environment: 'test' or 'production'
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment

        # Set token URL based on environment
        self.token_url = (
            self.PRODUCTION_TOKEN_URL if environment == 'production'
            else self.SANDBOX_TOKEN_URL
        )

        # Thread lock for token refresh
        self._token_lock = threading.Lock()

    def get_cache_key(self) -> str:
        """Generate cache key for this API client."""
        # Use client ID hash for cache key (avoid storing actual key)
        import hashlib
        key_hash = hashlib.sha256(self.client_id.encode()).hexdigest()[:16]
        return f"{self.CACHE_KEY_PREFIX}:{self.environment}:{key_hash}"

    def get_token(self) -> str:
        """
        Get valid OAuth access token.

        Returns cached token if valid, otherwise acquires new token.
        Thread-safe implementation prevents multiple simultaneous token acquisitions.

        Returns:
            Valid OAuth 2.0 access token (Bearer token)

        Raises:
            ConnectionError: If token acquisition fails
            ValueError: If credentials are invalid
        """
        cache_key = self.get_cache_key()

        # Check cache first
        cached_token = cache.get(cache_key)
        if cached_token:
            logger.debug("Using cached UPS OAuth token")
            return cached_token

        # Acquire lock to prevent race condition
        with self._token_lock:
            # Double-check cache after acquiring lock
            # (another thread may have refreshed while we waited)
            cached_token = cache.get(cache_key)
            if cached_token:
                logger.debug("Using cached UPS OAuth token (after lock)")
                return cached_token

            # Acquire new token
            logger.info("Acquiring new UPS OAuth token")
            token = self._acquire_token()

            # Cache token with expiration
            cache.set(cache_key, token, self.TOKEN_LIFETIME_SECONDS)
            logger.info(f"UPS OAuth token cached for {self.TOKEN_LIFETIME_SECONDS} seconds")

            return token

    def _acquire_token(self) -> str:
        """
        Acquire new OAuth token from UPS API.

        Makes POST request to /security/v1/oauth/token endpoint with client credentials.

        Returns:
            Access token string

        Raises:
            ConnectionError: If API request fails
            ValueError: If credentials are invalid
        """
        try:
            # Prepare request
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }

            # Make request
            logger.debug(f"Requesting OAuth token from: {self.token_url}")
            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                timeout=10
            )

            # Handle errors
            if response.status_code == 401:
                logger.error("UPS OAuth authentication failed: Invalid credentials")
                raise ValueError(_("Invalid UPS API credentials. Please check your Client ID and Client Secret."))

            if response.status_code == 403:
                logger.error("UPS OAuth authentication forbidden")
                raise ValueError(_("Access forbidden. Please verify your UPS account permissions and API access."))

            if response.status_code >= 400:
                error_msg = self._parse_error_response(response)
                logger.error(f"UPS OAuth token acquisition failed: {error_msg}")
                raise ConnectionError(_("Failed to acquire UPS OAuth token: %(error)s") % {'error': error_msg})

            # Parse response
            response.raise_for_status()
            token_data = response.json()

            # Extract access token
            access_token = token_data.get('access_token')
            if not access_token:
                logger.error("UPS OAuth response missing access_token")
                raise ConnectionError(_("Invalid response from UPS OAuth endpoint"))

            # Log token info (but not the actual token)
            token_type = token_data.get('token_type', 'Bearer')
            expires_in = token_data.get('expires_in', 3600)
            issued_at = token_data.get('issued_at', '')
            logger.info(
                f"UPS OAuth token acquired successfully "
                f"(type={token_type}, expires_in={expires_in}s, issued_at={issued_at})"
            )

            return access_token

        except requests.exceptions.Timeout:
            logger.error("UPS OAuth token request timed out")
            raise ConnectionError(_("Connection timeout. Please check your network and try again."))

        except requests.exceptions.ConnectionError as e:
            logger.error(f"UPS OAuth connection error: {e}")
            raise ConnectionError(_("Unable to connect to UPS API. Please check your network connection."))

        except requests.exceptions.RequestException as e:
            logger.error(f"UPS OAuth request failed: {e}")
            raise ConnectionError(_("UPS API request failed: %(error)s") % {'error': str(e)})

    def _parse_error_response(self, response: requests.Response) -> str:
        """
        Parse error response from UPS API.

        Args:
            response: Failed HTTP response

        Returns:
            Human-readable error message
        """
        try:
            error_data = response.json()

            # UPS error format: {"response": {"errors": [{"code": "...", "message": "..."}]}}
            if 'response' in error_data:
                errors = error_data['response'].get('errors', [])
                if errors:
                    error = errors[0]
                    code = error.get('code', 'UNKNOWN')
                    message = error.get('message', 'Unknown error')
                    return f"{code}: {message}"

            # Fallback to error_description or error
            return error_data.get('error_description', error_data.get('error', 'Unknown error'))

        except Exception:
            return f"HTTP {response.status_code}"

    def invalidate_token(self):
        """
        Invalidate cached token.

        Forces acquisition of new token on next get_token() call.
        Useful when token is known to be invalid.
        """
        cache_key = self.get_cache_key()
        cache.delete(cache_key)
        logger.info("UPS OAuth token invalidated")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with OAuth Bearer token.

        Returns:
            Dictionary of headers including Authorization header

        Raises:
            ConnectionError: If token acquisition fails
            ValueError: If credentials are invalid
        """
        token = self.get_token()

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }


def create_oauth_client(credentials: Dict[str, Any]) -> UPSOAuthClient:
    """
    Factory function to create UPS OAuth client from credentials.

    Args:
        credentials: Dictionary containing:
            - api_key: UPS Client ID
            - api_secret: UPS Client Secret
            - environment: 'test' or 'production' (optional, default: 'test')

    Returns:
        Configured UPSOAuthClient instance

    Raises:
        ValueError: If required credentials are missing
    """
    required_fields = ['api_key', 'api_secret']
    missing_fields = [f for f in required_fields if not credentials.get(f)]

    if missing_fields:
        raise ValueError(
            _("Missing required credentials: %(fields)s") %
            {'fields': ', '.join(missing_fields)}
        )

    return UPSOAuthClient(
        client_id=credentials['api_key'],
        client_secret=credentials['api_secret'],
        environment=credentials.get('environment', 'test')
    )
