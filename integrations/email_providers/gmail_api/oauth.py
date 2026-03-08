"""
Gmail API OAuth 2.0 Authorization Code Flow Handler

Handles OAuth 2.0 authorization code flow for Gmail API authentication.
Implements the three-legged OAuth flow requiring user authorization.

References:
- Google OAuth 2.0 Documentation: https://developers.google.com/identity/protocols/oauth2
- Gmail API Authorization: https://developers.google.com/gmail/api/auth/web-server
- OAuth 2.0 Scopes: https://developers.google.com/gmail/api/auth/scopes
"""
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class GmailOAuthHandler:
    """
    OAuth 2.0 handler for Gmail API authorization code flow.

    Manages the three-step OAuth process:
    1. Generate authorization URL for user consent
    2. Exchange authorization code for access/refresh tokens
    3. Refresh access tokens when expired
    """

    # OAuth scopes required for sending emails
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send'
    ]

    # Google OAuth endpoints
    AUTHORIZATION_BASE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URI = 'https://oauth2.googleapis.com/token'

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Gmail OAuth handler.

        Args:
            client_id: Google OAuth client ID from Cloud Console
            client_secret: Google OAuth client secret
            redirect_uri: Authorized redirect URI (must match Cloud Console config)

        Raises:
            ValueError: If any required parameter is missing
        """
        if not client_id:
            raise ValueError("client_id is required")
        if not client_secret:
            raise ValueError("client_secret is required")
        if not redirect_uri:
            raise ValueError("redirect_uri is required")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # Client config for google-auth-oauthlib
        self.client_config = {
            'web': {
                'client_id': client_id,
                'client_secret': client_secret,
                'auth_uri': self.AUTHORIZATION_BASE_URL,
                'token_uri': self.TOKEN_URI,
                'redirect_uris': [redirect_uri],
            }
        }

    def get_authorization_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate OAuth authorization URL for user consent.

        Args:
            state: Optional state parameter for CSRF protection
                   Should be a unique token tied to user session

        Returns:
            Dictionary with:
                - authorization_url: URL to redirect user to
                - state: State parameter (generated if not provided)

        Example:
            handler = GmailOAuthHandler(client_id, client_secret, redirect_uri)
            result = handler.get_authorization_url(state='random_token_123')
            # Redirect user to result['authorization_url']
        """
        try:
            # Create flow instance
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )

            # Generate authorization URL
            authorization_url, state_value = flow.authorization_url(
                access_type='offline',  # Request refresh token
                include_granted_scopes='true',  # Incremental authorization
                state=state,  # CSRF protection
                prompt='consent'  # Force consent screen to get refresh token
            )

            logger.info("Generated Gmail OAuth authorization URL")

            return {
                'authorization_url': authorization_url,
                'state': state_value
            }

        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        This is step 2 of OAuth flow, called after user authorizes the app
        and is redirected back with an authorization code.

        Args:
            authorization_code: Authorization code from OAuth callback

        Returns:
            Dictionary with OAuth token information:
                - token: Access token
                - refresh_token: Refresh token (for getting new access tokens)
                - token_uri: Token endpoint URI
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
                - scopes: Granted OAuth scopes
                - expiry: Token expiration datetime (ISO format)

        Raises:
            ValueError: If authorization code is invalid
            ConnectionError: If token exchange fails

        Example:
            # After user is redirected back with code
            credentials = handler.exchange_code_for_tokens(code)
            # Store credentials (encrypted) in database
        """
        if not authorization_code:
            raise ValueError("authorization_code is required")

        try:
            # Create flow instance
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )

            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens")
            flow.fetch_token(code=authorization_code)

            # Extract credentials
            credentials = flow.credentials

            # Convert to dictionary for storage
            credentials_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            }

            # Add expiry if available
            if credentials.expiry:
                credentials_dict['expiry'] = credentials.expiry.isoformat()

            logger.info("Successfully exchanged authorization code for tokens")

            return credentials_dict

        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            if "invalid_grant" in str(e).lower():
                raise ValueError("Invalid or expired authorization code")
            raise ConnectionError(f"Failed to obtain OAuth tokens: {str(e)}")

    def refresh_access_token(self, credentials_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token.

        Args:
            credentials_dict: Dictionary with OAuth credentials including refresh_token

        Returns:
            Updated credentials dictionary with new access token

        Raises:
            ValueError: If refresh token is missing or invalid
            ConnectionError: If token refresh fails

        Example:
            # When access token expires
            updated_credentials = handler.refresh_access_token(stored_credentials)
            # Update stored credentials in database
        """
        if not credentials_dict.get('refresh_token'):
            raise ValueError("refresh_token is required for token refresh")

        try:
            # Create Credentials object from stored data
            credentials = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict['refresh_token'],
                token_uri=credentials_dict.get('token_uri', self.TOKEN_URI),
                client_id=credentials_dict.get('client_id', self.client_id),
                client_secret=credentials_dict.get('client_secret', self.client_secret),
                scopes=credentials_dict.get('scopes', self.SCOPES)
            )

            # Refresh the token
            logger.info("Refreshing Gmail OAuth access token")
            credentials.refresh(Request())

            # Convert back to dictionary
            updated_credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            }

            # Add expiry if available
            if credentials.expiry:
                updated_credentials['expiry'] = credentials.expiry.isoformat()

            logger.info("Successfully refreshed access token")

            return updated_credentials

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            if "invalid_grant" in str(e).lower():
                raise ValueError("Invalid or revoked refresh token. User must re-authorize.")
            raise ConnectionError(f"Failed to refresh OAuth token: {str(e)}")

    def revoke_token(self, token: str) -> bool:
        """
        Revoke an OAuth token (access or refresh token).

        Args:
            token: Token to revoke (access_token or refresh_token)

        Returns:
            True if revocation succeeded, False otherwise

        Example:
            # When user disconnects account
            handler.revoke_token(credentials['refresh_token'])
        """
        try:
            import requests

            revoke_url = 'https://oauth2.googleapis.com/revoke'
            response = requests.post(
                revoke_url,
                params={'token': token},
                headers={'content-type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Successfully revoked OAuth token")
                return True
            else:
                logger.warning(f"Token revocation returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    def validate_credentials(self, credentials_dict: Dict[str, Any]) -> bool:
        """
        Validate that credentials dictionary has all required fields.

        Args:
            credentials_dict: Credentials dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']

        for field in required_fields:
            if field not in credentials_dict or not credentials_dict[field]:
                logger.warning(f"Missing or empty required credential field: {field}")
                return False

        # Validate token_uri is HTTPS
        token_uri = credentials_dict.get('token_uri', '')
        if not token_uri.startswith('https://'):
            logger.warning(f"Invalid token_uri (must be HTTPS): {token_uri}")
            return False

        # Validate client_id format
        client_id = credentials_dict.get('client_id', '')
        if not client_id.endswith('.apps.googleusercontent.com'):
            logger.warning(f"Invalid client_id format: {client_id}")
            return False

        return True


def create_oauth_handler(
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> GmailOAuthHandler:
    """
    Factory function to create Gmail OAuth handler.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: Authorized redirect URI

    Returns:
        Configured GmailOAuthHandler instance

    Raises:
        ValueError: If required parameters are missing

    Example:
        handler = create_oauth_handler(
            client_id='xxx.apps.googleusercontent.com',
            client_secret='xxx',
            redirect_uri='https://example.com/oauth/callback/'
        )
    """
    return GmailOAuthHandler(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
