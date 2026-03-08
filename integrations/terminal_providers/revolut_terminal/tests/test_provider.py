"""Tests for Revolut Terminal provider."""
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ..provider import RevolutTerminalProvider

SANDBOX_CREDENTIALS = {
    'secret_key': 'sk_test_abc123def456',
}

SANDBOX_CONFIG = {
    'environment': 'sandbox',
    'location_id': 'loc_test_123',
}


class TestRevolutTerminalInit(TestCase):
    """Test provider initialization."""

    def test_initialization(self):
        provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )
        self.assertEqual(provider.provider_key, 'revolut_terminal')
        self.assertEqual(provider.provider_name, 'Revolut Terminal')
        self.assertEqual(provider.integration_mode, 'cloud')

    def test_sandbox_url(self):
        provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )
        self.assertIn('sandbox-merchant.revolut.com', provider._get_base_url())

    def test_production_url(self):
        provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS,
            config={'environment': 'production', 'location_id': 'loc_123'},
        )
        self.assertIn('merchant.revolut.com', provider._get_base_url())

    def test_missing_secret_key(self):
        with self.assertRaises(ValueError):
            RevolutTerminalProvider(
                credentials={'secret_key': ''}, config=SANDBOX_CONFIG
            )


class TestRevolutTerminalConnection(TestCase):
    """Test connection testing."""

    def setUp(self):
        self.provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )

    @patch('requests.get')
    def test_connection_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertTrue(result['success'])

    @patch('requests.get')
    def test_connection_invalid_key(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])
        self.assertIn('Invalid', result['message'])


class TestRevolutTerminalReaders(TestCase):
    """Test reader discovery."""

    def setUp(self):
        self.provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )

    @patch('requests.get')
    def test_list_readers_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 'term_001',
                'name': 'Counter Terminal',
                'type': 'revolut_terminal',
                'serial_number': 'SN12345',
                'status': 'ONLINE',
                'location_id': 'loc_test_123',
            },
            {
                'id': 'term_002',
                'name': 'Mobile Reader',
                'type': 'revolut_reader',
                'serial_number': 'SN67890',
                'status': 'OFFLINE',
                'location_id': 'loc_test_123',
            },
        ]
        mock_get.return_value = mock_response

        result = self.provider.list_readers()
        self.assertTrue(result['success'])
        self.assertEqual(len(result['readers']), 2)
        self.assertEqual(result['readers'][0]['id'], 'term_001')
        self.assertEqual(result['readers'][0]['status'], 'online')
        self.assertEqual(result['readers'][1]['status'], 'offline')

    @patch('requests.get')
    def test_list_readers_empty(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = self.provider.list_readers()
        self.assertTrue(result['success'])
        self.assertEqual(len(result['readers']), 0)


class TestRevolutTerminalPayments(TestCase):
    """Test cloud payment operations."""

    def setUp(self):
        self.provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )

    @patch('requests.post')
    def test_initiate_payment_success(self, mock_post):
        # Order creation response
        order_response = MagicMock()
        order_response.status_code = 201
        order_response.json.return_value = {'id': 'ord_t001', 'state': 'PENDING'}
        order_response.content = b'{}'

        # Payment push response
        payment_response = MagicMock()
        payment_response.status_code = 201
        payment_response.json.return_value = {'id': 'pay_001'}
        payment_response.content = b'{}'

        mock_post.side_effect = [order_response, payment_response]

        result = self.provider.initiate_cloud_payment(
            amount=Decimal('25.50'),
            currency='GBP',
            reader_id='term_001',
            metadata={'order_reference': 'POS-001'},
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['transaction_id'], 'ord_t001')
        self.assertEqual(result['status'], 'pending')

    @patch('requests.post')
    def test_initiate_payment_order_fail(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'message': 'Invalid currency'}
        mock_response.content = b'{}'
        mock_post.return_value = mock_response

        result = self.provider.initiate_cloud_payment(
            amount=Decimal('25.50'),
            currency='INVALID',
            reader_id='term_001',
        )
        self.assertFalse(result['success'])

    @patch('requests.get')
    def test_check_status_completed(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'ord_t001',
            'state': 'COMPLETED',
            'order_amount': {'value': 2550, 'currency': 'GBP'},
            'currency': 'GBP',
            'payments': [
                {
                    'payment_method': {
                        'type': 'card',
                        'card': {'card_brand': 'Visa', 'card_last_four': '1234'},
                    }
                }
            ],
        }
        mock_get.return_value = mock_response

        result = self.provider.check_payment_status('ord_t001')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(result['card_brand'], 'visa')
        self.assertEqual(result['last4'], '1234')
        self.assertEqual(result['amount'], Decimal('25.50'))

    @patch('requests.get')
    def test_check_status_pending(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'ord_t001', 'state': 'PENDING'}
        mock_get.return_value = mock_response

        result = self.provider.check_payment_status('ord_t001')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'pending')

    @patch('requests.get')
    def test_check_status_cancelled(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'ord_t001',
            'state': 'CANCELLED',
            'reason': 'Customer cancelled',
        }
        mock_get.return_value = mock_response

        result = self.provider.check_payment_status('ord_t001')
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'canceled')

    @patch('requests.post')
    def test_cancel_payment_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'ord_t001', 'state': 'CANCELLED'}
        mock_response.content = b'{}'
        mock_post.return_value = mock_response

        result = self.provider.cancel_cloud_payment('ord_t001')
        self.assertTrue(result['success'])


class TestRevolutTerminalRefunds(TestCase):
    """Test refund operations."""

    def setUp(self):
        self.provider = RevolutTerminalProvider(
            credentials=SANDBOX_CREDENTIALS, config=SANDBOX_CONFIG
        )

    @patch('requests.post')
    def test_full_refund(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'ref_001'}
        mock_response.content = b'{}'
        mock_post.return_value = mock_response

        result = self.provider.refund_payment('ord_t001')
        self.assertTrue(result['success'])
        self.assertEqual(result['refund_id'], 'ref_001')

    @patch('requests.post')
    @patch('requests.get')
    def test_partial_refund(self, mock_get, mock_post):
        # GET order to get currency
        order_response = MagicMock()
        order_response.status_code = 200
        order_response.json.return_value = {'currency': 'GBP'}
        mock_get.return_value = order_response

        # POST refund
        refund_response = MagicMock()
        refund_response.status_code = 200
        refund_response.json.return_value = {'id': 'ref_002'}
        refund_response.content = b'{}'
        mock_post.return_value = refund_response

        result = self.provider.refund_payment('ord_t001', amount=Decimal('10.00'))
        self.assertTrue(result['success'])
