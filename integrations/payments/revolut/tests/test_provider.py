"""Tests for Revolut payment provider."""
import hashlib
import hmac as hmac_mod
import json
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ..provider import RevolutProvider

SANDBOX_CREDENTIALS = {
    'secret_key': 'sk_test_abc123def456',
    'public_key': 'pk_test_abc123def456',
    'webhook_secret': 'whsec_test_secret_123',
    'environment': 'sandbox',
    'capture_mode': 'AUTOMATIC',
}


class TestRevolutProviderInit(TestCase):
    """Test provider initialization and credential validation."""

    def test_initialization(self):
        provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)
        self.assertEqual(provider.provider_key, 'revolut')
        self.assertEqual(provider.provider_name, 'Revolut')
        self.assertEqual(provider.credentials['environment'], 'sandbox')

    def test_production_environment(self):
        creds = dict(SANDBOX_CREDENTIALS, environment='production', secret_key='sk_live_abc123def456')
        provider = RevolutProvider(credentials=creds)
        self.assertIn('merchant.revolut.com', provider._get_base_url())

    def test_sandbox_environment(self):
        provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)
        self.assertIn('sandbox-merchant.revolut.com', provider._get_base_url())

    def test_missing_secret_key(self):
        creds = dict(SANDBOX_CREDENTIALS, secret_key='')
        with self.assertRaises(ValueError):
            RevolutProvider(credentials=creds)

    def test_invalid_secret_key_format(self):
        creds = dict(SANDBOX_CREDENTIALS, secret_key='invalid_key')
        with self.assertRaises(ValueError):
            RevolutProvider(credentials=creds)


class TestRevolutProviderProperties(TestCase):
    """Test provider properties."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    def test_capabilities(self):
        caps = self.provider.capabilities
        self.assertTrue(caps['charge'])
        self.assertTrue(caps['authorize'])
        self.assertTrue(caps['capture'])
        self.assertTrue(caps['void'])
        self.assertTrue(caps['refund'])
        self.assertTrue(caps['partial_refund'])
        self.assertTrue(caps['webhooks'])
        self.assertTrue(caps['multi_currency'])
        self.assertTrue(caps['hosted_checkout'])
        self.assertFalse(caps['recurring'])

    def test_supported_currencies(self):
        currencies = self.provider.supported_currencies
        self.assertIn('GBP', currencies)
        self.assertIn('EUR', currencies)
        self.assertIn('USD', currencies)
        self.assertGreaterEqual(len(currencies), 20)

    def test_supported_payment_methods(self):
        methods = self.provider.supported_payment_methods
        self.assertIn('card', methods)
        self.assertIn('digital_wallet', methods)
        self.assertIn('revolut_pay', methods)

    def test_supported_countries(self):
        countries = self.provider.supported_countries
        self.assertIn('GB', countries)
        self.assertIn('IE', countries)
        self.assertIn('US', countries)


class TestRevolutProviderCredentials(TestCase):
    """Test credential handling."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    def test_redact_credentials(self):
        redacted = self.provider.redact_credentials(SANDBOX_CREDENTIALS)
        self.assertNotEqual(redacted['secret_key'], SANDBOX_CREDENTIALS['secret_key'])
        self.assertIn('***', redacted['secret_key'])
        self.assertNotEqual(redacted['webhook_secret'], SANDBOX_CREDENTIALS['webhook_secret'])


class TestRevolutProviderConnection(TestCase):
    """Test connection testing."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    @patch('requests.request')
    def test_connection_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        result = self.provider.test_connection()
        self.assertTrue(result['success'])
        self.assertIn('sandbox', result['message'])

    @patch('requests.request')
    def test_connection_invalid_key(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])
        self.assertIn('Invalid', result['message'])


class TestRevolutProviderPayments(TestCase):
    """Test payment operations."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    @patch('requests.request')
    def test_charge_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'ord_123',
            'state': 'COMPLETED',
            'checkout_url': 'https://checkout.revolut.com/pay/ord_123',
        }
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.charge(
            amount=Decimal('29.99'),
            currency='GBP',
            payment_method={'type': 'card'},
            metadata={'order_id': 'ORD-001'},
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['transaction_id'], 'ord_123')
        self.assertEqual(result['status'], 'succeeded')

    @patch('requests.request')
    def test_charge_failure(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'message': 'Invalid currency', 'code': 'INVALID_CURRENCY'}
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.charge(
            amount=Decimal('29.99'),
            currency='INVALID',
            payment_method={'type': 'card'},
        )
        self.assertFalse(result['success'])

    @patch('requests.request')
    def test_authorize_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'ord_456',
            'state': 'PENDING',
            'checkout_url': 'https://checkout.revolut.com/pay/ord_456',
        }
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.authorize(
            amount=Decimal('50.00'),
            currency='EUR',
            payment_method={'type': 'card'},
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['authorization_id'], 'ord_456')

        # Verify MANUAL capture mode was sent
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['json']['capture_mode'], 'MANUAL')

    @patch('requests.request')
    def test_capture_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'ord_456',
            'state': 'COMPLETED',
            'order_amount': {'value': 5000},
            'currency': 'EUR',
        }
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.capture(authorization_id='ord_456')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'completed')

    @patch('requests.request')
    def test_void_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'ord_456', 'state': 'CANCELLED'}
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.void(authorization_id='ord_456')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'voided')

    @patch('requests.request')
    def test_refund_success(self, mock_request):
        # First call: GET order to get currency
        order_response = MagicMock()
        order_response.status_code = 200
        order_response.json.return_value = {'currency': 'GBP'}
        order_response.content = b'{}'

        # Second call: POST refund
        refund_response = MagicMock()
        refund_response.status_code = 200
        refund_response.json.return_value = {'id': 'ref_789', 'state': 'COMPLETED'}
        refund_response.content = b'{}'

        mock_request.side_effect = [order_response, refund_response]

        result = self.provider.refund(
            transaction_id='ord_123',
            amount=Decimal('10.00'),
            reason='Customer request',
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['refund_id'], 'ref_789')


class TestRevolutProviderWebhooks(TestCase):
    """Test webhook handling."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    def test_verify_valid_signature(self):
        payload = b'{"order_id": "ord_123"}'
        timestamp = '1700000000'
        payload_to_sign = f"v1.{timestamp}.{payload.decode('utf-8')}"
        expected_hmac = hmac_mod.new(
            b'whsec_test_secret_123',
            payload_to_sign.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        signature = f'v1.{expected_hmac}'

        result = self.provider.verify_webhook_signature(
            payload=payload, signature=signature, timestamp=timestamp
        )
        self.assertTrue(result)

    def test_verify_invalid_signature(self):
        result = self.provider.verify_webhook_signature(
            payload=b'{"order_id": "ord_123"}',
            signature='v1.invalid_signature',
            timestamp='1700000000',
        )
        self.assertFalse(result)

    def test_verify_no_secret_configured(self):
        creds = dict(SANDBOX_CREDENTIALS, webhook_secret='')
        provider = RevolutProvider(credentials=creds)
        result = provider.verify_webhook_signature(
            payload=b'{"order_id": "ord_123"}',
            signature='v1.anything',
        )
        self.assertTrue(result)

    def test_handle_order_completed(self):
        result = self.provider.handle_webhook(
            'ORDER_COMPLETED', {'order_id': 'ord_123'}
        )
        self.assertTrue(result['handled'])
        self.assertEqual(result['action'], 'payment_completed')
        self.assertEqual(result['status'], 'succeeded')

    def test_handle_order_authorised(self):
        result = self.provider.handle_webhook(
            'ORDER_AUTHORISED', {'order_id': 'ord_456'}
        )
        self.assertTrue(result['handled'])
        self.assertEqual(result['action'], 'payment_authorized')
        self.assertEqual(result['status'], 'authorized')

    def test_handle_order_failed(self):
        result = self.provider.handle_webhook(
            'ORDER_FAILED', {'order_id': 'ord_789', 'reason': 'insufficient_funds'}
        )
        self.assertTrue(result['handled'])
        self.assertEqual(result['action'], 'payment_failed')

    def test_handle_unknown_event(self):
        result = self.provider.handle_webhook(
            'UNKNOWN_EVENT', {'order_id': 'ord_000'}
        )
        self.assertFalse(result['handled'])


class TestRevolutProviderCheckout(TestCase):
    """Test checkout orchestration."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    @patch('requests.request')
    def test_create_payment_intent(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'ord_abc',
            'token': 'tok_xyz',
            'checkout_url': 'https://checkout.revolut.com/pay/ord_abc',
            'state': 'PENDING',
        }
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.create_payment_intent_for_checkout(
            amount=Decimal('49.99'),
            currency='GBP',
            return_url='https://shop.example.com/success',
            cancel_url='https://shop.example.com/cancel',
            customer_email='test@example.com',
            metadata={'order_id': 'ORD-100'},
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['provider_intent_id'], 'ord_abc')
        self.assertEqual(result['client_secret'], 'tok_xyz')
        self.assertIn('checkout_url', result)

    @patch('requests.request')
    def test_retrieve_payment_intent(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'ord_abc',
            'state': 'COMPLETED',
            'payments': [
                {
                    'payment_method': {
                        'type': 'card',
                        'card': {'card_last_four': '4242', 'card_brand': 'visa'},
                    }
                }
            ],
        }
        mock_response.content = b'{}'
        mock_request.return_value = mock_response

        result = self.provider.retrieve_payment_intent('ord_abc')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['payment_method_last4'], '4242')
        self.assertEqual(result['payment_method_brand'], 'visa')


class TestRevolutAmountConversion(TestCase):
    """Test amount conversion helpers."""

    def setUp(self):
        self.provider = RevolutProvider(credentials=SANDBOX_CREDENTIALS)

    def test_amount_to_minor_standard(self):
        self.assertEqual(self.provider._amount_to_minor(Decimal('29.99'), 'GBP'), 2999)
        self.assertEqual(self.provider._amount_to_minor(Decimal('100.00'), 'EUR'), 10000)

    def test_amount_to_minor_zero_decimal(self):
        self.assertEqual(self.provider._amount_to_minor(Decimal('1000'), 'JPY'), 1000)

    def test_amount_from_minor_standard(self):
        self.assertEqual(self.provider._amount_from_minor(2999, 'GBP'), Decimal('29.99'))
        self.assertEqual(self.provider._amount_from_minor(10000, 'EUR'), Decimal('100'))

    def test_amount_from_minor_zero_decimal(self):
        self.assertEqual(self.provider._amount_from_minor(1000, 'JPY'), Decimal('1000'))
