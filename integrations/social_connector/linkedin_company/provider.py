"""
LinkedIn Company Page Social Connector
Post blog content to LinkedIn Company Pages via Marketing API
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


class LinkedInCompanyConnector(SocialConnectorBase):
    """LinkedIn Company Page connector implementation"""

    # Required class attributes
    provider_key = "linkedin_company"
    provider_name = "LinkedIn Company Page"

    # API configuration
    API_VERSION = "202401"
    BASE_URL = "https://api.linkedin.com/v2"
    REST_URL = "https://api.linkedin.com/rest"
    TIMEOUT = 30  # seconds
    CHARACTER_LIMIT = 3000

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize the connector with credentials

        Args:
            credentials: Dictionary with access_token and organization_id
            config: Optional configuration dictionary

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__(credentials, config)

        self.access_token = credentials.get('access_token')
        self.refresh_token = credentials.get('refresh_token')
        self.organization_id = credentials.get('organization_id')
        self.organization_name = credentials.get('organization_name', '')

        # Ensure organization ID is in URN format
        if self.organization_id and not self.organization_id.startswith('urn:li:'):
            self.organization_id = f"urn:li:organization:{self.organization_id}"

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
            'scheduling': False,
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
                'required': False,
                'secret': True,
                'help_text': 'Token for refreshing access token'
            },
            'organization_id': {
                'type': 'text',
                'label': 'Organization ID',
                'required': True,
                'help_text': 'LinkedIn Organization URN'
            },
            'organization_name': {
                'type': 'text',
                'label': 'Organization Name',
                'required': False,
                'help_text': 'Company page name'
            }
        }

    @property
    def oauth_config(self) -> Dict[str, Any]:
        """Return OAuth configuration"""
        return {
            'authorize_url': 'https://www.linkedin.com/oauth/v2/authorization',
            'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
            'scope': ['r_organization_social', 'w_organization_social', 'rw_organization_admin'],
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

        if not credentials.get('organization_id'):
            raise ValueError("Organization ID is required")

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
            if key in redacted and redacted[key]:
                token = redacted[key]
                if len(token) > 10:
                    redacted[key] = f"{token[:5]}***{token[-5:]}"
                else:
                    redacted[key] = "***"
        return redacted

    def _get_headers(self, use_rest_api: bool = False) -> Dict[str, str]:
        """Get authorization headers"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        if use_rest_api:
            headers['LinkedIn-Version'] = self.API_VERSION
        return headers

    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and credential validity

        Returns:
            Dictionary with success status, message, and details
        """
        try:
            # Get organization info to verify credentials
            org_id = self.organization_id.split(':')[-1] if ':' in self.organization_id else self.organization_id

            response = requests.get(
                f"{self.BASE_URL}/organizations/{org_id}",
                headers=self._get_headers(),
                params={'projection': '(id,localizedName,vanityName,logoV2)'},
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                logo_url = None
                if 'logoV2' in data:
                    logo_elements = data.get('logoV2', {}).get('original~', {}).get('elements', [])
                    if logo_elements:
                        logo_url = logo_elements[0].get('identifiers', [{}])[0].get('identifier')

                return {
                    'success': True,
                    'message': f"Successfully connected to {data.get('localizedName', 'LinkedIn Company')}",
                    'details': {
                        'account_id': data.get('id'),
                        'account_name': data.get('localizedName'),
                        'account_url': f"https://linkedin.com/company/{data.get('vanityName', org_id)}",
                        'avatar_url': logo_url,
                    }
                }

            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Access token is invalid or expired. Please reconnect.',
                    'details': {'status_code': 401, 'error': 'token_invalid'}
                }

            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'You do not have permission to access this organization.',
                    'details': {'status_code': 403, 'error': 'forbidden'}
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
                'message': 'Connection timeout - LinkedIn API is not responding',
                'details': {'error': 'timeout'}
            }

        except requests.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error - Unable to reach LinkedIn API',
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
        Create a post on the LinkedIn Company Page

        Args:
            message: The text content of the post (max 3000 chars)
            link: Optional URL to include (creates article preview)
            image_urls: Optional list of image URLs to attach
            image_files: Optional list of image file objects to upload
            scheduled_time: Not supported - will be ignored
            **kwargs: Additional options (visibility, etc.)

        Returns:
            Dictionary with post result
        """
        try:
            # Build the post payload
            visibility = kwargs.get('visibility', 'PUBLIC')

            payload = {
                'author': self.organization_id,
                'lifecycleState': 'PUBLISHED',
                'visibility': {
                    'com.linkedin.ugc.MemberNetworkVisibility': visibility
                },
                'specificContent': {
                    'com.linkedin.ugc.ShareContent': {
                        'shareCommentary': {
                            'text': message[:self.CHARACTER_LIMIT]
                        },
                        'shareMediaCategory': 'NONE'
                    }
                }
            }

            share_content = payload['specificContent']['com.linkedin.ugc.ShareContent']

            # Add article with link preview
            if link:
                share_content['shareMediaCategory'] = 'ARTICLE'
                share_content['media'] = [{
                    'status': 'READY',
                    'originalUrl': link
                }]

            # Handle image upload
            elif image_urls and len(image_urls) > 0:
                # Upload first image
                image_urn = self._upload_image(image_urls[0])
                if image_urn:
                    share_content['shareMediaCategory'] = 'IMAGE'
                    share_content['media'] = [{
                        'status': 'READY',
                        'media': image_urn
                    }]

            response = requests.post(
                f"{self.BASE_URL}/ugcPosts",
                headers=self._get_headers(),
                json=payload,
                timeout=self.TIMEOUT
            )

            if response.status_code in [200, 201]:
                data = response.json()
                post_id = data.get('id', '')

                # Extract activity ID for URL
                activity_id = post_id.split(':')[-1] if post_id else None

                return {
                    'success': True,
                    'post_id': post_id,
                    'post_url': f"https://linkedin.com/feed/update/{post_id}" if post_id else None,
                    'scheduled': False,
                    'message': 'Post created successfully'
                }

            else:
                error = response.json()
                error_message = error.get('message', 'Unknown error')

                if response.status_code == 401:
                    raise TokenRefreshError("Access token expired")
                elif response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded")

                raise PostError(f"Failed to create post: {error_message}")

        except (TokenRefreshError, RateLimitError, PostError):
            raise

        except requests.Timeout:
            raise PostError("Request timeout - LinkedIn API is not responding")

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            raise PostError(f"Failed to create post: {str(e)}")

    def _upload_image(self, image_url: str) -> Optional[str]:
        """
        Upload an image to LinkedIn

        Args:
            image_url: URL of the image to upload

        Returns:
            Image URN if successful, None otherwise
        """
        try:
            # Step 1: Register image upload
            register_payload = {
                'registerUploadRequest': {
                    'owner': self.organization_id,
                    'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                    'serviceRelationships': [{
                        'identifier': 'urn:li:userGeneratedContent',
                        'relationshipType': 'OWNER'
                    }]
                }
            }

            register_response = requests.post(
                f"{self.BASE_URL}/assets?action=registerUpload",
                headers=self._get_headers(),
                json=register_payload,
                timeout=self.TIMEOUT
            )

            if register_response.status_code != 200:
                logger.warning(f"Failed to register image upload: {register_response.text}")
                return None

            register_data = register_response.json()
            upload_url = register_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = register_data['value']['asset']

            # Step 2: Download image
            img_response = requests.get(image_url, timeout=self.TIMEOUT)
            if img_response.status_code != 200:
                logger.warning(f"Failed to download image from {image_url}")
                return None

            # Step 3: Upload image to LinkedIn
            upload_headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/octet-stream'
            }

            upload_response = requests.put(
                upload_url,
                headers=upload_headers,
                data=img_response.content,
                timeout=self.TIMEOUT
            )

            if upload_response.status_code in [200, 201]:
                return asset_urn

            logger.warning(f"Failed to upload image: {upload_response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None

    def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """
        Get the status of a LinkedIn post

        Args:
            post_id: The post URN

        Returns:
            Dictionary with post status
        """
        try:
            # LinkedIn doesn't provide easy post lookup
            # Return basic info based on post_id
            return {
                'exists': True,
                'status': 'published',
                'engagement': {
                    'likes': 0,
                    'comments': 0,
                    'shares': 0
                },
                'post_url': f"https://linkedin.com/feed/update/{post_id}"
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
        Delete a LinkedIn post

        Args:
            post_id: The post URN

        Returns:
            Dictionary with deletion result
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/ugcPosts/{post_id}",
                headers=self._get_headers(),
                timeout=self.TIMEOUT
            )

            if response.status_code in [200, 204]:
                return {
                    'success': True,
                    'message': 'Post deleted successfully'
                }

            return {
                'success': False,
                'message': f"Failed to delete post: HTTP {response.status_code}"
            }

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return {
                'success': False,
                'message': f'Error deleting post: {str(e)}'
            }

    def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the OAuth 2.0 access token

        Returns:
            Dictionary with new credentials
        """
        try:
            if not self.refresh_token:
                raise TokenRefreshError("No refresh token available")

            client_id = self.config.get('client_id')
            client_secret = self.config.get('client_secret')

            if not client_id or not client_secret:
                raise TokenRefreshError("Client credentials not configured")

            response = requests.post(
                'https://www.linkedin.com/oauth/v2/accessToken',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': client_id,
                    'client_secret': client_secret
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get('access_token')
                new_refresh_token = data.get('refresh_token', self.refresh_token)
                expires_in = data.get('expires_in', 5184000)

                return {
                    'success': True,
                    'credentials': {
                        'access_token': new_access_token,
                        'refresh_token': new_refresh_token,
                        'organization_id': self.organization_id,
                        'organization_name': self.organization_name,
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
        """Get LinkedIn's character limit"""
        return self.CHARACTER_LIMIT

    def get_organizations(self, user_access_token: str) -> List[Dict[str, Any]]:
        """
        Get list of organizations the user administers (used during OAuth flow)

        Args:
            user_access_token: User's access token from OAuth

        Returns:
            List of organizations with their IDs
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/organizationalEntityAcls",
                headers={
                    'Authorization': f'Bearer {user_access_token}',
                    'X-Restli-Protocol-Version': '2.0.0'
                },
                params={
                    'q': 'roleAssignee',
                    'role': 'ADMINISTRATOR',
                    'projection': '(elements*(organizationalTarget))'
                },
                timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                organizations = []

                for element in data.get('elements', []):
                    org_urn = element.get('organizationalTarget')
                    if org_urn:
                        # Get organization details
                        org_id = org_urn.split(':')[-1]
                        org_response = requests.get(
                            f"{self.BASE_URL}/organizations/{org_id}",
                            headers={
                                'Authorization': f'Bearer {user_access_token}',
                                'X-Restli-Protocol-Version': '2.0.0'
                            },
                            timeout=self.TIMEOUT
                        )
                        if org_response.status_code == 200:
                            org_data = org_response.json()
                            organizations.append({
                                'id': org_urn,
                                'name': org_data.get('localizedName'),
                                'vanity_name': org_data.get('vanityName')
                            })

                return organizations

            return []

        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")
            return []
