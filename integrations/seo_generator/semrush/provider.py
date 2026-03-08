"""
SEMrush SEO Provider

SEO content generation using SEMrush's keyword research API.
Uses keyword intelligence data to build optimized meta titles and descriptions
with strategically placed high-value keywords.

Author: Spwig
"""

import re
import logging
import requests
from typing import Dict, Optional, Any, List

from seo_generator.providers.base import BaseSEOProvider, GenerationError

logger = logging.getLogger(__name__)


class SEMrushSEOProvider(BaseSEOProvider):
    """
    SEMrush-powered SEO generation provider.

    Uses SEMrush keyword research API to find high-value keywords,
    then builds optimized meta titles and descriptions using
    keyword-driven templates.
    """

    provider_key = 'semrush'
    provider_name = 'SEMrush'
    requires_credentials = True

    BASE_URL = 'https://api.semrush.com'
    TIMEOUT = 30

    DATABASES = {
        'us': 'United States', 'uk': 'United Kingdom', 'ca': 'Canada',
        'au': 'Australia', 'de': 'Germany', 'fr': 'France', 'es': 'Spain',
        'it': 'Italy', 'br': 'Brazil', 'nl': 'Netherlands', 'be': 'Belgium',
        'ch': 'Switzerland', 'at': 'Austria', 'se': 'Sweden', 'dk': 'Denmark',
        'no': 'Norway', 'fi': 'Finland', 'pl': 'Poland', 'tr': 'Turkey',
        'ru': 'Russia', 'jp': 'Japan', 'kr': 'South Korea', 'in': 'India',
        'mx': 'Mexico', 'ar': 'Argentina', 'za': 'South Africa',
        'sg': 'Singapore', 'hk': 'Hong Kong', 'ie': 'Ireland',
        'nz': 'New Zealand', 'pt': 'Portugal',
    }

    # SEO title templates per content type
    TITLE_TEMPLATES = {
        'product': [
            "{name} - {top_keyword} | {brand}",
            "{name} - Buy {top_keyword} | {brand}",
            "{name} | {top_keyword} - {category}",
        ],
        'category': [
            "{name} - Best {top_keyword} Online",
            "Shop {name} - {top_keyword} Collection",
            "{name} - Top {top_keyword} Selection",
        ],
        'brand': [
            "{name} - Official {top_keyword} Products",
            "{name} | {top_keyword} & More",
            "{name} - Premium {top_keyword}",
        ],
        'page': [
            "{name} - {top_keyword}",
            "{name} | {top_keyword} Guide",
        ],
        'blogpost': [
            "{name} - {top_keyword}",
            "{name} | {top_keyword} Tips",
        ],
        'blogcategory': [
            "{name} - {top_keyword} Articles",
            "{name} | {top_keyword} Blog",
        ],
    }

    # Description CTA phrases
    CTAS = {
        'product': "Shop now for great prices and fast shipping.",
        'category': "Browse our curated selection today.",
        'brand': "Explore the full range of products.",
        'page': "Learn more and get started.",
        'blogpost': "Read the full article for expert insights.",
        'blogcategory': "Explore all articles and guides.",
    }

    def __init__(self, credentials: Optional[Dict[str, Any]] = None,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.api_key = self.credentials.get('api_key', '')
        self.database = self.credentials.get('database', 'us')
        self._keyword_cache = {}

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'meta_title': True,
            'meta_description': True,
            'keywords': True,
            'multi_language': False,  # Keywords are regional, not translated
            'bulk_generation': True,
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        if not credentials.get('api_key'):
            raise ValueError("API Key is required")
        if len(credentials['api_key']) < 10:
            raise ValueError("API Key must be at least 10 characters")
        database = credentials.get('database', 'us')
        if database not in self.DATABASES:
            raise ValueError(
                f"Invalid database '{database}'. "
                f"Valid options: {', '.join(sorted(self.DATABASES.keys()))}"
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        redacted = credentials.copy()
        if 'api_key' in redacted and redacted['api_key']:
            val = str(redacted['api_key'])
            if len(val) > 6:
                redacted['api_key'] = val[:3] + '***' + val[-3:]
            else:
                redacted['api_key'] = '***'
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        try:
            # Use a lightweight keyword overview call to test auth
            response = requests.get(
                self.BASE_URL,
                params={
                    'type': 'phrase_this',
                    'key': self.api_key,
                    'phrase': 'test',
                    'export_columns': 'Ph,Nq',
                    'database': self.database,
                },
                timeout=self.TIMEOUT,
            )

            text = response.text.strip()

            if response.status_code == 200:
                if 'ERROR' in text.upper():
                    if 'WRONG API KEY' in text.upper() or 'API KEY' in text.upper():
                        return {
                            'success': False,
                            'message': 'Authentication failed. Check your API key.',
                        }
                    return {
                        'success': False,
                        'message': f'API error: {text[:200]}',
                    }
                return {
                    'success': True,
                    'message': f'Connected to SEMrush ({self.DATABASES.get(self.database, self.database)} database)',
                    'details': {
                        'database': self.database,
                        'region': self.DATABASES.get(self.database, 'Unknown'),
                    },
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access denied. Check your API key and account status.',
                }
            else:
                return {
                    'success': False,
                    'message': f'API returned status {response.status_code}',
                }
        except requests.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except requests.ConnectionError:
            return {'success': False, 'message': 'Could not connect to SEMrush API'}
        except Exception as e:
            logger.warning("Unexpected error in test_connection: %s", e)
            return {'success': False, 'message': f'Unexpected error: {e}'}

    def _fetch_keyword_data(self, phrase: str) -> List[Dict[str, Any]]:
        """
        Fetch keyword data from SEMrush for a given phrase.

        Returns list of dicts with keyword, volume, cpc, competition.
        Results are cached per phrase within the provider instance.
        """
        cache_key = f"{phrase}_{self.database}"
        if cache_key in self._keyword_cache:
            return self._keyword_cache[cache_key]

        try:
            # Use phrase_related for broader keyword suggestions
            response = requests.get(
                self.BASE_URL,
                params={
                    'type': 'phrase_related',
                    'key': self.api_key,
                    'phrase': phrase,
                    'export_columns': 'Ph,Nq,Cp,Co',
                    'database': self.database,
                    'display_limit': 20,
                },
                timeout=self.TIMEOUT,
            )

            if response.status_code != 200:
                return []

            text = response.text.strip()
            if not text or 'ERROR' in text.upper():
                return []

            keywords = []
            for line in text.split('\n'):
                parts = line.strip().split(';')
                if len(parts) >= 2:
                    try:
                        kw_data = {
                            'keyword': parts[0].strip(),
                            'volume': int(parts[1]) if parts[1].isdigit() else 0,
                            'cpc': float(parts[2]) if len(parts) > 2 and parts[2] else 0,
                            'competition': float(parts[3]) if len(parts) > 3 and parts[3] else 0,
                        }
                        if kw_data['keyword']:
                            keywords.append(kw_data)
                    except (ValueError, IndexError):
                        continue

            # Sort by volume (higher = better)
            keywords.sort(key=lambda x: x['volume'], reverse=True)

            self._keyword_cache[cache_key] = keywords
            return keywords

        except (requests.Timeout, requests.ConnectionError):
            return []
        except Exception as e:
            logger.warning("Error fetching keyword data: %s", e)
            return []

    def extract_keywords(self, content: Dict[str, str], max_keywords: int = 10) -> List[str]:
        try:
            name = content.get('name', '')
            if not name:
                raise GenerationError("Content must have a 'name' field for keyword extraction")

            # Build search phrase from name + category
            phrase = name
            category = content.get('category', '')
            if category:
                phrase = f"{name} {category}"

            keyword_data = self._fetch_keyword_data(phrase)

            if keyword_data:
                keywords = [kd['keyword'] for kd in keyword_data[:max_keywords]]
                return keywords

            # Fallback: local extraction if API returns nothing
            return self._extract_keywords_local(content, max_keywords)

        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Keyword extraction failed: {e}")

    def _extract_keywords_local(self, content: Dict[str, str],
                                 max_keywords: int = 10) -> List[str]:
        """Fallback keyword extraction from content fields."""
        keywords = []
        name = content.get('name', '')
        brand = content.get('brand', '')
        category = content.get('category', '')

        # Add full name as a keyword
        if name:
            keywords.append(name.lower())
            # Also add individual significant words
            words = [w.lower() for w in name.split() if len(w) > 2]
            keywords.extend(words)

        if brand:
            keywords.append(brand.lower())
        if category:
            keywords.append(category.lower())

        # Deduplicate preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:max_keywords]

    def generate_meta_title(self, content: Dict[str, str], language: str = 'en') -> str:
        try:
            name = content.get('name', '')
            if not name:
                raise GenerationError("Content must have a 'name' field")

            content_type = content.get('type', 'product').lower()
            brand = content.get('brand', '')
            category = content.get('category', '')

            # Get top keyword from SEMrush data
            keywords = self.extract_keywords(content, max_keywords=5)
            top_keyword = keywords[0] if keywords else category or name

            # Select template
            templates = self.TITLE_TEMPLATES.get(content_type,
                                                  self.TITLE_TEMPLATES['product'])

            # Try templates in order, pick the first that fits in 60 chars
            for template in templates:
                title = template.format(
                    name=name,
                    top_keyword=top_keyword,
                    brand=brand or '',
                    category=category or '',
                )
                # Clean up empty placeholders
                title = re.sub(r'\s*-\s*$', '', title)
                title = re.sub(r'\s*\|\s*$', '', title)
                title = re.sub(r'\s*-\s*-\s*', ' - ', title)
                title = re.sub(r'\s+', ' ', title).strip()

                if len(title) <= 60:
                    return title

            # If no template fits, truncate the first one
            title = templates[0].format(
                name=name,
                top_keyword=top_keyword,
                brand=brand or '',
                category=category or '',
            )
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) > 60:
                title = title[:57] + '...'

            return title

        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Meta title generation failed: {e}")

    def generate_meta_description(self, content: Dict[str, str], language: str = 'en') -> str:
        try:
            name = content.get('name', '')
            if not name:
                raise GenerationError("Content must have a 'name' field")

            content_type = content.get('type', 'product').lower()
            description = content.get('description', '')
            brand = content.get('brand', '')
            category = content.get('category', '')

            # Get keywords for inclusion
            keywords = self.extract_keywords(content, max_keywords=3)
            keyword_phrase = ', '.join(keywords[:2]) if keywords else ''

            # Build description
            cta = self.CTAS.get(content_type, self.CTAS['product'])

            if description:
                # Clean HTML and get first meaningful sentence
                clean_desc = re.sub(r'<[^>]+>', '', description)
                clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                first_sentence = re.split(r'[.!?]\s', clean_desc)[0]
                if len(first_sentence) > 80:
                    first_sentence = first_sentence[:80]

                if content_type == 'product':
                    desc = f"{name}"
                    if brand:
                        desc += f" by {brand}"
                    desc += f" - {first_sentence}. {cta}"
                elif content_type == 'category':
                    desc = f"Discover {name}. {first_sentence}. {cta}"
                elif content_type == 'brand':
                    desc = f"{name} - {first_sentence}. {cta}"
                else:
                    desc = f"{name} - {first_sentence}. {cta}"
            else:
                if content_type == 'product':
                    desc = f"{name}"
                    if brand:
                        desc += f" by {brand}"
                    if keyword_phrase:
                        desc += f". Features: {keyword_phrase}."
                    desc += f" {cta}"
                elif content_type == 'category':
                    desc = f"Discover the best {name}."
                    if keyword_phrase:
                        desc += f" Find {keyword_phrase} and more."
                    desc += f" {cta}"
                elif content_type == 'brand':
                    desc = f"Shop official {name} products."
                    if keyword_phrase:
                        desc += f" Featuring {keyword_phrase}."
                    desc += f" {cta}"
                else:
                    desc = f"{name}."
                    if keyword_phrase:
                        desc += f" {keyword_phrase.capitalize()}."
                    desc += f" {cta}"

            if len(desc) > 155:
                desc = desc[:152] + '...'

            return desc

        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Meta description generation failed: {e}")
