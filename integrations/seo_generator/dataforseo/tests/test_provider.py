"""
Tests for the DataForSEO Provider.

All HTTP calls are mocked - zero real network requests.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Django setup required for base class translation strings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from provider import DataForSEOProvider, GenerationError


class TestDataForSEOProviderInit(unittest.TestCase):
    """Test provider initialization."""

    def _make_creds(self, **overrides):
        creds = {
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        }
        creds.update(overrides)
        return creds

    def test_provider_key(self):
        provider = DataForSEOProvider(self._make_creds())
        self.assertEqual(provider.provider_key, 'dataforseo')

    def test_provider_name(self):
        provider = DataForSEOProvider(self._make_creds())
        self.assertEqual(provider.provider_name, 'DataForSEO')

    def test_requires_credentials(self):
        self.assertTrue(DataForSEOProvider.requires_credentials)

    def test_init_extracts_credentials(self):
        provider = DataForSEOProvider(self._make_creds())
        self.assertEqual(provider.login, 'test@example.com')
        self.assertEqual(provider.password, 'test_api_password_123')

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            DataForSEOProvider(None)

    def test_missing_login_raises(self):
        with self.assertRaises(ValueError):
            DataForSEOProvider({'password': 'test_api_password_123'})

    def test_missing_password_raises(self):
        with self.assertRaises(ValueError):
            DataForSEOProvider({'login': 'test@example.com'})

    def test_short_password_raises(self):
        with self.assertRaises(ValueError):
            DataForSEOProvider({'login': 'test@example.com', 'password': 'short'})


class TestCapabilities(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })

    def test_all_capabilities_present(self):
        caps = self.provider.capabilities
        for key in ('meta_title', 'meta_description', 'keywords',
                     'multi_language', 'bulk_generation'):
            self.assertIn(key, caps)

    def test_multi_language_supported(self):
        self.assertTrue(self.provider.capabilities['multi_language'])


class TestRedactCredentials(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })

    def test_password_masked(self):
        redacted = self.provider.redact_credentials({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })
        self.assertIn('***', redacted['password'])
        self.assertEqual(redacted['login'], 'test@example.com')


class TestTestConnection(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })

    @patch('provider.requests.get')
    def test_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{'login': 'test@example.com', 'money': {'balance': 50.0}}]}],
        }
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertTrue(result['success'])

    @patch('provider.requests.get')
    def test_auth_failure(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])

    @patch('provider.requests.get')
    def test_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout()

        result = self.provider.test_connection()
        self.assertFalse(result['success'])


class TestGenerateMetaTitle(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
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
            'status_code': 20000,
            'tasks': [{'result': [{
                'title': 'Wireless Bluetooth Headphones - AudioTech',
                'description': 'Premium noise-cancelling headphones by AudioTech.',
            }]}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertIsInstance(title, str)
        self.assertLessEqual(len(title), 60)

    @patch('provider.requests.post')
    def test_truncation(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{'title': 'A' * 100, 'description': ''}]}],
        }
        mock_post.return_value = mock_response

        title = self.provider.generate_meta_title(self.content)
        self.assertLessEqual(len(title), 60)

    @patch('provider.requests.post')
    def test_auth_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with self.assertRaises(GenerationError):
            self.provider.generate_meta_title(self.content)

    @patch('provider.requests.post')
    def test_empty_content_raises(self, mock_post):
        with self.assertRaises(GenerationError):
            self.provider.generate_meta_title({})


class TestGenerateMetaDescription(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'description': 'Premium headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{
                'title': 'Wireless Headphones',
                'description': 'Shop premium Wireless Headphones by AudioTech.',
            }]}],
        }
        mock_post.return_value = mock_response

        desc = self.provider.generate_meta_description(self.content)
        self.assertIsInstance(desc, str)
        self.assertLessEqual(len(desc), 155)


class TestGenerateSEOOverride(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'description': 'Premium headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_single_call_for_title_and_description(self, mock_post):
        """generate_seo makes one call for title+desc, one for keywords."""
        # First call: meta tags
        meta_response = Mock()
        meta_response.status_code = 200
        meta_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{
                'title': 'Wireless Headphones',
                'description': 'Shop premium headphones.',
            }]}],
        }
        # Second call: text summary for keywords
        keyword_response = Mock()
        keyword_response.status_code = 200
        keyword_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{'keyword_density': {'wireless': 5, 'headphones': 4}}]}],
        }
        mock_post.side_effect = [meta_response, keyword_response]

        result = self.provider.generate_seo(self.content)
        self.assertIn('meta_title', result)
        self.assertIn('meta_description', result)
        self.assertIn('keywords', result)
        self.assertEqual(mock_post.call_count, 2)  # Not 3


class TestExtractKeywords(unittest.TestCase):

    def setUp(self):
        self.provider = DataForSEOProvider({
            'login': 'test@example.com',
            'password': 'test_api_password_123',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'description': 'Premium headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.post')
    def test_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status_code': 20000,
            'tasks': [{'result': [{'keyword_density': {
                'wireless': 5, 'headphones': 4, 'premium': 2, 'audio': 1,
            }}]}],
        }
        mock_post.return_value = mock_response

        keywords = self.provider.extract_keywords(self.content)
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 10)

    def test_fallback_extraction(self):
        """When API is unavailable, fallback extracts from content."""
        keywords = self.provider._extract_keywords_fallback(self.content)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)


if __name__ == '__main__':
    unittest.main()
