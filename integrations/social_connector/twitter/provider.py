"""
X (Twitter) Social Connector
Post blog content to X via Twitter API v2
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import logging
import base64

from blog.social_connectors.providers.base import (
    SocialConnectorBase,
    PostError,
    TokenRefreshError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class TwitterConnector(SocialConnectorBase):
    """X (Twitter) connector implementation using API v2"""

    # Required class attributes
    provider_key = "twitter"
    provider_name = "X (Twitter)"

    # API configuration
    API_VERSION = "2"
    BASE_URL = "https://api.twitter.com/2"
    UPLOAD_URL = "https://upload.twitter.com/1.1"
    TIMEOUT = 30  # seconds
    CHARACTER_LIMIT = 280

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the connector with credentials

        Args:
            credentials: Dictionary with access_token, refresh_token, user_id
            config: Optional configuration dictionary

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__(credentials, config)

        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.user_id = credentials.get('user_id')
        self.username = credentials.get('username', '')

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return connector capabilities"""
        return {
            'text_posts': True,
            'image_posts': True,
            'video_posts': False,
            'carousel_posts': True,  # Up to 4 images
            'stories': False,
            'reels': False,
            'scheduling': False,  # Not available in free tier
            'link_preview': True,
            'hashtags': True,
            'mentions': True,
            'analytics': False,
            'comments': False,
            'token_refresh': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """Return JSON schema for credentials"""
        return {
            'access_token': {
                'type': 'text',
                'label': 'Access Token',
                'required': True,
                'secret': True,
                'help_text': 'OAuth 2.0 access token'
            },
            'refresh_token': {
                'type': 'text',
                'label': 'Refresh Token',
                'required': True,
                'secret': True,
                'help_text': 'Token used to refresh access token'
            },
            'user_id': {
                'type': 'text',
                'label': 'User ID',
                'required': True,
                'help_text': 'X user ID'
            },
            'username': {
                'type': 'text',
                'label': 'Username',
                'required': False,
                'help_text': 'X username/handle'
            }
        }

    @property
    def oauth_config(self) -> Dict[str, Any]:
        """Return OAuth configuration"""
        return {
            'authorize_url': 'https://twitter.com/i/oauth2/authorize',
            'token_url': 'https://api.twitter.com/2/oauth2/token',
            'scope': ['tweet.read', 'tweet.write', 'users.read', 'offline.access'],
            'response_type': 'code',
            'pkce_required': True,
        }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate credential format

        Args:
            credentials: Credentials dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        if not credentials.get('access_token'):
            raise ValueError("Access token is required")

        if not credentials.get('refresh_token'):
            raise ValueError("Refresh token is required")

        if not credentials.get('user_id'):
            raise ValueError("User ID is required")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()
        for key in ['access_token', 'refresh_token']:
            if key in redacted:
                token = redacted[key]
                if len(token) > 10:
                    redacted[key] = f"{token[:5]}***{token[-5:]}"
                else:
                    redacted[key] = "***"
        return redacted

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Get user info to verify credentials
            response = requests.get(
                f"{self.BASE_URL}/users/{self.user_id}",
                headers=self._get_headers(),
                params={'user.fields': 'id,name,username,profile_image_url,public_metrics,verified'},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                metrics = data.get('public_metrics', {})

                return {
                    'success': True,
                    'message': f"Successfully connected to @{data.get('username', 'unknown')}",
                    'details': {
                        'account_id': data.get('id'),
                        'account_name': data.get('name'),
                        'username': data.get('username'),
                        'followers': metrics.get('followers_count', 0),
                        'account_url': f"https://x.com/{data.get('username')}",
                        'avatar_url': data.get('profile_image_url'),
                        'is_verified': data.get('verified', False)
                    }
                }

            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Access token is invalid or expired. Please reconnect.',
                    'details': {'status_code': 401, 'error': 'token_invalid'}
                }

            elif response.status_code == 429:
                return {
                    'success': False,
                    'message': 'Rate limit exceeded. Please try again later.',
                    'details': {'status_code': 429, 'error': 'rate_limited'}
                }

            else:
                return {
                    'success': False,
                    'message': f'API error: HTTP {response.status_code}',
                    'details': {
                        'status_code': response.status_code,
                        'response': response.text[:200]
                    }
                }

        except requests.Timeout:
            return {
                'success': False,
                'message': 'Connection timeout - X API is not responding',
                'details': {'error': 'timeout'}
            }

        except requests.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error - Unable to reach X API',
                'details': {'error': 'connection_error'}
            }

        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return {
                'success': False,
                'message': f'Connection error: {str(e)}',
                'details': {'error': str(e)}
            }

    def create_post(
        self,
        message: str,
        link: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        image_files: Optional[List[Any]] = None,
        scheduled_time: Optional[datetime] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a tweet on X

        Args:
            message: The text content of the tweet (max 280 chars)
            link: Optional URL to include
            image_urls: Optional list of image URLs to attach (max 4)
            image_files: Optional list of image file objects to upload
            scheduled_time: Not supported - will be ignored
            **kwargs: Additional options

        Returns:
            Dictionary with post result
        """
        try:
            # Build tweet text
            tweet_text = message

            # Add link if provided (links count as 23 characters)
            if link:
                if tweet_text:
                    tweet_text = f"{tweet_text}\n\n{link}"
                else:
                    tweet_text = link

            # Truncate if necessary
            if len(tweet_text) > self.CHARACTER_LIMIT:
                # Reserve space for "..." and link
                max_text = self.CHARACTER_LIMIT - 3
                if link:
                    max_text -= (23 + 2)  # 23 for link + 2 for newlines
                tweet_text = message[:max_text] + "..."
                if link:
                    tweet_text = f"{tweet_text}\n\n{link}"

            payload = {'text': tweet_text}

            # Handle media attachments
            media_ids = []
            if image_urls:
                for url in image_urls[:4]:  # Max 4 images
                    media_id = self._upload_media_from_url(url)
                    if media_id:
                        media_ids.append(media_id)

            if media_ids:
                payload['media'] = {'media_ids': media_ids}

            response = requests.post(
                f"{self.BASE_URL}/tweets",
                headers=self._get_headers(),
                json=payload,
                timeout=self.TIMEOUT
            )

            if response.status_code in [200, 201]:
                data = response.json().get('data', {})
                tweet_id = data.get('id')

                return {
                    'success': True,
                    'post_id': tweet_id,
                    'post_url': f"https://x.com/{self.username}/status/{tweet_id}" if self.username else None,
                    'scheduled': False,
                    'message': 'Tweet posted successfully'
                }

            else:
                error = response.json()
                error_detail = error.get('detail', error.get('title', 'Unknown error'))

                if response.status_code == 401:
                    raise TokenRefreshError("Access token expired")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")

                raise PostError(f"Failed to create tweet: {error_detail}")

        except (TokenRefreshError, RateLimitError, PostError):
            raise

        except requests.Timeout:
            raise PostError("Request timeout - X API is not responding")

        except Exception as e:
            logger.error(f"Error creating tweet: {e}")
            raise PostError(f"Failed to create tweet: {str(e)}")

    def _upload_media_from_url(self, image_url: str) -> Optional[str]:
        """
        Upload media from URL to Twitter

        Args:
            image_url: URL of the image to upload

        Returns:
            Media ID if successful, None otherwise
        """
        try:
            # Download image
            img_response = requests.get(image_url, timeout=self.TIMEOUT)
            if img_response.status_code != 200:
                logger.warning(f"Failed to download image from {image_url}")
                return None

            # Upload to Twitter
            # Note: This requires OAuth 1.0a for media upload
            # For OAuth 2.0, you'd need to use a different approach
            # This is a simplified version
            media_data = base64.b64encode(img_response.content).decode('utf-8')

            upload_response = requests.post(
                f"{self.UPLOAD_URL}/media/upload.json",
                headers={'Authorization': f'Bearer {self.access_token}'},
                data={'media_data': media_data},
                timeout=self.TIMEOUT
            )

            if upload_response.status_code == 200:
                return upload_response.json().get('media_id_string')

            return None

        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None

    def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """
        Get the status of a tweet

        Args:
            post_id: The tweet ID

        Returns:
            Dictionary with tweet status and engagement
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/tweets/{post_id}",
                headers=self._get_headers(),
                params={'tweet.fields': 'public_metrics,created_at'},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                metrics = data.get('public_metrics', {})

                return {
                    'exists': True,
                    'status': 'published',
                    'engagement': {
                        'likes': metrics.get('like_count', 0),
                        'comments': metrics.get('reply_count', 0),
                        'shares': metrics.get('retweet_count', 0),
                        'impressions': metrics.get('impression_count', 0)
                    },
                    'post_url': f"https://x.com/i/status/{post_id}",
                    'created_at': data.get('created_at')
                }

            elif response.status_code == 404:
                return {
                    'exists': False,
                    'status': 'deleted',
                    'message': 'Tweet not found'
                }

            else:
                return {
                    'exists': False,
                    'status': 'unknown',
                    'message': f'Error fetching tweet: HTTP {response.status_code}'
                }

        except Exception as e:
            logger.error(f"Error getting tweet status: {e}")
            return {
                'exists': False,
                'status': 'error',
                'message': str(e)
            }

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        """
        Delete a tweet

        Args:
            post_id: The tweet ID

        Returns:
            Dictionary with deletion result
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/tweets/{post_id}",
                headers=self._get_headers(),
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                if data.get('deleted', False):
                    return {
                        'success': True,
                        'message': 'Tweet deleted successfully'
                    }

            error = response.json()
            return {
                'success': False,
                'message': f"Failed to delete tweet: {error.get('detail', 'Unknown error')}"
            }

        except Exception as e:
            logger.error(f"Error deleting tweet: {e}")
            return {
                'success': False,
                'message': f'Error deleting tweet: {str(e)}'
            }

    def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the OAuth 2.0 access token

        Returns:
            Dictionary with new credentials
        """
        try:
            # Get client credentials from config
            client_id = self.config.get('client_id')
            client_secret = self.config.get('client_secret')

            if not client_id:
                raise TokenRefreshError("Client ID not configured")

            # Prepare auth header
            if client_secret:
                auth_string = f"{client_id}:{client_secret}"
                auth_header = base64.b64encode(auth_string.encode()).decode()
                headers = {
                    'Authorization': f'Basic {auth_header}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            else:
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}

            response = requests.post(
                'https://api.twitter.com/2/oauth2/token',
                headers=headers,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': client_id
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get('access_token')
                new_refresh_token = data.get('refresh_token', self.refresh_token)
                expires_in = data.get('expires_in', 7200)

                return {
                    'success': True,
                    'credentials': {
                        'access_token': new_access_token,
                        'refresh_token': new_refresh_token,
                        'user_id': self.user_id,
                        'username': self.username,
                    },
                    'expires_in': expires_in,
                    'message': 'Token refreshed successfully'
                }

            error = response.json()
            raise TokenRefreshError(
                f"Failed to refresh token: {error.get('error_description', error.get('error', 'Unknown error'))}"
            )

        except TokenRefreshError:
            raise

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise TokenRefreshError(f"Failed to refresh token: {str(e)}")

    def get_character_limit(self) -> int:
        """Get X's character limit"""
        return self.CHARACTER_LIMIT
