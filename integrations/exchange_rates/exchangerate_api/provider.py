"""
ExchangeRate-API Provider
Real-time currency exchange rates from ExchangeRate-API v6
"""
from typing import Dict, List, Any, Optional
from decimal import Decimal
import requests
import logging

from exchange_rates.providers.base import ExchangeRateProviderBase

logger = logging.getLogger(__name__)


class ExchangeRateAPIProvider(ExchangeRateProviderBase):
    """ExchangeRate-API provider implementation"""

    # Required class attributes
    provider_key = "exchangerate_api"
    provider_name = "ExchangeRate-API"

    # API configuration
    BASE_URL = "https://v6.exchangerate-api.com/v6"
    TIMEOUT = 10  # seconds

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with credentials

        Args:
            credentials: Dictionary with api_key
            config: Optional configuration dictionary

        Raises:
            ValueError: If api_key is missing or invalid
        """
        super().__init__(credentials, config)

        self.api_key = credentials.get('api_key')

        if not self.api_key:
            raise ValueError("API Key is required")

        # Validate api_key format (should be alphanumeric)
        if len(self.api_key) < 10:
            raise ValueError("API Key appears to be invalid (too short)")

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return provider capabilities"""
        return {
            'live_rates': True,
            'historical': False,  # Not available on free tier
            'crypto': False,
            'commodities': False,
            'base_currency_selection': True,  # Any base currency supported
            'batch_requests': True  # /latest endpoint returns all rates
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """Return JSON schema for credentials"""
        return {
            "api_key": {
                "type": "text",
                "label": "API Key",
                "required": True,
                "help_text": "Your ExchangeRate-API key from your dashboard",
                "placeholder": "e.g., 1137a55f91aad6c1244b0ac4"
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
        if not credentials.get('api_key'):
            raise ValueError("API Key is required")

        api_key = credentials['api_key']

        # Basic format validation
        if len(api_key) < 10:
            raise ValueError("API Key appears to be invalid (too short)")

        if not all(c.isalnum() for c in api_key):
            raise ValueError("API Key should only contain alphanumeric characters")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()
        if 'api_key' in redacted:
            api_key = redacted['api_key']
            if len(api_key) > 6:
                redacted['api_key'] = f"{api_key[:3]}***{api_key[-3:]}"
            else:
                redacted['api_key'] = "***"
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Test with codes endpoint (lightweight, returns supported currencies)
            response = requests.get(
                f"{self.BASE_URL}/{self.api_key}/codes",
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()

                # Check result field
                if data.get('result') == 'success':
                    # Get quota information
                    quota_info = self._get_quota_info()

                    supported_codes = data.get('supported_codes', [])
                    currency_count = len(supported_codes)

                    return {
                        'success': True,
                        'message': 'Connection successful! API key is valid.',
                        'details': {
                            'status_code': 200,
                            'supported_currencies': currency_count,
                            'plan_quota': quota_info.get('plan_quota'),
                            'requests_remaining': quota_info.get('requests_remaining'),
                            'plan_type': quota_info.get('plan_type', 'unknown')
                        }
                    }
                else:
                    # API returned error
                    error_type = data.get('error-type', 'unknown')

                    if error_type == 'invalid-key':
                        return {
                            'success': False,
                            'message': 'Invalid API Key. Please check your credentials.',
                            'details': {'status_code': 200, 'error': 'invalid-key'}
                        }
                    elif error_type == 'inactive-account':
                        return {
                            'success': False,
                            'message': 'Account is inactive. Please check your account status.',
                            'details': {'status_code': 200, 'error': 'inactive-account'}
                        }
                    elif error_type == 'quota-reached':
                        return {
                            'success': False,
                            'message': 'Rate limit exceeded. Please upgrade your plan or wait for quota reset.',
                            'details': {'status_code': 200, 'error': 'quota-reached'}
                        }
                    else:
                        return {
                            'success': False,
                            'message': f'API error: {error_type}',
                            'details': {'status_code': 200, 'error': error_type}
                        }

            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access forbidden. Your API Key may not have permission to access this endpoint.',
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
                'message': 'Connection error - Unable to reach ExchangeRate-API',
                'details': {'error': 'connection_error'}
            }

        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return {
                'success': False,
                'message': f'Connection error: {str(e)}',
                'details': {'error': str(e)}
            }

    def _get_quota_info(self) -> Dict[str, Any]:
        """
        Get quota information from /quota endpoint

        Returns:
            Dictionary with quota details
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/{self.api_key}/quota",
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('result') == 'success':
                    plan_quota = data.get('plan_quota', 0)

                    # Detect plan type based on quota
                    # Free tier: 30,000 requests/month
                    # Pro tiers: 50,000+
                    if plan_quota <= 30000:
                        plan_type = 'free'
                    elif plan_quota <= 100000:
                        plan_type = 'pro_basic'
                    else:
                        plan_type = 'pro_advanced'

                    return {
                        'plan_quota': plan_quota,
                        'requests_remaining': data.get('requests_remaining'),
                        'refresh_day_of_month': data.get('refresh_day_of_month'),
                        'plan_type': plan_type
                    }

        except Exception as e:
            logger.warning(f"Failed to fetch quota info: {e}")

        return {
            'plan_quota': None,
            'requests_remaining': None,
            'refresh_day_of_month': None,
            'plan_type': 'unknown'
        }

    def get_rates(self, base_currency: str, date: Optional[Any] = None) -> Dict[str, Decimal]:
        """
        Get all exchange rates for a base currency

        Args:
            base_currency: Base currency code (e.g., 'USD')
            date: Optional date for historical rates (not supported)

        Returns:
            Dictionary of {currency_code: rate}

        Raises:
            Exception: If API request fails
        """
        if date is not None:
            raise Exception("Historical rates not supported on free tier")

        base_currency = base_currency.upper()

        try:
            # Make API request
            response = requests.get(
                f"{self.BASE_URL}/{self.api_key}/latest/{base_currency}",
                timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                if response.status_code == 401:
                    raise Exception("Invalid API Key")
                elif response.status_code == 403:
                    raise Exception("Access forbidden - check your API Key permissions")
                elif response.status_code == 429:
                    raise Exception("Rate limit exceeded - upgrade your plan or try again later")
                else:
                    raise Exception(
                        f"API request failed with status {response.status_code}: {response.text[:200]}"
                    )

            # Parse response
            data = response.json()

            # Check result field
            if data.get('result') != 'success':
                error_type = data.get('error-type', 'unknown')

                if error_type == 'invalid-key':
                    raise Exception("Invalid API Key")
                elif error_type == 'quota-reached':
                    raise Exception("Rate limit exceeded - upgrade your plan or try again later")
                elif error_type == 'unsupported-code':
                    raise Exception(f"Unsupported base currency: {base_currency}")
                elif error_type == 'inactive-account':
                    raise Exception("Account is inactive")
                else:
                    raise Exception(f"API error: {error_type}")

            # Extract conversion rates
            conversion_rates = data.get('conversion_rates', {})

            if not conversion_rates:
                raise Exception("No conversion rates in API response")

            # Convert to Decimal and validate
            rates = {}
            for currency, rate in conversion_rates.items():
                # Skip base currency (it will be 1.0)
                if currency == base_currency:
                    continue

                try:
                    decimal_rate = Decimal(str(rate))

                    # Sanity check
                    if decimal_rate <= 0:
                        logger.warning(f"Non-positive rate for {currency}: {decimal_rate}")
                        continue

                    if decimal_rate > Decimal('1000000'):
                        logger.warning(f"Suspiciously high rate for {currency}: {decimal_rate}")
                        continue

                    rates[currency] = decimal_rate

                except (ValueError, TypeError) as e:
                    logger.warning(f"Cannot convert rate for {currency}: {e}")
                    continue

            return rates

        except requests.Timeout:
            raise Exception("API request timeout after 10 seconds")

        except requests.ConnectionError:
            raise Exception("Connection error - unable to reach ExchangeRate-API")

        except Exception as e:
            # Re-raise with context if it's already our exception
            if "API request failed" in str(e) or "Invalid API Key" in str(e):
                raise
            raise Exception(f"Failed to fetch exchange rates: {str(e)}")

    def get_rate(self, from_currency: str, to_currency: str, date: Optional[Any] = None) -> Decimal:
        """
        Get exchange rate between two currencies

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR')
            date: Optional date for historical rate (not supported)

        Returns:
            Exchange rate as Decimal (e.g., 0.85 means 1 USD = 0.85 EUR)

        Raises:
            Exception: If API request fails or rate not available
        """
        if date is not None:
            raise Exception("Historical rates not supported")

        # Fetch all rates for the base currency
        rates = self.get_rates(from_currency, date=None)

        if to_currency.upper() not in rates:
            raise Exception(f"Rate for {from_currency}/{to_currency} not available")

        return rates[to_currency.upper()]

    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currency codes from /codes endpoint

        Returns:
            List of ISO 4217 currency codes
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/{self.api_key}/codes",
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('result') == 'success':
                    # Extract currency codes from [["USD", "United States Dollar"], ...]
                    supported_codes = data.get('supported_codes', [])
                    return [code for code, name in supported_codes]

        except Exception as e:
            logger.warning(f"Failed to fetch supported currencies: {e}")

        # Return comprehensive default list if API call fails
        # ExchangeRate-API supports 160+ currencies
        return [
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'INR',
            'BRL', 'ZAR', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
            'HRK', 'RUB', 'TRY', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'KRW', 'TWD',
            'HKD', 'SGD', 'MYR', 'THB', 'IDR', 'PHP', 'VND', 'ILS', 'SAR', 'AED',
            'KWD', 'QAR', 'BHD', 'OMR', 'JOD', 'EGP', 'MAD', 'NGN', 'KES', 'GHS',
            'ETB', 'UGX', 'TZS', 'XOF', 'XAF', 'CDF', 'AOA', 'MZN', 'ZMW', 'BWP',
            'NAD', 'SZL', 'LSL', 'MUR', 'SCR', 'MGA', 'KMF', 'DJF', 'SOS', 'RWF',
            'BIF', 'GNF', 'SLL', 'LRD', 'GMD', 'MWK', 'CVE', 'STN', 'BSD', 'BBD',
            'BZD', 'TTD', 'HTG', 'JMD', 'KYD', 'XCD', 'AWG', 'ANG', 'BMD', 'SRD',
            'GYD', 'FJD', 'PGK', 'SBD', 'VUV', 'TOP', 'WST', 'KID', 'NIO', 'PAB',
            'CRC', 'GTQ', 'HNL', 'SVC', 'DOP', 'CUP', 'BOB', 'PYG', 'UYU', 'VES',
            'AZN', 'AMD', 'GEL', 'MDL', 'UAH', 'BYN', 'KZT', 'UZS', 'KGS', 'TJS',
            'TMT', 'AFN', 'PKR', 'LKR', 'NPR', 'BDT', 'BTN', 'MVR', 'MMK', 'LAK',
            'KHR', 'MNT', 'IRR', 'IQD', 'SYP', 'LBP', 'YER', 'SDG', 'SSP', 'LYD',
            'TND', 'DZD', 'MRU', 'ERN', 'AED', 'ISK', 'ALL', 'RSD', 'MKD', 'BAM',
            'TRY', 'GEL', 'AED', 'BND', 'FOK', 'GIP', 'IMP', 'JEP', 'SHP', 'TVD',
            'ZWL'
        ]

    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get current rate limit information from /quota endpoint

        Returns:
            Dictionary with rate limit details
        """
        quota_info = self._get_quota_info()

        return {
            'plan_quota': quota_info.get('plan_quota'),
            'requests_remaining': quota_info.get('requests_remaining'),
            'refresh_day_of_month': quota_info.get('refresh_day_of_month'),
            'plan_type': quota_info.get('plan_type'),
            'requests_per_month': quota_info.get('plan_quota'),  # For compatibility
            'requests_per_minute': None,  # No per-minute limit
            'remaining': quota_info.get('requests_remaining'),
            'reset_at': None  # Reset day is provided instead
        }
