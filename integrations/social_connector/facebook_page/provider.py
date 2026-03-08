"""
Facebook Page Social Connector
Post blog content to Facebook Pages via Graph API
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import logging

from blog.social_connectors.providers.base import (
    SocialConnectorBase,
    PostError,
    TokenRefreshError,
    RateLimitError
)

logger = logging.getLogger(__name__)


class FacebookPageConnector(SocialConnectorBase):
    """Facebook Page connector implementation"""

    # Required class attributes
    provider_key = "facebook_page"
    provider_name = "Facebook Page"

    # API configuration
    API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    TIMEOUT = 30  # seconds

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the connector with credentials

        Args:
            credentials: Dictionary with access_token and page_id
            config: Optional configuration dictionary

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__(credentials, config)

        self.access_token = credentials.get('access_token')
        self.page_id = credentials.get('page_id')
        self.page_name = credentials.get('page_name', '')

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return connector capabilities"""
        return {
            'text_posts': True,
            'image_posts': True,
            'video_posts': False,
            'carousel_posts': False,
            'stories': False,
            'reels': False,
            'scheduling': True,
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
                'help_text': 'Page access token from Facebook OAuth'
            },
            'page_id': {
                'type': 'text',
                'label': 'Page ID',
                'required': True,
                'help_text': 'The Facebook Page ID to post to'
            },
            'page_name': {
                'type': 'text',
                'label': 'Page Name',
                'required': False,
                'help_text': 'Display name of the page'
            }
        }

    @property
    def oauth_config(self) -> Dict[str, Any]:
        """Return OAuth configuration"""
        return {
            'authorize_url': f'https://www.facebook.com/{self.API_VERSION}/dialog/oauth',
            'token_url': f'{self.BASE_URL}/oauth/access_token',
            'scope': ['pages_manage_posts', 'pages_read_engagement', 'pages_show_list'],
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

        if not credentials.get('page_id'):
            raise ValueError("Page ID is required")

        # Basic format validation
        access_token = credentials['access_token']
        if len(access_token) < 20:
            raise ValueError("Access token appears to be invalid (too short)")

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
            # Get page info to verify credentials
            response = requests.get(
                f"{self.BASE_URL}/{self.page_id}",
                params={
                    'access_token': self.access_token,
                    'fields': 'id,name,fan_count,picture,link,verification_status'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': f"Successfully connected to {data.get('name', 'Facebook Page')}",
                    'details': {
                        'account_id': data.get('id'),
                        'account_name': data.get('name'),
                        'followers': data.get('fan_count', 0),
                        'account_url': data.get('link'),
                        'avatar_url': data.get('picture', {}).get('data', {}).get('url'),
                        'is_verified': data.get('verification_status') == 'verified'
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
                'message': 'Connection timeout - Facebook API is not responding',
                'details': {'error': 'timeout'}
            }

        except requests.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error - Unable to reach Facebook API',
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
        Create a post on the Facebook Page

        Args:
            message: The text content of the post
            link: Optional URL to include (creates link preview)
            image_urls: Optional list of image URLs to attach
            image_files: Optional list of image file objects to upload
            scheduled_time: Optional datetime for scheduled posting
            **kwargs: Additional options

        Returns:
            Dictionary with post result
        """
        try:
            endpoint = f"{self.BASE_URL}/{self.page_id}/feed"
            params = {
                'access_token': self.access_token,
                'message': message
            }

            # Add link for link preview
            if link:
                params['link'] = link

            # Handle scheduling
            if scheduled_time:
                # Facebook requires Unix timestamp
                params['published'] = 'false'
                params['scheduled_publish_time'] = int(scheduled_time.timestamp())

            # Handle image posting
            if image_urls and len(image_urls) > 0:
                # For single image, use photo endpoint
                if len(image_urls) == 1:
                    endpoint = f"{self.BASE_URL}/{self.page_id}/photos"
                    params['url'] = image_urls[0]
                    if message:
                        params['caption'] = message
                    params.pop('message', None)

            response = requests.post(endpoint, data=params, timeout=self.TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                post_id = data.get('id') or data.get('post_id')

                return {
                    'success': True,
                    'post_id': post_id,
                    'post_url': f"https://facebook.com/{post_id}" if post_id else None,
                    'scheduled': scheduled_time is not None,
                    'message': 'Post created successfully'
                }

            else:
                error = response.json().get('error', {})
                error_message = error.get('message', 'Unknown error')

                # Check for specific errors
                if error.get('code') == 190:
                    raise TokenRefreshError("Access token expired")
                elif error.get('code') == 4:
                    raise RateLimitError("Rate limit exceeded")

                raise PostError(f"Failed to create post: {error_message}")

        except (TokenRefreshError, RateLimitError, PostError):
            raise

        except requests.Timeout:
            raise PostError("Request timeout - Facebook API is not responding")

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise PostError(f"Failed to create post: {str(e)}")

    def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """
        Get the status of a posted content

        Args:
            post_id: The Facebook post ID

        Returns:
            Dictionary with post status and engagement
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/{post_id}",
                params={
                    'access_token': self.access_token,
                    'fields': 'id,message,created_time,shares,likes.summary(true),comments.summary(true),is_published'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'exists': True,
                    'status': 'published' if data.get('is_published', True) else 'scheduled',
                    'engagement': {
                        'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
                        'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
                        'shares': data.get('shares', {}).get('count', 0)
                    },
                    'post_url': f"https://facebook.com/{post_id}",
                    'created_at': data.get('created_time')
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
        Delete a post from the Facebook Page

        Args:
            post_id: The Facebook post ID

        Returns:
            Dictionary with deletion result
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/{post_id}",
                params={'access_token': self.access_token},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success', False):
                    return {
                        'success': True,
                        'message': 'Post deleted successfully'
                    }

            error = response.json().get('error', {})
            return {
                'success': False,
                'message': f"Failed to delete post: {error.get('message', 'Unknown error')}"
            }

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return {
                'success': False,
                'message': f'Error deleting post: {str(e)}'
            }

    def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the page access token

        Note: Page access tokens obtained from long-lived user tokens
        don't expire and don't need refresh. This method exchanges
        a short-lived token for a long-lived one.

        Returns:
            Dictionary with new credentials
        """
        try:
            # Exchange for long-lived token
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
                expires_in = data.get('expires_in', 5184000)  # Default 60 days

                return {
                    'success': True,
                    'credentials': {
                        'access_token': new_token,
                        'page_id': self.page_id,
                        'page_name': self.page_name,
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
        """Get Facebook's character limit for posts"""
        return 63206  # Facebook's limit

    def get_pages(self, user_access_token: str) -> List[Dict[str, Any]]:
        """
        Get list of pages the user manages (used during OAuth flow)

        Args:
            user_access_token: User's access token from OAuth

        Returns:
            List of pages with their access tokens
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/me/accounts",
                params={
                    'access_token': user_access_token,
                    'fields': 'id,name,access_token,picture,fan_count,link'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])

            return []

        except Exception as e:
            logger.error(f"Error fetching pages: {e}")
            return []
