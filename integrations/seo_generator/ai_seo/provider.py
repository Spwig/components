"""
AI SEO Generator Provider

Unified AI-powered SEO content generation supporting Claude (Anthropic) and
OpenAI (GPT). Generates contextually rich, native-language meta titles,
descriptions, and keywords using large language models.

Author: Spwig
"""

import json
import logging
import requests
from typing import Dict, Optional, Any, List

from seo_generator.providers.base import BaseSEOProvider, GenerationError

logger = logging.getLogger(__name__)


class AISEOProvider(BaseSEOProvider):
    """
    AI-powered SEO generation provider.

    Supports multiple AI backends (Claude, OpenAI) via a unified interface.
    The merchant selects their preferred AI service and model during setup.
    """

    provider_key = 'ai_seo'
    provider_name = 'AI SEO Generator'
    requires_credentials = True

    TIMEOUT = 60  # LLM calls can be slower

    API_ENDPOINTS = {
        'claude': 'https://api.anthropic.com/v1/messages',
        'openai': 'https://api.openai.com/v1/chat/completions',
    }

    VALID_MODELS = {
        'claude': [
            'claude-sonnet-4-20250514',
            'claude-haiku-4-20250514',
        ],
        'openai': [
            'gpt-4o-mini',
            'gpt-4o',
        ],
    }

    ANTHROPIC_VERSION = '2023-06-01'

    def __init__(self, credentials: Optional[Dict[str, Any]] = None,
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(credentials, config)
        self.ai_service = self.credentials.get('ai_service', 'claude')
        self.api_key = self.credentials.get('api_key', '')
        self.model = self.credentials.get('model', 'claude-sonnet-4-20250514')

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
        ai_service = credentials.get('ai_service', '')
        if ai_service not in ('claude', 'openai'):
            raise ValueError(
                "AI service must be 'claude' or 'openai'"
            )

        api_key = credentials.get('api_key', '')
        if not api_key:
            raise ValueError("API Key is required")
        if len(api_key) < 20:
            raise ValueError("API Key must be at least 20 characters")

        model = credentials.get('model', '')
        if not model:
            raise ValueError("Model selection is required")

        valid_models = self.VALID_MODELS.get(ai_service, [])
        if model not in valid_models:
            raise ValueError(
                f"Model '{model}' is not valid for {ai_service}. "
                f"Valid models: {', '.join(valid_models)}"
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        redacted = credentials.copy()
        if 'api_key' in redacted and redacted['api_key']:
            val = str(redacted['api_key'])
            if len(val) > 10:
                redacted['api_key'] = val[:6] + '***' + val[-4:]
            else:
                redacted['api_key'] = '***'
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        try:
            prompt = "Respond with exactly: OK"
            result = self._call_ai(prompt, max_tokens=10)
            return {
                'success': True,
                'message': f'Connected to {self.ai_service.title()} ({self.model})',
                'details': {
                    'service': self.ai_service,
                    'model': self.model,
                },
            }
        except GenerationError as e:
            error_msg = str(e)
            if '401' in error_msg or 'auth' in error_msg.lower():
                return {
                    'success': False,
                    'message': 'Authentication failed. Check your API key.',
                }
            if '429' in error_msg or 'rate' in error_msg.lower():
                return {
                    'success': False,
                    'message': 'Rate limit exceeded. Try again later.',
                }
            return {
                'success': False,
                'message': f'Connection failed: {error_msg}',
            }
        except Exception as e:
            logger.warning("Unexpected error in test_connection: %s", e)
            return {
                'success': False,
                'message': f'Unexpected error: {e}',
            }

    def _build_seo_prompt(self, content: Dict[str, str], task: str,
                          language: str = 'en') -> str:
        """Build a structured prompt for SEO generation."""
        content_type = content.get('type', 'product')
        name = content.get('name', '')
        description = content.get('description', '')
        category = content.get('category', '')
        brand = content.get('brand', '')

        context_parts = [f"Content type: {content_type}", f"Name: {name}"]
        if description:
            # Truncate very long descriptions to save tokens
            desc_text = description[:500]
            context_parts.append(f"Description: {desc_text}")
        if category:
            context_parts.append(f"Category: {category}")
        if brand:
            context_parts.append(f"Brand: {brand}")

        context_block = '\n'.join(context_parts)

        lang_instruction = ""
        if language != 'en':
            lang_instruction = f"\nGenerate the content in the '{language}' language. The output must be in native {language}, not translated from English."

        if task == 'meta_title':
            return (
                f"You are an SEO specialist. Generate an optimized meta title for search engines.\n\n"
                f"Content:\n{context_block}\n\n"
                f"Rules:\n"
                f"- Maximum 60 characters\n"
                f"- Include the primary keyword (the name) near the beginning\n"
                f"- Make it compelling for click-through\n"
                f"- Do NOT include a site name\n"
                f"- Do NOT use quotes around the title\n"
                f"{lang_instruction}\n\n"
                f"Respond with ONLY the meta title, nothing else."
            )
        elif task == 'meta_description':
            return (
                f"You are an SEO specialist. Generate an optimized meta description for search engines.\n\n"
                f"Content:\n{context_block}\n\n"
                f"Rules:\n"
                f"- Maximum 155 characters\n"
                f"- Include a call-to-action (e.g., Shop now, Discover, Learn more)\n"
                f"- Make it compelling and informative\n"
                f"- Include relevant keywords naturally\n"
                f"- Do NOT use quotes around the description\n"
                f"{lang_instruction}\n\n"
                f"Respond with ONLY the meta description, nothing else."
            )
        elif task == 'keywords':
            return (
                f"You are an SEO specialist. Extract the most relevant SEO keywords for this content.\n\n"
                f"Content:\n{context_block}\n\n"
                f"Rules:\n"
                f"- Return up to 10 keywords\n"
                f"- Order by relevance (most relevant first)\n"
                f"- Include both short-tail and long-tail keywords\n"
                f"- Focus on search intent and commercial value\n"
                f"{lang_instruction}\n\n"
                f"Respond with ONLY a comma-separated list of keywords, nothing else."
            )
        elif task == 'full_seo':
            return (
                f"You are an SEO specialist. Generate a complete SEO package for search engine optimization.\n\n"
                f"Content:\n{context_block}\n\n"
                f"Generate the following as a JSON object:\n"
                f"1. \"meta_title\": An optimized meta title (max 60 chars, include primary keyword near start, no site name, no quotes)\n"
                f"2. \"meta_description\": An optimized meta description (max 155 chars, include CTA, compelling and informative)\n"
                f"3. \"keywords\": An array of up to 10 relevant keywords ordered by relevance\n"
                f"{lang_instruction}\n\n"
                f"Respond with ONLY the JSON object, no markdown formatting, no code blocks."
            )
        else:
            raise GenerationError(f"Unknown task: {task}")

    def _call_ai(self, prompt: str, max_tokens: int = 300) -> str:
        """Route to the appropriate AI backend and return the response text."""
        if self.ai_service == 'claude':
            return self._call_claude(prompt, max_tokens)
        elif self.ai_service == 'openai':
            return self._call_openai(prompt, max_tokens)
        else:
            raise GenerationError(f"Unknown AI service: {self.ai_service}")

    def _call_claude(self, prompt: str, max_tokens: int) -> str:
        """Call the Anthropic Messages API."""
        try:
            response = requests.post(
                self.API_ENDPOINTS['claude'],
                headers={
                    'x-api-key': self.api_key,
                    'anthropic-version': self.ANTHROPIC_VERSION,
                    'content-type': 'application/json',
                },
                json={
                    'model': self.model,
                    'max_tokens': max_tokens,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                },
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed (401). Check your Anthropic API key.")
            if response.status_code == 429:
                raise GenerationError("Rate limit exceeded (429). Try again later.")
            if response.status_code != 200:
                raise GenerationError(
                    f"Claude API error (HTTP {response.status_code}): {response.text[:200]}"
                )

            data = response.json()
            content_blocks = data.get('content', [])
            if not content_blocks:
                raise GenerationError("Empty response from Claude API")

            return content_blocks[0].get('text', '').strip()

        except requests.Timeout:
            raise GenerationError("Claude API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to Claude API")
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Claude API call failed: {e}")

    def _call_openai(self, prompt: str, max_tokens: int) -> str:
        """Call the OpenAI Chat Completions API."""
        try:
            response = requests.post(
                self.API_ENDPOINTS['openai'],
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.model,
                    'max_tokens': max_tokens,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                },
                timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                raise GenerationError("Authentication failed (401). Check your OpenAI API key.")
            if response.status_code == 429:
                raise GenerationError("Rate limit exceeded (429). Try again later.")
            if response.status_code != 200:
                raise GenerationError(
                    f"OpenAI API error (HTTP {response.status_code}): {response.text[:200]}"
                )

            data = response.json()
            choices = data.get('choices', [])
            if not choices:
                raise GenerationError("Empty response from OpenAI API")

            return choices[0].get('message', {}).get('content', '').strip()

        except requests.Timeout:
            raise GenerationError("OpenAI API request timed out")
        except requests.ConnectionError:
            raise GenerationError("Could not connect to OpenAI API")
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"OpenAI API call failed: {e}")

    def generate_meta_title(self, content: Dict[str, str], language: str = 'en') -> str:
        prompt = self._build_seo_prompt(content, 'meta_title', language)
        result = self._call_ai(prompt, max_tokens=100)
        # Strip any quotes the AI might add
        result = result.strip('"\'')
        # Truncate to 60 chars
        if len(result) > 60:
            result = result[:57] + '...'
        return result

    def generate_meta_description(self, content: Dict[str, str], language: str = 'en') -> str:
        prompt = self._build_seo_prompt(content, 'meta_description', language)
        result = self._call_ai(prompt, max_tokens=200)
        result = result.strip('"\'')
        if len(result) > 155:
            result = result[:152] + '...'
        return result

    def extract_keywords(self, content: Dict[str, str], max_keywords: int = 10) -> List[str]:
        prompt = self._build_seo_prompt(content, 'keywords')
        result = self._call_ai(prompt, max_tokens=300)
        # Parse comma-separated keywords
        keywords = [kw.strip().strip('"\'') for kw in result.split(',')]
        keywords = [kw for kw in keywords if kw]  # Remove empty
        return keywords[:max_keywords]

    def generate_seo(self, content: Dict[str, str], language: str = 'en') -> Dict[str, Any]:
        """
        Override to make a single AI call for all three fields.

        More efficient (1 API call vs 3) and produces more coherent results.
        Falls back to individual calls if JSON parsing fails.
        """
        try:
            prompt = self._build_seo_prompt(content, 'full_seo', language)
            result = self._call_ai(prompt, max_tokens=500)

            # Try to parse as JSON
            # Strip markdown code fences if present
            cleaned = result.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                # Remove first and last lines (```json and ```)
                lines = [l for l in lines if not l.strip().startswith('```')]
                cleaned = '\n'.join(lines)

            data = json.loads(cleaned)

            meta_title = str(data.get('meta_title', '')).strip('"\'')
            meta_description = str(data.get('meta_description', '')).strip('"\'')
            keywords = data.get('keywords', [])

            if isinstance(keywords, str):
                keywords = [kw.strip() for kw in keywords.split(',')]

            # Enforce limits
            if len(meta_title) > 60:
                meta_title = meta_title[:57] + '...'
            if len(meta_description) > 155:
                meta_description = meta_description[:152] + '...'
            keywords = [str(kw) for kw in keywords[:10] if kw]

            return {
                'meta_title': meta_title,
                'meta_description': meta_description,
                'keywords': keywords,
            }

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fall back to individual calls if JSON parsing fails
            logger.info("Full SEO JSON parse failed, falling back to individual calls")
            return {
                'meta_title': self.generate_meta_title(content, language),
                'meta_description': self.generate_meta_description(content, language),
                'keywords': self.extract_keywords(content),
            }
