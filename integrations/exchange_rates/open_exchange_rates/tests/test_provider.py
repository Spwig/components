"""
Unit tests for Open Exchange Rates provider
"""
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider import OpenExchangeRatesProvider


class TestOpenExchangeRatesProvider(unittest.TestCase):
    """Test Open Exchange Rates provider implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.credentials = {
            'app_id': 'abc123def456789012345678901234567'
        }
        self.provider = OpenExchangeRatesProvider(self.credentials)

    def test_initialization(self):
        """Test provider initialization"""
        self.assertEqual(self.provider.provider_key, 'open_exchange_rates')
        self.assertEqual(self.provider.provider_name, 'Open Exchange Rates')
        self.assertEqual(self.provider.app_id, 'abc123def456789012345678901234567')

    def test_initialization_without_app_id(self):
        """Test initialization fails without App ID"""
        with self.assertRaises(ValueError) as cm:
            OpenExchangeRatesProvider({})
        self.assertIn("App ID is required", str(cm.exception))

    def test_initialization_with_short_app_id(self):
        """Test initialization fails with short App ID"""
        with self.assertRaises(ValueError) as cm:
            OpenExchangeRatesProvider({'app_id': 'short'})
        self.assertIn("invalid", str(cm.exception).lower())

    def test_capabilities(self):
        """Test provider capabilities"""
        capabilities = self.provider.capabilities
        self.assertTrue(capabilities['live_rates'])
        self.assertFalse(capabilities['historical'])
        self.assertFalse(capabilities['crypto'])
        self.assertFalse(capabilities['base_currency_selection'])

    def test_credential_schema(self):
        """Test credential schema"""
        schema = self.provider.credential_schema
        self.assertIn('app_id', schema)
        self.assertTrue(schema['app_id']['required'])
        self.assertEqual(schema['app_id']['type'], 'text')

    def test_validate_credentials_success(self):
        """Test credential validation succeeds with valid credentials"""
        try:
            self.provider.validate_credentials(self.credentials)
        except ValueError:
            self.fail("validate_credentials raised ValueError unexpectedly")

    def test_validate_credentials_missing_app_id(self):
        """Test credential validation fails without App ID"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({})
        self.assertIn("App ID is required", str(cm.exception))

    def test_validate_credentials_short_app_id(self):
        """Test credential validation fails with short App ID"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({'app_id': 'abc'})
        self.assertIn("invalid", str(cm.exception).lower())

    def test_validate_credentials_non_alphanumeric(self):
        """Test credential validation fails with non-alphanumeric characters"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({'app_id': 'abc-123-def-456'})
        self.assertIn("alphanumeric", str(cm.exception).lower())

    def test_redact_credentials(self):
        """Test credential redaction"""
        redacted = self.provider.redact_credentials(self.credentials)
        self.assertEqual(redacted['app_id'], 'abc***567')
        self.assertNotEqual(redacted['app_id'], self.credentials['app_id'])

    def test_redact_credentials_short_app_id(self):
        """Test credential redaction with short App ID"""
        short_creds = {'app_id': 'abc'}
        redacted = self.provider.redact_credentials(short_creds)
        self.assertEqual(redacted['app_id'], '***')

    @patch('requests.get')
    def test_connection_success(self, mock_get):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'USD': 'United States Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound'
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertTrue(result['success'])
        self.assertIn('Successfully connected', result['message'])
        self.assertEqual(result['details']['currency_count'], 3)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_connection_invalid_app_id(self, mock_get):
        """Test connection fails with invalid App ID"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Invalid App ID'
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Invalid App ID', result['message'])
        self.assertEqual(result['details']['status_code'], 401)

    @patch('requests.get')
    def test_connection_rate_limited(self, mock_get):
        """Test connection handles rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = 'Rate limit exceeded'
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Rate limit', result['message'])
        self.assertEqual(result['details']['status_code'], 429)

    @patch('requests.get')
    def test_connection_timeout(self, mock_get):
        """Test connection handles timeout"""
        import requests
        mock_get.side_effect = requests.Timeout()

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('timeout', result['message'].lower())

    @patch('requests.get')
    def test_get_exchange_rate_success_usd_base(self, mock_get):
        """Test successful rate fetching with USD base"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'timestamp': 1234567890,
            'base': 'USD',
            'rates': {
                'EUR': 0.85,
                'GBP': 0.73,
                'JPY': 110.5
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])

        self.assertEqual(len(rates), 2)
        self.assertEqual(rates['EUR'], Decimal('0.85'))
        self.assertEqual(rates['GBP'], Decimal('0.73'))
        self.assertNotIn('JPY', rates)  # Not requested

    @patch('requests.get')
    def test_get_exchange_rate_success_non_usd_base(self, mock_get):
        """Test successful rate fetching with non-USD base (EUR)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'timestamp': 1234567890,
            'base': 'USD',
            'rates': {
                'EUR': 0.85,  # USD to EUR
                'GBP': 0.73   # USD to GBP
            }
        }
        mock_get.return_value = mock_response

        # Request EUR to GBP
        # Expected: 0.73 / 0.85 = 0.8588...
        rates = self.provider.get_exchange_rate('EUR', ['GBP'])

        self.assertEqual(len(rates), 1)
        self.assertIn('GBP', rates)
        # Check it's approximately 0.859
        self.assertAlmostEqual(float(rates['GBP']), 0.859, places=2)

    @patch('requests.get')
    def test_get_exchange_rate_api_error(self, mock_get):
        """Test rate fetching handles API errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal server error'
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('USD', ['EUR'])
        self.assertIn('API request failed', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_invalid_response(self, mock_get):
        """Test rate fetching handles invalid response format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'invalid': 'response'}
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('USD', ['EUR'])
        self.assertIn('Invalid API response', str(cm.exception))

    def test_get_exchange_rate_empty_targets(self):
        """Test rate fetching with empty target list"""
        rates = self.provider.get_exchange_rate('USD', [])
        self.assertEqual(rates, {})

    def test_get_exchange_rate_base_in_targets(self):
        """Test rate fetching filters out base currency from targets"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'base': 'USD',
                'rates': {'EUR': 0.85}
            }
            mock_get.return_value = mock_response

            # USD in targets should be filtered out
            rates = self.provider.get_exchange_rate('USD', ['USD', 'EUR'])
            self.assertEqual(len(rates), 1)
            self.assertIn('EUR', rates)
            self.assertNotIn('USD', rates)

    @patch('requests.get')
    def test_get_supported_currencies_success(self, mock_get):
        """Test getting supported currencies"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'USD': 'United States Dollar',
            'EUR': 'Euro',
            'GBP': 'British Pound'
        }
        mock_get.return_value = mock_response

        currencies = self.provider.get_supported_currencies()

        self.assertIsInstance(currencies, list)
        self.assertEqual(len(currencies), 3)
        self.assertIn('USD', currencies)
        self.assertIn('EUR', currencies)
        self.assertIn('GBP', currencies)

    @patch('requests.get')
    def test_get_supported_currencies_fallback(self, mock_get):
        """Test fallback when currencies API fails"""
        mock_get.side_effect = Exception("API error")

        currencies = self.provider.get_supported_currencies()

        self.assertIsInstance(currencies, list)
        self.assertGreater(len(currencies), 0)
        self.assertIn('USD', currencies)
        self.assertIn('EUR', currencies)

    def test_get_rate_limits(self):
        """Test getting rate limits"""
        limits = self.provider.get_rate_limits()

        self.assertIn('requests_per_month', limits)
        self.assertEqual(limits['requests_per_month'], 1000)
        self.assertIsNone(limits['requests_per_minute'])


if __name__ == '__main__':
    unittest.main()
