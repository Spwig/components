"""
NinjaVan OAuth 2.0 Client

This module implements OAuth 2.0 authorization code grant flow for NinjaVan Plugin APIs.
Includes token exchange, refresh token handling, and logout functionality.
"""

import requests
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, quote
import threading
import logging

from .exceptions import (
    NinjaVanOAuthError,
    NinjaVanAuthenticationError,
    NinjaVanNetworkError,
    parse_error_response,
)

logger = logging.getLogger(__name__)


class NinjaVanOAuthClient:
    """
    OAuth 2.0 client for NinjaVan Plugin APIs.

    Implements authorization code grant flow with refresh token support.
    Thread-safe token refresh to prevent race conditions.
    """

    # OAuth endpoints
    SANDBOX_AUTH_URL = "https://dashboard-sandbox.ninjavan.co/oauth/login"
    PRODUCTION_AUTH_URL = "https://dashboard.ninjavan.co/oauth/login"

    SANDBOX_TOKEN_URL = "https://api-sandbox.ninjavan.co/1.0/oauth/token"
    PRODUCTION_TOKEN_URL = "https://api.ninjavan.co/1.0/oauth/token"

    SANDBOX_LOGOUT_URL = "https://api-sandbox.ninjavan.co/global/aaa/1.0/logout"
    PRODUCTION_LOGOUT_URL = "https://api.ninjavan.co/global/aaa/1.0/logout"

    # Required OAuth scopes for plugin
    REQUIRED_SCOPES = [
        "SHIPPER_PUBLIC_APIS_CREATE_ORDER",
        "SHIPPER_PUBLIC_APIS_CANCEL_ORDER",
        "SHIPPER_PUBLIC_APIS_GET_AWB",
        "SHIPPER_PUBLIC_APIS_GET_SHIPPER_SETTINGS",
        "SHIPPER_PUBLIC_APIS_GET_SUBSCRIPTIONS",
        "SHIPPER_PUBLIC_APIS_CREATE_SUBSCRIPTIONS",
        "SHIPPER_PUBLIC_APIS_DELETE_SUBSCRIPTIONS",
    ]

    # Token refresh buffer (refresh 5 minutes before expiry)
    TOKEN_REFRESH_BUFFER_SECONDS = 300

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        environment: str = "sandbox",
        timeout: int = 30,
    ):
        """
        Initialize OAuth client.

        Args:
            client_id: Client ID from NinjaVan Dashboard
            client_secret: Client Secret from NinjaVan Dashboard
            environment: 'sandbox' or 'production'
            timeout: Request timeout in seconds (default: 30)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment.lower()
        self.timeout = timeout

        # Thread lock for token refresh
        self._refresh_lock = threading.Lock()

        # Set environment-specific URLs
        if self.environment == "production":
            self.auth_url = self.PRODUCTION_AUTH_URL
            self.token_url = self.PRODUCTION_TOKEN_URL
            self.logout_url = self.PRODUCTION_LOGOUT_URL
        else:
            self.auth_url = self.SANDBOX_AUTH_URL
            self.token_url = self.SANDBOX_TOKEN_URL
            self.logout_url = self.SANDBOX_LOGOUT_URL

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        scopes: Optional[list] = None,
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL for user redirect.

        Args:
            redirect_uri: URL to redirect back to after authorization
            state: Optional state parameter for CSRF protection (generated if not provided)
            scopes: Optional list of scopes (uses REQUIRED_SCOPES if not provided)

        Returns:
            Tuple of (authorization_url, state)

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> url, state = client.get_authorization_url("https://myshop.com/callback")
            >>> # Redirect user to url, store state in session
        """
        # Generate state if not provided
        if state is None:
            state = secrets.token_urlsafe(32)

        # Use required scopes if not provided
        if scopes is None:
            scopes = self.REQUIRED_SCOPES

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "scopes": " ".join(scopes),  # Space-separated
            "state": state,
        }

        # URL encode the scopes parameter properly
        encoded_params = []
        for key, value in params.items():
            if key == "scopes":
                # Use encodeURIComponent equivalent for scopes
                encoded_value = quote(value, safe='')
                encoded_params.append(f"{key}={encoded_value}")
            else:
                encoded_params.append(f"{key}={quote(str(value), safe='')}")

        query_string = "&".join(encoded_params)
        authorization_url = f"{self.auth_url}?{query_string}"

        logger.info(f"Generated authorization URL with state: {state[:8]}...")

        return authorization_url, state

    def exchange_code_for_token(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token and refresh token.

        This is called after the user authorizes the plugin and NinjaVan
        redirects back to your redirect_uri with the authorization code.

        Args:
            code: Authorization code from redirect callback

        Returns:
            Dict containing:
                - access_token: Bearer token for API requests
                - refresh_token: Token for refreshing access token
                - expires_in: Token lifetime in seconds (dynamic)
                - token_type: "bearer"
                - expires_at: Calculated expiration timestamp (datetime)

        Raises:
            NinjaVanOAuthError: If token exchange fails
            NinjaVanNetworkError: If network communication fails

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> tokens = client.exchange_code_for_token(code)
            >>> # Store tokens.access_token, tokens.refresh_token, tokens.expires_at
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
        }

        logger.info("Exchanging authorization code for access token")

        try:
            response = requests.post(
                self.token_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()

                # Calculate expiration time
                expires_in = data.get("expires_in", 3600)  # Default 1 hour
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                result = {
                    "access_token": data["access_token"],
                    "refresh_token": data["refresh_token"],
                    "expires_in": expires_in,
                    "token_type": data.get("token_type", "bearer"),
                    "expires_at": expires_at,
                }

                logger.info(
                    f"Successfully exchanged code for token. "
                    f"Expires in {expires_in}s ({expires_at.isoformat()})"
                )

                return result

            else:
                # Parse error response
                error = parse_error_response(response)
                logger.error(f"Token exchange failed: {error}")
                raise error

        except requests.exceptions.Timeout:
            raise NinjaVanNetworkError(
                "Token exchange request timed out",
                status_code=None,
            )
        except requests.exceptions.ConnectionError as e:
            raise NinjaVanNetworkError(
                f"Failed to connect to NinjaVan OAuth server: {str(e)}",
                status_code=None,
            )
        except requests.exceptions.RequestException as e:
            raise NinjaVanNetworkError(
                f"Network error during token exchange: {str(e)}",
                status_code=None,
            )

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Should be called 5 minutes before token expiry or on 401 errors.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            Dict containing new tokens (same format as exchange_code_for_token)

        Raises:
            NinjaVanOAuthError: If token refresh fails (may require re-authorization)
            NinjaVanNetworkError: If network communication fails

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> new_tokens = client.refresh_access_token(old_refresh_token)
            >>> # Update stored tokens
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        logger.info("Refreshing access token")

        try:
            response = requests.post(
                self.token_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()

                # Calculate expiration time
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                result = {
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token", refresh_token),  # May return same refresh token
                    "expires_in": expires_in,
                    "token_type": data.get("token_type", "bearer"),
                    "expires_at": expires_at,
                }

                logger.info(
                    f"Successfully refreshed token. "
                    f"Expires in {expires_in}s ({expires_at.isoformat()})"
                )

                return result

            else:
                # Parse error response
                error = parse_error_response(response)
                logger.error(f"Token refresh failed: {error}")
                raise error

        except requests.exceptions.Timeout:
            raise NinjaVanNetworkError(
                "Token refresh request timed out",
                status_code=None,
            )
        except requests.exceptions.ConnectionError as e:
            raise NinjaVanNetworkError(
                f"Failed to connect to NinjaVan OAuth server: {str(e)}",
                status_code=None,
            )
        except requests.exceptions.RequestException as e:
            raise NinjaVanNetworkError(
                f"Network error during token refresh: {str(e)}",
                status_code=None,
            )

    def logout(self, access_token: str) -> bool:
        """
        Invalidate access token and refresh token.

        Should be called when merchant disconnects their NinjaVan account.

        Args:
            access_token: Current access token to invalidate

        Returns:
            True if logout successful, False otherwise

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> success = client.logout(access_token)
            >>> # Clear stored tokens
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        logger.info("Logging out and invalidating tokens")

        try:
            response = requests.post(
                self.logout_url,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 204:
                logger.info("Successfully logged out and invalidated tokens")
                return True
            else:
                logger.warning(
                    f"Logout request returned status {response.status_code}. "
                    f"Tokens may still be valid."
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error during logout: {e}")
            return False

    def should_refresh_token(self, expires_at: datetime) -> bool:
        """
        Check if access token should be refreshed.

        Tokens should be refreshed 5 minutes before expiry to avoid
        authentication errors during API calls.

        Args:
            expires_at: Token expiration timestamp

        Returns:
            True if token should be refreshed, False otherwise

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> if client.should_refresh_token(expires_at):
            >>>     new_tokens = client.refresh_access_token(refresh_token)
        """
        if expires_at is None:
            # If we don't have expiry info, assume we need to refresh
            return True

        # Convert to datetime if string
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except Exception:
                return True

        # Check if we're within the refresh buffer
        now = datetime.utcnow()
        time_until_expiry = (expires_at - now).total_seconds()

        should_refresh = time_until_expiry <= self.TOKEN_REFRESH_BUFFER_SECONDS

        if should_refresh:
            logger.info(
                f"Token should be refreshed. "
                f"Expires in {time_until_expiry:.0f}s "
                f"(buffer: {self.TOKEN_REFRESH_BUFFER_SECONDS}s)"
            )

        return should_refresh

    def refresh_if_needed(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> Tuple[str, str, datetime, bool]:
        """
        Refresh token if needed (thread-safe).

        This method is thread-safe and will only perform one refresh
        even if called concurrently from multiple threads.

        Args:
            access_token: Current access token
            refresh_token: Current refresh token
            expires_at: Current token expiration

        Returns:
            Tuple of (access_token, refresh_token, expires_at, was_refreshed)

        Example:
            >>> client = NinjaVanOAuthClient(client_id, client_secret)
            >>> token, refresh, expires, refreshed = client.refresh_if_needed(
            >>>     access_token, refresh_token, expires_at
            >>> )
            >>> if refreshed:
            >>>     # Store new tokens
        """
        # Check if refresh is needed
        if not self.should_refresh_token(expires_at):
            return access_token, refresh_token, expires_at, False

        # Use lock to prevent multiple simultaneous refreshes
        with self._refresh_lock:
            # Double-check after acquiring lock (another thread may have refreshed)
            if not self.should_refresh_token(expires_at):
                return access_token, refresh_token, expires_at, False

            try:
                logger.info("Refreshing access token (thread-safe)")
                new_tokens = self.refresh_access_token(refresh_token)

                return (
                    new_tokens["access_token"],
                    new_tokens["refresh_token"],
                    new_tokens["expires_at"],
                    True,
                )

            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                # Return original tokens and let the caller handle the error
                return access_token, refresh_token, expires_at, False
