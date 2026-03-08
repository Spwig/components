"""
XE Currency Data API Provider
Premium exchange rates from XE.com - 220+ currencies from 100+ sources
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, List, Optional, Any
from requests.auth import HTTPBasicAuth
from datetime import datetime

from exchange_rates.providers.base import ExchangeRateProviderBase

logger = logging.getLogger(__name__)


class XEProvider(ExchangeRateProviderBase):
    """
    XE Currency Data API provider implementation

    Features:
    - 220+ currencies from 100+ authoritative sources
    - Dual credential authentication (Account ID + API Key)
    - Automatic package detection and capability awareness
    - Trial mode detection with mock rate warnings
    - Historical data (package dependent)
    - Batch rate fetching
    """

    provider_key = "xe"
    provider_name = "XE Currency Data API"
    BASE_URL = "https://xecdapi.xe.com/v1"
    TIMEOUT = 15  # XE can be slower due to aggregation

    def __init__(self, credentials: Dict[str, str], config: Optional[Dict[str, Any]] = None):
        """
        Initialize XE provider with dual credentials

        Args:
            credentials: Dict with 'account_id' and 'api_key'
            config: Optional configuration dict
        """
        self.account_id = credentials.get('account_id', '').strip()
        self.api_key = credentials.get('api_key', '').strip()
        self.config = config or {}

        if not self.account_id or not self.api_key:
            raise ValueError("Both Account ID and API Key are required for XE provider")

        # Cache for account info (doesn't count against quota!)
        self._account_info_cache = None
        self._currencies_cache = None

    def _get_account_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get account information from /account_info endpoint

        This endpoint is FREE and doesn't count against quota!
        Use it to detect package type, trial mode, etc.

        Args:
            force_refresh: Force refresh cache

        Returns:
            Dict with account details including package type
        """
        if self._account_info_cache and not force_refresh:
            return self._account_info_cache

        try:
            response = requests.get(
                f"{self.BASE_URL}/account_info.json",
                auth=HTTPBasicAuth(self.account_id, self.api_key),
                timeout=self.TIMEOUT
            )

            if response.status_code == 401:
                raise Exception("Authentication failed - invalid Account ID or API Key")
            elif response.status_code == 403:
                raise Exception("Access forbidden - check account status")
            elif response.status_code != 200:
                raise Exception(f"Failed to fetch account info: HTTP {response.status_code}")

            data = response.json()

            # Detect trial mode and mock rates
            package = data.get('package', '').lower()
            is_trial = 'trial' in package

            account_info = {
                'id': data.get('id'),
                'organization': data.get('organization'),
                'package': data.get('package'),
                'service_start': data.get('service_start_timestamp'),
                'is_trial': is_trial,
                'mock_rates': is_trial,  # Trial mode returns mock rates
                'historical_supported': is_trial or 'premium' in package or 'enterprise' in package
            }

            # Cache result
            self._account_info_cache = account_info

            logger.info(f"XE account info: {account_info['organization']} ({account_info['package']} package)")

            if is_trial:
                logger.warning(
                    "⚠️  XE TRIAL MODE: This account returns MOCK RATES, not real market data. "
                    "Upgrade at https://www.xe.com/xecurrencydata/ for production use."
                )

            return account_info

        except requests.exceptions.Timeout:
            raise Exception("Request timeout connecting to XE API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error connecting to XE API: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to XE API by fetching account info

        Returns:
            Dict with success status and account details
        """
        try:
            account_info = self._get_account_info(force_refresh=True)

            result = {
                'success': True,
                'message': f"Connected to XE API successfully",
                'account_id': account_info['id'],
                'organization': account_info['organization'],
                'package': account_info['package'],
                'is_trial': account_info['is_trial']
            }

            # Add prominent warning for trial accounts
            if account_info['is_trial']:
                result['mock_rates_warning'] = (
                    "⚠️  TRIAL MODE: This account returns MOCK RATES, not real market data. "
                    "These rates are for testing purposes only and should NOT be used in production. "
                    "Upgrade to a paid package at https://www.xe.com/xecurrencydata/ for real exchange rates."
                )

            return result

        except Exception as e:
            logger.error(f"XE connection test failed: {str(e)}")
            return {
                'success': False,
                'message': f"Connection failed: {str(e)}"
            }

    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currency codes from /currencies endpoint

        Returns:
            List of ISO 4217 currency codes (220+)
        """
        if self._currencies_cache:
            return self._currencies_cache

        try:
            response = requests.get(
                f"{self.BASE_URL}/currencies.json",
                auth=HTTPBasicAuth(self.account_id, self.api_key),
                timeout=self.TIMEOUT
            )

            if response.status_code == 401:
                raise Exception("Authentication failed - invalid credentials")
            elif response.status_code == 403:
                raise Exception("Quota exceeded or access forbidden")
            elif response.status_code != 200:
                raise Exception(f"Failed to fetch currencies: HTTP {response.status_code}")

            data = response.json()

            # Extract currency codes from response
            # XE returns array of currency objects with 'iso' field
            currencies = []
            for currency in data.get('currencies', []):
                iso_code = currency.get('iso')
                if iso_code:
                    currencies.append(iso_code)

            # Cache result
            self._currencies_cache = currencies

            logger.info(f"XE supports {len(currencies)} currencies")

            return currencies

        except requests.exceptions.Timeout:
            raise Exception("Request timeout fetching currency list")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching currencies: {str(e)}")

    def get_rates(self, base_currency: str, date: Optional[Any] = None) -> Dict[str, Decimal]:
        """
        Get all exchange rates for a base currency

        XE allows comma-separated targets, so we fetch ALL currencies in one call.

        Args:
            base_currency: Base currency code (e.g., 'USD')
            date: Optional date for historical rates (package dependent)

        Returns:
            Dict mapping currency codes to exchange rates
        """
        try:
            # Get all supported currencies
            all_currencies = self.get_supported_currencies()

            # Remove base currency from targets
            target_currencies = [c for c in all_currencies if c != base_currency]

            # Build comma-separated list
            to_param = ','.join(target_currencies)

            # Choose endpoint based on date
            if date:
                # Historical rates endpoint
                account_info = self._get_account_info()

                if not account_info.get('historical_supported'):
                    raise Exception(
                        "Historical rates not supported on your package. "
                        "Upgrade at https://www.xe.com/xecurrencydata/"
                    )

                # Convert date to string if needed
                if hasattr(date, 'strftime'):
                    date_str = date.strftime('%Y-%m-%d')
                else:
                    date_str = str(date)

                url = f"{self.BASE_URL}/historic_rate.json"
                params = {
                    'from': base_currency,
                    'to': to_param,
                    'date': date_str
                }
            else:
                # Live rates endpoint
                url = f"{self.BASE_URL}/convert_from.json"
                params = {
                    'from': base_currency,
                    'to': to_param,
                    'amount': 1
                }

            response = requests.get(
                url,
                params=params,
                auth=HTTPBasicAuth(self.account_id, self.api_key),
                timeout=self.TIMEOUT
            )

            if response.status_code == 401:
                raise Exception("Authentication failed - invalid credentials")
            elif response.status_code == 403:
                raise Exception("Quota exceeded or access forbidden")
            elif response.status_code == 404:
                raise Exception(f"Currency not supported: {base_currency}")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded - too many requests")
            elif response.status_code != 200:
                raise Exception(f"API request failed: HTTP {response.status_code}")

            data = response.json()

            # Parse response
            rates = {}
            for item in data.get('to', []):
                currency_code = item.get('quotecurrency')
                mid_rate = item.get('mid')

                if not currency_code or mid_rate is None:
                    continue

                # Convert to Decimal
                decimal_rate = Decimal(str(mid_rate))

                # Sanity check
                if decimal_rate <= 0 or decimal_rate > Decimal('1000000'):
                    logger.warning(f"Skipping invalid rate for {currency_code}: {decimal_rate}")
                    continue

                rates[currency_code] = decimal_rate

            logger.info(f"Fetched {len(rates)} rates from XE for base currency {base_currency}")

            # Warn if trial mode
            account_info = self._get_account_info()
            if account_info.get('is_trial'):
                logger.warning(
                    f"⚠️  MOCK RATES: {len(rates)} rates fetched are NOT real market data (trial mode)"
                )

            return rates

        except requests.exceptions.Timeout:
            raise Exception("Request timeout fetching exchange rates")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error fetching rates: {str(e)}")

    def get_rate(self, from_currency: str, to_currency: str, date: Optional[Any] = None) -> Decimal:
        """
        Get exchange rate for a specific currency pair

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            date: Optional date for historical rate

        Returns:
            Exchange rate as Decimal
        """
        # Use batch fetching and extract specific pair
        rates = self.get_rates(from_currency, date)

        if to_currency not in rates:
            raise Exception(f"Rate not available for {from_currency} -> {to_currency}")

        return rates[to_currency]

    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get rate limit information

        Note: XE doesn't expose quota in API responses like some other providers.
        We can only return what we know from account info.

        Returns:
            Dict with available rate limit information
        """
        account_info = self._get_account_info()

        return {
            'package': account_info.get('package'),
            'is_trial': account_info.get('is_trial'),
            'requests_per_month': 100 if account_info.get('is_trial') else 'Package-specific',
            'requests_remaining': None,  # Not provided by XE API
            'reset_at': None,
            'service_start': account_info.get('service_start'),
            'note': 'Contact XE for package-specific quota details at https://www.xe.com/xecurrencydata/'
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credential format

        Args:
            credentials: Dict with 'account_id' and 'api_key'

        Raises:
            ValueError: If credentials are invalid
        """
        errors = []

        account_id = credentials.get('account_id', '').strip()
        api_key = credentials.get('api_key', '').strip()

        if not account_id:
            errors.append("Account ID is required")
        elif len(account_id) < 5:
            errors.append("Account ID seems too short")

        if not api_key:
            errors.append("API Key is required")
        elif len(api_key) < 20:
            errors.append("API Key seems too short (should be ~26 characters)")

        if errors:
            raise ValueError('; '.join(errors))

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential information for logging

        Account ID is NOT secret (it's the username for Basic Auth)
        API Key IS secret (it's the password)

        Args:
            credentials: Dict with 'account_id' and 'api_key'

        Returns:
            Dict with redacted credentials
        """
        account_id = credentials.get('account_id', '')
        api_key = credentials.get('api_key', '')

        # Account ID: Show in full (not secret)
        redacted_account_id = account_id

        # API Key: Redact middle (secret)
        if len(api_key) > 6:
            redacted_api_key = f"{api_key[:3]}...{api_key[-3:]}"
        else:
            redacted_api_key = "***"

        return {
            'account_id': redacted_account_id,
            'api_key': redacted_api_key
        }

    @property
    def capabilities(self) -> Dict[str, Any]:
        """
        Get provider capabilities based on account package

        Returns:
            Dict with capability flags
        """
        account_info = self._get_account_info()

        return {
            'live_rates': True,  # All packages
            'historical': account_info.get('historical_supported', False),
            'crypto': False,  # XE doesn't support crypto
            'base_currency_selection': True,
            'batch_requests': True,
            'mock_rates': account_info.get('mock_rates', False)
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for credentials

        Returns:
            Dictionary describing required credentials
        """
        return {
            "account_id": {
                "type": "text",
                "label": "Account ID",
                "required": True,
                "help_text": "Your XE Account ID (not secret - visible in logs)",
                "placeholder": "e.g., yourcompany123456789"
            },
            "api_key": {
                "type": "text",
                "label": "API Key",
                "required": True,
                "help_text": "Your XE API Key (keep secure - will be encrypted)",
                "placeholder": "e.g., abc123def456ghi789jkl012mno"
            }
        }
