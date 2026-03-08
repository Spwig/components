"""
Unit tests for XE Provider - Dual credentials, account detection, redaction
"""

import os
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from ..provider import XEProvider


class TestXEProviderInit:
    """Test provider initialization and credential handling"""

    def test_init_with_valid_credentials(self):
        """Should initialize with both account_id and api_key"""
        credentials = {
            'account_id': 'test_account_123',
            'api_key': 'test_key_456789'
        }
        provider = XEProvider(credentials)

        assert provider.account_id == 'test_account_123'
        assert provider.api_key == 'test_key_456789'
        assert provider.provider_key == 'xe'
        assert provider.provider_name == 'XE Currency Data API'

    def test_init_missing_account_id(self):
        """Should raise error if account_id is missing"""
        credentials = {
            'api_key': 'test_key_456789'
        }

        with pytest.raises(ValueError) as exc:
            XEProvider(credentials)

        assert 'Both Account ID and API Key are required' in str(exc.value)

    def test_init_missing_api_key(self):
        """Should raise error if api_key is missing"""
        credentials = {
            'account_id': 'test_account_123'
        }

        with pytest.raises(ValueError) as exc:
            XEProvider(credentials)

        assert 'Both Account ID and API Key are required' in str(exc.value)

    def test_init_empty_credentials(self):
        """Should raise error if credentials are empty strings"""
        credentials = {
            'account_id': '   ',
            'api_key': '   '
        }

        with pytest.raises(ValueError) as exc:
            XEProvider(credentials)

        assert 'Both Account ID and API Key are required' in str(exc.value)

    def test_init_strips_whitespace(self):
        """Should strip whitespace from credentials"""
        credentials = {
            'account_id': '  test_account_123  ',
            'api_key': '  test_key_456789  '
        }
        provider = XEProvider(credentials)

        assert provider.account_id == 'test_account_123'
        assert provider.api_key == 'test_key_456789'


class TestXECredentialValidation:
    """Test credential validation"""

    def test_validate_valid_credentials(self):
        """Should validate correct credential format"""
        credentials = {
            'account_id': 'spwig686304491',
            'api_key': 'ajd6ph4c3djpqt10p22if94tni'
        }

        result = XEProvider.validate_credentials(credentials)

        assert result['valid'] is True
        assert 'message' in result

    def test_validate_missing_account_id(self):
        """Should reject missing account_id"""
        credentials = {
            'api_key': 'ajd6ph4c3djpqt10p22if94tni'
        }

        result = XEProvider.validate_credentials(credentials)

        assert result['valid'] is False
        assert 'Account ID is required' in result['errors']

    def test_validate_missing_api_key(self):
        """Should reject missing api_key"""
        credentials = {
            'account_id': 'spwig686304491'
        }

        result = XEProvider.validate_credentials(credentials)

        assert result['valid'] is False
        assert 'API Key is required' in result['errors']

    def test_validate_short_account_id(self):
        """Should warn about suspiciously short account_id"""
        credentials = {
            'account_id': 'abc',
            'api_key': 'ajd6ph4c3djpqt10p22if94tni'
        }

        result = XEProvider.validate_credentials(credentials)

        assert result['valid'] is False
        assert any('too short' in err for err in result['errors'])

    def test_validate_short_api_key(self):
        """Should warn about suspiciously short api_key"""
        credentials = {
            'account_id': 'spwig686304491',
            'api_key': 'short'
        }

        result = XEProvider.validate_credentials(credentials)

        assert result['valid'] is False
        assert any('too short' in err for err in result['errors'])


class TestXECredentialRedaction:
    """Test credential redaction for secure logging"""

    def test_redact_account_id_shown_in_full(self):
        """Account ID should be shown in full (not secret)"""
        credentials = {
            'account_id': 'spwig686304491',
            'api_key': 'ajd6ph4c3djpqt10p22if94tni'
        }

        redacted = XEProvider.redact_credentials(credentials)

        # Account ID not redacted (it's the username)
        assert redacted['account_id'] == 'spwig686304491'

    def test_redact_api_key_masked(self):
        """API Key should be redacted (it's secret)"""
        credentials = {
            'account_id': 'spwig686304491',
            'api_key': 'ajd6ph4c3djpqt10p22if94tni'
        }

        redacted = XEProvider.redact_credentials(credentials)

        # API Key redacted (show first 3 and last 3 only)
        assert redacted['api_key'] == 'ajd...tni'
        assert '...' in redacted['api_key']

    def test_redact_short_api_key(self):
        """Should handle short API keys gracefully"""
        credentials = {
            'account_id': 'test123',
            'api_key': 'abc'
        }

        redacted = XEProvider.redact_credentials(credentials)

        # Too short to redact meaningfully
        assert redacted['api_key'] == '***'


class TestXEAccountInfo:
    """Test account info fetching and caching"""

    @patch('requests.get')
    def test_get_account_info_trial_package(self, mock_get):
        """Should detect trial package and mock rates"""
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

        account_info = provider._get_account_info()

        assert account_info['package'] == 'trial'
        assert account_info['is_trial'] is True
        assert account_info['mock_rates'] is True
        assert account_info['organization'] == 'Spwig'

    @patch('requests.get')
    def test_get_account_info_premium_package(self, mock_get):
        """Should detect premium package (not trial)"""
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

        account_info = provider._get_account_info()

        assert account_info['package'] == 'premium'
        assert account_info['is_trial'] is False
        assert account_info['mock_rates'] is False
        assert account_info['historical_supported'] is True

    @patch('requests.get')
    def test_get_account_info_caching(self, mock_get):
        """Should cache account info to avoid repeated API calls"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test123',
            'organization': 'Test',
            'package': 'trial',
            'service_start_timestamp': '2025-10-25T00:00:00Z'
        }
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'test123',
            'api_key': 'test_key'
        }
        provider = XEProvider(credentials)

        # First call
        info1 = provider._get_account_info()

        # Second call (should use cache)
        info2 = provider._get_account_info()

        # API should only be called once
        assert mock_get.call_count == 1
        assert info1 == info2

    @patch('requests.get')
    def test_get_account_info_401_error(self, mock_get):
        """Should handle authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        credentials = {
            'account_id': 'invalid',
            'api_key': 'invalid'
        }
        provider = XEProvider(credentials)

        with pytest.raises(Exception) as exc:
            provider._get_account_info()

        assert 'Authentication failed' in str(exc.value)


class TestXECapabilities:
    """Test capability detection based on package"""

    @patch('requests.get')
    def test_capabilities_trial_package(self, mock_get):
        """Trial package should have mock_rates flag"""
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

        caps = provider.capabilities()

        assert caps['live_rates'] is True
        assert caps['historical'] is True  # Trial has historical for testing
        assert caps['crypto'] is False
        assert caps['base_currency_selection'] is True
        assert caps['batch_requests'] is True
        assert caps['mock_rates'] is True  # IMPORTANT: Trial returns mock data

    @patch('requests.get')
    def test_capabilities_premium_package(self, mock_get):
        """Premium package should have real rates"""
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

        caps = provider.capabilities()

        assert caps['live_rates'] is True
        assert caps['historical'] is True
        assert caps['crypto'] is False
        assert caps['mock_rates'] is False  # Real data


# Skip integration tests if no credentials
SKIP_INTEGRATION = not (
    os.getenv('XE_TEST_ACCOUNT_ID') and
    os.getenv('XE_TEST_API_KEY')
)

@pytest.mark.skipif(SKIP_INTEGRATION, reason="XE credentials not configured")
class TestXEIntegration:
    """Integration tests with real XE API (requires credentials)"""

    def test_connection_with_real_credentials(self):
        """Should connect to XE with real credentials"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        result = provider.test_connection()

        assert result['success'] is True
        assert 'account_id' in result
        assert 'package' in result

    def test_get_supported_currencies(self):
        """Should fetch 220+ currencies"""
        credentials = {
            'account_id': os.getenv('XE_TEST_ACCOUNT_ID'),
            'api_key': os.getenv('XE_TEST_API_KEY')
        }
        provider = XEProvider(credentials)

        currencies = provider.get_supported_currencies()

        assert isinstance(currencies, list)
        assert len(currencies) >= 220
        assert 'USD' in currencies
        assert 'EUR' in currencies
        assert 'GBP' in currencies
