"""
DeepL translation provider.

Premium quality translations with advanced neural networks.
Supports formality levels and is especially strong for European languages.
"""
import logging
from typing import Dict, List, Optional, Any

import requests

from translations.providers.base import TranslationProviderBase

logger = logging.getLogger(__name__)


class DeepLProvider(TranslationProviderBase):
    provider_key = 'deepl'
    provider_name = 'DeepL'

    # DeepL language codes
    SUPPORTED_LANGS = [
        'bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'et', 'fi', 'fr',
        'hu', 'id', 'it', 'ja', 'ko', 'lt', 'lv', 'nb', 'nl', 'pl',
        'pt', 'ro', 'ru', 'sk', 'sl', 'sv', 'tr', 'uk', 'zh',
        'ar', 'en-gb', 'en-us', 'pt-br', 'pt-pt',
    ]

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self._api_key = credentials.get('api_key', '')
        # Determine endpoint based on key type
        if self._api_key.endswith(':fx'):
            self._base_url = 'https://api-free.deepl.com/v2'
        else:
            self._base_url = 'https://api.deepl.com/v2'

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'batch_translate': True,
            'language_detection': True,
            'formality': True,
            'glossary': False,
            'html_support': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        return {
            'api_key': {
                'type': 'password',
                'label': 'API Key',
                'help_text': 'Your DeepL API key. Free keys end with :fx',
                'required': True,
            }
        }

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGS

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('api_key'):
            raise ValueError("DeepL API key is required")

    def test_connection(self) -> Dict[str, Any]:
        """Test the DeepL API connection."""
        try:
            headers = {
                'Authorization': f'DeepL-Auth-Key {self._api_key}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {
                'text': 'Hello',
                'source_lang': 'EN',
                'target_lang': 'ES',
            }
            response = requests.post(
                f'{self._base_url}/translate',
                headers=headers,
                data=data,
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'DeepL connection successful!',
                    'supported_languages': len(self.SUPPORTED_LANGS),
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': 'Invalid API key or wrong endpoint (free vs pro)',
                }
            else:
                return {
                    'success': False,
                    'error': f'Connection failed: HTTP {response.status_code}',
                }
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single text string via DeepL."""
        results = self.translate_batch([text], source_lang, target_lang)
        return results[0]

    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """Translate multiple texts in a single DeepL request."""
        headers = {
            'Authorization': f'DeepL-Auth-Key {self._api_key}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'text': texts,
            'source_lang': source_lang.upper(),
            'target_lang': target_lang.upper(),
        }

        response = requests.post(
            f'{self._base_url}/translate',
            headers=headers,
            data=data,
            timeout=self.config.get('timeout', 30),
        )
        response.raise_for_status()

        result = response.json()
        return [t['text'] for t in result['translations']]
