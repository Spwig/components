"""
Validation tests for XE Provider - connection testing, trial warnings
"""

import os
import pytest
from unittest.mock import Mock, patch
from ..provider import XEProvider


class TestXEConnectionTest:
    """Test connection testing functionality"""

    @patch('requests.get')
    def test_connection_success_trial_account(self, mock_get):
        """Should succeed and warn for trial account"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'spwig686304491',
            'organization': 'Spwig',
            'package': 'trial',
            'service_start_timestamp': '2025-10-25T00:00:00Z'
        }
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'spwig686304491',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is True
        assert result['account_id'] == 'spwig686304491'
        assert result['organization'] == 'Spwig'
        assert result['package'] == 'trial'
        assert result['is_trial'] is True

        # IMPORTANT: Should include mock rate warning
        assert 'mock_rates_warning' in result
        assert 'MOCK RATES' in result['mock_rates_warning']
        assert 'testing purposes only' in result['mock_rates_warning']

    @patch('requests.get')
    def test_connection_success_production_account(self, mock_get):
        """Should succeed without warning for production account"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'prod123456',
            'organization': 'Production Co',
            'package': 'premium',
            'service_start_timestamp': '2025-01-01T00:00:00Z'
        }
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'prod123456',
            'api_key': 'prod_key'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is True
        assert result['is_trial'] is False

        # Should NOT include mock rate warning
        assert 'mock_rates_warning' not in result

    @patch('requests.get')
    def test_connection_failure_invalid_credentials(self, mock_get):
        """Should fail with clear message for invalid credentials"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'invalid',
            'api_key': 'invalid'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is False
        assert 'Authentication failed' in result['message'] or 'invalid' in result['message'].lower()

    @patch('requests.get')
    def test_connection_failure_forbidden(self, mock_get):
        """Should handle 403 forbidden error"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is False
        assert 'forbidden' in result['message'].lower() or 'access' in result['message'].lower()

    @patch('requests.get')
    def test_connection_failure_timeout(self, mock_get):
        """Should handle timeout errors"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is False
        assert 'timeout' in result['message'].lower()

    @patch('requests.get')
    def test_connection_failure_network_error(self, mock_get):
        """Should handle network errors"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is False
        assert 'Network error' in result['message'] or 'connection' in result['message'].lower()


class TestXERateLimits:
    """Test rate limit information retrieval"""

    @patch('requests.get')
    def test_get_rate_limits_trial(self, mock_get):
        """Should return trial limits"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test',
            'organization': 'Test',
            'package': 'trial',
            'service_start_timestamp': '2025-10-25T00:00:00Z'
        }
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        limits = provider.get_rate_limits()

        assert limits['package'] == 'trial'
        assert limits['is_trial'] is True
        assert limits['requests_per_month'] == 100  # Trial limit
        assert limits['requests_remaining'] is None  # Not provided by XE
        assert 'service_start' in limits

    @patch('requests.get')
    def test_get_rate_limits_production(self, mock_get):
        """Should return package-specific for production"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test',
            'organization': 'Test',
            'package': 'premium',
            'service_start_timestamp': '2025-01-01T00:00:00Z'
        }
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'test',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        limits = provider.get_rate_limits()

        assert limits['package'] == 'premium'
        assert limits['is_trial'] is False
        assert limits['requests_per_month'] == 'Package-specific'
        assert 'note' in limits
        assert 'XE' in limits['note']


# Skip integration tests if no credentials
SKIP_INTEGRATION = not (
    os.getenv('XE_TEST_ACCOUNT_ID') and
    os.getenv('XE_TEST_API_KEY')
)

@pytest.mark.skipif(SKIP_INTEGRATION, reason="XE credentials not configured")
class TestXEValidationIntegration:
    """Integration tests for validation with real API"""

    def test_real_connection_test(self):
        """Should test connection with real credentials"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is True
        assert 'account_id' in result
        assert 'organization' in result
        assert 'package' in result

        # If trial account, should have warning
        if result.get('is_trial'):
            assert 'mock_rates_warning' in result
            print(f"\n⚠️  Trial Warning: {result['mock_rates_warning']}")

    def test_real_rate_limits(self):
        """Should get rate limits from real account"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        limits = provider.get_rate_limits()

        assert 'package' in limits
        assert 'is_trial' in limits

        print(f"\n📊 Rate Limits:")
        print(f"   Package: {limits['package']}")
        print(f"   Is Trial: {limits['is_trial']}")
        print(f"   Requests/Month: {limits['requests_per_month']}")

    def test_real_capabilities(self):
        """Should get capabilities from real account"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        caps = provider.capabilities()

        assert caps['live_rates'] is True
        assert caps['base_currency_selection'] is True
        assert caps['batch_requests'] is True
        assert caps['crypto'] is False

        print(f"\n🔧 Capabilities:")
        print(f"   Live Rates: {caps['live_rates']}")
        print(f"   Historical: {caps['historical']}")
        print(f"   Mock Rates: {caps.get('mock_rates', False)}")
