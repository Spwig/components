"""
DataForSEO Provider

Professional SEO content generation powered by DataForSEO's Content Generation
API. Generates optimized meta titles, descriptions, and keywords using
DataForSEO's data-driven approach.

Author: Spwig
"""

import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Optional, Any, List

from seo_generator.providers.base import BaseSEOProvider, GenerationError

logger = logging.getLogger(__name__)


class DataForSEOProvider(BaseSEOProvider):
    """
    DataForSEO-powered SEO generation provider.

    Uses the DataForSEO Content Generation API for meta tag generation
    and keyword extraction. Authentication is via HTTP Basic Auth.
    """

    provider_key = 'dataforseo'
    provider_name = 'DataForSEO'
    requires_credentials = True

    BASE_URL = 'https://api.dataforseo.com/v3'
    TIMEOUT = 30

    # Language code mapping for DataForSEO API
    LANGUAGE_MAP = {
        'en': 'en', 'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it',
        'pt': 'pt', 'nl': 'nl', 'ru': 'ru', 'ja': 'ja', 'ko': 'ko',
        'zh': 'zh', 'ar': 'ar', 'hi': 'hi', 'tr': 'tr', 'pl': 'pl',
        'sv': 'sv', 'da': 'da', 'no': 'no', 'fi': 'fi', 'th': 'th',
        'vi': 'vi', 'id': 'id',
    }

    def __init__(self, credentials: Optional[Dict[str, Any]] = None,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.login = self.credentials.get('login', '')
        self.password = self.credentials.get('password', '')
        self._auth = HTTPBasicAuth(self.login, self.password)

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'meta_title': True,
            'meta_description': True,
            'keywords': True,
            'multi_language': True,
            'bulk_generation': True,
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('login'):
            raise ValueError("Login email is required")
        if not credentials.get('password'):
            raise ValueError("API password is required")
        if len(credentials['password']) < 8:
            raise ValueError("API password must be at least 8 characters")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        redacted = credentials.copy()
        if 'password' in redacted and redacted['password']:
            val = str(redacted['password'])
            if len(val) > 6:
                redacted['password'] = val[:3] + '***' + val[-3:]
            else:
                redacted['password'] = '***'
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/appendix/user_data",
                auth=self._auth,
                timeout=self.TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 20000:
                    user_data = data.get('tasks', [{}])[0].get('result', [{}])[0] if data.get('tasks') else {}
                    return {
                        'success': True,
                        'message': 'Connected to DataForSEO',
                        'details': {
                            'login': user_data.get('login', self.login),
                            'money_balance': user_data.get('money', {}).get('balance', 'N/A'),
                        },
                    }
                else:
                    error_msg = data.get('status_message', 'Unknown error')
                    return {
                        'success': False,
                        'message': f'API error: {error_msg}',
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Authentication failed. Check your login and API password.',
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access denied. Your account may be inactive.',
                }
            else:
                return {
                    'success': False,
                    'message': f'API returned status {response.status_code}',
                }
        except requests.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except requests.ConnectionError:
            return {'success': False, 'message': 'Could not connect to DataForSEO API'}
        except Exception as e:
            logger.warning("Unexpected error in test_connection: %s", e)
            return {'success': False, 'message': f'Unexpected error: {e}'}

    def _build_content_text(self, content: Dict[str, str]) -> str:
        """Build a combined text string from content fields."""
        parts = []
        name = content.get('name', '')
        description = content.get('description', '')
        category = content.get('category', '')
        brand = content.get('brand', '')
        content_type = content.get('type', 'product')

        if name:
            parts.append(name)
        if brand:
            parts.append(f"Brand: {brand}")
        if category:
            parts.append(f"Category: {category}")
        if description:
            # Truncate to avoid excessive API costs
            parts.append(description[:500])

        return '. '.join(parts)

    def _get_language(self, language: str) -> str:
        """Map language code to DataForSEO language code."""
        return self.LANGUAGE_MAP.get(language, 'en')

    def generate_meta_title(self, content: Dict[str, str], language: str = 'en') -> str:
        try:
            text = self._build_content_text(content)
            if not text:
                raise GenerationError("No content provided for title generation")

            response = requests.post(
                f"{self.BASE_URL}/content_generation/generate_meta_tags/live",
                auth=self._auth,
                json=[{
                    'text': text,
                    'target_language': self._get_language(language),
                }],
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed. Check your credentials.")
            if response.status_code == 402:
                raise GenerationError("Insufficient balance. Top up your DataForSEO account.")

            data = response.json()
            if data.get('status_code') != 20000:
                error_msg = data.get('status_message', 'Unknown error')
                raise GenerationError(f"DataForSEO API error: {error_msg}")

            tasks = data.get('tasks', [])
            if not tasks or not tasks[0].get('result'):
                raise GenerationError("No results returned from DataForSEO")

            result = tasks[0]['result'][0]
            title = result.get('title', '')

            if not title:
                # Fallback: construct from name
                title = content.get('name', '')[:60]

            # Truncate to 60 chars
            if len(title) > 60:
                title = title[:57] + '...'

            return title

        except GenerationError:
            raise
        except requests.Timeout:
            raise GenerationError("DataForSEO API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to DataForSEO API")
        except Exception as e:
            raise GenerationError(f"Meta title generation failed: {e}")

    def generate_meta_description(self, content: Dict[str, str], language: str = 'en') -> str:
        try:
            text = self._build_content_text(content)
            if not text:
                raise GenerationError("No content provided for description generation")

            response = requests.post(
                f"{self.BASE_URL}/content_generation/generate_meta_tags/live",
                auth=self._auth,
                json=[{
                    'text': text,
                    'target_language': self._get_language(language),
                }],
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed. Check your credentials.")
            if response.status_code == 402:
                raise GenerationError("Insufficient balance. Top up your DataForSEO account.")

            data = response.json()
            if data.get('status_code') != 20000:
                error_msg = data.get('status_message', 'Unknown error')
                raise GenerationError(f"DataForSEO API error: {error_msg}")

            tasks = data.get('tasks', [])
            if not tasks or not tasks[0].get('result'):
                raise GenerationError("No results returned from DataForSEO")

            result = tasks[0]['result'][0]
            description = result.get('description', '')

            if not description:
                description = content.get('description', content.get('name', ''))[:155]

            if len(description) > 155:
                description = description[:152] + '...'

            return description

        except GenerationError:
            raise
        except requests.Timeout:
            raise GenerationError("DataForSEO API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to DataForSEO API")
        except Exception as e:
            raise GenerationError(f"Meta description generation failed: {e}")

    def generate_seo(self, content: Dict[str, str], language: str = 'en') -> Dict[str, Any]:
        """
        Override to make a single API call for both title and description.

        The DataForSEO generate_meta_tags endpoint returns both title and
        description in one response, so we avoid duplicate calls.
        """
        try:
            text = self._build_content_text(content)
            if not text:
                raise GenerationError("No content provided for SEO generation")

            response = requests.post(
                f"{self.BASE_URL}/content_generation/generate_meta_tags/live",
                auth=self._auth,
                json=[{
                    'text': text,
                    'target_language': self._get_language(language),
                }],
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed. Check your credentials.")
            if response.status_code == 402:
                raise GenerationError("Insufficient balance. Top up your DataForSEO account.")

            data = response.json()
            if data.get('status_code') != 20000:
                error_msg = data.get('status_message', 'Unknown error')
                raise GenerationError(f"DataForSEO API error: {error_msg}")

            tasks = data.get('tasks', [])
            if not tasks or not tasks[0].get('result'):
                raise GenerationError("No results returned from DataForSEO")

            result = tasks[0]['result'][0]
            title = result.get('title', content.get('name', '')[:60])
            description = result.get('description', '')

            if len(title) > 60:
                title = title[:57] + '...'
            if len(description) > 155:
                description = description[:152] + '...'

            # Keywords still need a separate call
            keywords = self.extract_keywords(content)

            return {
                'meta_title': title,
                'meta_description': description,
                'keywords': keywords,
            }

        except GenerationError:
            raise
        except requests.Timeout:
            raise GenerationError("DataForSEO API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to DataForSEO API")
        except Exception as e:
            raise GenerationError(f"SEO generation failed: {e}")

    def extract_keywords(self, content: Dict[str, str], max_keywords: int = 10) -> List[str]:
        try:
            text = self._build_content_text(content)
            if not text:
                raise GenerationError("No content provided for keyword extraction")

            response = requests.post(
                f"{self.BASE_URL}/content_generation/text_summary/live",
                auth=self._auth,
                json=[{
                    'text': text,
                }],
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed. Check your credentials.")

            data = response.json()
            if data.get('status_code') != 20000:
                # Fall back to extracting from content locally
                return self._extract_keywords_fallback(content, max_keywords)

            tasks = data.get('tasks', [])
            if not tasks or not tasks[0].get('result'):
                return self._extract_keywords_fallback(content, max_keywords)

            result = tasks[0]['result'][0]
            # DataForSEO text_summary returns keyword_density
            keyword_density = result.get('keyword_density', {})

            if keyword_density:
                # Sort by frequency/density and return top keywords
                sorted_keywords = sorted(
                    keyword_density.items(),
                    key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                    reverse=True,
                )
                keywords = [kw for kw, _ in sorted_keywords[:max_keywords]]
                return keywords

            return self._extract_keywords_fallback(content, max_keywords)

        except GenerationError:
            raise
        except requests.Timeout:
            raise GenerationError("DataForSEO API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to DataForSEO API")
        except Exception as e:
            raise GenerationError(f"Keyword extraction failed: {e}")

    def _extract_keywords_fallback(self, content: Dict[str, str],
                                    max_keywords: int = 10) -> List[str]:
        """Simple keyword extraction when API endpoint is unavailable."""
        keywords = []
        name = content.get('name', '')
        if name:
            # Split name into words and use as keywords
            words = [w.strip().lower() for w in name.split() if len(w.strip()) > 2]
            keywords.extend(words)

        brand = content.get('brand', '')
        if brand:
            keywords.append(brand.lower())

        category = content.get('category', '')
        if category:
            keywords.append(category.lower())

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:max_keywords]
