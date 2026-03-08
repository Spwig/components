"""
Tests for AirWallex Payment Provider
"""
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from provider import AirwallexProvider


class TestAirwallexProvider(unittest.TestCase):
    """Test cases for AirWallex provider."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'client_id': 'test_client_id',
            'api_key': 'test_api_key',
            'environment': 'demo',
            'webhook_secret': 'test_webhook_secret',
            'auto_capture': True,
            'payment_descriptor': 'TEST STORE'
        }
        self.provider = AirwallexProvider(self.config)

    def test_initialization(self):
        """Test provider initialization."""
        self.assertEqual(self.provider.client_id, 'test_client_id')
        self.assertEqual(self.provider.api_key, 'test_api_key')
        self.assertEqual(self.provider.environment, 'demo')
        self.assertEqual(self.provider.api_base, AirwallexProvider.DEMO_API_BASE)
        self.assertTrue(self.provider.auto_capture)

    def test_production_environment(self):
        """Test production environment configuration."""
        prod_config = self.config.copy()
        prod_config['environment'] = 'production'
        provider = AirwallexProvider(prod_config)

        self.assertEqual(provider.api_base, AirwallexProvider.PRODUCTION_API_BASE)

    @patch('provider.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful access token retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {'token': 'test_access_token'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        token = self.provider._get_access_token()

        self.assertEqual(token, 'test_access_token')
        mock_post.assert_called_once()

        # Verify headers
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        self.assertEqual(headers['x-client-id'], 'test_client_id')
        self.assertEqual(headers['x-api-key'], 'test_api_key')

    @patch('provider.requests.post')
    def test_get_access_token_cached(self, mock_post):
        """Test that access token is cached."""
        mock_response = Mock()
        mock_response.json.return_value = {'token': 'test_access_token'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # First call
        token1 = self.provider._get_access_token()

        # Second call should use cache
        token2 = self.provider._get_access_token()

        self.assertEqual(token1, token2)
        # Should only be called once due to caching
        self.assertEqual(mock_post.call_count, 1)

    @patch.object(AirwallexProvider, '_make_request')
    @patch.object(AirwallexProvider, '_get_access_token')
    def test_test_connection_success(self, mock_token, mock_request):
        """Test successful connection test using /pa/ scoped endpoint."""
        mock_token.return_value = 'test_token'
        mock_request.return_value = {
            'items': [
                {'name': 'card', 'active': True},
                {'name': 'googlepay', 'active': True},
            ]
        }

        result = self.provider.test_connection()

        self.assertTrue(result['success'])
        self.assertIn('Successfully connected', result['message'])
        self.assertEqual(result['details']['environment'], 'demo')
        self.assertEqual(result['details']['payment_methods_available'], 2)

        # Verify it calls the /pa/ scoped endpoint
        mock_request.assert_called_once_with(
            method='GET',
            endpoint='/pa/config/payment_method_types'
        )

    @patch.object(AirwallexProvider, '_make_request')
    @patch.object(AirwallexProvider, '_get_access_token')
    def test_test_connection_failure(self, mock_token, mock_request):
        """Test failed connection test."""
        mock_token.return_value = 'test_token'
        mock_request.side_effect = Exception('Insufficient permissions')

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Connection test failed', result['message'])

    @patch.object(AirwallexProvider, '_make_request')
    def test_create_payment_success(self, mock_request):
        """Test successful payment creation."""
        mock_request.return_value = {
            'id': 'int_123456',
            'client_secret': 'secret_abc',
            'status': 'REQUIRES_PAYMENT_METHOD',
            'amount': 100.00,
            'currency': 'USD'
        }

        result = self.provider.create_payment(
            amount=Decimal('100.00'),
            currency='USD',
            order_id='order_123',
            customer_email='test@example.com',
            description='Test payment'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['payment_intent_id'], 'int_123456')
        self.assertEqual(result['client_secret'], 'secret_abc')
        self.assertEqual(result['currency'], 'USD')

        # Verify request was made correctly
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['endpoint'], '/pa/payment_intents/create')
        self.assertEqual(call_args[1]['data']['amount'], 100.00)
        self.assertEqual(call_args[1]['data']['currency'], 'USD')

    @patch.object(AirwallexProvider, '_make_request')
    def test_create_payment_failure(self, mock_request):
        """Test payment creation failure."""
        mock_request.side_effect = Exception('API Error')

        result = self.provider.create_payment(
            amount=Decimal('100.00'),
            currency='USD',
            order_id='order_123'
        )

        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch.object(AirwallexProvider, '_make_request')
    def test_capture_payment_success(self, mock_request):
        """Test successful payment capture."""
        mock_request.return_value = {
            'id': 'int_123456',
            'status': 'SUCCEEDED',
            'amount': 100.00
        }

        result = self.provider.capture_payment('int_123456')

        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(result['amount_captured'], Decimal('100.00'))

    @patch.object(AirwallexProvider, '_make_request')
    def test_refund_payment_success(self, mock_request):
        """Test successful refund creation."""
        mock_request.return_value = {
            'id': 'ref_123456',
            'payment_intent_id': 'int_123456',
            'status': 'RECEIVED',
            'amount': 50.00,
            'currency': 'USD'
        }

        result = self.provider.refund_payment(
            payment_intent_id='int_123456',
            amount=Decimal('50.00'),
            reason='Customer request'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['refund_id'], 'ref_123456')
        self.assertEqual(result['amount'], Decimal('50.00'))

    @patch.object(AirwallexProvider, '_make_request')
    def test_get_payment_status_success(self, mock_request):
        """Test successful payment status retrieval."""
        mock_request.return_value = {
            'id': 'int_123456',
            'status': 'SUCCEEDED',
            'amount': 100.00,
            'currency': 'USD'
        }

        result = self.provider.get_payment_status('int_123456')

        self.assertTrue(result['success'])
        self.assertEqual(result['payment_intent_id'], 'int_123456')
        self.assertEqual(result['status'], 'SUCCEEDED')

    def test_verify_webhook_valid_signature(self):
        """Test webhook signature verification with valid signature."""
        import hmac
        import hashlib

        timestamp = '1234567890'
        payload = b'{"name": "payment_intent.succeeded", "data": {}}'

        # Create valid signature
        signed_payload = f"{timestamp}{payload.decode('utf-8')}"
        signature = hmac.new(
            key=self.config['webhook_secret'].encode('utf-8'),
            msg=signed_payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        is_valid = self.provider.verify_webhook(payload, timestamp, signature)
        self.assertTrue(is_valid)

    def test_verify_webhook_invalid_signature(self):
        """Test webhook signature verification with invalid signature."""
        timestamp = '1234567890'
        payload = b'{"name": "payment_intent.succeeded", "data": {}}'
        invalid_signature = 'invalid_signature_hash'

        is_valid = self.provider.verify_webhook(payload, timestamp, invalid_signature)
        self.assertFalse(is_valid)

    def test_verify_webhook_no_secret(self):
        """Test webhook verification when no secret is configured."""
        provider = AirwallexProvider({
            'client_id': 'test',
            'api_key': 'test',
            'environment': 'demo'
        })

        # Should return True when no secret configured
        is_valid = provider.verify_webhook(b'{}', '123', 'any_signature')
        self.assertTrue(is_valid)

    def test_process_webhook_payment_succeeded(self):
        """Test processing payment succeeded webhook."""
        event_data = {
            'name': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'int_123456',
                    'amount': 100.00,
                    'currency': 'USD',
                    'merchant_order_id': 'order_123'
                }
            }
        }

        result = self.provider.process_webhook(event_data)

        self.assertEqual(result['event_type'], 'payment.succeeded')
        self.assertTrue(result['handled'])
        self.assertEqual(result['payment_intent_id'], 'int_123456')
        self.assertEqual(result['amount'], Decimal('100.00'))

    def test_process_webhook_payment_failed(self):
        """Test processing payment failed webhook."""
        event_data = {
            'name': 'payment_intent.failed',
            'data': {
                'object': {
                    'id': 'int_123456',
                    'merchant_order_id': 'order_123',
                    'latest_payment_error': {'message': 'Card declined'}
                }
            }
        }

        result = self.provider.process_webhook(event_data)

        self.assertEqual(result['event_type'], 'payment.failed')
        self.assertTrue(result['handled'])
        self.assertEqual(result['status'], 'failed')

    def test_process_webhook_refund_settled(self):
        """Test processing refund settled webhook."""
        event_data = {
            'name': 'refund.settled',
            'data': {
                'object': {
                    'id': 'ref_123456',
                    'payment_intent_id': 'int_123456',
                    'amount': 50.00,
                    'currency': 'USD',
                    'status': 'SETTLED'
                }
            }
        }

        result = self.provider.process_webhook(event_data)

        self.assertEqual(result['event_type'], 'refund_completed')
        self.assertTrue(result['handled'])
        self.assertEqual(result['refund_id'], 'ref_123456')

    def test_process_webhook_unknown_event(self):
        """Test processing unknown webhook event."""
        event_data = {
            'name': 'unknown.event',
            'data': {}
        }

        result = self.provider.process_webhook(event_data)

        self.assertEqual(result['event_type'], 'unknown.event')
        self.assertFalse(result['handled'])

    def test_get_supported_currencies(self):
        """Test getting supported currencies."""
        currencies = self.provider.get_supported_currencies()

        self.assertIsInstance(currencies, list)
        self.assertIn('USD', currencies)
        self.assertIn('EUR', currencies)
        self.assertIn('GBP', currencies)

    def test_get_capabilities(self):
        """Test getting provider capabilities."""
        capabilities = self.provider.get_capabilities()

        self.assertTrue(capabilities['capture'])
        self.assertTrue(capabilities['refund'])
        self.assertTrue(capabilities['webhooks'])
        self.assertTrue(capabilities['3d_secure'])
        self.assertIn('card', capabilities['payment_methods'])


if __name__ == '__main__':
    unittest.main()
