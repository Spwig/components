"""
Unit tests for Gmail API Provider
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import base64
from email.mime.multipart import MIMEMultipart

from components.integrations.email_providers.gmail_api.v1.0.0.provider import GmailProvider
from email_system.providers.base import (
    EmailMessage,
    EmailProviderAuthError,
    EmailProviderRateLimitError,
)


class TestGmailProvider(unittest.TestCase):
    """Test cases for Gmail API provider"""

    def setUp(self):
        """Set up test fixtures"""
        self.valid_credentials = {
            'token': 'test_access_token_12345',
            'refresh_token': 'test_refresh_token_67890',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client.apps.googleusercontent.com',
            'client_secret': 'test_client_secret_abcdef',
        }

        self.test_message: EmailMessage = {
            'message_id': 'test-uuid-1234',
            'from_email': 'sender@example.com',
            'from_name': 'Test Sender',
            'to': ['recipient@example.com'],
            'cc': [],
            'bcc': [],
            'reply_to': None,
            'subject': 'Test Email',
            'html': '<p>This is a test email</p>',
            'text': 'This is a test email',
            'headers': {},
            'return_path': '',
            'attachments': [],
            'inline_images': [],
            'tags': [],
            'metadata': {},
        }

    def test_init_with_valid_credentials(self):
        """Test provider initialization with valid credentials"""
        provider = GmailProvider(credentials=self.valid_credentials)

        self.assertEqual(provider.provider_key, 'gmail_api')
        self.assertEqual(provider.provider_name, 'Gmail API')
        self.assertIsNotNone(provider.oauth_creds)

    def test_init_with_missing_credentials(self):
        """Test provider initialization with missing credentials"""
        invalid_creds = {'token': 'test_token'}  # Missing required fields

        with self.assertRaises(ValueError) as context:
            GmailProvider(credentials=invalid_creds)

        self.assertIn('Missing required OAuth credentials', str(context.exception))

    def test_capabilities(self):
        """Test provider capabilities property"""
        provider = GmailProvider(credentials=self.valid_credentials)
        capabilities = provider.capabilities

        self.assertTrue(capabilities['send'])
        self.assertTrue(capabilities['oauth'])
        self.assertTrue(capabilities['healthcheck'])
        self.assertTrue(capabilities['attachments'])
        self.assertTrue(capabilities['inline_images'])
        self.assertFalse(capabilities['batch_send'])
        self.assertFalse(capabilities['webhooks'])
        self.assertFalse(capabilities['tracking'])

    def test_credential_schema(self):
        """Test credential schema property"""
        provider = GmailProvider(credentials=self.valid_credentials)
        schema = provider.credential_schema

        self.assertIn('token', schema)
        self.assertIn('refresh_token', schema)
        self.assertIn('client_id', schema)
        self.assertIn('client_secret', schema)
        self.assertTrue(schema['token']['secret'])
        self.assertTrue(schema['refresh_token']['secret'])
        self.assertTrue(schema['client_secret']['secret'])

    def test_validate_credentials_valid(self):
        """Test credential validation with valid credentials"""
        provider = GmailProvider(credentials=self.valid_credentials)

        # Should not raise exception
        provider.validate_credentials(self.valid_credentials)

    def test_validate_credentials_missing_field(self):
        """Test credential validation with missing field"""
        provider = GmailProvider(credentials=self.valid_credentials)
        invalid_creds = self.valid_credentials.copy()
        del invalid_creds['token']

        with self.assertRaises(ValueError) as context:
            provider.validate_credentials(invalid_creds)

        self.assertIn('Missing required OAuth credential: token', str(context.exception))

    def test_validate_credentials_invalid_token_uri(self):
        """Test credential validation with invalid token URI"""
        provider = GmailProvider(credentials=self.valid_credentials)
        invalid_creds = self.valid_credentials.copy()
        invalid_creds['token_uri'] = 'http://oauth2.googleapis.com/token'  # HTTP not HTTPS

        with self.assertRaises(ValueError) as context:
            provider.validate_credentials(invalid_creds)

        self.assertIn('token_uri must be an HTTPS URL', str(context.exception))

    def test_validate_credentials_invalid_client_id(self):
        """Test credential validation with invalid client ID format"""
        provider = GmailProvider(credentials=self.valid_credentials)
        invalid_creds = self.valid_credentials.copy()
        invalid_creds['client_id'] = 'invalid_client_id'  # Doesn't end with .apps.googleusercontent.com

        with self.assertRaises(ValueError) as context:
            provider.validate_credentials(invalid_creds)

        self.assertIn('Invalid Google OAuth client_id format', str(context.exception))

    def test_redact_credentials(self):
        """Test credential redaction for logging"""
        provider = GmailProvider(credentials=self.valid_credentials)
        redacted = provider.redact_credentials(self.valid_credentials)

        # Sensitive fields should be redacted
        self.assertIn('...', redacted['token'])
        self.assertIn('...', redacted['refresh_token'])
        self.assertIn('...', redacted['client_secret'])

        # Non-sensitive fields should remain
        self.assertEqual(redacted['client_id'], self.valid_credentials['client_id'])
        self.assertEqual(redacted['token_uri'], self.valid_credentials['token_uri'])

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.provider.build')
    def test_send_success(self, mock_build):
        """Test successful email send"""
        # Mock Gmail API service
        mock_service = MagicMock()
        mock_messages = MagicMock()
        mock_send = MagicMock()

        mock_send.execute.return_value = {
            'id': 'gmail_message_id_12345',
            'threadId': 'thread_id_67890',
            'labelIds': ['SENT']
        }

        mock_messages.send.return_value = mock_send
        mock_service.users.return_value.messages.return_value = mock_messages
        mock_build.return_value = mock_service

        provider = GmailProvider(credentials=self.valid_credentials)

        # Mock OAuth token (set as not expired)
        with patch.object(provider.oauth_creds, 'expired', False):
            result = provider.send(self.test_message)

        self.assertTrue(result['accepted'])
        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['provider_message_id'], 'gmail_message_id_12345')
        self.assertIsNone(result['error'])

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.provider.build')
    def test_create_mime_message(self, mock_build):
        """Test MIME message creation"""
        provider = GmailProvider(credentials=self.valid_credentials)

        mime_message = provider._create_mime_message(self.test_message)

        self.assertIsInstance(mime_message, MIMEMultipart)
        self.assertEqual(mime_message['Subject'], 'Test Email')
        self.assertIn('recipient@example.com', mime_message['To'])
        self.assertIn('sender@example.com', mime_message['From'])

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.provider.build')
    def test_healthcheck_success(self, mock_build):
        """Test successful health check"""
        # Mock Gmail API service
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_profile = MagicMock()

        mock_profile.execute.return_value = {
            'emailAddress': 'test@gmail.com',
            'messagesTotal': 100,
            'threadsTotal': 50,
            'historyId': '12345'
        }

        mock_users.getProfile.return_value = mock_profile
        mock_service.users.return_value = mock_users
        mock_build.return_value = mock_service

        provider = GmailProvider(credentials=self.valid_credentials)

        # Mock OAuth token (set as not expired)
        with patch.object(provider.oauth_creds, 'expired', False):
            result = provider.healthcheck()

        self.assertTrue(result['success'])
        self.assertIn('Successfully connected', result['message'])
        self.assertEqual(result['details']['email_address'], 'test@gmail.com')

    def test_get_rate_limits(self):
        """Test rate limit information"""
        provider = GmailProvider(credentials=self.valid_credentials)
        limits = provider.get_rate_limits()

        self.assertEqual(limits['emails_per_second'], 15)
        self.assertEqual(limits['emails_per_day'], 2000)
        self.assertEqual(limits['emails_per_day_standard'], 500)
        self.assertTrue(limits['has_burst_limit'])


if __name__ == '__main__':
    unittest.main()
