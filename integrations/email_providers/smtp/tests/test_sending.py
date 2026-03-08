"""
Integration tests for SMTP Email Provider

Tests actual email sending with real SMTP credentials.
Set environment variables to run these tests:
  - TEST_SMTP_HOST
  - TEST_SMTP_PORT
  - TEST_SMTP_USERNAME
  - TEST_SMTP_PASSWORD
  - TEST_SMTP_USE_TLS
  - TEST_SMTP_FROM_EMAIL
  - TEST_SMTP_TO_EMAIL
"""
import unittest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provider import SMTPProvider


@unittest.skipUnless(
    os.environ.get('TEST_SMTP_HOST'),
    "Requires TEST_SMTP_HOST and related environment variables"
)
class TestSMTPProviderIntegration(unittest.TestCase):
    """Integration tests with real SMTP server"""

    def setUp(self):
        """Set up with real test credentials from environment"""
        self.credentials = {
            'host': os.environ['TEST_SMTP_HOST'],
            'port': int(os.environ.get('TEST_SMTP_PORT', '587')),
            'username': os.environ['TEST_SMTP_USERNAME'],
            'password': os.environ['TEST_SMTP_PASSWORD'],
            'use_tls': os.environ.get('TEST_SMTP_USE_TLS', 'true').lower() == 'true',
            'use_ssl': os.environ.get('TEST_SMTP_USE_SSL', 'false').lower() == 'true',
            'timeout': int(os.environ.get('TEST_SMTP_TIMEOUT', '30'))
        }
        self.provider = SMTPProvider(self.credentials)

        self.from_email = os.environ.get('TEST_SMTP_FROM_EMAIL', self.credentials['username'])
        self.to_email = os.environ.get('TEST_SMTP_TO_EMAIL', self.credentials['username'])

    def test_live_healthcheck(self):
        """Test health check with real SMTP server"""
        result = self.provider.healthcheck()

        self.assertTrue(
            result['success'],
            f"Health check failed: {result.get('message')}"
        )
        self.assertIn('details', result)
        self.assertEqual(result['details']['smtp_host'], self.credentials['host'])

    def test_live_send_simple_email(self):
        """Test sending simple email via real SMTP server"""
        message = {
            'message_id': 'test_smtp_001',
            'from_email': self.from_email,
            'from_name': 'SMTP Test',
            'to': [self.to_email],
            'cc': [],
            'bcc': [],
            'subject': 'SMTP Integration Test - Simple Email',
            'html': '<p>This is a <strong>test email</strong> from SMTP integration tests.</p>',
            'text': 'This is a test email from SMTP integration tests.',
            'reply_to': None,
            'headers': {},
            'return_path': self.from_email,
            'attachments': [],
            'inline_images': [],
            'tags': [],
            'metadata': {}
        }

        result = self.provider.send(message)

        # Verify send succeeded
        self.assertTrue(result['accepted'], f"Send failed: {result.get('error')}")
        self.assertEqual(result['status'], 'sent')
        self.assertIsNone(result['error'])

        print(f"Email sent successfully")
        if result.get('provider_message_id'):
            print(f"  Message ID: {result['provider_message_id']}")

    def test_live_send_with_html_and_text(self):
        """Test sending email with both HTML and plain text"""
        message = {
            'message_id': 'test_smtp_002',
            'from_email': self.from_email,
            'from_name': 'SMTP Test',
            'to': [self.to_email],
            'cc': [],
            'bcc': [],
            'subject': 'SMTP Integration Test - HTML + Text',
            'html': '''
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <h1 style="color: #0066cc;">Test Email</h1>
                    <p>This email contains both HTML and plain text versions.</p>
                    <ul>
                        <li>HTML version with <strong>formatting</strong></li>
                        <li>Plain text <em>fallback</em></li>
                    </ul>
                </body>
                </html>
            ''',
            'text': '''
Test Email

This email contains both HTML and plain text versions.

- HTML version with formatting
- Plain text fallback
            ''',
            'reply_to': None,
            'headers': {},
            'return_path': self.from_email,
            'attachments': [],
            'inline_images': [],
            'tags': [],
            'metadata': {}
        }

        result = self.provider.send(message)

        self.assertTrue(result['accepted'], f"Send failed: {result.get('error')}")
        self.assertEqual(result['status'], 'sent')
        print(f"HTML + Text email sent successfully")

    def test_live_send_with_custom_headers(self):
        """Test sending email with custom headers"""
        message = {
            'message_id': 'test_smtp_003',
            'from_email': self.from_email,
            'from_name': 'SMTP Test',
            'to': [self.to_email],
            'cc': [],
            'bcc': [],
            'subject': 'SMTP Integration Test - Custom Headers',
            'html': '<p>This email includes custom headers.</p>',
            'text': 'This email includes custom headers.',
            'reply_to': self.from_email,
            'headers': {
                'X-Campaign-ID': 'test-campaign-001',
                'X-Test-Header': 'Integration Test',
                'X-Priority': '1'
            },
            'return_path': self.from_email,
            'attachments': [],
            'inline_images': [],
            'tags': ['integration-test'],
            'metadata': {'test': 'true', 'environment': 'testing'}
        }

        result = self.provider.send(message)

        self.assertTrue(result['accepted'], f"Send failed: {result.get('error')}")
        self.assertEqual(result['status'], 'sent')
        print(f"Email with custom headers sent successfully")

    def test_live_send_with_cc_bcc(self):
        """Test sending email with CC and BCC"""
        message = {
            'message_id': 'test_smtp_004',
            'from_email': self.from_email,
            'from_name': 'SMTP Test',
            'to': [self.to_email],
            'cc': [self.to_email],  # CC to same address for testing
            'bcc': [self.to_email],  # BCC to same address for testing
            'subject': 'SMTP Integration Test - CC and BCC',
            'html': '<p>This email tests CC and BCC functionality.</p>',
            'text': 'This email tests CC and BCC functionality.',
            'reply_to': None,
            'headers': {},
            'return_path': self.from_email,
            'attachments': [],
            'inline_images': [],
            'tags': [],
            'metadata': {}
        }

        result = self.provider.send(message)

        self.assertTrue(result['accepted'], f"Send failed: {result.get('error')}")
        self.assertEqual(result['status'], 'sent')
        print(f"Email with CC and BCC sent successfully")

    @unittest.skipUnless(
        os.environ.get('TEST_SMTP_ATTACHMENT_PATH'),
        "Requires TEST_SMTP_ATTACHMENT_PATH environment variable"
    )
    def test_live_send_with_attachment(self):
        """Test sending email with file attachment"""
        # Read attachment from file
        attachment_path = os.environ['TEST_SMTP_ATTACHMENT_PATH']
        with open(attachment_path, 'rb') as f:
            attachment_content = f.read()

        attachment_filename = os.path.basename(attachment_path)

        message = {
            'message_id': 'test_smtp_005',
            'from_email': self.from_email,
            'from_name': 'SMTP Test',
            'to': [self.to_email],
            'cc': [],
            'bcc': [],
            'subject': 'SMTP Integration Test - Attachment',
            'html': f'<p>This email includes an attachment: <strong>{attachment_filename}</strong></p>',
            'text': f'This email includes an attachment: {attachment_filename}',
            'reply_to': None,
            'headers': {},
            'return_path': self.from_email,
            'attachments': [
                {
                    'filename': attachment_filename,
                    'content': attachment_content,
                    'content_type': 'application/octet-stream'
                }
            ],
            'inline_images': [],
            'tags': [],
            'metadata': {}
        }

        result = self.provider.send(message)

        self.assertTrue(result['accepted'], f"Send failed: {result.get('error')}")
        self.assertEqual(result['status'], 'sent')
        print(f"Email with attachment sent successfully: {attachment_filename}")


if __name__ == '__main__':
    # Print test configuration
    if os.environ.get('TEST_SMTP_HOST'):
        print("=" * 60)
        print("SMTP Integration Test Configuration")
        print("=" * 60)
        print(f"Host: {os.environ.get('TEST_SMTP_HOST')}")
        print(f"Port: {os.environ.get('TEST_SMTP_PORT', '587')}")
        print(f"Username: {os.environ.get('TEST_SMTP_USERNAME')}")
        print(f"Use TLS: {os.environ.get('TEST_SMTP_USE_TLS', 'true')}")
        print(f"From: {os.environ.get('TEST_SMTP_FROM_EMAIL', os.environ.get('TEST_SMTP_USERNAME'))}")
        print(f"To: {os.environ.get('TEST_SMTP_TO_EMAIL', os.environ.get('TEST_SMTP_USERNAME'))}")
        print("=" * 60)
        print()

    unittest.main()
