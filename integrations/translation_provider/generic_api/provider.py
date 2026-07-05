"""
Generic API translation provider.

Connects to any REST-based translation API with configurable
base URL, authentication, and request/response formats.
Ideal for self-hosted translation services or custom API integrations.

Accepts a base URL (e.g., https://translate.example.com:8443) and
constructs endpoint paths automatically:
  - {base_url}/translate       — single translation
  - {base_url}/translate_batch — batch translation
  - {base_url}/health          — health check

An optional translate path override allows non-standard APIs
(e.g., /v2/translate for DeepL-compatible services).
"""
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import requests

from translations.providers.base import TranslationProviderBase

logger = logging.getLogger(__name__)


class GenericAPIProvider(TranslationProviderBase):
    provider_key = 'generic_api'
    provider_name = 'Generic API'

    # Comprehensive list — the actual API may support fewer
    SUPPORTED_LANGS = [
        'af', 'am', 'ar', 'az', 'be', 'bg', 'bn', 'bs', 'ca', 'ceb',
        'co', 'cs', 'cy', 'da', 'de', 'el', 'en', 'eo', 'es', 'et',
        'eu', 'fa', 'fi', 'fr', 'fy', 'ga', 'gd', 'gl', 'gu', 'ha',
        'haw', 'he', 'hi', 'hmn', 'hr', 'ht', 'hu', 'hy', 'id', 'ig',
        'is', 'it', 'ja', 'jw', 'ka', 'kk', 'km', 'kn', 'ko', 'ku',
        'ky', 'la', 'lb', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml',
        'mn', 'mr', 'ms', 'mt', 'my', 'ne', 'nl', 'no', 'ny', 'or',
        'pa', 'pl', 'ps', 'pt', 'ro', 'ru', 'rw', 'sd', 'si', 'sk',
        'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'st', 'su', 'sv', 'sw',
        'ta', 'te', 'tg', 'th', 'tk', 'tl', 'tr', 'tt', 'ug', 'uk',
        'ur', 'uz', 'vi', 'xh', 'yi', 'yo', 'zh', 'zu',
    ]

    # Request format mappings
    FORMATS = {
        'standard': {
            'text_field': 'text',
            'source_field': 'source_lang',
            'target_field': 'target_lang',
            'response_field': 'translated_text',
        },
        'libretranslate': {
            'text_field': 'q',
            'source_field': 'source',
            'target_field': 'target',
            'response_field': 'translatedText',
        },
    }

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self._base_url = credentials.get('base_url', '').rstrip('/')
        self._api_key = credentials.get('api_key', '')
        self._auth_method = credentials.get('auth_method', 'bearer')
        self._request_format = credentials.get('request_format', 'standard')
        self._response_field = credentials.get('response_field', '').strip()
        self._translate_path = credentials.get('translate_path', '').strip() or '/translate'

        # Ensure translate path starts with /
        if not self._translate_path.startswith('/'):
            self._translate_path = '/' + self._translate_path

        # Resolve format config
        fmt = self.FORMATS.get(self._request_format, self.FORMATS['standard'])
        self._text_field = fmt['text_field']
        self._source_field = fmt['source_field']
        self._target_field = fmt['target_field']
        # Custom response field overrides format default
        self._resp_field = self._response_field or fmt['response_field']

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'batch_translate': True,
            'language_detection': False,
            'formality': False,
            'glossary': False,
            'html_support': False,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        return {
            'base_url': {
                'type': 'url',
                'label': 'API Base URL',
                'help_text': 'Base URL of the translation service (e.g., https://translate.example.com:8443)',
                'required': True,
                'placeholder': 'https://translate.example.com',
            },
            'api_key': {
                'type': 'password',
                'label': 'API Key',
                'help_text': 'API key for authentication (leave empty if not required)',
                'required': False,
                'placeholder': 'Enter your API key',
            },
            'auth_method': {
                'type': 'select',
                'label': 'Authentication Method',
                'help_text': 'How to send the API key in requests',
                'required': False,
                'default': 'bearer',
                'options': [
                    {'value': 'bearer', 'label': 'Bearer Token (Authorization header)'},
                    {'value': 'x-api-key', 'label': 'X-API-Key Header'},
                    {'value': 'query', 'label': 'Query Parameter (?api_key=...)'},
                    {'value': 'none', 'label': 'No Authentication'},
                ],
            },
            'request_format': {
                'type': 'select',
                'label': 'Request Format',
                'help_text': 'How the API expects translation requests',
                'required': False,
                'default': 'standard',
                'options': [
                    {'value': 'standard', 'label': 'Standard (text, source_lang, target_lang)'},
                    {'value': 'libretranslate', 'label': 'LibreTranslate (q, source, target)'},
                ],
            },
            'translate_path': {
                'type': 'text',
                'label': 'Translate Path',
                'help_text': 'Path for the translate endpoint (default: /translate). Change for APIs with different paths (e.g., /v2/translate)',
                'required': False,
                'default': '/translate',
                'placeholder': '/translate',
            },
            'response_field': {
                'type': 'text',
                'label': 'Response Field',
                'help_text': 'JSON field name in the API response containing the translated text (leave empty for format default)',
                'required': False,
                'default': '',
                'placeholder': 'translated_text',
            },
        }

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGS

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        base_url = credentials.get('base_url', '').strip()
        if not base_url:
            raise ValueError("API Base URL is required")
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError("API Base URL must start with http:// or https://")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers based on auth configuration."""
        headers = {'Content-Type': 'application/json'}
        if self._api_key and self._auth_method == 'bearer':
            headers['Authorization'] = f'Bearer {self._api_key}'
        elif self._api_key and self._auth_method == 'x-api-key':
            headers['X-API-Key'] = self._api_key
        return headers

    def _build_url(self, path: str) -> str:
        """Build full request URL from base URL + path, with query param auth if configured."""
        url = self._base_url + path
        if self._api_key and self._auth_method == 'query':
            sep = '&' if '?' in url else '?'
            url = f'{url}{sep}{urlencode({"api_key": self._api_key})}'
        return url

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection.

        First tries GET {base_url}/health. If that works, also runs a
        test translation to verify the translate endpoint. If /health
        is not available, falls back to just the test translation.
        """
        health_info = ''

        # Try health endpoint first
        try:
            resp = requests.get(
                self._build_url('/health'),
                headers=self._build_headers(),
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'backends' in data:
                    healthy = sum(1 for b in data['backends'] if b.get('healthy'))
                    total = len(data['backends'])
                    health_info = f' ({healthy}/{total} backends healthy)'
        except Exception:
            pass  # Health endpoint is optional

        # Test translation
        try:
            payload = {
                self._text_field: 'Hello',
                self._source_field: 'en',
                self._target_field: 'es',
            }

            response = requests.post(
                self._build_url(self._translate_path),
                json=payload,
                headers=self._build_headers(),
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                translated = self._extract_translation(data)
                if translated:
                    safe_text = translated[:200].replace('<', '&lt;').replace('>', '&gt;')
                    msg = f'Connection successful! Test: "Hello" \u2192 "{safe_text}"'
                    if health_info:
                        msg += health_info
                    return {'success': True, 'message': msg}
                return {
                    'success': False,
                    'error': 'API returned 200 but the configured response field was not found in the response',
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Authentication failed (401). Check your API key and auth method.',
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': 'Access forbidden (403). Check your API key permissions.',
                }
            else:
                return {
                    'success': False,
                    'error': f'API returned HTTP {response.status_code}',
                }
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Could not connect to the API. Check the base URL.'}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Connection timed out. The API may be slow or unreachable.'}
        except requests.exceptions.RequestException as e:
            logger.error("Generic API connection error: %s", e)
            return {'success': False, 'error': 'Connection error. Check the API base URL and try again.'}

    def _extract_translation(self, data: Any) -> Optional[str]:
        """Extract translated text from API response using configured field."""
        if isinstance(data, dict):
            # Try direct field access
            if self._resp_field in data:
                return str(data[self._resp_field])
            # Try nested dot notation (e.g., "data.translation")
            if '.' in self._resp_field:
                obj = data
                for part in self._resp_field.split('.'):
                    if isinstance(obj, dict) and part in obj:
                        obj = obj[part]
                    else:
                        return None
                return str(obj)
        return None

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single text string via the configured API."""
        payload = {
            self._text_field: text,
            self._source_field: source_lang,
            self._target_field: target_lang,
        }

        response = requests.post(
            self._build_url(self._translate_path),
            json=payload,
            headers=self._build_headers(),
            timeout=self.config.get('timeout', 30),
        )
        response.raise_for_status()

        data = response.json()
        result = self._extract_translation(data)
        if result is None:
            raise ValueError(
                f'Response field "{self._resp_field}" not found in API response'
            )
        return result

    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """
        Translate multiple texts.

        Tries the batch endpoint ({base_url}/translate_batch) first.
        Falls back to sequential single requests if batch is unavailable.
        """
        # Build batch payload in standard format
        items = []
        for i, text in enumerate(texts):
            items.append({
                'id': str(i),
                'text': text,
                'source_lang': source_lang,
                'target_lang': target_lang,
            })

        # Try batch endpoint
        try:
            response = requests.post(
                self._build_url('/translate_batch'),
                json={'items': items},
                headers=self._build_headers(),
                timeout=self.config.get('timeout', 30) * 2,
            )
            if response.status_code == 200:
                data = response.json()
                results_list = data.get('results', [])
                # Build ordered result list from batch response
                result_map = {}
                for item in results_list:
                    item_id = item.get('id', '')
                    translated = item.get('translated_text', '')
                    if translated:
                        result_map[item_id] = translated
                return [result_map.get(str(i), texts[i]) for i in range(len(texts))]
        except Exception:
            logger.debug("Batch endpoint unavailable, falling back to sequential requests")

        # Fallback: sequential single requests
        results = []
        for text in texts:
            results.append(self.translate(text, source_lang, target_lang))
        return results
