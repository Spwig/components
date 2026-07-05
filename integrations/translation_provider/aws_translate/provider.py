"""
AWS Translate provider.

Amazon's scalable translation service with deep AWS integration.
Uses boto3 for AWS API communication.
"""
import logging
from typing import Dict, List, Optional, Any

from translations.providers.base import TranslationProviderBase

logger = logging.getLogger(__name__)


class AWSTranslateProvider(TranslationProviderBase):
    provider_key = 'aws_translate'
    provider_name = 'AWS Translate'

    SUPPORTED_LANGS = [
        'af', 'am', 'ar', 'az', 'bg', 'bn', 'bs', 'ca', 'cs', 'cy',
        'da', 'de', 'el', 'en', 'es', 'et', 'fa', 'fi', 'fr', 'ga',
        'gu', 'ha', 'he', 'hi', 'hr', 'hu', 'hy', 'id', 'is', 'it',
        'ja', 'ka', 'kk', 'kn', 'ko', 'lt', 'lv', 'mk', 'ml', 'mn',
        'mr', 'ms', 'mt', 'nl', 'no', 'or', 'pa', 'pl', 'ps', 'pt',
        'ro', 'ru', 'sd', 'si', 'sk', 'sl', 'so', 'sq', 'sr', 'sv',
        'sw', 'ta', 'te', 'tg', 'th', 'tl', 'tr', 'uk', 'ur', 'uz',
        'vi', 'zh', 'zh-tw',
    ]

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self._access_key_id = credentials.get('access_key_id', '')
        self._secret_access_key = credentials.get('secret_access_key', '')
        self._region = credentials.get('region', 'us-east-1')

    def _get_client(self):
        """Create a boto3 Translate client."""
        import boto3
        return boto3.client(
            'translate',
            region_name=self._region,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
        )

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
            'access_key_id': {
                'type': 'password',
                'label': 'Access Key ID',
                'required': True,
            },
            'secret_access_key': {
                'type': 'password',
                'label': 'Secret Access Key',
                'required': True,
            },
            'region': {
                'type': 'text',
                'label': 'AWS Region',
                'required': False,
                'default': 'us-east-1',
            },
        }

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGS

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('access_key_id'):
            raise ValueError("AWS Access Key ID is required")
        if not credentials.get('secret_access_key'):
            raise ValueError("AWS Secret Access Key is required")

    def test_connection(self) -> Dict[str, Any]:
        """Test the AWS Translate API connection."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
        except ImportError:
            return {
                'success': False,
                'error': 'boto3 library not installed. Run: pip install boto3',
            }

        try:
            client = self._get_client()
            response = client.translate_text(
                Text='Hello',
                SourceLanguageCode='en',
                TargetLanguageCode='es',
            )
            if response and 'TranslatedText' in response:
                return {
                    'success': True,
                    'message': 'AWS Translate connection successful!',
                    'supported_languages': len(self.SUPPORTED_LANGS),
                }
            return {'success': False, 'error': 'Unexpected response from AWS Translate'}
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidSignatureException':
                return {'success': False, 'error': 'Invalid AWS credentials'}
            elif error_code == 'AccessDeniedException':
                return {'success': False, 'error': 'Access denied. Ensure IAM user has TranslateFullAccess policy'}
            elif error_code == 'ThrottlingException':
                return {'success': False, 'error': 'Rate limit exceeded. Try again later'}
            return {'success': False, 'error': f'AWS Error: {e.response["Error"]["Message"]}'}
        except NoCredentialsError:
            return {'success': False, 'error': 'AWS credentials not provided or invalid'}
        except Exception as e:
            return {'success': False, 'error': f'AWS connection error: {str(e)}'}

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate a single text string via AWS Translate."""
        client = self._get_client()
        response = client.translate_text(
            Text=text,
            SourceLanguageCode=source_lang.lower(),
            TargetLanguageCode=target_lang.lower(),
        )
        return response['TranslatedText']

    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[str]:
        """Translate multiple texts via AWS Translate (sequential API calls)."""
        # AWS Translate doesn't have a batch API — translate one by one
        client = self._get_client()
        results = []
        for text in texts:
            response = client.translate_text(
                Text=text,
                SourceLanguageCode=source_lang.lower(),
                TargetLanguageCode=target_lang.lower(),
            )
            results.append(response['TranslatedText'])
        return results
