"""
Wise Payout Provider

Implements payouts via Wise (formerly TransferWise) API.
Supports transfers to 170+ countries with real exchange rates.
"""

import hashlib
import base64
import json
import logging
import requests
from decimal import Decimal
from typing import Any
from datetime import datetime

from payout_providers.base import BasePayoutProvider

logger = logging.getLogger(__name__)


class WisePayoutProvider(BasePayoutProvider):
    """
    Wise payout provider implementation.

    Uses the Wise API to send money transfers with:
    - Real mid-market exchange rates
    - Transparent, upfront fees
    - Support for 170+ countries
    - Quote-based transfers
    """

    SANDBOX_URL = "https://api.sandbox.transferwise.tech"
    PRODUCTION_URL = "https://api.transferwise.com"

    # Transfer states
    STATE_INCOMING_PAYMENT_WAITING = "incoming_payment_waiting"
    STATE_PROCESSING = "processing"
    STATE_FUNDS_CONVERTED = "funds_converted"
    STATE_OUTGOING_PAYMENT_SENT = "outgoing_payment_sent"
    STATE_CANCELLED = "cancelled"
    STATE_FUNDS_REFUNDED = "funds_refunded"
    STATE_BOUNCED_BACK = "bounced_back"

    FINAL_STATES = [STATE_OUTGOING_PAYMENT_SENT, STATE_CANCELLED, STATE_FUNDS_REFUNDED]

    def __init__(self, credentials: dict, settings: dict = None):
        super().__init__(credentials, settings)
        self.api_token = credentials.get('api_token')
        self.profile_id = credentials.get('profile_id')
        self.environment = credentials.get('environment', 'sandbox')
        self.webhook_public_key = credentials.get('webhook_secret')  # Actually public key for RSA

        self.base_url = self.PRODUCTION_URL if self.environment == 'production' else self.SANDBOX_URL

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request to Wise."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data,
                timeout=30
            )

            if response.status_code == 204:
                return {}

            result = response.json() if response.content else {}

            if response.status_code >= 400:
                error_msg = result.get('error', result.get('message', 'Unknown error'))
                logger.error(f"Wise API error: {error_msg}")
                raise Exception(f"Wise API error: {error_msg}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Wise request failed: {e}")
            raise

    def _get_profile_id(self) -> str:
        """Get or retrieve the business profile ID."""
        if self.profile_id:
            return self.profile_id

        # Auto-detect profile ID
        profiles = self._make_request('GET', '/v1/profiles')

        # Look for business profile first
        for profile in profiles:
            if profile.get('type') == 'business':
                return str(profile['id'])

        # Fall back to personal profile
        for profile in profiles:
            if profile.get('type') == 'personal':
                return str(profile['id'])

        raise Exception("No Wise profile found")

    def test_connection(self) -> dict:
        """Test API credentials by fetching profile info."""
        try:
            profiles = self._make_request('GET', '/v1/profiles')

            if not profiles:
                return {
                    'success': False,
                    'error': 'No profiles found for this API token'
                }

            # Get business profile info
            business_profile = None
            for profile in profiles:
                if profile.get('type') == 'business':
                    business_profile = profile
                    break

            if not business_profile:
                business_profile = profiles[0]

            profile_type = business_profile.get('type', 'unknown')
            details = business_profile.get('details', {})
            name = details.get('name') or details.get('firstName', 'Unknown')

            return {
                'success': True,
                'message': f'Connected to Wise {profile_type} profile: {name}',
                'profile_id': business_profile.get('id'),
                'profile_type': profile_type,
                'environment': self.environment
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_quote(self, source_currency: str, target_currency: str,
                     source_amount: Decimal = None, target_amount: Decimal = None) -> dict:
        """
        Create a quote for a transfer.

        Either source_amount or target_amount must be provided.
        """
        profile_id = self._get_profile_id()

        data = {
            'sourceCurrency': source_currency,
            'targetCurrency': target_currency,
            'profile': int(profile_id),
        }

        if source_amount:
            data['sourceAmount'] = float(source_amount)
        elif target_amount:
            data['targetAmount'] = float(target_amount)
        else:
            raise ValueError("Either source_amount or target_amount must be provided")

        quote = self._make_request('POST', '/v3/profiles/{}/quotes'.format(profile_id), data)

        return {
            'quote_id': quote.get('id'),
            'source_amount': Decimal(str(quote.get('sourceAmount', 0))),
            'target_amount': Decimal(str(quote.get('targetAmount', 0))),
            'rate': Decimal(str(quote.get('rate', 0))),
            'fee': Decimal(str(quote.get('fee', 0))),
            'estimated_delivery': quote.get('deliveryEstimate'),
            'expiration': quote.get('expirationTime'),
            'raw_response': quote
        }

    def create_recipient(self, recipient_data: dict) -> dict:
        """
        Create a recipient account for transfers.

        recipient_data should include:
        - currency: Target currency code
        - type: Account type (e.g., 'iban', 'sort_code', 'aba', etc.)
        - account_holder_name: Full name
        - details: Bank-specific details (varies by type)
        """
        profile_id = self._get_profile_id()

        data = {
            'currency': recipient_data.get('currency'),
            'type': recipient_data.get('type'),
            'profile': int(profile_id),
            'accountHolderName': recipient_data.get('account_holder_name'),
            'details': recipient_data.get('details', {})
        }

        # Add email for email recipients
        if recipient_data.get('email'):
            data['details']['email'] = recipient_data['email']

        account = self._make_request('POST', '/v1/accounts', data)

        return {
            'recipient_id': account.get('id'),
            'currency': account.get('currency'),
            'account_holder_name': account.get('accountHolderName'),
            'raw_response': account
        }

    def send_payout(self, payout_data: dict) -> dict:
        """
        Send a payout to a recipient.

        payout_data should include:
        - amount: Decimal amount to send
        - currency: Source currency
        - target_currency: Target currency
        - recipient_id: Wise recipient account ID (or recipient_data to create new)
        - recipient_data: Dict with recipient details (if recipient_id not provided)
        - reference: Payment reference/note
        - external_id: Your unique transaction ID
        """
        try:
            profile_id = self._get_profile_id()

            # Get or create recipient
            recipient_id = payout_data.get('recipient_id')
            if not recipient_id and payout_data.get('recipient_data'):
                recipient = self.create_recipient(payout_data['recipient_data'])
                recipient_id = recipient['recipient_id']

            if not recipient_id:
                raise ValueError("Either recipient_id or recipient_data must be provided")

            # Create quote
            quote = self.create_quote(
                source_currency=payout_data.get('currency', 'USD'),
                target_currency=payout_data.get('target_currency', payout_data.get('currency', 'USD')),
                source_amount=payout_data.get('amount')
            )

            # Create transfer
            transfer_data = {
                'targetAccount': int(recipient_id),
                'quoteUuid': quote['quote_id'],
                'customerTransactionId': payout_data.get('external_id', self._generate_transaction_id()),
                'details': {
                    'reference': payout_data.get('reference', 'Affiliate payout')[:35],  # Max 35 chars
                }
            }

            transfer = self._make_request('POST', '/v1/transfers', transfer_data)

            # Fund the transfer from balance
            transfer_id = transfer.get('id')
            fund_data = {
                'type': 'BALANCE'
            }

            try:
                self._make_request(
                    'POST',
                    f'/v3/profiles/{profile_id}/transfers/{transfer_id}/payments',
                    fund_data
                )
            except Exception as e:
                # Funding may fail if insufficient balance - transfer is still created
                logger.warning(f"Transfer funding failed: {e}")

            return {
                'success': True,
                'payout_id': str(transfer_id),
                'payout_batch_id': None,  # Wise doesn't have batch IDs
                'status': self._map_status(transfer.get('status')),
                'amount': payout_data.get('amount'),
                'currency': payout_data.get('currency'),
                'fee': quote.get('fee'),
                'exchange_rate': quote.get('rate'),
                'recipient_id': recipient_id,
                'reference': payout_data.get('reference'),
                'raw_response': transfer
            }

        except Exception as e:
            logger.error(f"Wise payout failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        import uuid
        return str(uuid.uuid4())

    def get_payout_status(self, payout_id: str) -> dict:
        """Get the status of a transfer."""
        try:
            transfer = self._make_request('GET', f'/v1/transfers/{payout_id}')

            return {
                'success': True,
                'payout_id': str(transfer.get('id')),
                'status': self._map_status(transfer.get('status')),
                'wise_status': transfer.get('status'),
                'source_amount': Decimal(str(transfer.get('sourceValue', 0))),
                'target_amount': Decimal(str(transfer.get('targetValue', 0))),
                'source_currency': transfer.get('sourceCurrency'),
                'target_currency': transfer.get('targetCurrency'),
                'created_at': transfer.get('created'),
                'raw_response': transfer
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_payout(self, payout_id: str) -> dict:
        """Cancel a pending transfer."""
        try:
            result = self._make_request('PUT', f'/v1/transfers/{payout_id}/cancel')

            return {
                'success': True,
                'payout_id': payout_id,
                'status': 'cancelled',
                'raw_response': result
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def estimate_fee(self, amount: Decimal, source_currency: str,
                     target_currency: str = None) -> dict:
        """Estimate the fee for a transfer."""
        try:
            target = target_currency or source_currency
            quote = self.create_quote(
                source_currency=source_currency,
                target_currency=target,
                source_amount=amount
            )

            return {
                'success': True,
                'fee': quote['fee'],
                'fee_currency': source_currency,
                'exchange_rate': quote['rate'],
                'source_amount': quote['source_amount'],
                'target_amount': quote['target_amount'],
                'estimated_delivery': quote.get('estimated_delivery'),
                'raw_response': quote.get('raw_response')
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _map_status(self, wise_status: str) -> str:
        """Map Wise status to standard status."""
        status_map = {
            'incoming_payment_waiting': 'pending',
            'waiting_recipient_input_to_proceed': 'pending',
            'processing': 'processing',
            'funds_converted': 'processing',
            'outgoing_payment_sent': 'completed',
            'cancelled': 'cancelled',
            'funds_refunded': 'refunded',
            'bounced_back': 'failed',
            'charged_back': 'failed',
            'unknown': 'unknown'
        }
        return status_map.get(wise_status, 'unknown')

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using RSA public key.

        Wise uses RSA-SHA256 signatures for webhooks.
        """
        if not self.webhook_public_key:
            logger.warning("No webhook public key configured, skipping verification")
            return True

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend

            # Load the public key
            public_key = serialization.load_pem_public_key(
                self.webhook_public_key.encode(),
                backend=default_backend()
            )

            # Decode the signature
            signature_bytes = base64.b64decode(signature)

            # Verify
            public_key.verify(
                signature_bytes,
                payload,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return True

        except ImportError:
            logger.warning("cryptography library not installed, skipping signature verification")
            return True
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def process_webhook(self, payload: dict, headers: dict = None) -> dict:
        """Process a webhook notification from Wise."""
        try:
            event_type = payload.get('event_type') or payload.get('eventType')
            data = payload.get('data', {})
            resource = data.get('resource', {})

            # Extract transfer info
            transfer_id = resource.get('id')
            current_state = resource.get('current_state') or resource.get('currentState')

            # Map to standard event types
            event_map = {
                'transfers#state-change': 'transfer.status_changed',
                'transfers#active-cases': 'transfer.issue',
                'balances#credit': 'balance.credited',
            }

            standard_event = event_map.get(event_type, event_type)

            return {
                'success': True,
                'event_type': standard_event,
                'payout_id': str(transfer_id) if transfer_id else None,
                'status': self._map_status(current_state) if current_state else None,
                'wise_status': current_state,
                'raw_payload': payload
            }

        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_balance(self, currency: str = None) -> dict:
        """Get account balance(s)."""
        try:
            profile_id = self._get_profile_id()
            balances = self._make_request('GET', f'/v4/profiles/{profile_id}/balances?types=STANDARD')

            result = {
                'success': True,
                'balances': []
            }

            for balance in balances:
                balance_info = {
                    'currency': balance.get('currency'),
                    'amount': Decimal(str(balance.get('amount', {}).get('value', 0))),
                    'reserved': Decimal(str(balance.get('reservedAmount', {}).get('value', 0))),
                }

                if currency is None or balance_info['currency'] == currency:
                    result['balances'].append(balance_info)

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
