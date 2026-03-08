"""
Open Exchange Rates Provider
Real-time currency exchange rates from Open Exchange Rates API
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal
import requests
import logging

from exchange_rates.providers.base import ExchangeRateProviderBase

logger = logging.getLogger(__name__)


class OpenExchangeRatesProvider(ExchangeRateProviderBase):
    """Open Exchange Rates provider implementation"""

    # Required class attributes
    provider_key = "open_exchange_rates"
    provider_name = "Open Exchange Rates"

    # API configuration
    BASE_URL = "https://openexchangerates.org/api"
    TIMEOUT = 10  # seconds

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with credentials

        Args:
            credentials: Dictionary with app_id
            config: Optional configuration dictionary

        Raises:
            ValueError: If app_id is missing or invalid
        """
        super().__init__(credentials, config)

        self.app_id = credentials.get('app_id')

        if not self.app_id:
            raise ValueError("App ID is required")

        # Validate app_id format (should be 32 character hex string)
        if len(self.app_id) < 10:
            raise ValueError("App ID appears to be invalid (too short)")

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
            "app_id": {
                "type": "text",
                "label": "App ID",
                "required": True,
                "help_text": "Your Open Exchange Rates App ID from the dashboard",
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
        if not credentials.get('app_id'):
            raise ValueError("App ID is required")

        app_id = credentials['app_id']

        # Basic format validation
        if len(app_id) < 10:
            raise ValueError("App ID appears to be invalid (too short)")

        if not all(c.isalnum() for c in app_id):
            raise ValueError("App ID should only contain alphanumeric characters")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()
        if 'app_id' in redacted:
            app_id = redacted['app_id']
            if len(app_id) > 6:
                redacted['app_id'] = f"{app_id[:3]}***{app_id[-3:]}"
            else:
                redacted['app_id'] = "***"
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Test with currencies endpoint (lightweight, doesn't count against rate limit as much)
            response = requests.get(
                f"{self.BASE_URL}/currencies.json",
                params={'app_id': self.app_id},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                currency_count = len(data) if isinstance(data, dict) else 0

                return {
                    'success': True,
                    'message': f'Successfully connected to Open Exchange Rates API ({currency_count} currencies available)',
                    'details': {
                        'currency_count': currency_count,
                        'api_version': 'v1',
                        'base_currency': 'USD'
                    }
                }

            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid App ID. Please check your credentials.',
                    'details': {'status_code': 401, 'error': 'unauthorized'}
                }

            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access forbidden. Your App ID may not have permission to access this endpoint.',
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
                'message': 'Connection error - Unable to reach Open Exchange Rates API',
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
            # Make API request - Open Exchange Rates always returns rates relative to USD
            response = requests.get(
                f"{self.BASE_URL}/latest.json",
                params={
                    'app_id': self.app_id,
                    # Free tier doesn't support base parameter, always USD
                    # 'symbols': ','.join(target_currencies)  # Also not supported on free tier
                },
                timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                if response.status_code == 401:
                    raise Exception("Invalid App ID")
                elif response.status_code == 403:
                    raise Exception("Access forbidden - check your App ID permissions")
                elif response.status_code == 429:
                    raise Exception("Rate limit exceeded - upgrade your plan or try again later")
                else:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text[:200]}"
                    )

            # Parse response
            data = response.json()

            # Validate response structure
            if not isinstance(data, dict) or 'rates' not in data:
                raise Exception("Invalid API response format - missing 'rates' field")

            all_rates = data['rates']

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
            raise Exception("Connection error - unable to reach Open Exchange Rates API")

        except Exception as e:
            # Re-raise with context if it's already our exception
            if "API request failed" in str(e) or "Invalid App ID" in str(e):
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
                f"{self.BASE_URL}/currencies.json",
                params={'app_id': self.app_id},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    return list(data.keys())

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
        # Open Exchange Rates doesn't provide rate limit info in response headers on free tier
        return {
            'requests_per_month': 1000,  # Free tier limit
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
