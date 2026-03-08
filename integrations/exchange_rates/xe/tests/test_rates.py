"""
Integration tests for XE rate fetching - batch requests, historical rates
"""

import os
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch
from ..provider import XEProvider


class TestXERateFetching:
    """Test rate fetching with mocked responses"""

    @patch('requests.get')
    def test_get_rates_batch_fetching(self, mock_get):
        """Should fetch all rates in one API call"""
        # Mock currencies response
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [
                {'iso': 'USD'},
                {'iso': 'EUR'},
                {'iso': 'GBP'},
                {'iso': 'JPY'}
            ]
        }

        # Mock rates response
        rates_response = Mock()
        rates_response.status_code = 200
        rates_response.json.return_value = {
            'from': 'USD',
            'amount': 1.0,
            'timestamp': '2025-10-25T12:00:00Z',
            'to': [
                {'quotecurrency': 'EUR', 'mid': 0.8601},
                {'quotecurrency': 'GBP', 'mid': 0.7515},
                {'quotecurrency': 'JPY', 'mid': 152.81}
            ]
        }

        # Return different responses based on URL
        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        rates = provider.get_rates('USD')

        # Should return Decimal rates
        assert isinstance(rates, dict)
        assert isinstance(rates['EUR'], Decimal)
        assert rates['EUR'] == Decimal('0.8601')
        assert rates['GBP'] == Decimal('0.7515')
        assert rates['JPY'] == Decimal('152.81')

    @patch('requests.get')
    def test_get_rate_single_pair(self, mock_get):
        """Should fetch single currency pair rate"""
        # Mock currencies response
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [
                {'iso': 'USD'},
                {'iso': 'EUR'},
                {'iso': 'GBP'}
            ]
        }

        # Mock rates response
        rates_response = Mock()
        rates_response.status_code = 200
        rates_response.json.return_value = {
            'from': 'USD',
            'to': [
                {'quotecurrency': 'EUR', 'mid': 0.8601},
                {'quotecurrency': 'GBP', 'mid': 0.7515}
            ]
        }

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        rate = provider.get_rate('USD', 'EUR')

        assert isinstance(rate, Decimal)
        assert rate == Decimal('0.8601')

    @patch('requests.get')
    def test_get_rates_filters_invalid_rates(self, mock_get):
        """Should filter out invalid rates (zero, negative, too high)"""
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [
                {'iso': 'USD'},
                {'iso': 'EUR'},
                {'iso': 'BAD1'},
                {'iso': 'BAD2'},
                {'iso': 'BAD3'}
            ]
        }

        rates_response = Mock()
        rates_response.status_code = 200
        rates_response.json.return_value = {
            'from': 'USD',
            'to': [
                {'quotecurrency': 'EUR', 'mid': 0.8601},  # Valid
                {'quotecurrency': 'BAD1', 'mid': 0},  # Zero - invalid
                {'quotecurrency': 'BAD2', 'mid': -0.5},  # Negative - invalid
                {'quotecurrency': 'BAD3', 'mid': 2000000}  # Too high - invalid
            ]
        }

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        rates = provider.get_rates('USD')

        # Should only include valid rate
        assert 'EUR' in rates
        assert 'BAD1' not in rates
        assert 'BAD2' not in rates
        assert 'BAD3' not in rates

    @patch('requests.get')
    def test_get_rates_different_base_currency(self, mock_get):
        """Should support any base currency (not just USD)"""
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [
                {'iso': 'EUR'},
                {'iso': 'USD'},
                {'iso': 'GBP'}
            ]
        }

        rates_response = Mock()
        rates_response.status_code = 200
        rates_response.json.return_value = {
            'from': 'EUR',
            'to': [
                {'quotecurrency': 'USD', 'mid': 1.1625},
                {'quotecurrency': 'GBP', 'mid': 0.8740}
            ]
        }

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        rates = provider.get_rates('EUR')

        assert 'USD' in rates
        assert 'GBP' in rates
        assert rates['USD'] == Decimal('1.1625')


class TestXEErrorHandling:
    """Test error handling for various API failures"""

    @patch('requests.get')
    def test_401_invalid_credentials(self, mock_get):
        """Should handle 401 unauthorized error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'invalid',
            'api_key': 'invalid'
        }
        provider = XEProvider(credentials)

        with pytest.raises(Exception) as exc:
            provider.get_supported_currencies()

        assert 'Authentication failed' in str(exc.value)

    @patch('requests.get')
    def test_403_quota_exceeded(self, mock_get):
        """Should handle 403 forbidden (quota exceeded)"""
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [{'iso': 'USD'}, {'iso': 'EUR'}]
        }

        rates_response = Mock()
        rates_response.status_code = 403

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        with pytest.raises(Exception) as exc:
            provider.get_rates('USD')

        assert 'Quota exceeded' in str(exc.value) or 'access forbidden' in str(exc.value).lower()

    @patch('requests.get')
    def test_404_invalid_currency(self, mock_get):
        """Should handle 404 not found (invalid currency)"""
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [{'iso': 'USD'}, {'iso': 'EUR'}]
        }

        rates_response = Mock()
        rates_response.status_code = 404

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        with pytest.raises(Exception) as exc:
            provider.get_rates('INVALID')

        assert 'not supported' in str(exc.value).lower() or '404' in str(exc.value)

    @patch('requests.get')
    def test_429_rate_limited(self, mock_get):
        """Should handle 429 too many requests"""
        currencies_response = Mock()
        currencies_response.status_code = 200
        currencies_response.json.return_value = {
            'currencies': [{'iso': 'USD'}, {'iso': 'EUR'}]
        }

        rates_response = Mock()
        rates_response.status_code = 429

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            if 'currencies' in url:
                return currencies_response
            else:
                return rates_response

        mock_get.side_effect = side_effect

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        with pytest.raises(Exception) as exc:
            provider.get_rates('USD')

        assert 'Rate limit exceeded' in str(exc.value)


# Skip integration tests if no credentials
SKIP_INTEGRATION = not (
    os.getenv('XE_TEST_ACCOUNT_ID') and
    os.getenv('XE_TEST_API_KEY')
)

@pytest.mark.skipif(SKIP_INTEGRATION, reason="XE credentials not configured")
class TestXERealAPI:
    """Integration tests with real XE API"""

    def test_fetch_real_rates(self):
        """Should fetch real rates from XE API"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        rates = provider.get_rates('USD')

        assert isinstance(rates, dict)
        assert len(rates) >= 200  # Should have 220+ currencies
        assert 'EUR' in rates
        assert 'GBP' in rates
        assert 'JPY' in rates

        # Verify rates are Decimal
        assert isinstance(rates['EUR'], Decimal)

        # Verify rates are reasonable (sanity check)
        assert Decimal('0.5') < rates['EUR'] < Decimal('1.5')
        assert Decimal('0.5') < rates['GBP'] < Decimal('1.5')
        assert Decimal('100') < rates['JPY'] < Decimal('200')

    def test_fetch_single_rate(self):
        """Should fetch single currency pair"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        rate = provider.get_rate('USD', 'EUR')

        assert isinstance(rate, Decimal)
        assert Decimal('0.5') < rate < Decimal('1.5')

    def test_different_base_currency(self):
        """Should support EUR as base currency"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        rates = provider.get_rates('EUR')

        assert 'USD' in rates
        assert 'GBP' in rates
        assert isinstance(rates['USD'], Decimal)
