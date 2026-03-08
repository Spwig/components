"""
Validation and error handling tests for ExchangeRate-API Provider
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from provider import ExchangeRateAPIProvider


class TestErrorHandling:
    """Test error handling for various scenarios"""

    def setup_method(self):
        """Set up test provider"""
        self.provider = ExchangeRateAPIProvider({'api_key': '1137a55f91aad6c1244b0ac4'})

    def test_historical_rates_not_supported(self):
        """Test that historical rates raise appropriate error"""
        from datetime import datetime

        with pytest.raises(Exception, match="Historical rates not supported"):
            self.provider.get_rates('USD', date=datetime.now())

    def test_historical_single_rate_not_supported(self):
        """Test that historical single rate raises error"""
        from datetime import datetime

        with pytest.raises(Exception, match="Historical rates not supported"):
            self.provider.get_rate('USD', 'EUR', date=datetime.now())

    @patch('requests.get')
    def test_invalid_api_key_response(self, mock_get):
        """Test handling of invalid API key response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'error',
            'error-type': 'invalid-key'
        }
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Invalid API Key"):
            self.provider.get_rates('USD')

    @patch('requests.get')
    def test_quota_reached_response(self, mock_get):
        """Test handling of quota reached response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'error',
            'error-type': 'quota-reached'
        }
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Rate limit exceeded"):
            self.provider.get_rates('USD')

    @patch('requests.get')
    def test_unsupported_currency_response(self, mock_get):
        """Test handling of unsupported currency"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'error',
            'error-type': 'unsupported-code'
        }
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Unsupported base currency"):
            self.provider.get_rates('XYZ')

    @patch('requests.get')
    def test_inactive_account_response(self, mock_get):
        """Test handling of inactive account"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'error',
            'error-type': 'inactive-account'
        }
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Account is inactive"):
            self.provider.get_rates('USD')

    @patch('requests.get')
    def test_connection_timeout(self, mock_get):
        """Test handling of connection timeout"""
        import requests
        mock_get.side_effect = requests.Timeout()

        with pytest.raises(Exception, match="timeout"):
            self.provider.get_rates('USD')

    @patch('requests.get')
    def test_connection_error(self, mock_get):
        """Test handling of connection error"""
        import requests
        mock_get.side_effect = requests.ConnectionError()

        with pytest.raises(Exception, match="Connection error"):
            self.provider.get_rates('USD')


class TestRateValidation:
    """Test rate validation and sanity checking"""

    def setup_method(self):
        """Set up test provider"""
        self.provider = ExchangeRateAPIProvider({'api_key': '1137a55f91aad6c1244b0ac4'})

    @patch('requests.get')
    def test_filters_zero_rates(self, mock_get):
        """Test that zero or negative rates are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'conversion_rates': {
                'USD': 1.0,
                'EUR': 0.86,
                'INVALID': 0,  # Should be filtered
                'NEGATIVE': -1.5  # Should be filtered
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_rates('USD')

        assert 'EUR' in rates
        assert 'INVALID' not in rates
        assert 'NEGATIVE' not in rates

    @patch('requests.get')
    def test_filters_suspiciously_high_rates(self, mock_get):
        """Test that suspiciously high rates are filtered out"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'conversion_rates': {
                'USD': 1.0,
                'EUR': 0.86,
                'TOOHIGH': 2000000  # Should be filtered
            }
        }
        mock_get.return_value = mock_response

        rates = self.provider.get_rates('USD')

        assert 'EUR' in rates
        assert 'TOOHIGH' not in rates


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
