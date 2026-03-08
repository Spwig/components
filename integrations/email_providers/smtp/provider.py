"""
SMTP Email Provider
External SMTP server integration for sending transactional emails

Supports any standard SMTP server including:
- Gmail SMTP
- Outlook / Office 365
- SendGrid SMTP Relay
- Mailgun SMTP
- Amazon SES
- Custom SMTP servers
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from email.utils import formataddr, formatdate, make_msgid
from typing import Dict, Any, Optional, List
import socket

from email_system.providers.base import EmailProviderBase, EmailMessage

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProviderBase):
    """
    External SMTP server provider for sending transactional emails.

    Uses Python's built-in smtplib to connect to any standard SMTP server.
    Supports TLS/STARTTLS and SSL connections, attachments, and inline images.
    """

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize SMTP provider with credentials.

        Args:
            credentials: Dictionary containing SMTP configuration:
                - host (str): SMTP server hostname
                - port (int): SMTP server port
                - username (str): SMTP authentication username
                - password (str): SMTP authentication password
                - use_tls (bool): Use STARTTLS (default: True)
                - use_ssl (bool): Use implicit SSL (default: False)
                - timeout (int): Connection timeout in seconds (default: 30)
            config: Optional configuration dictionary
        """
        super().__init__(credentials, config)
        self.validate_credentials(credentials)
        self.host = credentials.get('host')
        self.port = credentials.get('port', 587)
        self.username = credentials.get('username')
        self.password = credentials.get('password')
        self.use_tls = credentials.get('use_tls', True)
        self.use_ssl = credentials.get('use_ssl', False)
        self.timeout = credentials.get('timeout', 30)

    @property
    def provider_key(self) -> str:
        """Unique identifier for this provider."""
        return 'smtp'

    @property
    def provider_name(self) -> str:
        """Human-readable name."""
        return 'SMTP Server'

    @property
    def credential_schema(self) -> Dict[str, Dict[str, Any]]:
        """Return credential schema for SMTP provider."""
        return {
            'host': {
                'type': 'text', 'label': 'SMTP Server Host',
                'help_text': 'Hostname or IP address of the SMTP server',
                'required': True,
            },
            'port': {
                'type': 'number', 'label': 'SMTP Port',
                'help_text': 'Port number (usually 587 for TLS, 465 for SSL)',
                'required': True, 'default': 587,
            },
            'username': {
                'type': 'text', 'label': 'Username',
                'help_text': 'SMTP authentication username',
                'required': True,
            },
            'password': {
                'type': 'password', 'label': 'Password',
                'help_text': 'SMTP authentication password',
                'required': True,
            },
            'use_tls': {
                'type': 'boolean', 'label': 'Use TLS (STARTTLS)',
                'help_text': 'Enable TLS encryption via STARTTLS command',
                'default': True,
            },
            'use_ssl': {
                'type': 'boolean', 'label': 'Use SSL',
                'help_text': 'Use implicit SSL/TLS connection',
                'default': False,
            },
            'timeout': {
                'type': 'number', 'label': 'Connection Timeout (seconds)',
                'help_text': 'Timeout for SMTP operations',
                'default': 30,
            },
        }

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Provider capabilities."""
        return {
            'send': True,
            'attachments': True,
            'inline_images': True,
            'html_email': True,
            'text_email': True,
            'healthcheck': True,
            'oauth': False,
            'webhooks': False,
            'bounce_handling': False,
        }

    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Send an email via SMTP.

        Args:
            message: EmailMessage TypedDict with email details

        Returns:
            SendResult with success status and message_id
        """
        try:
            # Build MIME message
            mime_message = self._build_mime_message(message)

            # Connect to SMTP server
            smtp = self._connect_smtp()

            try:
                # Authenticate
                if self.username and self.password:
                    smtp.login(self.username, self.password)

                # Get all recipients
                recipients = list(message['to'])
                if message.get('cc'):
                    recipients.extend(message['cc'])
                if message.get('bcc'):
                    recipients.extend(message['bcc'])

                # Send email
                response = smtp.sendmail(
                    message['from_email'],
                    recipients,
                    mime_message.as_string()
                )

                # Get message ID from headers
                message_id = mime_message.get('Message-ID', '')

                logger.info(
                    f"Email sent via SMTP to {', '.join(message['to'])} "
                    f"(Message-ID: {message_id})"
                )

                return {
                    'accepted': True,
                    'status': 'sent',
                    'provider_message_id': message_id,
                    'error': None,
                    'details': {'provider_response': str(response) if response else None},
                }

            finally:
                smtp.quit()

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                'accepted': False,
                'status': 'failed',
                'provider_message_id': '',
                'error': f"Authentication failed: {str(e)}",
                'details': {'error_code': 'auth_failed'},
            }

        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP recipients refused: {e}")
            return {
                'accepted': False,
                'status': 'failed',
                'provider_message_id': '',
                'error': f"Recipients refused: {str(e)}",
                'details': {'error_code': 'recipients_refused'},
            }

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                'accepted': False,
                'status': 'failed',
                'provider_message_id': '',
                'error': f"SMTP error: {str(e)}",
                'details': {'error_code': 'smtp_error'},
            }

        except socket.timeout:
            logger.error("SMTP connection timeout")
            return {
                'accepted': False,
                'status': 'failed',
                'provider_message_id': '',
                'error': 'Connection timeout',
                'details': {'error_code': 'timeout'},
            }

        except Exception as e:
            logger.exception(f"Unexpected error sending email via SMTP: {e}")
            return {
                'accepted': False,
                'status': 'failed',
                'provider_message_id': '',
                'error': str(e),
                'details': {'error_code': 'unknown'},
            }

    def _connect_smtp(self) -> smtplib.SMTP:
        """
        Connect to SMTP server with appropriate security settings.

        Returns:
            Connected SMTP instance

        Raises:
            SMTPException: If connection fails
        """
        if self.use_ssl:
            # Implicit SSL (usually port 465)
            smtp = smtplib.SMTP_SSL(
                self.host,
                self.port,
                timeout=self.timeout
            )
        else:
            # Plain connection or STARTTLS (usually port 587 or 25)
            smtp = smtplib.SMTP(
                self.host,
                self.port,
                timeout=self.timeout
            )

            # Identify ourselves
            smtp.ehlo()

            # Upgrade to TLS if requested
            if self.use_tls:
                smtp.starttls()
                smtp.ehlo()  # EHLO again after STARTTLS

        return smtp

    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Build MIME message from EmailMessage TypedDict.

        Args:
            message: EmailMessage with email details

        Returns:
            MIMEMultipart message ready to send
        """
        # Create message container
        msg = MIMEMultipart('mixed')

        # Set headers
        msg['Subject'] = message['subject']
        msg['From'] = formataddr((message.get('from_name', ''), message['from_email']))
        msg['To'] = ', '.join(message['to'])
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=message['from_email'].split('@')[1])

        if message.get('cc'):
            msg['Cc'] = ', '.join(message['cc'])

        if message.get('reply_to'):
            msg['Reply-To'] = message['reply_to']

        # Add custom headers
        if message.get('headers'):
            for key, value in message['headers'].items():
                msg[key] = value

        # Create alternative part for HTML and text versions
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Add text version
        if message.get('text'):
            text_part = MIMEText(message['text'], 'plain', 'utf-8')
            msg_alternative.attach(text_part)

        # Add HTML version
        if message.get('html'):
            # If we have inline images, create a related container
            if message.get('inline_images'):
                msg_related = MIMEMultipart('related')
                msg_alternative.attach(msg_related)

                html_part = MIMEText(message['html'], 'html', 'utf-8')
                msg_related.attach(html_part)

                # Attach inline images
                for inline_image in message['inline_images']:
                    img_part = MIMEImage(inline_image['content'])
                    img_part.add_header('Content-ID', f"<{inline_image['cid']}>")
                    img_part.add_header('Content-Disposition', 'inline')
                    msg_related.attach(img_part)
            else:
                html_part = MIMEText(message['html'], 'html', 'utf-8')
                msg_alternative.attach(html_part)

        # Add attachments
        if message.get('attachments'):
            for attachment in message['attachments']:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment["filename"]}"'
                )
                if attachment.get('content_type'):
                    part.set_type(attachment['content_type'])
                msg.attach(part)

        return msg

    def healthcheck(self) -> Dict[str, Any]:
        """
        Check if SMTP server is reachable and credentials are valid.

        Returns:
            Dictionary with status and details
        """
        try:
            smtp = self._connect_smtp()

            try:
                # Test authentication
                if self.username and self.password:
                    smtp.login(self.username, self.password)

                # Send NOOP to verify connection
                status = smtp.noop()

                return {
                    'success': True,
                    'message': 'Successfully connected to SMTP server',
                    'details': {
                        'smtp_host': self.host,
                        'smtp_port': self.port,
                        'server_response': status[1].decode() if isinstance(status[1], bytes) else str(status[1]),
                    },
                }

            finally:
                smtp.quit()

        except smtplib.SMTPAuthenticationError as e:
            return {
                'success': False,
                'message': 'Authentication failed',
                'details': {'error': str(e)},
            }

        except socket.timeout:
            return {
                'success': False,
                'message': 'Connection timeout',
                'details': {'error': f'Could not connect to {self.host}:{self.port} within {self.timeout} seconds'},
            }

        except Exception as e:
            return {
                'success': False,
                'message': 'Connection failed',
                'details': {'error': str(e)},
            }

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Validate SMTP credential format before storage.

        Args:
            credentials: Credentials dictionary to validate

        Raises:
            ValueError: If required credentials are missing or invalid
        """
        required = ['host', 'port', 'username', 'password']
        for field in required:
            if not credentials.get(field):
                raise ValueError(f"Missing required credential: {field}")

        port = credentials.get('port')
        if isinstance(port, int) and (port < 1 or port > 65535):
            raise ValueError(f"Invalid port number: {port}")

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive information from credentials for logging.

        Args:
            credentials: Original credentials dictionary

        Returns:
            Redacted copy of credentials
        """
        redacted = credentials.copy()
        if 'password' in redacted:
            pwd = redacted['password']
            if len(pwd) <= 6:
                redacted['password'] = '***'
            else:
                redacted['password'] = f"{pwd[:3]}***{pwd[-3:]}"
        return redacted
