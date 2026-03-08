"""
Twilio WhatsApp Provider
Send WhatsApp messages via Twilio's WhatsApp Business API
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider:
    """
    Twilio WhatsApp provider for sending WhatsApp messages.

    Uses the Twilio WhatsApp Business API to send messages via WhatsApp.
    Supports both template messages and free-form messages within the 24-hour window.
    """

    provider_key = 'twilio_whatsapp'
    provider_name = 'Twilio WhatsApp'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Twilio WhatsApp provider with credentials.

        Args:
            credentials: Dictionary containing:
                - account_sid (str): Twilio Account SID
                - auth_token (str): Twilio Auth Token
                - whatsapp_number (str): WhatsApp-enabled phone number
            config: Optional configuration dictionary
        """
        self.credentials = credentials
        self.config = config or {}

        self.account_sid = credentials.get('account_sid')
        self.auth_token = credentials.get('auth_token')
        self.whatsapp_number = credentials.get('whatsapp_number')

        self._client = None

    @property
    def client(self):
        """Lazy-load Twilio client."""
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                raise ImportError(
                    "Twilio library not installed. "
                    "Install it with: pip install twilio>=8.0.0"
                )
        return self._client

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Provider capabilities."""
        return {
            'sms': False,
            'mms': False,
            'whatsapp': True,
            'unicode': True,
            'delivery_reports': True,
            'two_way': True,
            'templates': True,
            'bulk_send': True,
            'rich_media': True,
        }

    def send_whatsapp(
        self,
        phone: str,
        message: str = None,
        template_name: str = None,
        template_params: Dict[str, str] = None,
        media_url: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio.

        Args:
            phone: Recipient phone number (E.164 format)
            message: Free-form message text (only works within 24hr window)
            template_name: WhatsApp template name (for template messages)
            template_params: Template parameter values
            media_url: URL of media to send
            **kwargs: Additional options

        Returns:
            Dict with 'success' boolean, 'message_id' on success, 'error' on failure
        """
        try:
            # Normalize phone number
            to_phone = self.normalize_phone(phone)

            # Format WhatsApp addresses
            from_whatsapp = f"whatsapp:{self.whatsapp_number}"
            to_whatsapp = f"whatsapp:{to_phone}"

            # Build message parameters
            params = {
                'from_': from_whatsapp,
                'to': to_whatsapp,
            }

            if message:
                params['body'] = message
            elif template_name:
                # For template messages, construct the content SID format
                # Note: This is a simplified implementation
                # In production, you'd use the Content API for templates
                params['body'] = self._format_template(template_name, template_params or {})

            # Add media URL if provided
            if media_url:
                params['media_url'] = [media_url]

            # Add status callback
            if kwargs.get('status_callback'):
                params['status_callback'] = kwargs['status_callback']

            # Send message
            twilio_message = self.client.messages.create(**params)

            logger.info(
                f"WhatsApp message sent via Twilio to {to_phone} "
                f"(SID: {twilio_message.sid})"
            )

            return {
                'success': True,
                'message_id': twilio_message.sid,
                'status': twilio_message.status,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send WhatsApp via Twilio: {error_msg}")

            error_code = None
            if hasattr(e, 'code'):
                error_code = e.code

            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code,
            }

    def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        SMS is not supported by this provider.

        Use the Twilio SMS provider for SMS messages.
        """
        return {
            'success': False,
            'error': 'SMS not supported. Use the Twilio SMS provider instead.',
        }

    def _format_template(self, template_name: str, params: Dict[str, str]) -> str:
        """
        Format a template message.

        Note: This is a simplified implementation for basic templates.
        For full WhatsApp template support with the Content API,
        additional implementation would be needed.

        Args:
            template_name: Template identifier
            params: Parameter values to substitute

        Returns:
            Formatted message string
        """
        # This is a placeholder for template formatting
        # The actual implementation would depend on the template structure
        message = template_name
        for key, value in params.items():
            message = message.replace(f"{{{key}}}", str(value))
        return message

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Twilio WhatsApp API.

        Returns:
            Dict with 'success' boolean and status details
        """
        try:
            # Verify account by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()

            return {
                'success': True,
                'message': 'Successfully connected to Twilio',
                'account_name': account.friendly_name,
                'account_status': account.status,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Twilio WhatsApp connection test failed: {error_msg}")

            return {
                'success': False,
                'error': error_msg,
            }

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Validate Twilio WhatsApp credentials.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required credentials
        if not self.account_sid:
            return False, "Account SID is required"

        if not self.auth_token:
            return False, "Auth Token is required"

        if not self.whatsapp_number:
            return False, "WhatsApp number is required"

        # Validate format
        if not self.account_sid.startswith('AC'):
            return False, "Account SID should start with 'AC'"

        if len(self.account_sid) != 34:
            return False, "Account SID should be 34 characters"

        # Test connection
        result = self.test_connection()
        if result['success']:
            return True, None
        else:
            return False, result.get('error', 'Connection test failed')

    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to E.164 format.

        Args:
            phone: Phone number in various formats

        Returns:
            Phone number in E.164 format (e.g., +1234567890)
        """
        # Remove common formatting characters and whatsapp: prefix
        phone = phone.replace('whatsapp:', '')
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Ensure it starts with +
        if not cleaned.startswith('+'):
            if len(cleaned) == 10:
                cleaned = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                cleaned = '+' + cleaned
            else:
                cleaned = '+' + cleaned

        return cleaned

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive information from credentials for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Redacted copy of credentials
        """
        redacted = credentials.copy()

        if 'auth_token' in redacted:
            redacted['auth_token'] = '***REDACTED***'

        return redacted
