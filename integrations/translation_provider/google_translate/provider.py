"""
Google Translate provider.

Industry-leading translation service with support for 100+ languages.
Uses the Google Cloud Translation API v2.
"""
import logging
from typing import Dict, List, Optional, Any

import requests

from translations.providers.base import TranslationProviderBase

logger = logging.getLogger(__name__)

API_URL = 'https://translation.googleapis.com/language/translate/v2'


class GoogleTranslateProvider(TranslationProviderBase):
    provider_key = 'google_translate'
    provider_name = 'Google Translate'

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
        'ur', 'uz', 'vi', 'xh', 'yi', 'yo', 'zh', 'zh-cn', 'zh-tw',
        'zu',
    ]

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self._api_key = credentials.get('api_key', '')

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'batch_translate': True,
            'language_detection': True,
            'formality': False,
            'glossary': False,
            'html_support': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        return {
            'api_key': {
                'type': 'password',
                'label': 'API Key',
                'help_text': 'Google Cloud Translation API key',
                'required': True,
            }
        }

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGS

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('api_key'):
            raise ValueError("Google Translate API key is required")

    def test_connection(self) -> Dict[str, Any]:
        """Test the Google Translate API connection."""
        try:
            url = f"{API_URL}?key={self._api_key}"
            data = {
                'q': 'Hello',
                'source': 'en',
                'target': 'es',
                'format': 'text',
            }
            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Google Translate connection successful!',
                    'supported_languages': len(self.SUPPORTED_LANGS),
                }
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Connection failed')
                return {'success': False, 'error': error_msg}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single text string via Google Translate."""
        results = self.translate_batch([text], source_lang, target_lang)
        return results[0]

    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """Translate multiple texts via Google Translate API v2."""
        url = f"{API_URL}?key={self._api_key}"
        data = {
            'q': texts,
            'source': source_lang.lower(),
            'target': target_lang.lower(),
            'format': 'text',
        }

        response = requests.post(
            url, json=data,
            timeout=self.config.get('timeout', 30),
        )
        response.raise_for_status()

        result = response.json()
        return [t['translatedText'] for t in result['data']['translations']]
