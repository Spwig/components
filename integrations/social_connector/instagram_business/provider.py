"""
Instagram Business Social Connector
Post blog content to Instagram Business accounts via Facebook Graph API
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import logging
import time

from blog.social_connectors.providers.base import (
    SocialConnectorBase,
    PostError,
    TokenRefreshError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class InstagramBusinessConnector(SocialConnectorBase):
    """Instagram Business connector implementation using Facebook Graph API"""

    # Required class attributes
    provider_key = "instagram_business"
    provider_name = "Instagram Business"

    # API configuration
    API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    TIMEOUT = 30  # seconds
    CHARACTER_LIMIT = 2200
    MAX_HASHTAGS = 30
    MAX_CAROUSEL_IMAGES = 10

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the connector with credentials

        Args:
            credentials: Dictionary with access_token, instagram_account_id, etc.
            config: Optional configuration dictionary

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__(credentials, config)

        self.access_token = credentials.get('access_token')
        self.instagram_account_id = credentials.get('instagram_account_id')
        self.instagram_username = credentials.get('instagram_username', '')
        self.facebook_page_id = credentials.get('facebook_page_id')

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return connector capabilities"""
        return {
            'text_posts': False,  # Instagram requires images
            'image_posts': True,
            'video_posts': False,
            'carousel_posts': True,
            'stories': False,
            'reels': False,
            'scheduling': False,
            'link_preview': False,  # No clickable links in posts
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
                'help_text': 'Page access token with Instagram permissions'
            },
            'instagram_account_id': {
                'type': 'text',
                'label': 'Instagram Account ID',
                'required': True,
                'help_text': 'Instagram Business Account ID'
            },
            'instagram_username': {
                'type': 'text',
                'label': 'Instagram Username',
                'required': False,
                'help_text': 'Instagram username'
            },
            'facebook_page_id': {
                'type': 'text',
                'label': 'Facebook Page ID',
                'required': True,
                'help_text': 'Connected Facebook Page ID'
            }
        }

    @property
    def oauth_config(self) -> Dict[str, Any]:
        """Return OAuth configuration"""
        return {
            'authorize_url': f'https://www.facebook.com/{self.API_VERSION}/dialog/oauth',
            'token_url': f'{self.BASE_URL}/oauth/access_token',
            'scope': [
                'instagram_basic',
                'instagram_content_publish',
                'pages_show_list',
                'pages_read_engagement'
            ],
            'response_type': 'code',
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

        if not credentials.get('instagram_account_id'):
            raise ValueError("Instagram Account ID is required")

        if not credentials.get('facebook_page_id'):
            raise ValueError("Facebook Page ID is required")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive credential values for logging

        Args:
            credentials: Credentials dictionary

        Returns:
            Dictionary with sensitive values masked
        """
        redacted = credentials.copy()
        if 'access_token' in redacted:
            token = redacted['access_token']
            if len(token) > 10:
                redacted['access_token'] = f"{token[:5]}***{token[-5:]}"
            else:
                redacted['access_token'] = "***"
        return redacted

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Get Instagram account info
            response = requests.get(
                f"{self.BASE_URL}/{self.instagram_account_id}",
                params={
                    'access_token': self.access_token,
                    'fields': 'id,username,name,profile_picture_url,followers_count,media_count'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': f"Successfully connected to @{data.get('username', 'instagram')}",
                    'details': {
                        'account_id': data.get('id'),
                        'account_name': data.get('name'),
                        'username': data.get('username'),
                        'followers': data.get('followers_count', 0),
                        'account_url': f"https://instagram.com/{data.get('username')}",
                        'avatar_url': data.get('profile_picture_url'),
                        'media_count': data.get('media_count', 0)
                    }
                }

            elif response.status_code == 400:
                error = response.json().get('error', {})
                return {
                    'success': False,
                    'message': f"API Error: {error.get('message', 'Invalid request')}",
                    'details': {'error_code': error.get('code'), 'error_type': error.get('type')}
                }

            elif response.status_code == 401 or response.status_code == 190:
                return {
                    'success': False,
                    'message': 'Access token is invalid or expired. Please reconnect.',
                    'details': {'status_code': response.status_code, 'error': 'token_invalid'}
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
                'message': 'Connection timeout - Instagram API is not responding',
                'details': {'error': 'timeout'}
            }

        except requests.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error - Unable to reach Instagram API',
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
        Create a post on Instagram

        Note: Instagram requires at least one image for posts.
        Links cannot be clickable - consider adding "Link in bio" text.

        Args:
            message: The caption for the post (max 2200 chars)
            link: Not directly supported - will be added to caption as text
            image_urls: Required - list of image URLs (1-10 for carousel)
            image_files: Optional list of image file objects to upload
            scheduled_time: Not supported
            **kwargs: Additional options

        Returns:
            Dictionary with post result
        """
        try:
            if not image_urls or len(image_urls) == 0:
                raise PostError("Instagram requires at least one image for posts")

            # Prepare caption
            caption = message[:self.CHARACTER_LIMIT]

            # Add link text if provided (Instagram doesn't support clickable links)
            if link and kwargs.get('include_link_text', True):
                link_text = "\n\nLink in bio"
                if len(caption) + len(link_text) <= self.CHARACTER_LIMIT:
                    caption += link_text

            # Single image or carousel
            if len(image_urls) == 1:
                return self._create_single_image_post(image_urls[0], caption)
            else:
                return self._create_carousel_post(image_urls[:self.MAX_CAROUSEL_IMAGES], caption)

        except PostError:
            raise

        except requests.Timeout:
            raise PostError("Request timeout - Instagram API is not responding")

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise PostError(f"Failed to create post: {str(e)}")

    def _create_single_image_post(self, image_url: str, caption: str) -> Dict[str, Any]:
        """Create a single image post"""
        try:
            # Step 1: Create container
            container_response = requests.post(
                f"{self.BASE_URL}/{self.instagram_account_id}/media",
                params={
                    'access_token': self.access_token,
                    'image_url': image_url,
                    'caption': caption
                },
                timeout=self.TIMEOUT
            )

            if container_response.status_code != 200:
                error = container_response.json().get('error', {})
                if error.get('code') == 190:
                    raise TokenRefreshError("Access token expired")
                raise PostError(f"Failed to create media container: {error.get('message', 'Unknown error')}")

            container_id = container_response.json().get('id')

            # Step 2: Wait for container to be ready and publish
            return self._publish_container(container_id)

        except (TokenRefreshError, PostError):
            raise
        except Exception as e:
            logger.error(f"Error creating single image post: {e}")
            raise PostError(f"Failed to create post: {str(e)}")

    def _create_carousel_post(self, image_urls: List[str], caption: str) -> Dict[str, Any]:
        """Create a carousel post with multiple images"""
        try:
            # Step 1: Create individual image containers
            children_ids = []
            for image_url in image_urls:
                response = requests.post(
                    f"{self.BASE_URL}/{self.instagram_account_id}/media",
                    params={
                        'access_token': self.access_token,
                        'image_url': image_url,
                        'is_carousel_item': 'true'
                    },
                    timeout=self.TIMEOUT
                )

                if response.status_code != 200:
                    error = response.json().get('error', {})
                    logger.warning(f"Failed to create carousel item: {error.get('message')}")
                    continue

                children_ids.append(response.json().get('id'))

            if not children_ids:
                raise PostError("Failed to create any carousel items")

            # Step 2: Create carousel container
            carousel_response = requests.post(
                f"{self.BASE_URL}/{self.instagram_account_id}/media",
                params={
                    'access_token': self.access_token,
                    'media_type': 'CAROUSEL',
                    'caption': caption,
                    'children': ','.join(children_ids)
                },
                timeout=self.TIMEOUT
            )

            if carousel_response.status_code != 200:
                error = carousel_response.json().get('error', {})
                raise PostError(f"Failed to create carousel: {error.get('message', 'Unknown error')}")

            container_id = carousel_response.json().get('id')

            # Step 3: Publish
            return self._publish_container(container_id)

        except PostError:
            raise
        except Exception as e:
            logger.error(f"Error creating carousel post: {e}")
            raise PostError(f"Failed to create carousel: {str(e)}")

    def _publish_container(self, container_id: str, max_retries: int = 10) -> Dict[str, Any]:
        """
        Wait for container to be ready and publish it

        Args:
            container_id: The media container ID
            max_retries: Maximum number of status check retries

        Returns:
            Dictionary with post result
        """
        # Wait for container to be ready
        for _ in range(max_retries):
            status_response = requests.get(
                f"{self.BASE_URL}/{container_id}",
                params={
                    'access_token': self.access_token,
                    'fields': 'status_code,status'
                },
                timeout=self.TIMEOUT
            )

            if status_response.status_code == 200:
                status = status_response.json().get('status_code')
                if status == 'FINISHED':
                    break
                elif status == 'ERROR':
                    error_msg = status_response.json().get('status', 'Unknown error')
                    raise PostError(f"Media processing failed: {error_msg}")

            time.sleep(2)  # Wait 2 seconds before next check
        else:
            raise PostError("Media container did not become ready in time")

        # Publish the container
        publish_response = requests.post(
            f"{self.BASE_URL}/{self.instagram_account_id}/media_publish",
            params={
                'access_token': self.access_token,
                'creation_id': container_id
            },
            timeout=self.TIMEOUT
        )

        if publish_response.status_code == 200:
            media_id = publish_response.json().get('id')
            return {
                'success': True,
                'post_id': media_id,
                'post_url': f"https://instagram.com/p/{media_id}" if media_id else None,
                'scheduled': False,
                'message': 'Post published successfully'
            }

        error = publish_response.json().get('error', {})
        if error.get('code') == 190:
            raise TokenRefreshError("Access token expired")
        elif error.get('code') == 4:
            raise RateLimitError("Rate limit exceeded")

        raise PostError(f"Failed to publish: {error.get('message', 'Unknown error')}")

    def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """
        Get the status of an Instagram post

        Args:
            post_id: The Instagram media ID

        Returns:
            Dictionary with post status and engagement
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/{post_id}",
                params={
                    'access_token': self.access_token,
                    'fields': 'id,caption,media_type,timestamp,like_count,comments_count,permalink'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'exists': True,
                    'status': 'published',
                    'engagement': {
                        'likes': data.get('like_count', 0),
                        'comments': data.get('comments_count', 0),
                        'shares': 0  # Instagram doesn't expose share count
                    },
                    'post_url': data.get('permalink'),
                    'created_at': data.get('timestamp')
                }

            elif response.status_code == 404:
                return {
                    'exists': False,
                    'status': 'deleted',
                    'message': 'Post not found'
                }

            else:
                return {
                    'exists': False,
                    'status': 'unknown',
                    'message': f'Error fetching post: HTTP {response.status_code}'
                }

        except Exception as e:
            logger.error(f"Error getting post status: {e}")
            return {
                'exists': False,
                'status': 'error',
                'message': str(e)
            }

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        """
        Delete an Instagram post

        Note: Instagram API does not support deleting posts via API.
        Posts must be deleted manually through the Instagram app.

        Args:
            post_id: The Instagram media ID

        Returns:
            Dictionary indicating deletion is not supported
        """
        return {
            'success': False,
            'message': 'Instagram API does not support deleting posts. Please delete manually through the Instagram app.'
        }

    def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the page access token

        Note: Uses Facebook's token exchange endpoint.

        Returns:
            Dictionary with new credentials
        """
        try:
            # Exchange for long-lived token via Facebook
            response = requests.get(
                f"{self.BASE_URL}/oauth/access_token",
                params={
                    'grant_type': 'fb_exchange_token',
                    'client_id': self.config.get('app_id'),
                    'client_secret': self.config.get('app_secret'),
                    'fb_exchange_token': self.access_token
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                new_token = data.get('access_token')
                expires_in = data.get('expires_in', 5184000)

                return {
                    'success': True,
                    'credentials': {
                        'access_token': new_token,
                        'instagram_account_id': self.instagram_account_id,
                        'instagram_username': self.instagram_username,
                        'facebook_page_id': self.facebook_page_id,
                    },
                    'expires_in': expires_in,
                    'message': 'Token refreshed successfully'
                }

            error = response.json().get('error', {})
            raise TokenRefreshError(f"Failed to refresh token: {error.get('message', 'Unknown error')}")

        except TokenRefreshError:
            raise

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise TokenRefreshError(f"Failed to refresh token: {str(e)}")

    def get_character_limit(self) -> int:
        """Get Instagram's character limit for captions"""
        return self.CHARACTER_LIMIT

    def get_instagram_accounts(self, user_access_token: str) -> List[Dict[str, Any]]:
        """
        Get list of Instagram Business accounts connected to user's Facebook pages

        Args:
            user_access_token: User's access token from OAuth

        Returns:
            List of Instagram accounts with their IDs
        """
        try:
            # Get user's pages
            pages_response = requests.get(
                f"{self.BASE_URL}/me/accounts",
                params={
                    'access_token': user_access_token,
                    'fields': 'id,name,access_token,instagram_business_account'
                },
                timeout=self.TIMEOUT
            )

            if pages_response.status_code != 200:
                return []

            pages = pages_response.json().get('data', [])
            instagram_accounts = []

            for page in pages:
                ig_account = page.get('instagram_business_account')
                if ig_account:
                    # Get Instagram account details
                    ig_response = requests.get(
                        f"{self.BASE_URL}/{ig_account['id']}",
                        params={
                            'access_token': page['access_token'],
                            'fields': 'id,username,name,profile_picture_url'
                        },
                        timeout=self.TIMEOUT
                    )

                    if ig_response.status_code == 200:
                        ig_data = ig_response.json()
                        instagram_accounts.append({
                            'instagram_account_id': ig_data.get('id'),
                            'instagram_username': ig_data.get('username'),
                            'instagram_name': ig_data.get('name'),
                            'profile_picture': ig_data.get('profile_picture_url'),
                            'facebook_page_id': page.get('id'),
                            'facebook_page_name': page.get('name'),
                            'page_access_token': page.get('access_token')
                        })

            return instagram_accounts

        except Exception as e:
            logger.error(f"Error fetching Instagram accounts: {e}")
            return []
