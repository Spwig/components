"""
Tests for the SEMrush SEO Provider.

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
from provider import SEMrushSEOProvider, GenerationError


class TestSEMrushProviderInit(unittest.TestCase):
    """Test provider initialization."""

    def _make_creds(self, **overrides):
        creds = {
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        }
        creds.update(overrides)
        return creds

    def test_provider_key(self):
        provider = SEMrushSEOProvider(self._make_creds())
        self.assertEqual(provider.provider_key, 'semrush')

    def test_provider_name(self):
        provider = SEMrushSEOProvider(self._make_creds())
        self.assertEqual(provider.provider_name, 'SEMrush')

    def test_requires_credentials(self):
        self.assertTrue(SEMrushSEOProvider.requires_credentials)

    def test_init_extracts_credentials(self):
        provider = SEMrushSEOProvider(self._make_creds())
        self.assertEqual(provider.api_key, 'test_api_key_abc123def456')
        self.assertEqual(provider.database, 'us')

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            SEMrushSEOProvider(None)

    def test_missing_api_key_raises(self):
        with self.assertRaises(ValueError):
            SEMrushSEOProvider({'database': 'us'})

    def test_short_api_key_raises(self):
        with self.assertRaises(ValueError):
            SEMrushSEOProvider({'api_key': 'short', 'database': 'us'})

    def test_invalid_database_raises(self):
        with self.assertRaises(ValueError):
            SEMrushSEOProvider({'api_key': 'test_api_key_abc123def456', 'database': 'invalid'})


class TestCapabilities(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    def test_all_capabilities_present(self):
        caps = self.provider.capabilities
        for key in ('meta_title', 'meta_description', 'keywords',
                     'multi_language', 'bulk_generation'):
            self.assertIn(key, caps)

    def test_multi_language_not_supported(self):
        self.assertFalse(self.provider.capabilities['multi_language'])


class TestRedactCredentials(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    def test_api_key_masked(self):
        redacted = self.provider.redact_credentials({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })
        self.assertIn('***', redacted['api_key'])
        self.assertEqual(redacted['database'], 'us')


class TestTestConnection(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    @patch('provider.requests.get')
    def test_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'test;100\n'
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertTrue(result['success'])
        self.assertIn('SEMrush', result['message'])

    @patch('provider.requests.get')
    def test_wrong_api_key(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'ERROR 50 :: WRONG API KEY'
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])
        self.assertIn('Authentication', result['message'])

    @patch('provider.requests.get')
    def test_forbidden(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = self.provider.test_connection()
        self.assertFalse(result['success'])

    @patch('provider.requests.get')
    def test_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout()

        result = self.provider.test_connection()
        self.assertFalse(result['success'])


class TestExtractKeywords(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })
        self.content = {
            'type': 'product',
            'name': 'Wireless Bluetooth Headphones',
            'description': 'Premium noise-cancelling headphones.',
            'category': 'Electronics',
            'brand': 'AudioTech',
        }

    @patch('provider.requests.get')
    def test_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            'wireless headphones;12000;1.50;0.85\n'
            'bluetooth headphones;8000;1.20;0.75\n'
            'noise cancelling;5000;0.90;0.60\n'
        )
        mock_get.return_value = mock_response

        keywords = self.provider.extract_keywords(self.content)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertLessEqual(len(keywords), 10)

    @patch('provider.requests.get')
    def test_respects_limit(self, mock_get):
        lines = '\n'.join([f'keyword{i};{1000-i};0.5;0.5' for i in range(20)])
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = lines
        mock_get.return_value = mock_response

        keywords = self.provider.extract_keywords(self.content, max_keywords=5)
        self.assertLessEqual(len(keywords), 5)

    @patch('provider.requests.get')
    def test_fallback_on_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'ERROR 50 :: WRONG API KEY'
        mock_get.return_value = mock_response

        # Should fall back to local extraction, not raise
        keywords = self.provider.extract_keywords(self.content)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

    def test_missing_name_raises(self):
        with self.assertRaises(GenerationError):
            self.provider.extract_keywords({})


class TestGenerateMetaTitle(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    @patch('provider.requests.get')
    def test_product_title(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'wireless headphones;12000;1.50;0.85\n'
        mock_get.return_value = mock_response

        content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'brand': 'AudioTech',
            'category': 'Electronics',
        }
        title = self.provider.generate_meta_title(content)
        self.assertIsInstance(title, str)
        self.assertLessEqual(len(title), 60)
        self.assertGreater(len(title), 0)

    @patch('provider.requests.get')
    def test_category_title(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'electronics;50000;0.80;0.90\n'
        mock_get.return_value = mock_response

        content = {
            'type': 'category',
            'name': 'Electronics',
        }
        title = self.provider.generate_meta_title(content)
        self.assertIsInstance(title, str)
        self.assertLessEqual(len(title), 60)

    def test_missing_name_raises(self):
        with self.assertRaises(GenerationError):
            self.provider.generate_meta_title({'type': 'product'})


class TestGenerateMetaDescription(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    @patch('provider.requests.get')
    def test_product_description(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'wireless headphones;12000;1.50;0.85\n'
        mock_get.return_value = mock_response

        content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'description': 'Premium noise-cancelling headphones with long battery life.',
            'brand': 'AudioTech',
            'category': 'Electronics',
        }
        desc = self.provider.generate_meta_description(content)
        self.assertIsInstance(desc, str)
        self.assertLessEqual(len(desc), 155)
        self.assertGreater(len(desc), 0)

    @patch('provider.requests.get')
    def test_description_without_source_description(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'headphones;12000;1.50;0.85\n'
        mock_get.return_value = mock_response

        content = {
            'type': 'product',
            'name': 'Wireless Headphones',
            'brand': 'AudioTech',
        }
        desc = self.provider.generate_meta_description(content)
        self.assertIsInstance(desc, str)
        self.assertLessEqual(len(desc), 155)


class TestKeywordCaching(unittest.TestCase):
    """Test that keyword results are cached within the instance."""

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    @patch('provider.requests.get')
    def test_cache_prevents_duplicate_calls(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'keyword1;100;0.5;0.5\n'
        mock_get.return_value = mock_response

        content = {'type': 'product', 'name': 'Test Product', 'category': 'Test'}

        # First call
        self.provider.extract_keywords(content)
        # Second call with same content
        self.provider.extract_keywords(content)

        # Should only make one API call due to caching
        self.assertEqual(mock_get.call_count, 1)


class TestLocalKeywordFallback(unittest.TestCase):

    def setUp(self):
        self.provider = SEMrushSEOProvider({
            'api_key': 'test_api_key_abc123def456',
            'database': 'us',
        })

    def test_extracts_from_name(self):
        content = {'type': 'product', 'name': 'Wireless Bluetooth Headphones'}
        keywords = self.provider._extract_keywords_local(content)
        self.assertGreater(len(keywords), 0)

    def test_includes_brand_and_category(self):
        content = {
            'type': 'product',
            'name': 'Headphones',
            'brand': 'AudioTech',
            'category': 'Electronics',
        }
        keywords = self.provider._extract_keywords_local(content)
        self.assertIn('audiotech', keywords)
        self.assertIn('electronics', keywords)

    def test_deduplicates(self):
        content = {'type': 'product', 'name': 'Test Test Product'}
        keywords = self.provider._extract_keywords_local(content)
        self.assertEqual(len(keywords), len(set(keywords)))


if __name__ == '__main__':
    unittest.main()
