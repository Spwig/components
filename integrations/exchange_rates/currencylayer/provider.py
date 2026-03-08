"""
Currencylayer Provider
Real-time currency exchange rates from Currencylayer API
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal
import requests
import logging

from exchange_rates.providers.base import ExchangeRateProviderBase

logger = logging.getLogger(__name__)


class CurrencylayerProvider(ExchangeRateProviderBase):
    """Currencylayer provider implementation"""

    # Required class attributes
    provider_key = "currencylayer"
    provider_name = "Currencylayer"

    # API configuration
    BASE_URL = "https://api.currencylayer.com/api"
    TIMEOUT = 10  # seconds

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with credentials

        Args:
            credentials: Dictionary with access_key
            config: Optional configuration dictionary

        Raises:
            ValueError: If access_key is missing or invalid
        """
        super().__init__(credentials, config)

        self.access_key = credentials.get('access_key')

        if not self.access_key:
            raise ValueError("Access Key is required")

        # Validate access_key format (should be 32 character hex string)
        if len(self.access_key) < 10:
            raise ValueError("Access Key appears to be invalid (too short)")

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities"""
        return {
            'live_rates': True,
            'historical': False,  # Free tier doesn't support historical
            'crypto': False,
            'commodities': False,
            'base_currency_selection': False,  # Free tier only supports USD base
            'batch_requests': False
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """Return JSON schema for credentials"""
        return {
            "access_key": {
                "type": "text",
                "label": "Access Key",
                "required": True,
                "help_text": "Your Currencylayer Access Key from the APILayer dashboard",
                "placeholder": "e.g., abc123def456..."
            }
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credential format

        Args:
            credentials: Credentials dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        if not credentials.get('access_key'):
            raise ValueError("Access Key is required")

        access_key = credentials['access_key']

        # Basic format validation
        if len(access_key) < 10:
            raise ValueError("Access Key appears to be invalid (too short)")

        if not all(c.isalnum() for c in access_key):
            raise ValueError("Access Key should only contain alphanumeric characters")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()
        if 'access_key' in redacted:
            access_key = redacted['access_key']
            if len(access_key) > 6:
                redacted['access_key'] = f"{access_key[:3]}***{access_key[-3:]}"
            else:
                redacted['access_key'] = "***"
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Test with list endpoint (lightweight, returns supported currencies)
            response = requests.get(
                f"{self.BASE_URL}/list",
                params={'access_key': self.access_key},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()

                # Check for API error in successful response
                if not data.get('success', False):
                    error_info = data.get('error', {})
                    error_code = error_info.get('code', 'unknown')
                    error_message = error_info.get('info', 'Unknown error')

                    if error_code == 101:
                        return {
                            'success': False,
                            'message': 'Invalid Access Key. Please check your credentials.',
                            'details': {'status_code': 200, 'error': 'invalid_access_key'}
                        }
                    elif error_code == 104:
                        return {
                            'success': False,
                            'message': 'Rate limit exceeded. Please upgrade your plan or try again later.',
                            'details': {'status_code': 200, 'error': 'rate_limited'}
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'API error: {error_message}',
                            'details': {'status_code': 200, 'error': error_code}
                        }

                currencies = data.get('currencies', {})
                currency_count = len(currencies) if isinstance(currencies, dict) else 0

                return {
                    'success': True,
                    'message': f'Successfully connected to Currencylayer API ({currency_count} currencies available)',
                    'details': {
                        'currency_count': currency_count,
                        'api_version': 'v1',
                        'base_currency': 'USD'
                    }
                }

            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid Access Key. Please check your credentials.',
                    'details': {'status_code': 401, 'error': 'unauthorized'}
                }

            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access forbidden. Your Access Key may not have permission to access this endpoint.',
                    'details': {'status_code': 403, 'error': 'forbidden'}
                }

            elif response.status_code == 429:
                return {
                    'success': False,
                    'message': 'Rate limit exceeded. Please upgrade your plan or try again later.',
                    'details': {'status_code': 429, 'error': 'rate_limited'}
                }

            else:
                return {
                    'success': False,
                    'message': f'API error: HTTP {response.status_code}',
                    'details': {
                        'status_code': response.status_code,
                        'response': response.text[:200]  # First 200 chars
                    }
                }

        except requests.Timeout:
            return {
                'success': False,
                'message': 'Connection timeout - API is not responding',
                'details': {'error': 'timeout'}
            }

        except requests.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error - Unable to reach Currencylayer API',
                'details': {'error': 'connection_error'}
            }

        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return {
                'success': False,
                'message': f'Connection error: {str(e)}',
                'details': {'error': str(e)}
            }

    def get_exchange_rate(
        self,
        base_currency: str,
        target_currencies: List[str]
    ) -> Dict[str, Decimal]:
        """
        Fetch exchange rates for given currency pairs

        Note: Free tier only supports USD as base currency.
        If base_currency is not USD, we fetch USD rates and calculate conversions.

        Args:
            base_currency: Base currency code (e.g., 'USD')
            target_currencies: List of target currency codes

        Returns:
            Dictionary mapping currency codes to exchange rates as Decimals
            Example: {'EUR': Decimal('0.85'), 'GBP': Decimal('0.73')}

        Raises:
            Exception: If API request fails
        """
        # Validate inputs
        if not base_currency or not isinstance(base_currency, str):
            raise ValueError("base_currency must be a non-empty string")

        if not target_currencies or not isinstance(target_currencies, list):
            raise ValueError("target_currencies must be a non-empty list")

        # Remove duplicates and filter out base currency
        target_currencies = [c.upper() for c in set(target_currencies) if c.upper() != base_currency.upper()]

        if not target_currencies:
            return {}

        base_currency = base_currency.upper()

        try:
            # Make API request - Currencylayer always returns rates relative to USD
            response = requests.get(
                f"{self.BASE_URL}/live",
                params={
                    'access_key': self.access_key,
                    # Free tier doesn't support source parameter, always USD
                    # 'currencies': ','.join(target_currencies)  # Also not supported on free tier
                },
                timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                if response.status_code == 401:
                    raise Exception("Invalid Access Key")
                elif response.status_code == 403:
                    raise Exception("Access forbidden - check your Access Key permissions")
                elif response.status_code == 429:
                    raise Exception("Rate limit exceeded - upgrade your plan or try again later")
                else:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text[:200]}"
                    )

            # Parse response
            data = response.json()

            # Check for API error in successful response
            if not data.get('success', False):
                error_info = data.get('error', {})
                error_code = error_info.get('code', 'unknown')
                error_message = error_info.get('info', 'Unknown error')

                if error_code == 101:
                    raise Exception("Invalid Access Key")
                elif error_code == 104:
                    raise Exception("Rate limit exceeded - upgrade your plan or try again later")
                else:
                    raise Exception(f"API error: {error_message}")

            # Validate response structure
            if 'quotes' not in data:
                raise Exception("Invalid API response format - missing 'quotes' field")

            all_quotes = data['quotes']

            # Currencylayer returns rates with keys like 'USDEUR', 'USDGBP'
            # We need to convert these to just the currency code
            all_rates = {}
            for key, value in all_quotes.items():
                if key.startswith('USD'):
                    currency = key[3:]  # Remove 'USD' prefix
                    all_rates[currency] = value

            # If base currency is USD, directly extract target rates
            if base_currency == 'USD':
                rates = {}
                for currency in target_currencies:
                    if currency not in all_rates:
                        logger.warning(f"Rate for {currency} not in API response")
                        continue

                    try:
                        rate_decimal = Decimal(str(all_rates[currency]))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Cannot convert rate for {currency}: {e}")
                        continue

                    # Sanity check
                    if rate_decimal <= 0:
                        logger.warning(f"Non-positive rate for {currency}: {rate_decimal}")
                        continue

                    if rate_decimal > Decimal('1000000'):
                        logger.warning(f"Suspiciously high rate for {currency}: {rate_decimal}")
                        continue

                    rates[currency] = rate_decimal

                return rates

            else:
                # Base currency is not USD - need to convert
                # Formula: rate_EUR_GBP = rate_USD_GBP / rate_USD_EUR

                if base_currency not in all_rates:
                    raise Exception(f"Base currency {base_currency} not available in API response")

                base_rate = Decimal(str(all_rates[base_currency]))

                if base_rate <= 0:
                    raise Exception(f"Invalid base rate for {base_currency}: {base_rate}")

                rates = {}
                for currency in target_currencies:
                    if currency not in all_rates:
                        logger.warning(f"Rate for {currency} not in API response")
                        continue

                    try:
                        target_rate = Decimal(str(all_rates[currency]))
                        # Convert: if we want EUR to GBP, and we have USD to EUR and USD to GBP
                        # EUR_GBP = USD_GBP / USD_EUR
                        converted_rate = target_rate / base_rate
                    except (ValueError, TypeError, ZeroDivisionError) as e:
                        logger.warning(f"Cannot convert rate for {currency}: {e}")
                        continue

                    # Sanity check
                    if converted_rate <= 0:
                        logger.warning(f"Non-positive converted rate for {currency}: {converted_rate}")
                        continue

                    if converted_rate > Decimal('1000000'):
                        logger.warning(f"Suspiciously high converted rate for {currency}: {converted_rate}")
                        continue

                    rates[currency] = converted_rate

                return rates

        except requests.Timeout:
            raise Exception("API request timeout after 10 seconds")

        except requests.ConnectionError:
            raise Exception("Connection error - unable to reach Currencylayer API")

        except Exception as e:
            # Re-raise with context if it's already our exception
            if "API request failed" in str(e) or "Invalid Access Key" in str(e):
                raise
            raise Exception(f"Failed to fetch exchange rates: {str(e)}")

    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currency codes

        Returns:
            List of ISO 4217 currency codes
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/list",
                params={'access_key': self.access_key},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success', False) and isinstance(data.get('currencies'), dict):
                    return list(data['currencies'].keys())

        except Exception as e:
            logger.warning(f"Failed to fetch supported currencies: {e}")

        # Return default list if API call fails
        return [
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'INR',
            'BRL', 'ZAR', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
            'HRK', 'RUB', 'TRY', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'KRW', 'TWD',
            'HKD', 'SGD', 'MYR', 'THB', 'IDR', 'PHP', 'VND', 'ILS', 'SAR', 'AED'
        ]

    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get current rate limit information

        Returns:
            Dictionary with rate limit details
        """
        # Currencylayer doesn't provide rate limit info in response headers on free tier
        return {
            'requests_per_month': 100,  # Free tier limit
            'requests_per_minute': None,
            'remaining': None,  # Not provided by API
            'reset_at': None    # Not provided by API
        }

    def get_rate(self, from_currency: str, to_currency: str, date: Optional[Any] = None) -> Decimal:
        """
        Get exchange rate between two currencies (implements base class abstract method)

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR')
            date: Optional date for historical rate (not supported on free tier)

        Returns:
            Exchange rate as Decimal (e.g., 0.85 means 1 USD = 0.85 EUR)

        Raises:
            Exception: If API request fails or rate not available
        """
        if date is not None:
            raise Exception("Historical rates not supported on free tier")

        rates = self.get_exchange_rate(from_currency, [to_currency])

        if to_currency not in rates:
            raise Exception(f"Rate for {from_currency}/{to_currency} not available")

        return rates[to_currency]

    def get_rates(self, base_currency: str, date: Optional[Any] = None) -> Dict[str, Decimal]:
        """
        Get all exchange rates for a base currency (implements base class abstract method)

        Args:
            base_currency: Base currency code (e.g., 'USD')
            date: Optional date for historical rates (not supported on free tier)

        Returns:
            Dictionary of {currency_code: rate}

        Raises:
            Exception: If API request fails
        """
        if date is not None:
            raise Exception("Historical rates not supported on free tier")

        # Fetch all supported currencies
        supported_currencies = self.get_supported_currencies()

        # Remove base currency from the list
        target_currencies = [c for c in supported_currencies if c != base_currency.upper()]

        # Fetch rates for all target currencies
        return self.get_exchange_rate(base_currency, target_currencies)
