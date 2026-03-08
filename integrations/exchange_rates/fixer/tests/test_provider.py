"""
Unit tests for Fixer.io provider
"""
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider import FixerProvider


class TestFixerProvider(unittest.TestCase):
    """Test Fixer.io provider implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.credentials = {
            'access_key': 'abc123def456789012345678901234567'
        }
        self.provider = FixerProvider(self.credentials)

    def test_initialization(self):
        """Test provider initialization"""
        self.assertEqual(self.provider.provider_key, 'fixer')
        self.assertEqual(self.provider.provider_name, 'Fixer.io')
        self.assertEqual(self.provider.access_key, 'abc123def456789012345678901234567')

    def test_initialization_without_access_key(self):
        """Test initialization fails without Access Key"""
        with self.assertRaises(ValueError) as cm:
            FixerProvider({})
        self.assertIn("Access Key is required", str(cm.exception))

    def test_initialization_with_short_access_key(self):
        """Test initialization fails with short Access Key"""
        with self.assertRaises(ValueError) as cm:
            FixerProvider({'access_key': 'short'})
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
        self.assertIn('access_key', schema)
        self.assertTrue(schema['access_key']['required'])
        self.assertEqual(schema['access_key']['type'], 'text')

    def test_validate_credentials_success(self):
        """Test credential validation succeeds with valid credentials"""
        try:
            self.provider.validate_credentials(self.credentials)
        except ValueError:
            self.fail("validate_credentials raised ValueError unexpectedly")

    def test_validate_credentials_missing_access_key(self):
        """Test credential validation fails without Access Key"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({})
        self.assertIn("Access Key is required", str(cm.exception))

    def test_validate_credentials_short_access_key(self):
        """Test credential validation fails with short Access Key"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({'access_key': 'abc'})
        self.assertIn("invalid", str(cm.exception).lower())

    def test_validate_credentials_non_alphanumeric(self):
        """Test credential validation fails with non-alphanumeric characters"""
        with self.assertRaises(ValueError) as cm:
            self.provider.validate_credentials({'access_key': 'abc-123-def-456'})
        self.assertIn("alphanumeric", str(cm.exception).lower())

    def test_redact_credentials(self):
        """Test credential redaction"""
        redacted = self.provider.redact_credentials(self.credentials)
        self.assertEqual(redacted['access_key'], 'abc***567')
        self.assertNotEqual(redacted['access_key'], self.credentials['access_key'])

    def test_redact_credentials_short_access_key(self):
        """Test credential redaction with short Access Key"""
        short_creds = {'access_key': 'abc'}
        redacted = self.provider.redact_credentials(short_creds)
        self.assertEqual(redacted['access_key'], '***')

    @patch('requests.get')
    def test_connection_success(self, mock_get):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'symbols': {
                'USD': 'United States Dollar',
                'EUR': 'Euro',
                'GBP': 'British Pound'
            }
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertTrue(result['success'])
        self.assertIn('Successfully connected', result['message'])
        self.assertEqual(result['details']['currency_count'], 3)
        self.assertEqual(result['details']['base_currency'], 'EUR')
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_connection_api_error_response(self, mock_get):
        """Test connection handles API error response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 101,
                'info': 'Invalid Access Key'
            }
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Invalid Access Key', result['message'])
        self.assertEqual(result['details']['error_code'], 101)

    @patch('requests.get')
    def test_connection_invalid_access_key(self, mock_get):
        """Test connection fails with invalid Access Key (401)"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 101,
                'info': 'Invalid Access Key provided'
            }
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Invalid', result['message'])
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
    def test_get_exchange_rate_success_eur_base(self, mock_get):
        """Test successful rate fetching with EUR base"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'timestamp': 1234567890,
            'base': 'EUR',
            'rates': {
                'USD': 1.18,
                'GBP': 0.86,
                'JPY': 129.5
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('EUR', ['USD', 'GBP'])

        self.assertEqual(len(rates), 2)
        self.assertEqual(rates['USD'], Decimal('1.18'))
        self.assertEqual(rates['GBP'], Decimal('0.86'))
        self.assertNotIn('JPY', rates)  # Not requested

    @patch('requests.get')
    def test_get_exchange_rate_success_non_eur_base(self, mock_get):
        """Test successful rate fetching with non-EUR base (GBP)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'timestamp': 1234567890,
            'base': 'EUR',
            'rates': {
                'GBP': 0.86,  # EUR to GBP
                'USD': 1.18   # EUR to USD
            }
        }
        mock_get.return_value = mock_response

        # Request GBP to USD
        # Expected: 1.18 / 0.86 = 1.3720...
        rates = self.provider.get_exchange_rate('GBP', ['USD'])

        self.assertEqual(len(rates), 1)
        self.assertIn('USD', rates)
        # Check it's approximately 1.372
        self.assertAlmostEqual(float(rates['USD']), 1.372, places=2)

    @patch('requests.get')
    def test_get_exchange_rate_api_error_response(self, mock_get):
        """Test rate fetching handles API error response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 104,
                'info': 'Rate limit reached'
            }
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('EUR', ['USD'])
        self.assertIn('Rate limit', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_invalid_access_key_error(self, mock_get):
        """Test rate fetching handles invalid access key error"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 101,
                'info': 'Invalid Access Key'
            }
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('EUR', ['USD'])
        self.assertIn('Invalid Access Key', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_http_401_error(self, mock_get):
        """Test rate fetching handles HTTP 401 error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_response.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('EUR', ['USD'])
        self.assertIn('Invalid Access Key', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_http_500_error(self, mock_get):
        """Test rate fetching handles HTTP 500 error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal server error'
        mock_response.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('EUR', ['USD'])
        self.assertIn('API request failed', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_missing_rates_field(self, mock_get):
        """Test rate fetching handles missing rates field"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'timestamp': 1234567890
            # Missing 'rates' field
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('EUR', ['USD'])
        self.assertIn('missing', str(cm.exception).lower())

    def test_get_exchange_rate_empty_targets(self):
        """Test rate fetching with empty target list"""
        rates = self.provider.get_exchange_rate('EUR', [])
        self.assertEqual(rates, {})

    def test_get_exchange_rate_base_in_targets(self):
        """Test rate fetching filters out base currency from targets"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'success': True,
                'base': 'EUR',
                'rates': {'USD': 1.18}
            }
            mock_get.return_value = mock_response

            # EUR in targets should be filtered out
            rates = self.provider.get_exchange_rate('EUR', ['EUR', 'USD'])
            self.assertEqual(len(rates), 1)
            self.assertIn('USD', rates)
            self.assertNotIn('EUR', rates)

    @patch('requests.get')
    def test_get_exchange_rate_invalid_rate_value(self, mock_get):
        """Test rate fetching handles invalid rate values"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'base': 'EUR',
            'rates': {
                'USD': -1.18,  # Negative rate (invalid)
                'GBP': 0.86    # Valid rate
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('EUR', ['USD', 'GBP'])

        # USD should be filtered out due to negative value
        self.assertEqual(len(rates), 1)
        self.assertNotIn('USD', rates)
        self.assertIn('GBP', rates)

    @patch('requests.get')
    def test_get_exchange_rate_suspiciously_high_rate(self, mock_get):
        """Test rate fetching handles suspiciously high rates"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'base': 'EUR',
            'rates': {
                'USD': 2000000,  # Suspiciously high
                'GBP': 0.86      # Valid rate
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('EUR', ['USD', 'GBP'])

        # USD should be filtered out due to high value
        self.assertEqual(len(rates), 1)
        self.assertNotIn('USD', rates)
        self.assertIn('GBP', rates)

    @patch('requests.get')
    def test_get_supported_currencies_success(self, mock_get):
        """Test getting supported currencies"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'symbols': {
                'USD': 'United States Dollar',
                'EUR': 'Euro',
                'GBP': 'British Pound'
            }
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
        self.assertIn('EUR', currencies)
        self.assertIn('USD', currencies)

    def test_get_rate_limits(self):
        """Test getting rate limits"""
        limits = self.provider.get_rate_limits()

        self.assertIn('requests_per_month', limits)
        self.assertEqual(limits['requests_per_month'], 100)
        self.assertIsNone(limits['requests_per_minute'])

    @patch('requests.get')
    def test_get_rate_method(self, mock_get):
        """Test get_rate method (base class abstract method)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'base': 'EUR',
            'rates': {'USD': 1.18}
        }
        mock_get.return_value = mock_response

        rate = self.provider.get_rate('EUR', 'USD')

        self.assertEqual(rate, Decimal('1.18'))

    def test_get_rate_with_date_raises_exception(self):
        """Test get_rate with date raises exception (not supported)"""
        from datetime import datetime
        date = datetime.now()

        with self.assertRaises(Exception) as cm:
            self.provider.get_rate('EUR', 'USD', date=date)
        self.assertIn('Historical rates not supported', str(cm.exception))

    @patch('requests.get')
    def test_get_rates_method(self, mock_get):
        """Test get_rates method (base class abstract method)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'base': 'EUR',
            'rates': {
                'USD': 1.18,
                'GBP': 0.86,
                'JPY': 129.5
            }
        }
        mock_get.return_value = mock_response

        # Mock get_supported_currencies to return a short list
        with patch.object(self.provider, 'get_supported_currencies', return_value=['EUR', 'USD', 'GBP', 'JPY']):
            rates = self.provider.get_rates('EUR')

            self.assertIsInstance(rates, dict)
            self.assertGreater(len(rates), 0)
            self.assertIn('USD', rates)

    def test_get_rates_with_date_raises_exception(self):
        """Test get_rates with date raises exception (not supported)"""
        from datetime import datetime
        date = datetime.now()

        with self.assertRaises(Exception) as cm:
            self.provider.get_rates('EUR', date=date)
        self.assertIn('Historical rates not supported', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
