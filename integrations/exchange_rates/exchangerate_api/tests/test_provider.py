"""
Unit tests for ExchangeRate-API Provider
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from provider import ExchangeRateAPIProvider


class TestProviderInitialization:
    """Test provider initialization and validation"""

    def test_init_with_valid_credentials(self):
        """Test successful initialization with valid API key"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        assert provider.api_key == '1137a55f91aad6c1244b0ac4'
        assert provider.provider_key == 'exchangerate_api'
        assert provider.provider_name == 'ExchangeRate-API'

    def test_init_without_api_key(self):
        """Test initialization fails without API key"""
        credentials = {}

        with pytest.raises(ValueError, match="API Key is required"):
            ExchangeRateAPIProvider(credentials)

    def test_init_with_short_api_key(self):
        """Test initialization fails with too short API key"""
        credentials = {'api_key': 'short'}

        with pytest.raises(ValueError, match="too short"):
            ExchangeRateAPIProvider(credentials)


class TestCredentialValidation:
    """Test credential validation"""

    def test_validate_credentials_success(self):
        """Test successful credential validation"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        # Should not raise
        provider.validate_credentials(credentials)

    def test_validate_credentials_missing_key(self):
        """Test validation fails with missing API key"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        with pytest.raises(ValueError, match="API Key is required"):
            provider.validate_credentials({})

    def test_validate_credentials_invalid_characters(self):
        """Test validation fails with invalid characters"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        with pytest.raises(ValueError, match="alphanumeric"):
            provider.validate_credentials({'api_key': 'invalid-key-with-dashes!'})


class TestCredentialRedaction:
    """Test credential redaction for logging"""

    def test_redact_credentials(self):
        """Test API key is properly redacted"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        redacted = provider.redact_credentials(credentials)

        assert redacted['api_key'] == '113***ac4'
        assert '1137a55f91aad6c1244b0ac4' not in str(redacted)

    def test_redact_short_key(self):
        """Test redaction of short keys"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        redacted = provider.redact_credentials({'api_key': 'short'})

        assert redacted['api_key'] == '***'


class TestCapabilities:
    """Test provider capabilities"""

    def test_capabilities(self):
        """Test provider capabilities are correct"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        caps = provider.capabilities

        assert caps['live_rates'] is True
        assert caps['historical'] is False
        assert caps['crypto'] is False
        assert caps['base_currency_selection'] is True
        assert caps['batch_requests'] is True


class TestCredentialSchema:
    """Test credential schema"""

    def test_credential_schema(self):
        """Test credential schema structure"""
        credentials = {'api_key': '1137a55f91aad6c1244b0ac4'}
        provider = ExchangeRateAPIProvider(credentials)

        schema = provider.credential_schema

        assert 'api_key' in schema
        assert schema['api_key']['type'] == 'text'
        assert schema['api_key']['required'] is True
        assert 'label' in schema['api_key']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
