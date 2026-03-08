"""
USPS OAuth 2.0 Authentication

Handles OAuth 2.0 client credentials grant authentication for USPS API.
Implements token caching with 8-hour lifetime.
"""

import logging
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta

import requests
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .exceptions import (
    USPSAuthenticationError,
    USPSAuthorizationError,
    create_exception_from_response,
    handle_request_exception
)


logger = logging.getLogger(__name__)


class USPSOAuthClient:
    """
    OAuth 2.0 client for USPS API authentication.

    Handles token acquisition, caching, and automatic refresh.
    Tokens are valid for 8 hours (28,800 seconds).
    """

    # OAuth Token endpoints
    SANDBOX_TOKEN_URL = 'https://apis-tem.usps.com/oauth2/v3/token'
    PRODUCTION_TOKEN_URL = 'https://apis.usps.com/oauth2/v3/token'

    # Token lifetime (8 hours)
    TOKEN_LIFETIME_SECONDS = 28800  # 8 hours

    # Cache token for 7 hours 55 minutes (refresh before expiration)
    TOKEN_CACHE_SECONDS = 28500  # 7 hours 55 minutes

    def __init__(self, consumer_key: str, consumer_secret: str, environment: str = 'test'):
        """
        Initialize OAuth client.

        Args:
            consumer_key: USPS API Consumer Key (Client ID)
            consumer_secret: USPS API Consumer Secret (Client Secret)
            environment: 'test' or 'production'
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment.lower()

        # Select token URL based on environment
        if self.environment == 'production':
            self.token_url = self.PRODUCTION_TOKEN_URL
        else:
            self.token_url = self.SANDBOX_TOKEN_URL

        # Thread lock for token acquisition
        self._token_lock = threading.Lock()

        logger.debug(f"Initialized USPS OAuth client for {self.environment} environment")

    def get_token(self) -> str:
        """
        Get valid OAuth access token.

        Returns cached token if available and not expired,
        otherwise acquires new token and caches it.

        Returns:
            str: Access token

        Raises:
            USPSAuthenticationError: If authentication fails
        """
        # Try to get cached token
        cache_key = self.get_cache_key()
        cached_token = cache.get(cache_key)

        if cached_token:
            logger.debug("Using cached OAuth token")
            return cached_token

        # Acquire new token with thread safety
        with self._token_lock:
            # Double-check cache after acquiring lock
            cached_token = cache.get(cache_key)
            if cached_token:
                return cached_token

            # Acquire new token
            logger.info("Acquiring new OAuth token from USPS")
            token = self._acquire_token()

            # Cache token
            cache.set(cache_key, token, self.TOKEN_CACHE_SECONDS)
            logger.info(
                f"OAuth token cached for {self.TOKEN_CACHE_SECONDS}s "
                f"(expires in {self.TOKEN_LIFETIME_SECONDS}s)"
            )

            return token

    def _acquire_token(self) -> str:
        """
        Acquire new OAuth access token from USPS.

        Makes POST request to token endpoint with client credentials.

        Returns:
            str: Access token

        Raises:
            USPSAuthenticationError: If token acquisition fails
        """
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.consumer_key,
            'client_secret': self.consumer_secret
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.token_url,
                data=payload,
                headers=headers,
                timeout=30
            )

            # Check for successful response
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')

                if not access_token:
                    raise USPSAuthenticationError(
                        _("OAuth token response missing 'access_token' field"),
                        error_code="MISSING_ACCESS_TOKEN"
                    )

                logger.debug(f"Successfully acquired OAuth token (expires in {data.get('expires_in', 'unknown')}s)")
                return access_token

            # Handle error response
            error_data = None
            try:
                error_data = response.json()
            except Exception:
                pass

            exception = create_exception_from_response(
                response.status_code,
                error_data,
                default_message=_("Failed to acquire OAuth token")
            )

            logger.error(
                f"OAuth token acquisition failed: {exception.message} "
                f"(status: {response.status_code})"
            )
            raise exception

        except requests.exceptions.RequestException as e:
            exception = handle_request_exception(e, "OAuth token acquisition")
            logger.error(f"OAuth token acquisition request failed: {exception.message}")
            raise exception

    def invalidate_token(self) -> None:
        """
        Invalidate cached token.

        Use this when token becomes invalid or expires prematurely.
        Next call to get_token() will acquire a new token.
        """
        cache_key = self.get_cache_key()
        cache.delete(cache_key)
        logger.info("OAuth token cache invalidated")

    def get_cache_key(self) -> str:
        """
        Generate cache key for token storage.

        Returns:
            str: Cache key unique to this client's credentials
        """
        # Use consumer key and environment to create unique cache key
        return f"usps_oauth_token:{self.environment}:{self.consumer_key}"

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with Bearer token authentication.

        Returns:
            dict: Headers dict with Authorization header

        Example:
            headers = client.get_auth_headers()
            # {'Authorization': 'Bearer eyJ...'}
        """
        token = self.get_token()
        return {
            'Authorization': f'Bearer {token}'
        }

    def test_authentication(self) -> bool:
        """
        Test if authentication credentials are valid.

        Attempts to acquire a token to verify credentials work.

        Returns:
            bool: True if authentication succeeds

        Raises:
            USPSAuthenticationError: If authentication fails
        """
        try:
            self.get_token()
            return True
        except USPSAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            raise USPSAuthenticationError(
                _("Authentication test failed: {error}").format(error=str(e)),
                error_code="AUTH_TEST_FAILED"
            )


def create_oauth_client(credentials: Dict[str, str]) -> USPSOAuthClient:
    """
    Factory function to create OAuth client from credentials dict.

    Args:
        credentials: Dict with keys: consumer_key, consumer_secret, environment

    Returns:
        USPSOAuthClient: Configured OAuth client

    Raises:
        ValueError: If required credentials are missing

    Example:
        credentials = {
            'consumer_key': 'xxx',
            'consumer_secret': 'yyy',
            'environment': 'test'
        }
        client = create_oauth_client(credentials)
    """
    required_fields = ['consumer_key', 'consumer_secret', 'environment']

    missing_fields = [field for field in required_fields if not credentials.get(field)]
    if missing_fields:
        raise ValueError(
            f"Missing required credentials: {', '.join(missing_fields)}"
        )

    return USPSOAuthClient(
        consumer_key=credentials['consumer_key'],
        consumer_secret=credentials['consumer_secret'],
        environment=credentials['environment']
    )
