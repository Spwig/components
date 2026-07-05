"""
Azure Translator provider.

Microsoft's cloud translation service with extensive customization options
and enterprise features. Uses Azure Cognitive Services Translator v3.0.
"""
import logging
import uuid as uuid_lib
from typing import Dict, List, Optional, Any

import requests

from translations.providers.base import TranslationProviderBase

logger = logging.getLogger(__name__)

API_URL = 'https://api.cognitive.microsofttranslator.com'


class AzureTranslatorProvider(TranslationProviderBase):
    provider_key = 'azure_translator'
    provider_name = 'Azure Translator'

    SUPPORTED_LANGS = [
        'af', 'am', 'ar', 'as', 'az', 'ba', 'bg', 'bn', 'bo', 'bs',
        'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'es', 'et', 'eu',
        'fa', 'fi', 'fil', 'fj', 'fo', 'fr', 'ga', 'gl', 'gu', 'ha',
        'he', 'hi', 'hr', 'hsb', 'ht', 'hu', 'hy', 'id', 'ig', 'ikt',
        'is', 'it', 'iu', 'ja', 'ka', 'kk', 'km', 'kn', 'ko', 'ku',
        'ky', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mr',
        'ms', 'mt', 'my', 'nb', 'ne', 'nl', 'or', 'pa', 'pl', 'ps',
        'pt', 'ro', 'ru', 'rw', 'sd', 'si', 'sk', 'sl', 'sm', 'so',
        'sq', 'sr', 'st', 'sv', 'sw', 'ta', 'te', 'th', 'ti', 'tk',
        'tl', 'to', 'tr', 'tt', 'ty', 'ug', 'uk', 'ur', 'uz', 'vi',
        'xh', 'yo', 'yua', 'zh-hans', 'zh-hant', 'zu',
    ]

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self._api_key = credentials.get('api_key', '')
        self._region = credentials.get('region', '')

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
                'label': 'Subscription Key',
                'help_text': 'Azure Translator subscription key',
                'required': True,
            },
            'region': {
                'type': 'text',
                'label': 'Azure Region',
                'help_text': 'e.g., westus2, eastus, westeurope',
                'required': True,
            },
        }

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGS

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('api_key'):
            raise ValueError("Azure Translator subscription key is required")
        if not credentials.get('region'):
            raise ValueError("Azure region is required (e.g., westus2)")

    def _headers(self) -> Dict[str, str]:
        return {
            'Ocp-Apim-Subscription-Key': self._api_key,
            'Ocp-Apim-Subscription-Region': self._region,
            'Content-Type': 'application/json',
            'X-ClientTraceId': str(uuid_lib.uuid4()),
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test the Azure Translator API connection."""
        try:
            params = {
                'api-version': '3.0',
                'from': 'en',
                'to': 'es',
            }
            data = [{'text': 'Hello'}]

            response = requests.post(
                f'{API_URL}/translate',
                headers=self._headers(),
                params=params,
                json=data,
                timeout=10,
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Azure Translator connection successful!',
                    'supported_languages': len(self.SUPPORTED_LANGS),
                }
            elif response.status_code == 401:
                return {'success': False, 'error': 'Invalid API key or wrong region'}
            elif response.status_code == 403:
                return {'success': False, 'error': 'API key valid but may have exceeded quota'}
            else:
                return {'success': False, 'error': f'Connection failed: HTTP {response.status_code}'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single text string via Azure Translator."""
        results = self.translate_batch([text], source_lang, target_lang)
        return results[0]

    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """Translate multiple texts via Azure Translator v3.0."""
        params = {
            'api-version': '3.0',
            'from': source_lang.lower(),
            'to': target_lang.lower(),
        }
        data = [{'text': t} for t in texts]

        response = requests.post(
            f'{API_URL}/translate',
            headers=self._headers(),
            params=params,
            json=data,
            timeout=self.config.get('timeout', 30),
        )
        response.raise_for_status()

        result = response.json()
        return [item['translations'][0]['text'] for item in result]
