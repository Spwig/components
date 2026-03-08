"""
Gmail API Email Provider
Send transactional emails via Gmail API with OAuth 2.0 authentication
"""
from typing import Dict, List, Any, Optional
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from email_system.providers.base import (
    EmailProviderBase,
    EmailMessage,
    SendResult,
    EmailProviderError,
    EmailProviderAuthError,
    EmailProviderRateLimitError,
)

# Import OAuth handler from same package
try:
    from .oauth import GmailOAuthHandler
except ImportError:
    # Fallback for different import contexts
    from oauth import GmailOAuthHandler

logger = logging.getLogger(__name__)


class GmailProvider(EmailProviderBase):
    """Gmail API provider implementation"""

    # Required class attributes
    provider_key = "gmail_api"
    provider_name = "Gmail API"

    # API configuration
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    API_VERSION = 'v1'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with OAuth credentials

        Args:
            credentials: Dictionary with OAuth token information
            config: Optional configuration dictionary

        Raises:
            ValueError: If credentials are missing or invalid
        """
        super().__init__(credentials, config)

        # Validate required OAuth fields
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if field not in credentials]

        if missing_fields:
            raise ValueError(f"Missing required OAuth credentials: {', '.join(missing_fields)}")

        # Initialize OAuth credentials
        self.oauth_creds = Credentials(
            token=credentials['token'],
            refresh_token=credentials['refresh_token'],
            token_uri=credentials['token_uri'],
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            scopes=self.SCOPES
        )

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities"""
        return {
            'send': True,
            'oauth': True,
            'healthcheck': True,
            'batch_send': False,
            'webhooks': False,
            'attachments': True,
            'inline_images': True,
            'tracking': False
        }

    @property
    def credential_schema(self) -> Dict[str, Dict[str, Any]]:
        """Return JSON schema for credentials"""
        return {
            "token": {
                "type": "string",
                "label": "Access Token",
                "required": True,
                "secret": True,
                "help_text": "OAuth 2.0 access token"
            },
            "refresh_token": {
                "type": "string",
                "label": "Refresh Token",
                "required": True,
                "secret": True,
                "help_text": "OAuth 2.0 refresh token for automatic token renewal"
            },
            "token_uri": {
                "type": "string",
                "label": "Token URI",
                "required": True,
                "default": "https://oauth2.googleapis.com/token",
                "help_text": "Google OAuth token endpoint"
            },
            "client_id": {
                "type": "string",
                "label": "Client ID",
                "required": True,
                "help_text": "OAuth 2.0 client ID from Google Cloud Console"
            },
            "client_secret": {
                "type": "string",
                "label": "Client Secret",
                "required": True,
                "secret": True,
                "help_text": "OAuth 2.0 client secret from Google Cloud Console"
            },
            "scopes": {
                "type": "list",
                "label": "OAuth Scopes",
                "required": False,
                "default": self.SCOPES,
                "help_text": "OAuth scopes for Gmail API access"
            }
        }

    def _refresh_token_if_needed(self):
        """
        Refresh OAuth token if expired

        Returns:
            Updated credentials dictionary if token was refreshed
        """
        if self.oauth_creds.expired and self.oauth_creds.refresh_token:
            try:
                self.oauth_creds.refresh(Request())
                logger.info("OAuth token refreshed successfully")

                # Return updated credentials for storage
                return {
                    'token': self.oauth_creds.token,
                    'refresh_token': self.oauth_creds.refresh_token,
                    'token_uri': self.oauth_creds.token_uri,
                    'client_id': self.oauth_creds.client_id,
                    'client_secret': self.oauth_creds.client_secret,
                    'scopes': self.oauth_creds.scopes,
                }
            except Exception as e:
                logger.error(f"Failed to refresh OAuth token: {e}")
                raise EmailProviderAuthError(f"Failed to refresh OAuth token: {e}")

        return None

    def _build_gmail_service(self):
        """
        Build Gmail API service with authenticated credentials

        Returns:
            Gmail API service instance
        """
        # Refresh token if needed
        self._refresh_token_if_needed()

        try:
            service = build('gmail', self.API_VERSION, credentials=self.oauth_creds)
            return service
        except Exception as e:
            logger.error(f"Failed to build Gmail API service: {e}")
            raise EmailProviderError(f"Failed to initialize Gmail API: {e}")

    def _create_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Create MIME message from EmailMessage dictionary

        Args:
            message: EmailMessage dictionary

        Returns:
            MIMEMultipart message object
        """
        # Create multipart message
        mime_message = MIMEMultipart('mixed')

        # Set headers
        mime_message['From'] = f"{message.get('from_name', '')} <{message['from_email']}>" if message.get('from_name') else message['from_email']
        mime_message['To'] = ', '.join(message['to'])

        if message.get('cc'):
            mime_message['Cc'] = ', '.join(message['cc'])

        if message.get('bcc'):
            mime_message['Bcc'] = ', '.join(message['bcc'])

        if message.get('reply_to'):
            mime_message['Reply-To'] = message['reply_to']

        mime_message['Subject'] = message['subject']

        # Add custom headers
        if message.get('headers'):
            for header_name, header_value in message['headers'].items():
                mime_message[header_name] = header_value

        # Create alternative part for HTML and plain text
        msg_alternative = MIMEMultipart('alternative')
        mime_message.attach(msg_alternative)

        # Add plain text version
        if message.get('text'):
            text_part = MIMEText(message['text'], 'plain', 'utf-8')
            msg_alternative.attach(text_part)

        # Add HTML version
        if message.get('html'):
            html_part = MIMEText(message['html'], 'html', 'utf-8')
            msg_alternative.attach(html_part)

        # Add inline images
        if message.get('inline_images'):
            for inline_image in message['inline_images']:
                image_part = MIMEBase('image', inline_image['content_type'].split('/')[-1])
                image_part.set_payload(inline_image['content'])
                encoders.encode_base64(image_part)
                image_part.add_header('Content-ID', f"<{inline_image['cid']}>")
                image_part.add_header('Content-Disposition', 'inline', filename=inline_image['filename'])
                mime_message.attach(image_part)

        # Add attachments
        if message.get('attachments'):
            for attachment in message['attachments']:
                # Determine main type and subtype from content_type
                content_type = attachment['content_type']
                main_type, sub_type = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

                attachment_part = MIMEBase(main_type, sub_type)
                attachment_part.set_payload(attachment['content'])
                encoders.encode_base64(attachment_part)
                attachment_part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=attachment['filename']
                )
                mime_message.attach(attachment_part)

        return mime_message

    def send(self, message: EmailMessage) -> SendResult:
        """
        Send a single email message via Gmail API

        Args:
            message: EmailMessage dictionary with all email data

        Returns:
            SendResult dictionary with send status and provider message ID

        Raises:
            EmailProviderError: If sending fails
        """
        try:
            # Build Gmail API service
            service = self._build_gmail_service()

            # Create MIME message
            mime_message = self._create_mime_message(message)

            # Encode message for Gmail API
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode('utf-8')

            # Send message
            send_result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Email sent successfully via Gmail API: {send_result.get('id')}")

            return {
                'provider_message_id': send_result.get('id'),
                'accepted': True,
                'status': 'sent',
                'error': None,
                'details': {
                    'thread_id': send_result.get('threadId'),
                    'label_ids': send_result.get('labelIds', [])
                }
            }

        except HttpError as error:
            error_details = error.error_details if hasattr(error, 'error_details') else []
            error_reason = error_details[0].get('reason', 'unknown') if error_details else 'unknown'
            error_message = error_details[0].get('message', str(error)) if error_details else str(error)

            logger.error(f"Gmail API error: {error_reason} - {error_message}")

            # Handle specific error types
            if error.resp.status == 401:
                raise EmailProviderAuthError(f"Authentication failed: {error_message}")
            elif error.resp.status == 403:
                raise EmailProviderAuthError(f"Permission denied: {error_message}")
            elif error.resp.status == 429:
                raise EmailProviderRateLimitError(f"Rate limit exceeded: {error_message}")
            else:
                return {
                    'provider_message_id': '',
                    'accepted': False,
                    'status': 'failed',
                    'error': f"Gmail API error ({error.resp.status}): {error_message}",
                    'details': {
                        'status_code': error.resp.status,
                        'reason': error_reason
                    }
                }

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return {
                'provider_message_id': '',
                'accepted': False,
                'status': 'failed',
                'error': f"Failed to send email: {str(e)}",
                'details': {'error_type': type(e).__name__}
            }

    def healthcheck(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with health check results
        """
        try:
            # Build Gmail API service
            service = self._build_gmail_service()

            # Get user profile to verify credentials
            profile = service.users().getProfile(userId='me').execute()

            return {
                'success': True,
                'message': f'Successfully connected to Gmail API for {profile.get("emailAddress")}',
                'details': {
                    'email_address': profile.get('emailAddress'),
                    'messages_total': profile.get('messagesTotal'),
                    'threads_total': profile.get('threadsTotal'),
                    'history_id': profile.get('historyId')
                }
            }

        except HttpError as error:
            error_details = error.error_details if hasattr(error, 'error_details') else []
            error_message = error_details[0].get('message', str(error)) if error_details else str(error)

            if error.resp.status == 401:
                return {
                    'success': False,
                    'message': 'Authentication failed - invalid or expired OAuth token',
                    'details': {'status_code': 401, 'error': 'unauthorized'}
                }
            elif error.resp.status == 403:
                return {
                    'success': False,
                    'message': 'Permission denied - insufficient OAuth scopes',
                    'details': {'status_code': 403, 'error': 'forbidden'}
                }
            else:
                return {
                    'success': False,
                    'message': f'Gmail API error: {error_message}',
                    'details': {'status_code': error.resp.status}
                }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'success': False,
                'message': f'Connection error: {str(e)}',
                'details': {'error': str(e)}
            }

    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get current rate limit information

        Returns:
            Dictionary with rate limit details
        """
        # Gmail API rate limits depend on account type
        # Standard Gmail: 500 emails/day
        # Google Workspace: 2000 emails/day
        # Rate: 15 emails/second (burst)

        return {
            'emails_per_second': 15,
            'emails_per_day': 2000,  # Workspace limit
            'emails_per_day_standard': 500,  # Standard Gmail limit
            'has_burst_limit': True,
            'remaining': None,  # Not provided by API
            'reset_at': None    # Resets daily at midnight PT
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credential format before storage

        Args:
            credentials: Credentials dictionary to validate

        Raises:
            ValueError: If credentials are invalid
        """
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']

        for field in required_fields:
            if field not in credentials:
                raise ValueError(f"Missing required OAuth credential: {field}")

            if not credentials[field]:
                raise ValueError(f"OAuth credential '{field}' cannot be empty")

        # Validate token_uri format
        token_uri = credentials['token_uri']
        if not token_uri.startswith('https://'):
            raise ValueError("token_uri must be an HTTPS URL")

        # Validate client_id format (Google client IDs end with .apps.googleusercontent.com)
        client_id = credentials['client_id']
        if not client_id.endswith('.apps.googleusercontent.com'):
            raise ValueError("Invalid Google OAuth client_id format")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Plain credential dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()

        # Redact sensitive fields
        for field in ['token', 'refresh_token', 'client_secret']:
            if field in redacted and redacted[field]:
                value = redacted[field]
                if len(value) > 8:
                    redacted[field] = f"{value[:4]}...{value[-4:]}"
                else:
                    redacted[field] = "***"

        return redacted

    @staticmethod
    def create_oauth_handler(client_id: str, client_secret: str, redirect_uri: str) -> 'GmailOAuthHandler':
        """
        Create OAuth handler for authorization code flow.

        This is used by the platform to initiate the OAuth flow and handle callbacks.

        Args:
            client_id: Google OAuth client ID from Cloud Console
            client_secret: Google OAuth client secret
            redirect_uri: Authorized redirect URI (must match Cloud Console config)

        Returns:
            GmailOAuthHandler instance for managing OAuth flow

        Example:
            # In OAuth view/controller
            handler = GmailProvider.create_oauth_handler(
                client_id='xxx.apps.googleusercontent.com',
                client_secret='xxx',
                redirect_uri='https://example.com/admin/email_system/oauth/callback/gmail_api/'
            )

            # Step 1: Get authorization URL
            auth_result = handler.get_authorization_url(state=session_token)
            # Redirect user to auth_result['authorization_url']

            # Step 2: After callback with code
            credentials = handler.exchange_code_for_tokens(authorization_code)
            # Store credentials (encrypted) in EmailAccount
        """
        return GmailOAuthHandler(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
