"""
Unit tests for Gmail OAuth Handler
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from components.integrations.email_providers.gmail_api.v1.0.0.oauth import (
    GmailOAuthHandler,
    create_oauth_handler
)


class TestGmailOAuthHandler(unittest.TestCase):
    """Test cases for Gmail OAuth handler"""

    def setUp(self):
        """Set up test fixtures"""
        self.client_id = 'test_client.apps.googleusercontent.com'
        self.client_secret = 'test_client_secret'
        self.redirect_uri = 'https://example.com/oauth/callback/'

        self.handler = GmailOAuthHandler(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri
        )

    def test_init_with_valid_params(self):
        """Test handler initialization with valid parameters"""
        handler = GmailOAuthHandler(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri
        )

        self.assertEqual(handler.client_id, self.client_id)
        self.assertEqual(handler.client_secret, self.client_secret)
        self.assertEqual(handler.redirect_uri, self.redirect_uri)
        self.assertIsNotNone(handler.client_config)

    def test_init_missing_client_id(self):
        """Test handler initialization with missing client_id"""
        with self.assertRaises(ValueError) as context:
            GmailOAuthHandler(
                client_id='',
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri
            )

        self.assertIn('client_id is required', str(context.exception))

    def test_init_missing_client_secret(self):
        """Test handler initialization with missing client_secret"""
        with self.assertRaises(ValueError) as context:
            GmailOAuthHandler(
                client_id=self.client_id,
                client_secret='',
                redirect_uri=self.redirect_uri
            )

        self.assertIn('client_secret is required', str(context.exception))

    def test_init_missing_redirect_uri(self):
        """Test handler initialization with missing redirect_uri"""
        with self.assertRaises(ValueError) as context:
            GmailOAuthHandler(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=''
            )

        self.assertIn('redirect_uri is required', str(context.exception))

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.oauth.Flow')
    def test_get_authorization_url(self, mock_flow_class):
        """Test authorization URL generation"""
        # Mock flow instance
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            'https://accounts.google.com/o/oauth2/v2/auth?client_id=test&...',
            'state_token_12345'
        )
        mock_flow_class.from_client_config.return_value = mock_flow

        # Generate authorization URL
        result = self.handler.get_authorization_url(state='custom_state')

        # Verify result
        self.assertIn('authorization_url', result)
        self.assertIn('state', result)
        self.assertEqual(result['state'], 'state_token_12345')
        self.assertIn('https://accounts.google.com', result['authorization_url'])

        # Verify flow was configured correctly
        mock_flow.authorization_url.assert_called_once_with(
            access_type='offline',
            include_granted_scopes='true',
            state='custom_state',
            prompt='consent'
        )

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.oauth.Flow')
    def test_exchange_code_for_tokens(self, mock_flow_class):
        """Test exchanging authorization code for tokens"""
        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.token = 'access_token_12345'
        mock_credentials.refresh_token = 'refresh_token_67890'
        mock_credentials.token_uri = 'https://oauth2.googleapis.com/token'
        mock_credentials.client_id = self.client_id
        mock_credentials.client_secret = self.client_secret
        mock_credentials.scopes = ['https://www.googleapis.com/auth/gmail.send']
        mock_credentials.expiry = datetime.now() + timedelta(hours=1)

        # Mock flow instance
        mock_flow = MagicMock()
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_config.return_value = mock_flow

        # Exchange code for tokens
        result = self.handler.exchange_code_for_tokens('authorization_code_abc123')

        # Verify result
        self.assertEqual(result['token'], 'access_token_12345')
        self.assertEqual(result['refresh_token'], 'refresh_token_67890')
        self.assertEqual(result['client_id'], self.client_id)
        self.assertIn('expiry', result)

        # Verify flow was called
        mock_flow.fetch_token.assert_called_once_with(code='authorization_code_abc123')

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.oauth.Flow')
    def test_exchange_code_invalid_code(self, mock_flow_class):
        """Test exchanging invalid authorization code"""
        # Mock flow that raises error
        mock_flow = MagicMock()
        mock_flow.fetch_token.side_effect = Exception("invalid_grant: Bad Request")
        mock_flow_class.from_client_config.return_value = mock_flow

        # Should raise ValueError for invalid code
        with self.assertRaises(ValueError) as context:
            self.handler.exchange_code_for_tokens('invalid_code')

        self.assertIn('Invalid or expired authorization code', str(context.exception))

    @patch('components.integrations.email_providers.gmail_api.v1.0.0.oauth.Credentials')
    @patch('components.integrations.email_providers.gmail_api.v1.0.0.oauth.Request')
    def test_refresh_access_token(self, mock_request_class, mock_credentials_class):
        """Test refreshing access token"""
        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.token = 'new_access_token_12345'
        mock_credentials.refresh_token = 'refresh_token_67890'
        mock_credentials.token_uri = 'https://oauth2.googleapis.com/token'
        mock_credentials.client_id = self.client_id
        mock_credentials.client_secret = self.client_secret
        mock_credentials.scopes = ['https://www.googleapis.com/auth/gmail.send']
        mock_credentials.expiry = datetime.now() + timedelta(hours=1)

        mock_credentials_class.return_value = mock_credentials

        # Credentials to refresh
        credentials_dict = {
            'token': 'old_access_token',
            'refresh_token': 'refresh_token_67890',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scopes': ['https://www.googleapis.com/auth/gmail.send']
        }

        # Refresh token
        result = self.handler.refresh_access_token(credentials_dict)

        # Verify result
        self.assertEqual(result['token'], 'new_access_token_12345')
        self.assertEqual(result['refresh_token'], 'refresh_token_67890')

        # Verify refresh was called
        mock_credentials.refresh.assert_called_once()

    def test_refresh_access_token_missing_refresh_token(self):
        """Test refreshing without refresh token"""
        credentials_dict = {
            'token': 'access_token',
            # Missing refresh_token
        }

        with self.assertRaises(ValueError) as context:
            self.handler.refresh_access_token(credentials_dict)

        self.assertIn('refresh_token is required', str(context.exception))

    def test_validate_credentials_valid(self):
        """Test validating valid credentials"""
        credentials_dict = {
            'token': 'access_token_12345',
            'refresh_token': 'refresh_token_67890',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test.apps.googleusercontent.com',
            'client_secret': 'client_secret_abc'
        }

        result = self.handler.validate_credentials(credentials_dict)
        self.assertTrue(result)

    def test_validate_credentials_missing_field(self):
        """Test validating credentials with missing field"""
        credentials_dict = {
            'token': 'access_token_12345',
            # Missing refresh_token
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test.apps.googleusercontent.com',
            'client_secret': 'client_secret_abc'
        }

        result = self.handler.validate_credentials(credentials_dict)
        self.assertFalse(result)

    def test_validate_credentials_invalid_token_uri(self):
        """Test validating credentials with HTTP token URI"""
        credentials_dict = {
            'token': 'access_token_12345',
            'refresh_token': 'refresh_token_67890',
            'token_uri': 'http://oauth2.googleapis.com/token',  # HTTP not HTTPS
            'client_id': 'test.apps.googleusercontent.com',
            'client_secret': 'client_secret_abc'
        }

        result = self.handler.validate_credentials(credentials_dict)
        self.assertFalse(result)

    def test_validate_credentials_invalid_client_id(self):
        """Test validating credentials with invalid client_id format"""
        credentials_dict = {
            'token': 'access_token_12345',
            'refresh_token': 'refresh_token_67890',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'invalid_client_id',  # Wrong format
            'client_secret': 'client_secret_abc'
        }

        result = self.handler.validate_credentials(credentials_dict)
        self.assertFalse(result)

    def test_create_oauth_handler_factory(self):
        """Test factory function for creating handler"""
        handler = create_oauth_handler(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri
        )

        self.assertIsInstance(handler, GmailOAuthHandler)
        self.assertEqual(handler.client_id, self.client_id)


if __name__ == '__main__':
    unittest.main()
