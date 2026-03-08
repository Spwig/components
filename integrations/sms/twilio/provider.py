"""
Twilio SMS Provider
Send SMS messages via Twilio's global network
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TwilioSMSProvider:
    """
    Twilio SMS provider for sending text messages.

    Uses the Twilio REST API to send SMS messages worldwide.
    Supports delivery reports and two-way messaging.
    """

    provider_key = 'twilio'
    provider_name = 'Twilio SMS'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Twilio provider with credentials.

        Args:
            credentials: Dictionary containing:
                - account_sid (str): Twilio Account SID
                - auth_token (str): Twilio Auth Token
                - phone_number (str): From phone number in E.164 format
            config: Optional configuration dictionary
        """
        self.credentials = credentials
        self.config = config or {}

        self.account_sid = credentials.get('account_sid')
        self.auth_token = credentials.get('auth_token')
        self.phone_number = credentials.get('phone_number')

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
            'sms': True,
            'mms': True,
            'whatsapp': False,
            'unicode': True,
            'delivery_reports': True,
            'two_way': True,
            'templates': False,
            'bulk_send': True,
        }

    def send_sms(self, phone: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send an SMS message via Twilio.

        Args:
            phone: Recipient phone number (E.164 format preferred)
            message: Message text (max 1600 characters for concatenated SMS)
            **kwargs: Additional options:
                - media_url: URL of media to send (for MMS)
                - status_callback: URL for delivery status webhook

        Returns:
            Dict with 'success' boolean, 'message_id' on success, 'error' on failure
        """
        try:
            # Normalize phone number
            to_phone = self.normalize_phone(phone)

            # Build message parameters
            params = {
                'body': message,
                'from_': self.phone_number,
                'to': to_phone,
            }

            # Add media URL for MMS
            if kwargs.get('media_url'):
                params['media_url'] = [kwargs['media_url']]

            # Add status callback
            if kwargs.get('status_callback'):
                params['status_callback'] = kwargs['status_callback']

            # Send message
            twilio_message = self.client.messages.create(**params)

            logger.info(
                f"SMS sent via Twilio to {to_phone} "
                f"(SID: {twilio_message.sid})"
            )

            return {
                'success': True,
                'message_id': twilio_message.sid,
                'status': twilio_message.status,
                'segments': twilio_message.num_segments,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send SMS via Twilio: {error_msg}")

            # Extract Twilio error code if available
            error_code = None
            if hasattr(e, 'code'):
                error_code = e.code

            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code,
            }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Twilio API.

        Returns:
            Dict with 'success' boolean and status details
        """
        try:
            # Verify account by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()

            # Check if phone number is valid
            try:
                incoming_numbers = self.client.incoming_phone_numbers.list(
                    phone_number=self.phone_number,
                    limit=1
                )
                phone_valid = len(incoming_numbers) > 0
            except Exception:
                phone_valid = False

            return {
                'success': True,
                'message': 'Successfully connected to Twilio',
                'account_name': account.friendly_name,
                'account_status': account.status,
                'phone_number_valid': phone_valid,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Twilio connection test failed: {error_msg}")

            return {
                'success': False,
                'error': error_msg,
            }

    def validate_credentials(self) -> tuple[bool, Optional[str]]:
        """
        Validate Twilio credentials.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required credentials
        if not self.account_sid:
            return False, "Account SID is required"

        if not self.auth_token:
            return False, "Auth Token is required"

        if not self.phone_number:
            return False, "From phone number is required"

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

    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance (if available).

        Returns:
            Dict with balance information
        """
        try:
            balance = self.client.api.accounts(self.account_sid).balance.fetch()
            return {
                'success': True,
                'balance': balance.balance,
                'currency': balance.currency,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to E.164 format.

        Args:
            phone: Phone number in various formats

        Returns:
            Phone number in E.164 format (e.g., +1234567890)
        """
        # Remove common formatting characters
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Ensure it starts with +
        if not cleaned.startswith('+'):
            # Assume it's a US number if no country code
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
