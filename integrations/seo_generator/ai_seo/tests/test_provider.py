"""
Tests for the AI SEO Generator Provider.

All HTTP calls are mocked - zero real network requests.
"""

import json
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Django setup required for base class translation strings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from provider import AISEOProvider, GenerationError


class TestAISEOProviderInit(unittest.TestCase):
    """Test provider initialization."""

    def _make_creds(self, **overrides):
        creds = {
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        }
        creds.update(overrides)
        return creds

    def test_provider_key(self):
        provider = AISEOProvider(self._make_creds())
        self.assertEqual(provider.provider_key, 'ai_seo')

    def test_provider_name(self):
        provider = AISEOProvider(self._make_creds())
        self.assertEqual(provider.provider_name, 'AI SEO Generator')

    def test_requires_credentials(self):
        self.assertTrue(AISEOProvider.requires_credentials)

    def test_init_claude(self):
        provider = AISEOProvider(self._make_creds())
        self.assertEqual(provider.ai_service, 'claude')
        self.assertEqual(provider.model, 'claude-sonnet-4-20250514')

    def test_init_openai(self):
        creds = self._make_creds(
            ai_service='openai',
            api_key='sk-proj-test-key-123456789012345678',
            model='gpt-4o-mini',
        )
        provider = AISEOProvider(creds)
        self.assertEqual(provider.ai_service, 'openai')
        self.assertEqual(provider.model, 'gpt-4o-mini')

    def test_init_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            AISEOProvider(None)

    def test_init_invalid_service_raises(self):
        with self.assertRaises(ValueError):
            AISEOProvider(self._make_creds(ai_service='invalid'))

    def test_init_mismatched_model_raises(self):
        with self.assertRaises(ValueError):
            AISEOProvider(self._make_creds(model='gpt-4o'))  # OpenAI model with Claude service

    def test_init_short_key_raises(self):
        with self.assertRaises(ValueError):
            AISEOProvider(self._make_creds(api_key='short'))


class TestCapabilities(unittest.TestCase):
    """Test capabilities property."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })

    def test_all_capabilities_present(self):
        caps = self.provider.capabilities
        for key in ('meta_title', 'meta_description', 'keywords',
                     'multi_language', 'bulk_generation'):
            self.assertIn(key, caps)

    def test_multi_language_supported(self):
        self.assertTrue(self.provider.capabilities['multi_language'])


class TestRedactCredentials(unittest.TestCase):
    """Test credential redaction."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })

    def test_api_key_masked(self):
        creds = {
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        }
        redacted = self.provider.redact_credentials(creds)
        self.assertIn('***', redacted['api_key'])
        self.assertEqual(redacted['ai_service'], 'claude')  # Non-secret kept
        self.assertEqual(redacted['model'], 'claude-sonnet-4-20250514')  # Non-secret kept


class TestTestConnection(unittest.TestCase):
    """Test connection testing."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })

    @patch('provider.requests.post')
    def test_claude_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'OK'}],
        }
        mock_post.return_value = mock_response

        result = self.provider.test_connection()
        self.assertTrue(result['success'])
        self.assertIn('Claude', result['message'])

    @patch('provider.requests.post')
    def test_auth_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_post.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])
        self.assertIn('Authentication', result['message'])

    @patch('provider.requests.post')
    def test_timeout(self, mock_post):
        import requests
        mock_post.side_effect = requests.Timeout()

        result = self.provider.test_connection()
        self.assertFalse(result['success'])


class TestGenerateMetaTitleClaude(unittest.TestCase):
    """Test meta title generation with Claude."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Bluetooth Headphones',
            'description': 'Premium noise-cancelling headphones with 30-hour battery.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Wireless Bluetooth Headphones - AudioTech Electronics'}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertIsInstance(title, str)
        self.assertLessEqual(len(title), 60)

    @patch('provider.requests.post')
    def test_strips_quotes(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': '"Wireless Bluetooth Headphones"'}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertFalse(title.startswith('"'))
        self.assertFalse(title.endswith('"'))

    @patch('provider.requests.post')
    def test_truncation(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'A' * 100}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertLessEqual(len(title), 60)

    @patch('provider.requests.post')
    def test_api_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        with self.assertRaises(GenerationError):
            self.provider.generate_meta_title(self.content)


class TestGenerateMetaTitleOpenAI(unittest.TestCase):
    """Test meta title generation with OpenAI."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'openai',
            'api_key': 'sk-proj-test-key-123456789012345678',
            'model': 'gpt-4o-mini',
        })
        self.content = {
            'type': 'product',
            'name': 'Organic Coffee Beans',
            'description': 'Fair-trade organic coffee beans from Colombia.',
            'category': 'Food & Beverages',
            'brand': 'BeanCraft',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Organic Coffee Beans - BeanCraft'}}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertIsInstance(title, str)
        self.assertLessEqual(len(title), 60)


class TestGenerateMetaDescription(unittest.TestCase):
    """Test meta description generation."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Bluetooth Headphones',
            'description': 'Premium noise-cancelling headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'Shop premium Wireless Bluetooth Headphones by AudioTech. Noise-cancelling, 30-hour battery. Free shipping available.'}],
        }
        mock_post.return_value = mock_response

        desc = self.provider.generate_meta_description(self.content)
        self.assertIsInstance(desc, str)
        self.assertLessEqual(len(desc), 155)


class TestExtractKeywords(unittest.TestCase):
    """Test keyword extraction."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Bluetooth Headphones',
            'description': 'Premium noise-cancelling headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'wireless headphones, bluetooth headphones, noise cancelling, AudioTech, premium headphones'}],
        }
        mock_post.return_value = mock_response

        keywords = self.provider.extract_keywords(self.content)
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 10)

    @patch('provider.requests.post')
    def test_respects_limit(self, mock_post):
        kw_list = ', '.join([f'keyword{i}' for i in range(20)])
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': kw_list}],
        }
        mock_post.return_value = mock_response

        keywords = self.provider.extract_keywords(self.content, max_keywords=5)
        self.assertLessEqual(len(keywords), 5)


class TestGenerateSEOOverride(unittest.TestCase):
    """Test the single-call generate_seo() override."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'description': 'Premium audio device.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_single_call_json_success(self, mock_post):
        seo_data = {
            'meta_title': 'Wireless Headphones - AudioTech Electronics',
            'meta_description': 'Shop premium Wireless Headphones by AudioTech. Free shipping.',
            'keywords': ['wireless headphones', 'AudioTech', 'electronics'],
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': json.dumps(seo_data)}],
        }
        mock_post.return_value = mock_response

        result = self.provider.generate_seo(self.content)
        self.assertIn('meta_title', result)
        self.assertIn('meta_description', result)
        self.assertIn('keywords', result)
        self.assertLessEqual(len(result['meta_title']), 60)
        self.assertLessEqual(len(result['meta_description']), 155)
        self.assertIsInstance(result['keywords'], list)

    @patch('provider.requests.post')
    def test_fallback_on_invalid_json(self, mock_post):
        """When JSON parsing fails, falls back to individual calls."""
        responses = [
            # First call (full_seo) returns invalid JSON
            Mock(status_code=200, json=Mock(return_value={
                'content': [{'text': 'Not valid JSON'}],
            })),
            # Fallback: individual title call
            Mock(status_code=200, json=Mock(return_value={
                'content': [{'text': 'Generated Title'}],
            })),
            # Fallback: individual description call
            Mock(status_code=200, json=Mock(return_value={
                'content': [{'text': 'Generated description for the product.'}],
            })),
            # Fallback: individual keywords call
            Mock(status_code=200, json=Mock(return_value={
                'content': [{'text': 'keyword1, keyword2, keyword3'}],
            })),
        ]
        mock_post.side_effect = responses

        result = self.provider.generate_seo(self.content)
        self.assertIn('meta_title', result)
        self.assertEqual(mock_post.call_count, 4)  # 1 failed + 3 fallback


class TestPromptBuilding(unittest.TestCase):
    """Test prompt construction."""

    def setUp(self):
        self.provider = AISEOProvider({
            'ai_service': 'claude',
            'api_key': 'sk-ant-api03-test-key-12345678901234567890',
            'model': 'claude-sonnet-4-20250514',
        })

    def test_prompt_includes_content_fields(self):
        content = {
            'type': 'product',
            'name': 'Test Product',
            'description': 'A test description',
            'category': 'Test Category',
            'brand': 'Test Brand',
        }
        prompt = self.provider._build_seo_prompt(content, 'meta_title')
        self.assertIn('Test Product', prompt)
        self.assertIn('Test Category', prompt)
        self.assertIn('Test Brand', prompt)

    def test_prompt_includes_language_instruction(self):
        content = {'type': 'product', 'name': 'Test'}
        prompt = self.provider._build_seo_prompt(content, 'meta_title', 'de')
        self.assertIn('de', prompt)

    def test_full_seo_prompt_requests_json(self):
        content = {'type': 'product', 'name': 'Test'}
        prompt = self.provider._build_seo_prompt(content, 'full_seo')
        self.assertIn('JSON', prompt)


if __name__ == '__main__':
    unittest.main()
