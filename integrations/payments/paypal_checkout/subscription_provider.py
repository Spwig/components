"""
PayPal Subscription Provider
Native subscription support using PayPal Billing API.
"""
import requests
import base64
import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

from subscriptions.provider_base import SubscriptionProviderBase, register_provider

logger = logging.getLogger(__name__)

# Currencies that use zero decimal places
ZERO_DECIMAL_CURRENCIES = {'JPY', 'HUF', 'TWD', 'KRW'}


@register_provider('paypal_checkout')
class PayPalSubscriptionProvider(SubscriptionProviderBase):
    """
    PayPal provider with native subscription support.
    Uses PayPal Billing API for subscription management and
    Vault API for payment method tokenization.
    """

    SANDBOX_API_BASE = "https://api-m.sandbox.paypal.com"
    LIVE_API_BASE = "https://api-m.paypal.com"

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'native_subscriptions': True,
            'tokenization': True,
            'webhooks': True,
            'trial_periods': True,
            'prorated_billing': False,
            'usage_based': False,
        }

    def _get_api_base(self) -> str:
        """Get API base URL based on environment."""
        environment = self.config.get('environment', 'sandbox')
        if environment == 'live':
            return self.LIVE_API_BASE
        return self.SANDBOX_API_BASE

    def _get_access_token(self) -> str:
        """
        Obtain OAuth2 access token from PayPal.
        Uses client credentials grant with Basic auth.
        Tokens are cached for 80% of reported lifetime.
        """
        if hasattr(self, '_access_token') and hasattr(self, '_token_expires_at'):
            if self._access_token and self._token_expires_at:
                if datetime.now() < self._token_expires_at:
                    return self._access_token

        client_id = self.config.get('client_id', '')
        client_secret = self.config.get('client_secret', '')
        api_base = self._get_api_base()

        auth_string = base64.b64encode(
            f"{client_id}:{client_secret}".encode('utf-8')
        ).decode('utf-8')

        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                f"{api_base}/v1/oauth2/token",
                headers=headers,
                data='grant_type=client_credentials',
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get('access_token')
            expires_in = data.get('expires_in', 32400)
            self._token_expires_at = datetime.now() + timedelta(seconds=int(expires_in * 0.8))

            return self._access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain PayPal access token: {e}")
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error_description', str(e))
                except (ValueError, KeyError):
                    pass
            raise Exception(f"PayPal authentication failed: {error_msg}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        extra_headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to PayPal API.

        Args:
            method: HTTP method
            endpoint: API endpoint path (e.g., '/v1/billing/subscriptions')
            data: Request body data
            params: URL query parameters
            extra_headers: Additional headers

        Returns:
            Response JSON as dictionary

        Raises:
            Exception: If request fails
        """
        token = self._get_access_token()
        api_base = self._get_api_base()
        url = f"{api_base}{endpoint}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal API request failed: {method} {endpoint} - {e}")
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'details' in error_data and error_data['details']:
                        detail_msgs = [
                            d.get('description', d.get('issue', ''))
                            for d in error_data['details']
                        ]
                        error_detail = '; '.join(filter(None, detail_msgs)) or error_data.get('message', str(e))
                    elif 'message' in error_data:
                        error_detail = error_data['message']
                except (ValueError, KeyError):
                    pass
            raise Exception(f"PayPal API error: {error_detail}")

    def _format_amount(self, amount: Decimal, currency: str) -> str:
        """Format amount for PayPal API (string with appropriate decimals)."""
        currency = currency.upper()
        if currency in ZERO_DECIMAL_CURRENCIES:
            return str(int(amount))
        return str(amount.quantize(Decimal('0.01')))

    # ===========================
    # Customer Management
    # ===========================

    def create_customer(self, user, email: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        PayPal does not require explicit customer creation.
        Customer identity is managed via email/payer ID during subscription creation.

        Returns:
            dict: {'customer_id': email, 'metadata': dict}
        """
        logger.info(f"PayPal customer reference created for user {user.id} ({email})")
        return {
            'customer_id': email,
            'metadata': metadata or {},
        }

    # ===========================
    # Payment Token Management (PayPal Vault)
    # ===========================

    def create_payment_token(
        self,
        customer_id: str,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a vaulted payment token for recurring billing.

        For PayPal wallet: Uses Vault v3 setup tokens.
        For cards: Tokenize card via Vault API.

        Args:
            customer_id: Customer email (used as reference)
            payment_method_data: {
                'vault_setup_token': str,   # From frontend PayPal Vault flow
                OR
                'payment_token_id': str,    # Already-vaulted token from PayPal SDK
            }

        Returns:
            dict: Token information
        """
        # If a payment_token_id is provided directly (from PayPal SDK)
        payment_token_id = payment_method_data.get('payment_token_id')
        if payment_token_id:
            # Retrieve token details from vault
            try:
                token_data = self._make_request(
                    'GET',
                    f'/v3/vault/payment-tokens/{payment_token_id}'
                )

                result = {
                    'token_id': payment_token_id,
                    'payment_method_type': token_data.get('payment_source', {}).get('type', 'paypal'),
                }

                # Extract card info if card source
                card = token_data.get('payment_source', {}).get('card', {})
                if card:
                    result.update({
                        'card_brand': card.get('brand', ''),
                        'card_last4': card.get('last_digits', ''),
                        'card_exp_month': card.get('expiry', {}).get('month'),
                        'card_exp_year': card.get('expiry', {}).get('year'),
                    })

                return result
            except Exception:
                # If retrieval fails, return basic info
                return {
                    'token_id': payment_token_id,
                    'payment_method_type': 'paypal',
                }

        # Create token from vault setup token
        vault_setup_token = payment_method_data.get('vault_setup_token')
        if vault_setup_token:
            try:
                token_data = self._make_request(
                    'POST',
                    '/v3/vault/payment-tokens',
                    data={'payment_source': {'token': {'id': vault_setup_token, 'type': 'SETUP_TOKEN'}}}
                )

                token_id = token_data.get('id', '')
                result = {
                    'token_id': token_id,
                    'payment_method_type': 'paypal',
                }

                # Check for card info in payment source
                card = token_data.get('payment_source', {}).get('card', {})
                if card:
                    result.update({
                        'payment_method_type': 'card',
                        'card_brand': card.get('brand', ''),
                        'card_last4': card.get('last_digits', ''),
                        'card_exp_month': card.get('expiry', {}).get('month'),
                        'card_exp_year': card.get('expiry', {}).get('year'),
                    })

                logger.info(f"Created PayPal vault token: {token_id}")
                return result

            except Exception as e:
                logger.error(f"Failed to create PayPal vault token: {e}")
                raise

        raise ValueError("Either 'payment_token_id' or 'vault_setup_token' is required")

    def delete_payment_token(self, token_id: str) -> bool:
        """
        Delete a vaulted payment token.

        Args:
            token_id: PayPal vault token ID

        Returns:
            bool: True if successful
        """
        try:
            self._make_request('DELETE', f'/v3/vault/payment-tokens/{token_id}')
            logger.info(f"Deleted PayPal vault token: {token_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete PayPal vault token: {e}")
            return False

    # ===========================
    # Subscription Management (Native)
    # ===========================

    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        payment_token_id: str,
        trial_end: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a PayPal subscription.

        Args:
            customer_id: Payer email
            plan_id: PayPal Billing Plan ID (e.g., 'P-XXXXXXX')
            payment_token_id: PayPal vault token ID
            trial_end: Trial end date (optional)
            metadata: Optional metadata

        Returns:
            dict: Subscription information
        """
        body = {
            'plan_id': plan_id,
            'subscriber': {
                'email_address': customer_id,
            },
            'application_context': {
                'brand_name': 'Store',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'SUBSCRIBE_NOW',
                'payment_method': {
                    'payer_selected': 'PAYPAL',
                    'payee_preferred': 'IMMEDIATE_PAYMENT_REQUIRED',
                },
            },
        }

        # Attach vaulted payment source if available
        if payment_token_id:
            body['payment_source'] = {
                'token': {
                    'id': payment_token_id,
                    'type': 'PAYMENT_METHOD_TOKEN',
                },
            }

        # Set start time for trial
        if trial_end:
            body['start_time'] = trial_end.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Add custom metadata
        if metadata:
            body['custom_id'] = json.dumps(metadata)[:127]  # PayPal limits to 127 chars

        try:
            result = self._make_request(
                'POST',
                '/v1/billing/subscriptions',
                data=body,
                extra_headers={'Prefer': 'return=representation'}
            )

            subscription_id = result.get('id', '')
            status = result.get('status', '')

            # Parse billing info
            billing_info = result.get('billing_info', {})
            now = timezone.now()

            # Determine period dates from response
            current_period_start = now
            if 'start_time' in result:
                try:
                    current_period_start = datetime.fromisoformat(
                        result['start_time'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    pass

            next_billing = billing_info.get('next_billing_time')
            if next_billing:
                try:
                    next_billing_date = datetime.fromisoformat(
                        next_billing.replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    next_billing_date = now + timedelta(days=30)
            else:
                next_billing_date = now + timedelta(days=30)

            logger.info(f"Created PayPal subscription: {subscription_id} (status: {status})")

            return {
                'subscription_id': subscription_id,
                'status': self._map_paypal_status(status),
                'current_period_start': current_period_start,
                'current_period_end': next_billing_date,
                'next_billing_date': next_billing_date,
            }

        except Exception as e:
            logger.error(f"Failed to create PayPal subscription: {e}")
            raise

    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a PayPal subscription.

        Args:
            subscription_id: PayPal subscription ID
            immediately: If True, cancel immediately (PayPal always cancels immediately)

        Returns:
            dict: Cancellation information
        """
        try:
            self._make_request(
                'POST',
                f'/v1/billing/subscriptions/{subscription_id}/cancel',
                data={'reason': 'Cancelled by merchant'}
            )

            logger.info(f"Canceled PayPal subscription: {subscription_id}")

            return {
                'status': 'canceled',
                'canceled_at': timezone.now(),
                'cancel_at_period_end': not immediately,
            }

        except Exception as e:
            logger.error(f"Failed to cancel PayPal subscription: {e}")
            raise

    def pause_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Suspend a PayPal subscription.

        Args:
            subscription_id: PayPal subscription ID

        Returns:
            dict: Pause information
        """
        try:
            self._make_request(
                'POST',
                f'/v1/billing/subscriptions/{subscription_id}/suspend',
                data={'reason': 'Paused by merchant'}
            )

            logger.info(f"Paused PayPal subscription: {subscription_id}")

            return {
                'status': 'paused',
                'paused_at': timezone.now(),
            }

        except Exception as e:
            logger.error(f"Failed to pause PayPal subscription: {e}")
            raise

    def resume_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Reactivate a suspended PayPal subscription.

        Args:
            subscription_id: PayPal subscription ID

        Returns:
            dict: Resume information
        """
        try:
            self._make_request(
                'POST',
                f'/v1/billing/subscriptions/{subscription_id}/activate',
                data={'reason': 'Resumed by merchant'}
            )

            logger.info(f"Resumed PayPal subscription: {subscription_id}")

            return {
                'status': 'active',
                'resumed_at': timezone.now(),
            }

        except Exception as e:
            logger.error(f"Failed to resume PayPal subscription: {e}")
            raise

    def update_subscription(
        self,
        subscription_id: str,
        plan_id: Optional[str] = None,
        payment_token_id: Optional[str] = None,
        proration_behavior: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a PayPal subscription.

        Args:
            subscription_id: PayPal subscription ID
            plan_id: New PayPal Plan ID (requires subscription revision)
            payment_token_id: New payment method token
            proration_behavior: Not supported by PayPal (ignored)

        Returns:
            dict: Update information
        """
        try:
            if payment_token_id:
                # Revise subscription to use new payment source
                revision_data = {
                    'payment_source': {
                        'token': {
                            'id': payment_token_id,
                            'type': 'PAYMENT_METHOD_TOKEN',
                        },
                    },
                }
                self._make_request(
                    'POST',
                    f'/v1/billing/subscriptions/{subscription_id}/revise',
                    data=revision_data
                )

            if plan_id:
                # PayPal plan changes require subscription revision
                revision_data = {
                    'plan_id': plan_id,
                }
                self._make_request(
                    'POST',
                    f'/v1/billing/subscriptions/{subscription_id}/revise',
                    data=revision_data
                )

            logger.info(f"Updated PayPal subscription: {subscription_id}")

            return {
                'status': 'active',
                'updated_at': timezone.now(),
            }

        except Exception as e:
            logger.error(f"Failed to update PayPal subscription: {e}")
            raise

    # ===========================
    # One-time Charging
    # ===========================

    def charge_payment_token(
        self,
        token_id: str,
        amount: Decimal,
        currency: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a one-time charge using a vaulted PayPal payment token.

        Args:
            token_id: PayPal vault token ID
            amount: Charge amount
            currency: Currency code
            description: Charge description
            metadata: Optional metadata

        Returns:
            dict: Charge result
        """
        formatted_amount = self._format_amount(amount, currency)

        body = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency.upper(),
                    'value': formatted_amount,
                },
                'description': description[:127],
            }],
            'payment_source': {
                'token': {
                    'id': token_id,
                    'type': 'PAYMENT_METHOD_TOKEN',
                },
            },
        }

        if metadata and 'order_id' in metadata:
            body['purchase_units'][0]['reference_id'] = str(metadata['order_id'])[:127]

        try:
            result = self._make_request('POST', '/v2/checkout/orders', data=body)

            order_id = result.get('id', '')
            status = result.get('status', '')

            # Extract capture ID if available
            transaction_id = order_id
            captures = (
                result.get('purchase_units', [{}])[0]
                .get('payments', {})
                .get('captures', [])
            )
            if captures:
                transaction_id = captures[0].get('id', order_id)

            is_success = status in ('COMPLETED', 'APPROVED')

            logger.info(f"PayPal charge {transaction_id}: {status}")

            return {
                'transaction_id': transaction_id,
                'status': 'succeeded' if is_success else 'failed',
                'amount': amount,
                'currency': currency,
                'error_message': '' if is_success else f'PayPal order status: {status}',
                'error_code': '' if is_success else status,
            }

        except Exception as e:
            logger.error(f"Failed to charge PayPal token: {e}")
            return {
                'transaction_id': '',
                'status': 'failed',
                'amount': amount,
                'currency': currency,
                'error_message': str(e),
                'error_code': 'exception',
            }

    # ===========================
    # Webhook Handling
    # ===========================

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify PayPal webhook using server-side verification API.

        Args:
            payload: Raw webhook payload
            signature: Not used directly — PayPal uses header-based verification

        Returns:
            bool: True if signature is valid
        """
        webhook_id = self.config.get('webhook_id')
        if not webhook_id:
            logger.warning("PayPal webhook_id not configured, skipping verification")
            return True

        # PayPal webhook verification requires multiple headers
        # The caller should pass them as JSON in the signature field
        try:
            headers_data = json.loads(signature) if isinstance(signature, str) else {}
        except (json.JSONDecodeError, TypeError):
            headers_data = {}

        body = {
            'auth_algo': headers_data.get('auth_algo', ''),
            'cert_url': headers_data.get('cert_url', ''),
            'transmission_id': headers_data.get('transmission_id', ''),
            'transmission_sig': headers_data.get('transmission_sig', ''),
            'transmission_time': headers_data.get('transmission_time', ''),
            'webhook_id': webhook_id,
            'webhook_event': json.loads(payload) if isinstance(payload, bytes) else payload,
        }

        try:
            result = self._make_request(
                'POST',
                '/v1/notifications/verify-webhook-signature',
                data=body
            )
            is_valid = result.get('verification_status') == 'SUCCESS'
            if not is_valid:
                logger.error("Invalid PayPal webhook signature")
            return is_valid

        except Exception as e:
            logger.error(f"PayPal webhook verification failed: {e}")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse PayPal webhook payload into standardized format.

        Args:
            payload: PayPal webhook event

        Returns:
            dict: Standardized event
        """
        event_type = payload.get('event_type', '')
        event_id = payload.get('id', '')
        resource = payload.get('resource', {})

        result = {
            'event_type': event_type,
            'event_id': event_id,
            'data': resource,
        }

        # Extract subscription ID
        if 'id' in resource and event_type.startswith('BILLING.SUBSCRIPTION'):
            result['subscription_id'] = resource.get('id')

        # Extract customer/payer ID
        subscriber = resource.get('subscriber', {})
        if subscriber:
            result['customer_id'] = subscriber.get('payer_id', subscriber.get('email_address', ''))

        return result

    # ===========================
    # Internal Helpers
    # ===========================

    @staticmethod
    def _map_paypal_status(paypal_status: str) -> str:
        """Map PayPal subscription status to internal status."""
        status_map = {
            'APPROVAL_PENDING': 'pending',
            'APPROVED': 'active',
            'ACTIVE': 'active',
            'SUSPENDED': 'paused',
            'CANCELLED': 'canceled',
            'EXPIRED': 'expired',
        }
        return status_map.get(paypal_status, paypal_status.lower())
