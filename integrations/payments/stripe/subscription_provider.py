"""
Stripe Subscription Provider
Native subscription support using Stripe's Billing API.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
import logging

from subscriptions.provider_base import SubscriptionProviderBase, register_provider

logger = logging.getLogger(__name__)


@register_provider('stripe')
class StripeSubscriptionProvider(SubscriptionProviderBase):
    """
    Stripe provider with native subscription support.
    Uses Stripe Billing API for subscription management.
    """

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            'native_subscriptions': True,  # Stripe manages subscriptions
            'tokenization': True,
            'webhooks': True,
            'trial_periods': True,
            'prorated_billing': True,
            'usage_based': True,
        }

    def _get_stripe(self):
        """Lazy import and configure Stripe SDK"""
        try:
            import stripe
        except ImportError:
            raise ImportError(
                "Stripe library not installed. Install with: pip install stripe"
            )

        stripe.api_key = self.config.get('secret_key')
        return stripe

    # ===========================
    # Customer & Token Management
    # ===========================

    def create_customer(self, user, email: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a Stripe Customer.

        Args:
            user: Django User instance
            email: Customer email
            metadata: Optional metadata

        Returns:
            dict: {'customer_id': str, 'metadata': dict}
        """
        stripe = self._get_stripe()

        customer_metadata = metadata or {}
        customer_metadata.update({
            'user_id': str(user.id),
            'username': user.username,
        })

        try:
            customer = stripe.Customer.create(
                email=email,
                description=f"Customer for {user.username}",
                metadata=customer_metadata,
            )

            logger.info(f"Created Stripe customer: {customer.id} for user {user.id}")

            return {
                'customer_id': customer.id,
                'metadata': dict(customer.metadata),
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise

    def create_payment_token(
        self,
        customer_id: str,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a payment method and attach to customer.

        Args:
            customer_id: Stripe customer ID
            payment_method_data: {
                'payment_method_id': str,  # From Stripe.js on frontend
                'set_as_default': bool,
            }

        Returns:
            dict: Token information
        """
        stripe = self._get_stripe()
        payment_method_id = payment_method_data.get('payment_method_id')

        if not payment_method_id:
            raise ValueError("payment_method_id is required")

        try:
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )

            # Set as default if requested
            if payment_method_data.get('set_as_default', False):
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        'default_payment_method': payment_method_id,
                    },
                )

            # Extract card information
            result = {
                'token_id': payment_method.id,
                'payment_method_type': payment_method.type,
            }

            if payment_method.type == 'card' and payment_method.card:
                result.update({
                    'card_brand': payment_method.card.brand,
                    'card_last4': payment_method.card.last4,
                    'card_exp_month': payment_method.card.exp_month,
                    'card_exp_year': payment_method.card.exp_year,
                })

            logger.info(f"Created payment method {payment_method.id} for customer {customer_id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment method: {str(e)}")
            raise

    def delete_payment_token(self, token_id: str) -> bool:
        """
        Detach payment method from customer.

        Args:
            token_id: Stripe payment method ID

        Returns:
            bool: True if successful
        """
        stripe = self._get_stripe()

        try:
            stripe.PaymentMethod.detach(token_id)
            logger.info(f"Deleted payment method: {token_id}")
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Failed to delete payment method: {str(e)}")
            return False

    # ===========================
    # Subscription Management
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
        Create a Stripe subscription.

        Args:
            customer_id: Stripe customer ID
            plan_id: Stripe price ID
            payment_token_id: Stripe payment method ID
            trial_end: Trial end date (optional)
            metadata: Optional metadata

        Returns:
            dict: Subscription information
        """
        stripe = self._get_stripe()

        subscription_params = {
            'customer': customer_id,
            'items': [{'price': plan_id}],
            'default_payment_method': payment_token_id,
            'metadata': metadata or {},
        }

        # Add trial period if specified
        if trial_end:
            subscription_params['trial_end'] = int(trial_end.timestamp())

        try:
            subscription = stripe.Subscription.create(**subscription_params)

            logger.info(f"Created Stripe subscription: {subscription.id}")

            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(
                    subscription.current_period_start,
                    tz=timezone.utc
                ),
                'current_period_end': datetime.fromtimestamp(
                    subscription.current_period_end,
                    tz=timezone.utc
                ),
                'next_billing_date': datetime.fromtimestamp(
                    subscription.current_period_end,
                    tz=timezone.utc
                ),
                'trial_end': datetime.fromtimestamp(
                    subscription.trial_end,
                    tz=timezone.utc
                ) if subscription.trial_end else None,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe subscription: {str(e)}")
            raise

    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID
            immediately: If True, cancel immediately; otherwise at period end

        Returns:
            dict: Cancellation information
        """
        stripe = self._get_stripe()

        try:
            if immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )

            logger.info(f"Canceled Stripe subscription: {subscription_id}")

            return {
                'status': subscription.status,
                'canceled_at': datetime.fromtimestamp(
                    subscription.canceled_at,
                    tz=timezone.utc
                ) if subscription.canceled_at else timezone.now(),
                'cancel_at_period_end': subscription.cancel_at_period_end,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription: {str(e)}")
            raise

    def pause_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Pause a Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            dict: Pause information
        """
        stripe = self._get_stripe()

        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection={'behavior': 'void'},
            )

            logger.info(f"Paused Stripe subscription: {subscription_id}")

            return {
                'status': subscription.status,
                'paused_at': timezone.now(),
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to pause Stripe subscription: {str(e)}")
            raise

    def resume_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Resume a paused Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            dict: Resume information
        """
        stripe = self._get_stripe()

        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection='',
            )

            logger.info(f"Resumed Stripe subscription: {subscription_id}")

            return {
                'status': subscription.status,
                'resumed_at': timezone.now(),
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to resume Stripe subscription: {str(e)}")
            raise

    def update_subscription(
        self,
        subscription_id: str,
        plan_id: Optional[str] = None,
        payment_token_id: Optional[str] = None,
        proration_behavior: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update Stripe subscription plan or payment method.

        Args:
            subscription_id: Stripe subscription ID
            plan_id: New Stripe price ID (optional)
            payment_token_id: New payment method ID (optional)
            proration_behavior: Stripe proration behavior
                ('create_prorations', 'none', 'always_invoice')

        Returns:
            dict: Update information
        """
        stripe = self._get_stripe()

        update_params = {}

        if payment_token_id:
            update_params['default_payment_method'] = payment_token_id

        if plan_id:
            # Get current subscription to find item ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            item_id = subscription['items']['data'][0].id

            update_params['items'] = [{
                'id': item_id,
                'price': plan_id,
            }]

        if proration_behavior:
            update_params['proration_behavior'] = proration_behavior

        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                **update_params
            )

            logger.info(f"Updated Stripe subscription: {subscription_id}")

            return {
                'status': subscription.status,
                'updated_at': timezone.now(),
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe subscription: {str(e)}")
            raise

    # ===========================
    # One-time Charging (Fallback - Not typically used for Stripe)
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
        Create a one-time charge (for refunds or manual charges).

        Args:
            token_id: Stripe payment method ID
            amount: Charge amount
            currency: Currency code
            description: Charge description
            metadata: Optional metadata

        Returns:
            dict: Charge information
        """
        stripe = self._get_stripe()

        # Convert to cents
        amount_cents = int(amount * 100)

        try:
            charge = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                payment_method=token_id,
                description=description,
                metadata=metadata or {},
                confirm=True,
                off_session=True,
            )

            logger.info(f"Created charge: {charge.id}")

            return {
                'transaction_id': charge.id,
                'status': 'succeeded' if charge.status == 'succeeded' else 'failed',
                'amount': amount,
                'currency': currency,
                'error_message': charge.last_payment_error.message if charge.last_payment_error else '',
                'error_code': charge.last_payment_error.code if charge.last_payment_error else '',
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create charge: {str(e)}")
            return {
                'transaction_id': '',
                'status': 'failed',
                'amount': amount,
                'currency': currency,
                'error_message': str(e),
                'error_code': getattr(e, 'code', ''),
            }

    # ===========================
    # Webhook Handling
    # ===========================

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw webhook payload
            signature: Stripe-Signature header value

        Returns:
            bool: True if signature is valid
        """
        stripe = self._get_stripe()
        webhook_secret = self.config.get('webhook_secret')

        if not webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            return False

        try:
            stripe.Webhook.construct_event(
                payload,
                signature,
                webhook_secret
            )
            return True

        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            return False

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Stripe webhook payload.

        Args:
            payload: Stripe webhook event

        Returns:
            dict: Standardized event format
        """
        event_type = payload.get('type', '')
        event_id = payload.get('id', '')
        data = payload.get('data', {}).get('object', {})

        result = {
            'event_type': event_type,
            'event_id': event_id,
            'data': data,
        }

        # Extract subscription ID if present
        if 'subscription' in data:
            result['subscription_id'] = data.get('subscription')

        # Extract customer ID if present
        if 'customer' in data:
            result['customer_id'] = data.get('customer')

        return result
