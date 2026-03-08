"""
Unit tests for Currencylayer provider
"""
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider import CurrencylayerProvider


class TestCurrencylayerProvider(unittest.TestCase):
    """Test Currencylayer provider implementation"""

    def setUp(self):
        """Set up test fixtures"""
        self.credentials = {
            'access_key': 'abc123def456789012345678901234567'
        }
        self.provider = CurrencylayerProvider(self.credentials)

    def test_initialization(self):
        """Test provider initialization"""
        self.assertEqual(self.provider.provider_key, 'currencylayer')
        self.assertEqual(self.provider.provider_name, 'Currencylayer')
        self.assertEqual(self.provider.access_key, 'abc123def456789012345678901234567')

    def test_initialization_without_access_key(self):
        """Test initialization fails without Access Key"""
        with self.assertRaises(ValueError) as cm:
            CurrencylayerProvider({})
        self.assertIn("Access Key is required", str(cm.exception))

    def test_initialization_with_short_access_key(self):
        """Test initialization fails with short Access Key"""
        with self.assertRaises(ValueError) as cm:
            CurrencylayerProvider({'access_key': 'short'})
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
            'currencies': {
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
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_connection_api_error_invalid_key(self, mock_get):
        """Test connection fails with invalid Access Key in API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 101,
                'info': 'Invalid access key'
            }
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Invalid Access Key', result['message'])

    @patch('requests.get')
    def test_connection_invalid_access_key_401(self, mock_get):
        """Test connection fails with 401 status"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Invalid Access Key'
        mock_get.return_value = mock_response

        result = self.provider.test_connection()

        self.assertFalse(result['success'])
        self.assertIn('Invalid Access Key', result['message'])
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
            'success': True,
            'timestamp': 1234567890,
            'source': 'USD',
            'quotes': {
                'USDEUR': 0.85,
                'USDGBP': 0.73,
                'USDJPY': 110.5
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
            'success': True,
            'timestamp': 1234567890,
            'source': 'USD',
            'quotes': {
                'USDEUR': 0.85,  # USD to EUR
                'USDGBP': 0.73   # USD to GBP
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
    def test_get_exchange_rate_api_error_in_response(self, mock_get):
        """Test rate fetching handles API errors in response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'error': {
                'code': 101,
                'info': 'Invalid access key'
            }
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_exchange_rate('USD', ['EUR'])
        self.assertIn('Invalid Access Key', str(cm.exception))

    @patch('requests.get')
    def test_get_exchange_rate_invalid_response(self, mock_get):
        """Test rate fetching handles invalid response format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'invalid': 'response'}
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
                'success': True,
                'source': 'USD',
                'quotes': {'USDEUR': 0.85}
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
            'success': True,
            'currencies': {
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
        self.assertIn('USD', currencies)
        self.assertIn('EUR', currencies)

    def test_get_rate_limits(self):
        """Test getting rate limits"""
        limits = self.provider.get_rate_limits()

        self.assertIn('requests_per_month', limits)
        self.assertEqual(limits['requests_per_month'], 100)
        self.assertIsNone(limits['requests_per_minute'])

    @patch('requests.get')
    def test_get_rate_method(self, mock_get):
        """Test get_rate method (base class implementation)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'source': 'USD',
            'quotes': {'USDEUR': 0.85}
        }
        mock_get.return_value = mock_response

        rate = self.provider.get_rate('USD', 'EUR')

        self.assertEqual(rate, Decimal('0.85'))

    @patch('requests.get')
    def test_get_rate_not_available(self, mock_get):
        """Test get_rate when rate is not available"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'source': 'USD',
            'quotes': {'USDGBP': 0.73}
        }
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as cm:
            self.provider.get_rate('USD', 'EUR')
        self.assertIn('not available', str(cm.exception))

    def test_get_rate_historical_not_supported(self):
        """Test get_rate with historical date raises exception"""
        with self.assertRaises(Exception) as cm:
            self.provider.get_rate('USD', 'EUR', date='2023-01-01')
        self.assertIn('Historical rates not supported', str(cm.exception))

    @patch('requests.get')
    def test_get_rates_method(self, mock_get):
        """Test get_rates method (base class implementation)"""
        # Mock both list and live endpoints
        def mock_response_func(*args, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200

            if '/list' in args[0]:
                mock_resp.json.return_value = {
                    'success': True,
                    'currencies': {
                        'USD': 'US Dollar',
                        'EUR': 'Euro',
                        'GBP': 'British Pound'
                    }
                }
            else:  # /live endpoint
                mock_resp.json.return_value = {
                    'success': True,
                    'source': 'USD',
                    'quotes': {
                        'USDEUR': 0.85,
                        'USDGBP': 0.73
                    }
                }
            return mock_resp

        mock_get.side_effect = mock_response_func

        rates = self.provider.get_rates('USD')

        self.assertIsInstance(rates, dict)
        self.assertIn('EUR', rates)
        self.assertIn('GBP', rates)
        self.assertNotIn('USD', rates)  # Base currency not in results

    def test_get_rates_historical_not_supported(self):
        """Test get_rates with historical date raises exception"""
        with self.assertRaises(Exception) as cm:
            self.provider.get_rates('USD', date='2023-01-01')
        self.assertIn('Historical rates not supported', str(cm.exception))

    @patch('requests.get')
    def test_rate_sanity_check_negative(self, mock_get):
        """Test that negative rates are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'source': 'USD',
            'quotes': {
                'USDEUR': -0.85,  # Invalid negative rate
                'USDGBP': 0.73
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])

        # EUR should be filtered out, only GBP should remain
        self.assertEqual(len(rates), 1)
        self.assertNotIn('EUR', rates)
        self.assertIn('GBP', rates)

    @patch('requests.get')
    def test_rate_sanity_check_too_high(self, mock_get):
        """Test that suspiciously high rates are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'source': 'USD',
            'quotes': {
                'USDEUR': 2000000,  # Suspiciously high rate
                'USDGBP': 0.73
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])

        # EUR should be filtered out, only GBP should remain
        self.assertEqual(len(rates), 1)
        self.assertNotIn('EUR', rates)
        self.assertIn('GBP', rates)


if __name__ == '__main__':
    unittest.main()
