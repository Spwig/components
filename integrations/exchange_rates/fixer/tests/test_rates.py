"""
Integration tests for Fixer.io provider
These tests make actual API calls and require a valid access key
Set TEST_FIXER_ACCESS_KEY environment variable to run these tests
"""
import unittest
import os
import sys
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from provider import FixerProvider


class TestFixerRatesIntegration(unittest.TestCase):
    """Integration tests for Fixer.io API"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for all tests"""
        cls.access_key = os.getenv('TEST_FIXER_ACCESS_KEY')

        if not cls.access_key:
            raise unittest.SkipTest(
                "TEST_FIXER_ACCESS_KEY environment variable not set. "
                "Skipping integration tests."
            )

        cls.credentials = {'access_key': cls.access_key}
        cls.provider = FixerProvider(cls.credentials)

    def test_connection(self):
        """Test actual connection to Fixer.io API"""
        result = self.provider.test_connection()

        print(f"\nConnection test result: {result}")

        self.assertTrue(result['success'], f"Connection failed: {result.get('message')}")
        self.assertIn('currency_count', result['details'])
        self.assertGreater(result['details']['currency_count'], 100)
        self.assertEqual(result['details']['base_currency'], 'EUR')

    def test_get_supported_currencies(self):
        """Test fetching supported currencies"""
        currencies = self.provider.get_supported_currencies()

        print(f"\nSupported currencies count: {len(currencies)}")
        print(f"Sample currencies: {currencies[:10]}")

        self.assertIsInstance(currencies, list)
        self.assertGreater(len(currencies), 100)

        # Check for major currencies
        major_currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        for currency in major_currencies:
            self.assertIn(currency, currencies, f"{currency} not in supported currencies")

    def test_get_eur_to_usd_rate(self):
        """Test fetching EUR to USD rate"""
        rates = self.provider.get_exchange_rate('EUR', ['USD'])

        print(f"\nEUR to USD rate: {rates.get('USD')}")

        self.assertIn('USD', rates)
        self.assertIsInstance(rates['USD'], Decimal)

        # Sanity check: EUR/USD typically between 0.8 and 1.5
        self.assertGreater(rates['USD'], Decimal('0.8'))
        self.assertLess(rates['USD'], Decimal('1.5'))

    def test_get_eur_to_multiple_rates(self):
        """Test fetching EUR to multiple currencies"""
        target_currencies = ['USD', 'GBP', 'JPY', 'CHF', 'CAD']
        rates = self.provider.get_exchange_rate('EUR', target_currencies)

        print(f"\nEUR to multiple currencies:")
        for currency, rate in rates.items():
            print(f"  {currency}: {rate}")

        # Should get all requested currencies
        for currency in target_currencies:
            self.assertIn(currency, rates)
            self.assertIsInstance(rates[currency], Decimal)
            self.assertGreater(rates[currency], Decimal('0'))

    def test_get_usd_to_gbp_rate_with_conversion(self):
        """Test fetching USD to GBP rate (requires EUR-based conversion)"""
        rates = self.provider.get_exchange_rate('USD', ['GBP'])

        print(f"\nUSD to GBP rate (via EUR conversion): {rates.get('GBP')}")

        self.assertIn('GBP', rates)
        self.assertIsInstance(rates['GBP'], Decimal)

        # Sanity check: USD/GBP typically between 0.6 and 0.9
        self.assertGreater(rates['GBP'], Decimal('0.6'))
        self.assertLess(rates['GBP'], Decimal('0.9'))

    def test_get_gbp_to_jpy_rate_with_conversion(self):
        """Test fetching GBP to JPY rate (requires EUR-based conversion)"""
        rates = self.provider.get_exchange_rate('GBP', ['JPY'])

        print(f"\nGBP to JPY rate (via EUR conversion): {rates.get('JPY')}")

        self.assertIn('JPY', rates)
        self.assertIsInstance(rates['JPY'], Decimal)

        # Sanity check: GBP/JPY typically between 140 and 200
        self.assertGreater(rates['JPY'], Decimal('140'))
        self.assertLess(rates['JPY'], Decimal('200'))

    def test_get_rate_method(self):
        """Test get_rate method (single currency pair)"""
        rate = self.provider.get_rate('EUR', 'USD')

        print(f"\nget_rate('EUR', 'USD'): {rate}")

        self.assertIsInstance(rate, Decimal)
        self.assertGreater(rate, Decimal('0'))

    def test_get_rates_method(self):
        """Test get_rates method (all currencies for base)"""
        # This might take a while as it fetches all currencies
        rates = self.provider.get_rates('EUR')

        print(f"\nget_rates('EUR') returned {len(rates)} currencies")
        print(f"Sample rates: {list(rates.items())[:5]}")

        self.assertIsInstance(rates, dict)
        self.assertGreater(len(rates), 100)

        # Check major currencies are included
        self.assertIn('USD', rates)
        self.assertIn('GBP', rates)
        self.assertIn('JPY', rates)

        # Check all rates are positive decimals
        for currency, rate in rates.items():
            self.assertIsInstance(rate, Decimal)
            self.assertGreater(rate, Decimal('0'))

    def test_rate_consistency(self):
        """Test that rates are consistent (triangular arbitrage check)"""
        # Fetch EUR->USD, EUR->GBP, and USD->GBP
        eur_rates = self.provider.get_exchange_rate('EUR', ['USD', 'GBP'])
        usd_rates = self.provider.get_exchange_rate('USD', ['GBP'])

        eur_usd = eur_rates['USD']
        eur_gbp = eur_rates['GBP']
        usd_gbp = usd_rates['GBP']

        print(f"\nTriangular arbitrage check:")
        print(f"  EUR/USD: {eur_usd}")
        print(f"  EUR/GBP: {eur_gbp}")
        print(f"  USD/GBP: {usd_gbp}")
        print(f"  EUR/GBP / EUR/USD = {eur_gbp / eur_usd}")

        # USD/GBP should equal EUR/GBP / EUR/USD (with small rounding error)
        calculated_usd_gbp = eur_gbp / eur_usd
        difference = abs(usd_gbp - calculated_usd_gbp)

        print(f"  Difference: {difference}")

        # Allow up to 0.1% difference due to rounding
        max_difference = usd_gbp * Decimal('0.001')
        self.assertLess(difference, max_difference)

    def test_invalid_currency_handling(self):
        """Test handling of invalid currency codes"""
        # Request a valid and invalid currency
        rates = self.provider.get_exchange_rate('EUR', ['USD', 'INVALID', 'GBP'])

        print(f"\nRequested EUR to USD, INVALID, GBP:")
        print(f"  Returned: {list(rates.keys())}")

        # Should return valid currencies, skip invalid ones
        self.assertIn('USD', rates)
        self.assertIn('GBP', rates)
        # INVALID might be silently skipped or might not be in response

    def test_rate_limits_info(self):
        """Test rate limits information"""
        limits = self.provider.get_rate_limits()

        print(f"\nRate limits: {limits}")

        self.assertIn('requests_per_month', limits)
        self.assertEqual(limits['requests_per_month'], 100)

    def test_credential_redaction(self):
        """Test that credentials are properly redacted"""
        redacted = self.provider.redact_credentials(self.credentials)

        print(f"\nOriginal access_key length: {len(self.credentials['access_key'])}")
        print(f"Redacted access_key: {redacted['access_key']}")

        self.assertNotEqual(redacted['access_key'], self.credentials['access_key'])
        self.assertIn('***', redacted['access_key'])


class TestFixerRatesErrors(unittest.TestCase):
    """Test error handling with invalid credentials"""

    def test_invalid_access_key(self):
        """Test that invalid access key raises appropriate error"""
        invalid_credentials = {'access_key': 'invalid_key_12345'}
        provider = FixerProvider(invalid_credentials)

        result = provider.test_connection()

        print(f"\nInvalid key test result: {result}")

        self.assertFalse(result['success'])
        # Should get 401 or error about invalid key


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
