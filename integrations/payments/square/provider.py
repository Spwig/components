"""
Square Payment Provider
Accept payments with Square - cards, digital wallets, and more.

API Documentation: https://developer.squareup.com/docs
SDK Reference: https://github.com/square/square-python-sdk
"""
import hmac
import hashlib
import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from payment_providers.providers.base import PaymentProviderBase
from subscriptions.events import SubscriptionEvent, SubscriptionEventType

logger = logging.getLogger(__name__)

# Zero-decimal currencies (amount is already in smallest unit)
ZERO_DECIMAL_CURRENCIES = {'JPY', 'KRW', 'VND', 'BIF', 'CLP', 'DJF',
                           'GNF', 'ISK', 'KMF', 'MGA', 'PYG', 'RWF',
                           'UGX', 'VUV', 'XAF', 'XOF', 'XPF'}


def _to_smallest_unit(amount: Decimal, currency: str) -> int:
    """
    Convert a decimal amount to the smallest currency unit (integer).

    Square requires amounts as integers in the smallest currency unit.
    For USD: $99.99 -> 9999 (cents)
    For JPY: 1000 -> 1000 (yen, no subdivision)
    """
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int((amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _from_smallest_unit(amount_int: int, currency: str) -> Decimal:
    """Convert from smallest currency unit back to decimal."""
    currency_upper = currency.upper()
    if currency_upper in ZERO_DECIMAL_CURRENCIES:
        return Decimal(str(amount_int))
    return Decimal(str(amount_int)) / Decimal('100')


def _extract_errors(api_error) -> str:
    """Extract error message from Square ApiError."""
    errors = getattr(api_error, 'errors', None) or []
    if errors:
        return '; '.join(
            e.get('detail', e.get('code', 'Unknown error'))
            if isinstance(e, dict)
            else str(e)
            for e in errors
        )
    body = getattr(api_error, 'body', {})
    if isinstance(body, dict) and 'errors' in body:
        return '; '.join(
            e.get('detail', e.get('code', 'Unknown error'))
            for e in body['errors']
        )
    return str(api_error)


class SquareProvider(PaymentProviderBase):
    """
    Square payment provider implementation.

    Supports:
    - Credit/debit card processing (Visa, Mastercard, Amex, Discover, JCB, Diners)
    - Digital wallets (Apple Pay, Google Pay, Cash App Pay, Afterpay/Clearpay)
    - Square Gift Cards
    - Hosted checkout via Square Payment Links
    - Full and partial refunds
    - Authorize and capture workflow
    - Webhook verification (HMAC-SHA1 with notification URL)
    - Multi-currency transactions (USD, CAD, GBP, AUD, JPY, EUR)
    """

    provider_key = 'square'
    provider_name = 'Square'

    def __init__(self, credentials: Dict[str, Any], config: Optional[Dict[str, Any]] = None):
        """
        Initialize Square provider with credentials.

        Args:
            credentials: Dictionary containing either:
                NEW (dual-credential):
                    - test_mode: boolean flag
                    - test_access_token, test_application_id, test_location_id: Sandbox credentials
                    - live_access_token, live_application_id, live_location_id: Production credentials
                    - webhook_signature_key: Shared webhook signature key (optional)
                LEGACY (single-credential):
                    - access_token: Square API access token
                    - application_id: Square application ID
                    - location_id: Square location ID
                    - webhook_signature_key: Optional webhook signature key
                    - environment: 'sandbox' or 'production'
            config: Optional additional configuration
        """
        self._client = None  # Set before super() in case validate_credentials references it

        # Base class handles credential selection and validation
        super().__init__(credentials, config)

        # Extract selected credentials (base class already validated via _select_credentials)
        selected = self._select_credentials(credentials)
        self.access_token = selected.get('access_token', '')
        self.application_id = selected.get('application_id', '')
        self.location_id = selected.get('location_id', '')
        self.webhook_signature_key = selected.get('webhook_signature_key', '')
        self.environment = selected.get('environment', 'sandbox')
        self.test_mode = selected.get('test_mode', self.environment == 'sandbox')

        # Initialize Square SDK client
        self._init_client()

    def _init_client(self):
        """Initialize the Square SDK client."""
        try:
            from square.client import Square, SquareEnvironment

            env = (SquareEnvironment.PRODUCTION
                   if self.environment == 'production'
                   else SquareEnvironment.SANDBOX)

            self._client = Square(
                token=self.access_token,
                environment=env
            )
            logger.info(
                f"Square client initialized (environment={self.environment})"
            )
        except ImportError:
            logger.error(
                "Square SDK not installed. Install with: pip install squareup>=38.0.0"
            )
            raise ImportError(
                "squareup package is required. Install with: pip install squareup>=38.0.0"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Square client: {e}")
            raise

    def _generate_idempotency_key(self) -> str:
        """Generate a unique idempotency key for Square API calls."""
        return str(uuid.uuid4())

    # -------------------------------------------------------------------------
    # Abstract property implementations
    # -------------------------------------------------------------------------

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Return dictionary of provider capabilities."""
        return {
            'charge': True,
            'authorize': True,
            'capture': True,
            'void': True,
            'refund': True,
            'partial_refund': True,
            'recurring': True,
            'save_payment_method': False,
            'hosted_checkout': True,
            'integrated_checkout': True,
            'webhooks': True,
            'multi_currency': True,
        }

    @property
    def credential_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for required credentials (post-selection, unprefixed keys).
        Note: The authoritative credential schema (used by setup wizard) is in manifest.json.
        This property describes what validate_credentials() expects after _select_credentials().
        """
        return {
            'type': 'object',
            'properties': {
                'access_token': {
                    'type': 'string',
                    'title': 'Access Token',
                    'description': 'Your Square Access Token from the Developer Dashboard',
                    'required': True,
                    'secret': True
                },
                'application_id': {
                    'type': 'string',
                    'title': 'Application ID',
                    'description': 'Your Square Application ID',
                    'required': True
                },
                'location_id': {
                    'type': 'string',
                    'title': 'Location ID',
                    'description': 'Your Square Location ID for processing payments',
                    'required': True
                },
                'webhook_signature_key': {
                    'type': 'string',
                    'title': 'Webhook Signature Key',
                    'description': 'Signature key for webhook verification (optional)',
                    'required': False,
                    'secret': True
                },
            }
        }

    @property
    def supported_payment_methods(self) -> List[str]:
        """Return list of supported payment method types."""
        return [
            'credit_card', 'debit_card', 'digital_wallet',
            'apple_pay', 'google_pay', 'cash_app_pay',
            'afterpay_clearpay', 'square_gift_card'
        ]

    @property
    def supported_currencies(self) -> List[str]:
        """Return list of supported currency codes."""
        return ['USD', 'CAD', 'GBP', 'AUD', 'JPY', 'EUR']

    @property
    def supported_countries(self) -> List[str]:
        """Return list of supported country codes."""
        return ['US', 'CA', 'GB', 'AU', 'JP', 'IE', 'FR', 'ES']

    # -------------------------------------------------------------------------
    # Credential management
    # -------------------------------------------------------------------------

    def validate_credentials(self, credentials: Dict[str, Any]) -> None:
        """Validate that required credentials are present."""
        required_fields = ['access_token', 'application_id', 'location_id']
        missing = [f for f in required_fields if not credentials.get(f)]

        if missing:
            raise ValueError(
                f"Missing required Square credentials: {', '.join(missing)}"
            )

        env = credentials.get('environment', 'sandbox')
        if env not in ('sandbox', 'production'):
            raise ValueError(
                f"Invalid environment '{env}'. Must be 'sandbox' or 'production'."
            )

    def redact_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive credential values (handles both prefixed and unprefixed keys)."""
        redacted = dict(credentials)
        sensitive_substrings = ('access_token', 'webhook_signature_key')
        for key, value in redacted.items():
            if isinstance(value, str) and any(s in key for s in sensitive_substrings):
                if len(value) > 12:
                    redacted[key] = f"{value[:4]}***{value[-4:]}"
                elif value:
                    redacted[key] = '***'
        return redacted

    # -------------------------------------------------------------------------
    # Connection testing
    # -------------------------------------------------------------------------

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection by retrieving the configured location."""
        try:
            result = self._client.locations.get(
                location_id=self.location_id
            )

            location = result.location
            if location:
                location_name = location.name or 'Unknown'
                location_status = location.status or 'Unknown'
                country = location.country or 'Unknown'

                logger.info(
                    f"Square connection test successful: "
                    f"location='{location_name}', status={location_status}"
                )

                return {
                    'success': True,
                    'message': f'Successfully connected to Square location: {location_name}',
                    'details': {
                        'location_id': self.location_id,
                        'location_name': location_name,
                        'location_status': location_status,
                        'country': country,
                        'environment': self.environment,
                        'application_id': self.application_id,
                    }
                }

            # Response had errors
            errors = result.errors or []
            error_msg = '; '.join(
                e.get('detail', e.get('code', 'Unknown error'))
                if isinstance(e, dict) else str(e)
                for e in errors
            )
            logger.error(f"Square connection test failed: {error_msg}")
            return {
                'success': False,
                'message': f'Connection test failed: {error_msg}',
                'details': {
                    'environment': self.environment,
                    'errors': [str(e) for e in errors]
                }
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square connection test exception: {error_msg}")
            return {
                'success': False,
                'message': f'Connection test failed: {error_msg}',
                'details': {
                    'environment': self.environment,
                    'error': error_msg
                }
            }

    # -------------------------------------------------------------------------
    # Payment processing
    # -------------------------------------------------------------------------

    def charge(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an immediate payment (authorize + auto-capture).

        Args:
            amount: Payment amount
            currency: Currency code
            payment_method: Must contain 'token' (source_id / nonce)
            metadata: Optional metadata (order_id, customer_email, etc.)
        """
        metadata = metadata or {}
        source_id = payment_method.get('token') or payment_method.get('source_id')

        if not source_id:
            raise ValueError("payment_method must contain 'token' or 'source_id'")

        amount_cents = _to_smallest_unit(amount, currency)
        idempotency_key = self._generate_idempotency_key()

        kwargs = {
            'source_id': source_id,
            'idempotency_key': idempotency_key,
            'amount_money': {
                'amount': amount_cents,
                'currency': currency.upper()
            },
            'location_id': self.location_id,
            'autocomplete': True,
        }

        if metadata.get('order_id'):
            kwargs['reference_id'] = str(metadata['order_id'])
        if metadata.get('description'):
            kwargs['note'] = metadata['description'][:500]
        if metadata.get('customer_email'):
            kwargs['buyer_email_address'] = metadata['customer_email']

        try:
            result = self._client.payments.create(**kwargs)
            payment = result.payment

            if payment:
                payment_id = payment.id or ''
                status = payment.status or ''

                logger.info(
                    f"Square charge successful: payment_id={payment_id}, "
                    f"status={status}, amount={amount} {currency}"
                )

                return {
                    'success': True,
                    'transaction_id': payment_id,
                    'provider_transaction_id': payment_id,
                    'status': 'completed' if status == 'COMPLETED' else status.lower(),
                    'amount': amount,
                    'currency': currency.upper(),
                    'created_at': datetime.utcnow(),
                    'message': 'Payment successful',
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square charge failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'message': f'Payment failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square charge exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'message': f'Payment failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def authorize(
        self,
        amount: Decimal,
        currency: str,
        payment_method: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Authorize a payment without capturing (delayed capture).

        Square supports this via autocomplete=False on create.
        """
        metadata = metadata or {}
        source_id = payment_method.get('token') or payment_method.get('source_id')

        if not source_id:
            raise ValueError("payment_method must contain 'token' or 'source_id'")

        amount_cents = _to_smallest_unit(amount, currency)
        idempotency_key = self._generate_idempotency_key()

        kwargs = {
            'source_id': source_id,
            'idempotency_key': idempotency_key,
            'amount_money': {
                'amount': amount_cents,
                'currency': currency.upper()
            },
            'location_id': self.location_id,
            'autocomplete': False,
        }

        if metadata.get('order_id'):
            kwargs['reference_id'] = str(metadata['order_id'])
        if metadata.get('description'):
            kwargs['note'] = metadata['description'][:500]
        if metadata.get('customer_email'):
            kwargs['buyer_email_address'] = metadata['customer_email']

        try:
            result = self._client.payments.create(**kwargs)
            payment = result.payment

            if payment:
                payment_id = payment.id or ''
                status = payment.status or ''

                logger.info(
                    f"Square authorization successful: payment_id={payment_id}, "
                    f"status={status}, amount={amount} {currency}"
                )

                expires_at = datetime.utcnow() + timedelta(days=6)

                return {
                    'success': True,
                    'authorization_id': payment_id,
                    'provider_authorization_id': payment_id,
                    'status': 'authorized' if status == 'APPROVED' else status.lower(),
                    'amount': amount,
                    'currency': currency.upper(),
                    'expires_at': expires_at,
                    'created_at': datetime.utcnow(),
                    'message': 'Authorization successful',
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square authorization failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'message': f'Authorization failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square authorization exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'amount': amount,
                'currency': currency.upper(),
                'message': f'Authorization failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def capture(
        self,
        authorization_id: str,
        amount: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Capture (complete) a previously authorized payment.

        Note: Square does not support partial capture; the full authorized
        amount is always captured.
        """
        try:
            result = self._client.payments.complete(
                payment_id=authorization_id
            )
            payment = result.payment

            if payment:
                payment_id = payment.id or ''
                status = payment.status or ''
                amount_money = payment.amount_money
                captured_amount = _from_smallest_unit(
                    amount_money.amount if amount_money else 0,
                    amount_money.currency if amount_money else 'USD'
                )
                currency = amount_money.currency if amount_money else 'USD'

                logger.info(
                    f"Square capture successful: payment_id={payment_id}, "
                    f"amount={captured_amount} {currency}"
                )

                return {
                    'success': True,
                    'transaction_id': payment_id,
                    'provider_transaction_id': payment_id,
                    'status': 'completed' if status == 'COMPLETED' else status.lower(),
                    'amount': captured_amount,
                    'currency': currency,
                    'created_at': datetime.utcnow(),
                    'message': 'Capture successful',
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square capture failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Capture failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square capture exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Capture failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def void(
        self,
        authorization_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Void (cancel) an uncaptured authorization."""
        try:
            result = self._client.payments.cancel(
                payment_id=authorization_id
            )
            payment = result.payment

            if payment:
                payment_id = payment.id or ''
                status = payment.status or ''

                logger.info(f"Square void successful: payment_id={payment_id}")

                return {
                    'success': True,
                    'authorization_id': payment_id,
                    'status': 'voided' if status == 'CANCELED' else status.lower(),
                    'message': 'Authorization voided',
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square void failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Void failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square void exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Void failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Refund a completed payment (full or partial)."""
        idempotency_key = self._generate_idempotency_key()

        kwargs = {
            'payment_id': transaction_id,
            'idempotency_key': idempotency_key,
        }

        if amount is not None:
            currency = 'USD'
            if metadata and metadata.get('currency'):
                currency = metadata['currency']
            else:
                try:
                    payment_result = self._client.payments.get(
                        payment_id=transaction_id
                    )
                    if payment_result.payment and payment_result.payment.amount_money:
                        currency = payment_result.payment.amount_money.currency or 'USD'
                except Exception:
                    logger.warning(
                        f"Could not retrieve payment {transaction_id} for currency; "
                        f"defaulting to USD"
                    )

            amount_cents = _to_smallest_unit(amount, currency)
            kwargs['amount_money'] = {
                'amount': amount_cents,
                'currency': currency.upper()
            }
        else:
            # Full refund — Square requires amount_money, so look up the payment
            try:
                payment_result = self._client.payments.get(
                    payment_id=transaction_id
                )
                if payment_result.payment and payment_result.payment.amount_money:
                    kwargs['amount_money'] = {
                        'amount': payment_result.payment.amount_money.amount,
                        'currency': payment_result.payment.amount_money.currency
                    }
            except Exception:
                pass

        if reason:
            kwargs['reason'] = reason[:192]

        try:
            result = self._client.refunds.refund_payment(**kwargs)
            refund_data = result.refund

            if refund_data:
                refund_id = refund_data.id or ''
                status = refund_data.status or ''
                amount_money = refund_data.amount_money
                refund_amount = _from_smallest_unit(
                    amount_money.amount if amount_money else 0,
                    amount_money.currency if amount_money else 'USD'
                )
                refund_currency = amount_money.currency if amount_money else 'USD'

                logger.info(
                    f"Square refund successful: refund_id={refund_id}, "
                    f"amount={refund_amount} {refund_currency}"
                )

                status_map = {
                    'PENDING': 'pending',
                    'APPROVED': 'pending',
                    'COMPLETED': 'completed',
                    'REJECTED': 'failed',
                    'FAILED': 'failed',
                }

                return {
                    'success': True,
                    'refund_id': refund_id,
                    'provider_refund_id': refund_id,
                    'status': status_map.get(status, status.lower()),
                    'amount': refund_amount,
                    'currency': refund_currency,
                    'created_at': datetime.utcnow(),
                    'message': 'Refund successful',
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square refund failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Refund failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square refund exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Refund failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    # -------------------------------------------------------------------------
    # Webhook methods
    # -------------------------------------------------------------------------

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        **kwargs
    ) -> bool:
        """
        Verify Square webhook signature using HMAC-SHA256.

        Square computes the signature over: notification_url + raw_body
        using the webhook signature key.
        """
        if not self.webhook_signature_key:
            logger.error(
                "Square webhook signature key not configured - cannot verify webhook signature"
            )
            return False

        notification_url = kwargs.get('notification_url', '')
        if not notification_url:
            logger.warning(
                "notification_url not provided for Square webhook verification"
            )
            return False

        try:
            payload_str = payload.decode('utf-8') if isinstance(payload, bytes) else payload
            string_to_sign = notification_url + payload_str

            expected_signature = hmac.new(
                key=self.webhook_signature_key.encode('utf-8'),
                msg=string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()

            import base64
            expected_b64 = base64.b64encode(expected_signature).decode('utf-8')

            is_valid = hmac.compare_digest(expected_b64, signature)

            if not is_valid:
                logger.warning("Square webhook signature mismatch")
            else:
                logger.debug("Square webhook signature verified successfully")

            return is_valid

        except Exception as e:
            logger.error(f"Square webhook signature verification error: {e}")
            return False

    def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a Square webhook event.

        Supported events:
        - payment.completed: Payment was successfully completed
        - payment.updated: Payment status changed
        - refund.created: Refund was initiated
        - refund.updated: Refund status changed
        """
        logger.info(f"Processing Square webhook: {event_type}")

        data_object = payload.get('data', {}).get('object', {})

        if event_type == 'payment.completed':
            return self._handle_payment_completed(data_object, payload)
        elif event_type == 'payment.updated':
            return self._handle_payment_updated(data_object, payload)
        elif event_type == 'refund.created':
            return self._handle_refund_event(data_object, payload, 'refund_created')
        elif event_type == 'refund.updated':
            return self._handle_refund_event(data_object, payload, 'refund_updated')
        else:
            logger.warning(f"Unhandled Square webhook event: {event_type}")
            return {
                'action': 'unknown',
                'event_type': event_type,
                'handled': False,
                'raw_event': payload
            }

    def _handle_payment_completed(
        self, data: Dict[str, Any], raw_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle payment.completed webhook event."""
        payment = data.get('payment', data)
        amount_money = payment.get('amount_money', {})
        currency = amount_money.get('currency', 'USD')

        return {
            'action': 'payment_completed',
            'transaction_id': payment.get('id'),
            'status': 'completed',
            'amount': _from_smallest_unit(
                amount_money.get('amount', 0), currency
            ),
            'currency': currency,
            'reference_id': payment.get('reference_id'),
            'metadata': {
                'order_id': payment.get('order_id'),
                'reference_id': payment.get('reference_id'),
            },
            'handled': True,
            'raw_event': raw_event
        }

    def _handle_payment_updated(
        self, data: Dict[str, Any], raw_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle payment.updated webhook event."""
        payment = data.get('payment', data)
        amount_money = payment.get('amount_money', {})
        currency = amount_money.get('currency', 'USD')
        sq_status = payment.get('status', '')

        status_map = {
            'COMPLETED': 'completed',
            'APPROVED': 'authorized',
            'PENDING': 'pending',
            'CANCELED': 'canceled',
            'FAILED': 'failed',
        }

        return {
            'action': 'payment_updated',
            'transaction_id': payment.get('id'),
            'status': status_map.get(sq_status, sq_status.lower()),
            'provider_status': sq_status,
            'amount': _from_smallest_unit(
                amount_money.get('amount', 0), currency
            ),
            'currency': currency,
            'reference_id': payment.get('reference_id'),
            'metadata': {
                'order_id': payment.get('order_id'),
                'reference_id': payment.get('reference_id'),
            },
            'handled': True,
            'raw_event': raw_event
        }

    def _handle_refund_event(
        self,
        data: Dict[str, Any],
        raw_event: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        """Handle refund.created and refund.updated webhook events."""
        refund = data.get('refund', data)
        amount_money = refund.get('amount_money', {})
        currency = amount_money.get('currency', 'USD')
        sq_status = refund.get('status', '')

        status_map = {
            'PENDING': 'pending',
            'APPROVED': 'pending',
            'COMPLETED': 'completed',
            'REJECTED': 'failed',
            'FAILED': 'failed',
        }

        return {
            'action': action,
            'refund_id': refund.get('id'),
            'transaction_id': refund.get('payment_id'),
            'status': status_map.get(sq_status, sq_status.lower()),
            'provider_status': sq_status,
            'amount': _from_smallest_unit(
                amount_money.get('amount', 0), currency
            ),
            'currency': currency,
            'reason': refund.get('reason', ''),
            'metadata': {},
            'handled': True,
            'raw_event': raw_event
        }

    # -------------------------------------------------------------------------
    # Checkout / Payment Intent methods
    # -------------------------------------------------------------------------

    def create_payment_intent_for_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Square payment intent for checkout.

        Supports two modes:
        - hosted: Creates Payment Link and returns checkout_url
        - embedded: Creates Order and returns handler_config
        """
        checkout_mode = self.config.get('checkout_mode', 'embedded')

        if checkout_mode == 'hosted':
            return self._create_hosted_checkout(
                amount, currency, return_url, cancel_url, customer_email, metadata
            )
        else:
            return self._create_embedded_checkout(
                amount, currency, return_url, cancel_url, customer_email, metadata
            )

    def _create_hosted_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create hosted checkout using Payment Links API (v1.0.0 logic)."""
        metadata = metadata or {}
        idempotency_key = self._generate_idempotency_key()
        amount_cents = _to_smallest_unit(amount, currency)

        description = metadata.get('description', 'Order Payment')
        order_id = metadata.get('order_id', '')

        kwargs = {
            'idempotency_key': idempotency_key,
            'order': {
                'location_id': self.location_id,
                'line_items': [
                    {
                        'name': description,
                        'quantity': '1',
                        'base_price_money': {
                            'amount': amount_cents,
                            'currency': currency.upper()
                        }
                    }
                ],
            },
            'checkout_options': {
                'redirect_url': return_url,
                'allow_tipping': False,
            },
        }

        if order_id:
            kwargs['order']['reference_id'] = str(order_id)

        if customer_email:
            kwargs['pre_populated_data'] = {
                'buyer_email': customer_email
            }

        try:
            result = self._client.checkout.payment_links.create(**kwargs)
            payment_link = result.payment_link

            if payment_link:
                related_resources = result.related_resources
                sq_order_id = ''
                if related_resources and related_resources.orders:
                    sq_order_id = related_resources.orders[0].id or ''
                if not sq_order_id:
                    sq_order_id = payment_link.order_id or ''

                checkout_url = payment_link.url or ''
                link_id = payment_link.id or ''

                logger.info(
                    f"Square checkout link created: link_id={link_id}, "
                    f"order_id={sq_order_id}"
                )

                return {
                    'success': True,
                    'provider_intent_id': sq_order_id,
                    'client_secret': None,
                    'checkout_url': checkout_url,
                    'status': 'created',
                    'requires_action': False,
                    'expires_at': None,
                    'raw_response': result.dict(),
                    'metadata': {
                        'payment_link_id': link_id,
                        'square_order_id': sq_order_id,
                    }
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square checkout link creation failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Checkout creation failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square checkout link creation exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Checkout creation failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def _create_embedded_checkout(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create embedded checkout using Orders API."""
        metadata = metadata or {}
        idempotency_key = self._generate_idempotency_key()
        amount_cents = _to_smallest_unit(amount, currency)

        description = metadata.get('description', 'Order Payment')
        order_id = metadata.get('order_id', '')

        # Create Order using Orders API
        order_data = {
            'idempotency_key': idempotency_key,
            'order': {
                'location_id': self.location_id,
                'line_items': [
                    {
                        'name': description,
                        'quantity': '1',
                        'base_price_money': {
                            'amount': amount_cents,
                            'currency': currency.upper()
                        }
                    }
                ],
                'metadata': {
                    'order_id': str(order_id),
                    'customer_email': customer_email or '',
                }
            }
        }

        if order_id:
            order_data['order']['reference_id'] = str(order_id)

        try:
            result = self._client.orders.create_order(body=order_data)
            order = result.order

            if order:
                sq_order_id = order.id or ''

                logger.info(f"Square order created for embedded checkout: {sq_order_id}")

                # Build handler_config for Square Web Payments SDK
                handler_config = {
                    'application_id': self.application_id,
                    'location_id': self.location_id,
                    'order_id': sq_order_id,
                    'currency': currency.upper(),
                    'amount': amount_cents,
                    'environment': self.environment,
                }

                return {
                    'success': True,
                    'provider_intent_id': sq_order_id,
                    'client_secret': None,
                    'checkout_url': None,
                    'handler_config': handler_config,
                    'status': 'created',
                    'requires_action': False,
                    'expires_at': None,
                    'raw_response': result.dict(),
                    'metadata': {
                        'square_order_id': sq_order_id,
                        'mode': 'embedded',
                    }
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square order creation failed: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Order creation failed: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square order creation exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Order creation failed: {error_msg}',
                'error_code': 'PROVIDER_ERROR',
                'raw_response': {}
            }

    def process_payment_with_nonce(
        self,
        order_id: str,
        nonce: str,
        verification_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process payment using nonce from Square Web Payments SDK.

        Args:
            order_id: Square Order ID from _create_embedded_checkout
            nonce: Payment token from Square.js tokenization
            verification_token: Buyer verification token (for 3DS)

        Returns:
            dict with payment result
        """
        idempotency_key = self._generate_idempotency_key()
        autocapture = self.config.get('autocapture', True)

        # Retrieve order to get amount
        try:
            order_result = self._client.orders.retrieve_order(order_id=order_id)
            order = order_result.order
            if not order or not order.total_money:
                logger.error(f"Order {order_id} has no pricing information")
                return {
                    'success': False,
                    'error': 'Order has no pricing information',
                }
            total_money = order.total_money
        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Failed to retrieve order {order_id}: {error_msg}")
            return {
                'success': False,
                'error': f'Failed to retrieve order: {error_msg}',
            }

        # Prepare payment data
        payment_data = {
            'idempotency_key': idempotency_key,
            'source_id': nonce,
            'amount_money': {
                'amount': total_money.amount,
                'currency': total_money.currency
            },
            'location_id': self.location_id,
            'order_id': order_id,
            'autocomplete': autocapture
        }

        # Add verification token if provided
        if verification_token:
            payment_data['verification_token'] = verification_token

        # Create payment
        try:
            result = self._client.payments.create_payment(body=payment_data)
            payment = result.payment

            if payment:
                payment_id = payment.id
                status = payment.status

                logger.info(f"Square payment created: {payment_id}, status: {status}")

                # Check if payment requires additional verification
                if status == 'PENDING':
                    return {
                        'success': False,
                        'requires_action': True,
                        'action_type': 'verify_buyer',
                        'payment_id': payment_id,
                        'message': 'Payment requires buyer verification'
                    }

                if status in ['COMPLETED', 'APPROVED']:
                    return {
                        'success': True,
                        'payment_id': payment_id,
                        'status': status,
                        'order_id': order_id
                    }

                return {
                    'success': False,
                    'error': f'Payment status: {status}',
                    'payment_id': payment_id
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            logger.error(f"Square payment creation failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square payment creation exception: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """Retrieve current status of a Square order (used as payment intent)."""
        try:
            result = self._client.orders.get(order_id=intent_id)
            order = result.order

            if order:
                sq_state = order.state or ''

                state_map = {
                    'OPEN': 'created',
                    'COMPLETED': 'succeeded',
                    'CANCELED': 'canceled',
                    'DRAFT': 'created',
                }

                total_money = order.total_money
                currency = total_money.currency if total_money else 'USD'
                amount_val = total_money.amount if total_money else 0

                return {
                    'success': True,
                    'status': state_map.get(sq_state, sq_state.lower()),
                    'provider_status': sq_state,
                    'requires_action': False,
                    'amount': _from_smallest_unit(amount_val, currency),
                    'currency': currency,
                    'raw_response': result.dict()
                }

            errors = result.errors or []
            error_msg = '; '.join(str(e) for e in errors)
            return {
                'success': False,
                'status': 'failed',
                'message': f'Failed to retrieve order: {error_msg}',
                'raw_response': {}
            }

        except Exception as e:
            error_msg = _extract_errors(e) if hasattr(e, 'errors') else str(e)
            logger.error(f"Square retrieve_payment_intent exception: {error_msg}")
            return {
                'success': False,
                'status': 'failed',
                'message': f'Failed to retrieve order: {error_msg}',
                'raw_response': {}
            }

    def confirm_payment_intent(
        self,
        intent_id: str,
        confirmation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent.

        For embedded checkout: processes payment using nonce from
        confirmation_data (passed via payment_method_data).
        For hosted checkout: retrieves current order status.
        """
        confirmation_data = confirmation_data or {}
        nonce = confirmation_data.get('nonce')

        if nonce:
            # Embedded checkout: process payment with nonce from Square SDK
            logger.info(
                f"Square confirm_payment_intent with nonce for order {intent_id}"
            )
            return self.process_payment_with_nonce(
                order_id=intent_id,
                nonce=nonce,
                verification_token=confirmation_data.get('verification_token')
            )

        # Hosted checkout: just retrieve current status
        logger.info(
            f"Square confirm_payment_intent called for order {intent_id}. "
            f"Hosted checkout auto-captures; retrieving current status."
        )
        return self.retrieve_payment_intent(intent_id)

    def cancel_payment_intent(
        self,
        intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a payment intent (Square order)."""
        logger.info(
            f"Square cancel_payment_intent called for order {intent_id}. "
            f"Square payment links expire automatically."
        )

        return {
            'success': True,
            'status': 'canceled',
            'message': (
                'Square payment links cannot be explicitly cancelled via API. '
                'The link will expire automatically if unused.'
            ),
            'raw_response': {}
        }

    # -------------------------------------------------------------------------
    # Hosted checkout session (alternative interface)
    # -------------------------------------------------------------------------

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a hosted checkout session via Square Payment Links."""
        result = self.create_payment_intent_for_checkout(
            amount=amount,
            currency=currency,
            return_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )

        if result.get('success'):
            return {
                'success': True,
                'session_id': result.get('provider_intent_id', ''),
                'checkout_url': result.get('checkout_url', ''),
                'expires_at': result.get('expires_at'),
                'message': 'Checkout session created',
                'raw_response': result.get('raw_response', {})
            }

        return result

    # -------------------------------------------------------------------------
    # Payment method types
    # -------------------------------------------------------------------------

    def get_payment_method_types(self) -> Dict[str, Any]:
        """Get available payment method types for Square."""
        methods_by_country = {
            'US': [
                'card', 'apple_pay', 'google_pay',
                'cash_app_pay', 'afterpay_clearpay', 'square_gift_card'
            ],
            'CA': [
                'card', 'apple_pay', 'google_pay', 'square_gift_card'
            ],
            'GB': [
                'card', 'apple_pay', 'google_pay',
                'cash_app_pay', 'afterpay_clearpay', 'square_gift_card'
            ],
            'AU': [
                'card', 'apple_pay', 'google_pay',
                'afterpay_clearpay', 'square_gift_card'
            ],
            'JP': [
                'card', 'apple_pay', 'google_pay', 'square_gift_card'
            ],
            'IE': [
                'card', 'apple_pay', 'google_pay'
            ],
            'FR': [
                'card', 'apple_pay', 'google_pay'
            ],
            'ES': [
                'card', 'apple_pay', 'google_pay'
            ],
        }

        return {
            'success': True,
            'methods': methods_by_country,
            'raw_response': {}
        }

    # =========================================================================
    # Subscription Webhook Translation
    # =========================================================================

    # Square subscription status -> standardized event type mapping
    # Square only sends subscription.created and subscription.updated;
    # the specific lifecycle event is determined by the subscription status.
    # Ref: https://developer.squareup.com/reference/square/subscriptions-api/webhooks
    _SQUARE_STATUS_MAP = {
        'ACTIVE': SubscriptionEventType.ACTIVATED,
        'CANCELED': SubscriptionEventType.CANCELED,
        'DEACTIVATED': SubscriptionEventType.EXPIRED,
        'PAUSED': SubscriptionEventType.PAUSED,
        'PENDING': SubscriptionEventType.CREATED,
    }

    def translate_subscription_webhook(
        self, event_type: str, payload: dict
    ) -> Optional[SubscriptionEvent]:
        """
        Translate Square webhook event to standardized SubscriptionEvent.
        Returns None for non-subscription events.

        Square subscription webhooks use the structure:
            {type, event_id, data: {type, id, object: {subscription: {...}}}}

        Square sends two event types:
            - subscription.created
            - subscription.updated (status changes: active, canceled, paused, etc.)
        """
        if not event_type.startswith('subscription.'):
            return None

        event_id = payload.get('event_id', payload.get('id', ''))

        # Square nests subscription under data.object.subscription
        data_object = payload.get('data', {}).get('object', {})
        subscription = data_object.get('subscription', data_object)

        sub_id = subscription.get('id', '')
        customer_id = subscription.get('customer_id', '')
        status = subscription.get('status', '')

        # Determine the standardized event type
        if event_type == 'subscription.created':
            std_type = SubscriptionEventType.CREATED
        elif event_type == 'subscription.updated':
            std_type = self._SQUARE_STATUS_MAP.get(
                status, SubscriptionEventType.UPDATED
            )
        else:
            return None

        kwargs = {
            'event_type': std_type,
            'event_id': event_id,
            'source': 'webhook',
            'provider_subscription_id': sub_id,
            'provider_customer_id': customer_id,
            'provider_event_type': event_type,
        }

        # Extract billing period dates (Square uses RFC 3339 strings)
        start_date = subscription.get('start_date')
        if start_date:
            try:
                kwargs['period_start'] = datetime.fromisoformat(
                    start_date.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        # Square provides charged_through_date as period end
        charged_through = subscription.get('charged_through_date')
        if charged_through:
            try:
                kwargs['period_end'] = datetime.fromisoformat(
                    charged_through.replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

        # Extract price from plan variation
        phases = subscription.get('phases', [])
        if phases:
            price_money = phases[0].get('order_template', {}).get(
                'line_items', [{}]
            )[0].get('base_price_money', {}) if phases[0].get('order_template') else {}
            if price_money.get('amount'):
                currency = price_money.get('currency', 'USD')
                kwargs['amount'] = _from_smallest_unit(
                    price_money['amount'], currency
                )
                kwargs['currency'] = currency

        return SubscriptionEvent(**kwargs)
