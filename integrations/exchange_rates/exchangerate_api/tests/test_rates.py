"""
Integration tests for ExchangeRate-API rate fetching
Run with: EXCHANGERATE_API_KEY=your_key_here python test_rates.py
"""
import pytest
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from provider import ExchangeRateAPIProvider


# Skip tests if no API key provided
TEST_API_KEY = os.getenv('EXCHANGERATE_API_KEY', '1137a55f91aad6c1244b0ac4')
SKIP_INTEGRATION = not TEST_API_KEY

pytestmark = pytest.mark.skipif(SKIP_INTEGRATION, reason="No API key provided")


class TestRateFetching:
    """Test rate fetching functionality"""

    def setup_method(self):
        """Set up test provider"""
        self.provider = ExchangeRateAPIProvider({'api_key': TEST_API_KEY})

    def test_get_rates_usd(self):
        """Test fetching all rates for USD"""
        rates = self.provider.get_rates('USD')

        assert isinstance(rates, dict)
        assert len(rates) > 100  # Should have 160+ currencies
        assert 'EUR' in rates
        assert 'GBP' in rates
        assert 'JPY' in rates

        # Verify rates are Decimal
        assert isinstance(rates['EUR'], Decimal)

        # Sanity checks
        assert rates['EUR'] > 0
        assert rates['EUR'] < 2  # 1 USD should not be > 2 EUR

    def test_get_rates_eur(self):
        """Test fetching rates with EUR base"""
        rates = self.provider.get_rates('EUR')

        assert isinstance(rates, dict)
        assert 'USD' in rates
        assert 'GBP' in rates
        assert isinstance(rates['USD'], Decimal)

    def test_get_rate_single_pair(self):
        """Test fetching a single currency pair"""
        rate = self.provider.get_rate('USD', 'EUR')

        assert isinstance(rate, Decimal)
        assert rate > 0
        assert rate < 2

    def test_get_rate_reverse_pair(self):
        """Test fetching reverse pair (EUR to USD)"""
        eur_usd = self.provider.get_rate('EUR', 'USD')
        usd_eur = self.provider.get_rate('USD', 'EUR')

        # Should be roughly inverse
        product = eur_usd * usd_eur
        assert abs(product - Decimal('1.0')) < Decimal('0.01')


class TestSupportedCurrencies:
    """Test supported currencies fetching"""

    def setup_method(self):
        """Set up test provider"""
        self.provider = ExchangeRateAPIProvider({'api_key': TEST_API_KEY})

    def test_get_supported_currencies(self):
        """Test fetching supported currency list"""
        currencies = self.provider.get_supported_currencies()

        assert isinstance(currencies, list)
        assert len(currencies) > 100
        assert 'USD' in currencies
        assert 'EUR' in currencies
        assert 'GBP' in currencies
        assert 'JPY' in currencies


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
