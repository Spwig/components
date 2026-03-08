"""
Unit tests for SMTP Email Provider

Tests provider initialization, credential validation, and basic functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provider import SMTPProvider


class TestSMTPProvider(unittest.TestCase):
    """Test SMTP Provider implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.credentials = {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'test-password',
            'use_tls': True,
            'use_ssl': False,
            'timeout': 30
        }
        self.provider = SMTPProvider(self.credentials)

    def test_initialization(self):
        """Test provider initialization"""
        self.assertEqual(self.provider.provider_key, 'smtp')
        self.assertEqual(self.provider.provider_name, 'SMTP Server')
        self.assertEqual(self.provider.host, 'smtp.example.com')
        self.assertEqual(self.provider.port, 587)
        self.assertEqual(self.provider.username, 'test@example.com')
        self.assertTrue(self.provider.use_tls)
        self.assertFalse(self.provider.use_ssl)

    def test_initialization_missing_host(self):
        """Test initialization fails without SMTP host"""
        with self.assertRaises(ValueError) as context:
            SMTPProvider({'port': 587, 'username': 'x', 'password': 'y'})
        self.assertIn('host', str(context.exception).lower())

    def test_initialization_missing_port(self):
        """Test initialization fails without SMTP port"""
        with self.assertRaises(ValueError) as context:
            SMTPProvider({'host': 'smtp.example.com', 'username': 'x', 'password': 'y'})
        self.assertIn('port', str(context.exception).lower())

    def test_initialization_missing_username(self):
        """Test initialization fails without username"""
        with self.assertRaises(ValueError) as context:
            SMTPProvider({
                'host': 'smtp.example.com',
                'port': 587,
                'password': 'y'
            })
        self.assertIn('username', str(context.exception).lower())

    def test_initialization_missing_password(self):
        """Test initialization fails without password"""
        with self.assertRaises(ValueError) as context:
            SMTPProvider({
                'host': 'smtp.example.com',
                'port': 587,
                'username': 'test@example.com'
            })
        self.assertIn('password', str(context.exception).lower())

    def test_capabilities(self):
        """Test provider capabilities"""
        capabilities = self.provider.capabilities

        self.assertTrue(capabilities['send'])
        self.assertFalse(capabilities['oauth'])
        self.assertTrue(capabilities['attachments'])
        self.assertTrue(capabilities['inline_images'])
        self.assertTrue(capabilities['html_email'])
        self.assertTrue(capabilities['healthcheck'])
        self.assertFalse(capabilities['webhooks'])
        self.assertFalse(capabilities['bounce_handling'])

    def test_credential_schema(self):
        """Test credential schema"""
        schema = self.provider.credential_schema

        # Required fields
        self.assertIn('host', schema)
        self.assertIn('port', schema)
        self.assertIn('username', schema)
        self.assertIn('password', schema)

        # Check required flag
        self.assertTrue(schema['host']['required'])
        self.assertTrue(schema['port']['required'])
        self.assertTrue(schema['username']['required'])
        self.assertTrue(schema['password']['required'])

        # Check password type
        self.assertEqual(schema['password']['type'], 'password')

    def test_validate_credentials_success(self):
        """Test credential validation succeeds with valid credentials"""
        try:
            self.provider.validate_credentials(self.credentials)
        except ValueError:
            self.fail("validate_credentials raised ValueError unexpectedly")

    def test_validate_credentials_missing_host(self):
        """Test credential validation fails without host"""
        invalid_creds = self.credentials.copy()
        del invalid_creds['host']

        with self.assertRaises(ValueError):
            self.provider.validate_credentials(invalid_creds)

    def test_validate_credentials_missing_port(self):
        """Test credential validation fails without port"""
        invalid_creds = self.credentials.copy()
        del invalid_creds['port']

        with self.assertRaises(ValueError):
            self.provider.validate_credentials(invalid_creds)

    def test_validate_credentials_invalid_port(self):
        """Test credential validation fails with invalid port"""
        invalid_creds = self.credentials.copy()
        invalid_creds['port'] = 99999  # Out of range

        with self.assertRaises(ValueError):
            self.provider.validate_credentials(invalid_creds)

    def test_redact_credentials(self):
        """Test credential redaction"""
        redacted = self.provider.redact_credentials(self.credentials)

        # Password should be redacted
        self.assertEqual(redacted['password'], 'tes***ord')

        # Other fields should remain
        self.assertEqual(redacted['host'], 'smtp.example.com')
        self.assertEqual(redacted['port'], 587)
        self.assertEqual(redacted['username'], 'test@example.com')

    def test_redact_credentials_short_password(self):
        """Test credential redaction with short password"""
        creds = self.credentials.copy()
        creds['password'] = 'abc'

        redacted = self.provider.redact_credentials(creds)
        self.assertEqual(redacted['password'], '***')

    @patch('smtplib.SMTP')
    def test_healthcheck_success(self, mock_smtp):
        """Test successful health check"""
        # Mock SMTP connection
        mock_conn = MagicMock()
        mock_conn.noop.return_value = (250, b'OK')
        mock_smtp.return_value = mock_conn

        result = self.provider.healthcheck()

        self.assertTrue(result['success'])
        self.assertIn('successfully connected', result['message'].lower())
        self.assertEqual(result['details']['smtp_host'], 'smtp.example.com')
        self.assertEqual(result['details']['smtp_port'], 587)

    @patch('smtplib.SMTP')
    def test_healthcheck_authentication_failure(self, mock_smtp):
        """Test health check with authentication failure"""
        import smtplib as _smtplib
        # Mock SMTP connection that fails auth
        mock_conn = MagicMock()
        mock_conn.login.side_effect = _smtplib.SMTPAuthenticationError(535, b'Auth failed')
        mock_smtp.return_value = mock_conn

        result = self.provider.healthcheck()

        self.assertFalse(result['success'])
        self.assertIn('authentication', result['message'].lower())

    @patch('smtplib.SMTP')
    def test_healthcheck_connection_failure(self, mock_smtp):
        """Test health check with connection failure"""
        # Mock SMTP connection that fails to connect
        mock_smtp.side_effect = Exception("Connection refused")

        result = self.provider.healthcheck()

        self.assertFalse(result['success'])
        self.assertIn('connection', result['message'].lower())

    def test_build_mime_message_simple(self):
        """Test building simple MIME message"""
        message = {
            'message_id': 'test-001',
            'from_email': 'sender@example.com',
            'from_name': 'Test Sender',
            'to': ['recipient@example.com'],
            'subject': 'Test Email',
            'html': '<p>Hello World</p>',
            'text': 'Hello World',
            'cc': [],
            'bcc': [],
            'reply_to': None,
            'headers': {},
            'attachments': [],
            'inline_images': []
        }

        mime_msg = self.provider._build_mime_message(message)

        self.assertEqual(mime_msg['Subject'], 'Test Email')
        self.assertEqual(mime_msg['From'], 'Test Sender <sender@example.com>')
        self.assertEqual(mime_msg['To'], 'recipient@example.com')

    def test_build_mime_message_with_cc_bcc(self):
        """Test building MIME message with CC and BCC"""
        message = {
            'message_id': 'test-002',
            'from_email': 'sender@example.com',
            'to': ['recipient@example.com'],
            'cc': ['cc@example.com'],
            'bcc': ['bcc@example.com'],
            'subject': 'Test',
            'html': '<p>Test</p>',
            'text': 'Test',
            'headers': {},
            'attachments': [],
            'inline_images': []
        }

        mime_msg = self.provider._build_mime_message(message)

        self.assertEqual(mime_msg['Cc'], 'cc@example.com')
        # BCC should not be in headers (handled separately)
        self.assertNotIn('Bcc', mime_msg)

    def test_build_mime_message_with_attachments(self):
        """Test building MIME message with attachments"""
        message = {
            'message_id': 'test-003',
            'from_email': 'sender@example.com',
            'to': ['recipient@example.com'],
            'subject': 'Test',
            'html': '<p>Test</p>',
            'text': 'Test',
            'cc': [],
            'bcc': [],
            'headers': {},
            'attachments': [
                {
                    'filename': 'test.pdf',
                    'content': b'%PDF-1.4...',
                    'content_type': 'application/pdf'
                }
            ],
            'inline_images': []
        }

        mime_msg = self.provider._build_mime_message(message)

        # Check that message is multipart
        self.assertTrue(mime_msg.is_multipart())

    def test_build_mime_message_with_custom_headers(self):
        """Test building MIME message with custom headers"""
        message = {
            'message_id': 'test-004',
            'from_email': 'sender@example.com',
            'to': ['recipient@example.com'],
            'subject': 'Test',
            'html': '<p>Test</p>',
            'text': 'Test',
            'cc': [],
            'bcc': [],
            'headers': {
                'X-Campaign-ID': 'spring-2025',
                'X-Priority': '1'
            },
            'attachments': [],
            'inline_images': []
        }

        mime_msg = self.provider._build_mime_message(message)

        self.assertEqual(mime_msg['X-Campaign-ID'], 'spring-2025')
        self.assertEqual(mime_msg['X-Priority'], '1')

    @patch('smtplib.SMTP')
    def test_send_success(self, mock_smtp):
        """Test successful email send returns correct SendResult format"""
        mock_conn = MagicMock()
        mock_conn.sendmail.return_value = {}
        mock_smtp.return_value = mock_conn

        message = {
            'message_id': 'test-send-001',
            'from_email': 'sender@example.com',
            'from_name': 'Test',
            'to': ['recipient@example.com'],
            'subject': 'Test',
            'html': '<p>Test</p>',
            'text': 'Test',
            'cc': [],
            'bcc': [],
            'reply_to': None,
            'headers': {},
            'attachments': [],
            'inline_images': [],
            'return_path': 'sender@example.com',
            'tags': [],
            'metadata': {},
        }

        result = self.provider.send(message)

        self.assertTrue(result['accepted'])
        self.assertEqual(result['status'], 'sent')
        self.assertIsNotNone(result['provider_message_id'])
        self.assertIsNone(result['error'])

    @patch('smtplib.SMTP')
    def test_send_auth_failure(self, mock_smtp):
        """Test send with authentication failure returns correct SendResult"""
        import smtplib as _smtplib
        mock_conn = MagicMock()
        mock_conn.login.side_effect = _smtplib.SMTPAuthenticationError(535, b'Auth failed')
        mock_smtp.return_value = mock_conn

        message = {
            'message_id': 'test-send-002',
            'from_email': 'sender@example.com',
            'to': ['recipient@example.com'],
            'subject': 'Test',
            'html': '<p>Test</p>',
            'text': 'Test',
            'cc': [],
            'bcc': [],
            'headers': {},
            'attachments': [],
            'inline_images': [],
        }

        result = self.provider.send(message)

        self.assertFalse(result['accepted'])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Authentication failed', result['error'])
        self.assertEqual(result['details']['error_code'], 'auth_failed')


if __name__ == '__main__':
    unittest.main()
