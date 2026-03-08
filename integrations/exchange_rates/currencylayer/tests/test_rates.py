"""
Integration tests for Currencylayer provider
These tests actually call the API and require a valid test Access Key
"""
import unittest
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider import CurrencylayerProvider


@unittest.skipUnless(
    os.environ.get('TEST_CURRENCYLAYER_ACCESS_KEY'),
    "Requires TEST_CURRENCYLAYER_ACCESS_KEY environment variable"
)
class TestCurrencylayerIntegration(unittest.TestCase):
    """Integration tests with live API"""

    def setUp(self):
        """Set up with real test credentials"""
        self.credentials = {
            'access_key': os.environ['TEST_CURRENCYLAYER_ACCESS_KEY']
        }
        self.provider = CurrencylayerProvider(self.credentials)

    def test_live_connection(self):
        """Test connection with real API"""
        result = self.provider.test_connection()

        self.assertTrue(
            result['success'],
            f"Connection failed: {result.get('message')}"
        )
        self.assertIn('currency_count', result['details'])
        self.assertGreater(result['details']['currency_count'], 100)

    def test_live_fetch_rates_usd_base(self):
        """Test fetching rates from real API with USD base"""
        rates = self.provider.get_exchange_rate('USD', ['EUR', 'GBP', 'JPY'])

        # Verify we got rates back
        self.assertGreater(len(rates), 0)
        self.assertIn('EUR', rates)
        self.assertIn('GBP', rates)
        self.assertIn('JPY', rates)

        # Verify rates are Decimal
        for currency, rate in rates.items():
            self.assertIsInstance(rate, Decimal, f"Rate for {currency} should be Decimal")
            self.assertGreater(rate, 0, f"Rate for {currency} should be positive")

        # EUR should be roughly 0.7-1.2 USD (sanity check)
        if 'EUR' in rates:
            self.assertGreater(rates['EUR'], Decimal('0.5'))
            self.assertLess(rates['EUR'], Decimal('1.5'))

        # GBP should be roughly 0.6-1.0 USD
        if 'GBP' in rates:
            self.assertGreater(rates['GBP'], Decimal('0.5'))
            self.assertLess(rates['GBP'], Decimal('1.2'))

        # JPY should be roughly 100-150 per USD
        if 'JPY' in rates:
            self.assertGreater(rates['JPY'], Decimal('80'))
            self.assertLess(rates['JPY'], Decimal('200'))

    def test_live_fetch_rates_eur_base(self):
        """Test fetching rates from real API with EUR base"""
        rates = self.provider.get_exchange_rate('EUR', ['USD', 'GBP'])

        # Verify we got rates back
        self.assertGreater(len(rates), 0)

        # Verify rates are Decimal and positive
        for currency, rate in rates.items():
            self.assertIsInstance(rate, Decimal)
            self.assertGreater(rate, 0)

        # USD should be roughly 1.0-1.4 per EUR
        if 'USD' in rates:
            self.assertGreater(rates['USD'], Decimal('0.8'))
            self.assertLess(rates['USD'], Decimal('1.6'))

    def test_live_supported_currencies(self):
        """Test getting supported currencies from real API"""
        currencies = self.provider.get_supported_currencies()

        self.assertIsInstance(currencies, list)
        self.assertGreater(len(currencies), 100, "Should have over 100 currencies")

        # Check for major currencies
        major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        for currency in major_currencies:
            self.assertIn(
                currency,
                currencies,
                f"{currency} should be in supported currencies"
            )

    def test_live_rate_consistency(self):
        """Test that rates are consistent across multiple calls"""
        # Fetch rates twice
        rates1 = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])
        rates2 = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])

        # Rates should be very close (within 1% due to caching/timing)
        for currency in ['EUR', 'GBP']:
            if currency in rates1 and currency in rates2:
                diff_percent = abs(
                    (rates1[currency] - rates2[currency]) / rates1[currency] * 100
                )
                self.assertLess(
                    diff_percent,
                    1,
                    f"{currency} rates differ by more than 1%: {rates1[currency]} vs {rates2[currency]}"
                )

    def test_live_currency_conversion(self):
        """Test EUR to GBP conversion makes sense"""
        # Get USD rates
        usd_rates = self.provider.get_exchange_rate('USD', ['EUR', 'GBP'])

        # Get EUR to GBP rate
        eur_rates = self.provider.get_exchange_rate('EUR', ['GBP'])

        if 'EUR' in usd_rates and 'GBP' in usd_rates and 'GBP' in eur_rates:
            # Calculate expected EUR to GBP rate from USD rates
            expected = usd_rates['GBP'] / usd_rates['EUR']

            # Should be very close (within 0.1% due to rounding)
            diff_percent = abs((eur_rates['GBP'] - expected) / expected * 100)

            self.assertLess(
                diff_percent,
                0.1,
                f"EUR to GBP conversion inconsistent: {eur_rates['GBP']} vs expected {expected}"
            )

    def test_live_get_rate_method(self):
        """Test get_rate method with live API"""
        rate = self.provider.get_rate('USD', 'EUR')

        self.assertIsInstance(rate, Decimal)
        self.assertGreater(rate, 0)
        self.assertLess(rate, Decimal('2.0'))  # Sanity check

    def test_live_get_rates_method(self):
        """Test get_rates method with live API"""
        rates = self.provider.get_rates('USD')

        self.assertIsInstance(rates, dict)
        self.assertGreater(len(rates), 50, "Should have at least 50 currencies")

        # Check major currencies are present
        major_currencies = ['EUR', 'GBP', 'JPY', 'CHF']
        for currency in major_currencies:
            self.assertIn(
                currency,
                rates,
                f"{currency} should be in rates"
            )

        # Verify all rates are positive Decimals
        for currency, rate in rates.items():
            self.assertIsInstance(rate, Decimal)
            self.assertGreater(rate, 0)


if __name__ == '__main__':
    # Can run with: TEST_CURRENCYLAYER_ACCESS_KEY=your_access_key python test_rates.py
    unittest.main()
