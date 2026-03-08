"""
Zettle (PayPal) Terminal provider for cloud-based card-present payments.

Uses the Zettle Reader Connect API to push payment requests to PayPal Reader
hardware. Communication uses REST API for session creation and reader management,
then WebSocket for real-time payment flow.

Integration mode: cloud
- No frontend SDK required
- Backend creates a session and sends payment via REST + WebSocket
- Zettle cloud pushes request to the WiFi-connected PayPal Reader
- Reader handles card interaction
- Payment result streamed back in real-time via WebSocket

Zettle Reader Connect docs: https://developer.zettle.com/docs/payment-integrations/reader-connect/overview
"""
import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional

import requests

from pos_app.terminal_providers.base import TerminalProviderBase

logger = logging.getLogger(__name__)

# Zettle API endpoints
OAUTH_URL = 'https://oauth.zettle.com/token'
READER_CONNECT_URL = 'https://reader-connect.zettle.com'
PURCHASE_URL = 'https://purchase.izettle.com'


class ZettleTerminalProvider(TerminalProviderBase):
    provider_key = 'zettle_terminal'
    provider_name = 'Zettle (PayPal) Terminal'

    _access_token = None
    _token_expiry = 0

    @property
    def integration_mode(self):
        return 'cloud'

    @property
    def credential_schema(self):
        return {
            'type': 'object',
            'properties': {
                'client_id': {
                    'type': 'string',
                    'title': 'Client ID',
                    'description': 'Zettle application client ID',
                    'required': True,
                },
                'api_key': {
                    'type': 'string',
                    'title': 'API Key (JWT Assertion)',
                    'description': 'Zettle API key for assertion grant authentication',
                    'required': True,
                    'secret': True,
                },
            },
        }

    def validate_credentials(self, credentials):
        client_id = credentials.get('client_id', '')
        if not client_id:
            raise ValueError("Zettle client ID is required")
        api_key = credentials.get('api_key', '')
        if not api_key:
            raise ValueError("Zettle API key is required")

    # ── OAuth ──────────────────────────────────────────────────────

    def _get_access_token(self):
        """Obtain or refresh an access token using assertion grant."""
        now = time.time()
        if self._access_token and now < self._token_expiry:
            return self._access_token

        try:
            resp = requests.post(
                OAUTH_URL,
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'client_id': self.credentials['client_id'],
                    'assertion': self.credentials['api_key'],
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=15,
            )

            if resp.status_code != 200:
                logger.error(f"Zettle OAuth error: {resp.status_code} {resp.text}")
                return None

            data = resp.json()
            self._access_token = data.get('access_token', '')
            expires_in = data.get('expires_in', 7200)
            self._token_expiry = now + expires_in - 60  # refresh 60s early
            return self._access_token
        except Exception as e:
            logger.error(f"Zettle OAuth error: {e}")
            return None

    def _get_headers(self):
        token = self._get_access_token()
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }

    # ── Connection ─────────────────────────────────────────────────

    def test_connection(self):
        """Test connection by getting an access token and listing linked readers."""
        try:
            token = self._get_access_token()
            if not token:
                return {'success': False, 'message': 'Failed to authenticate with Zettle'}

            url = f"{READER_CONNECT_URL}/links"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                links = data if isinstance(data, list) else data.get('data', [])
                return {
                    'success': True,
                    'message': f"Connected to Zettle. {len(links)} reader(s) linked.",
                }
            elif resp.status_code == 401:
                return {'success': False, 'message': 'Invalid credentials'}
            else:
                return {'success': False, 'message': f'Zettle API error: {resp.status_code}'}
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Connection timed out'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ── Reader Management ──────────────────────────────────────────

    def list_readers(self, location_id=None):
        """List linked readers via Reader Connect API."""
        try:
            url = f"{READER_CONNECT_URL}/links"
            resp = requests.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return {'success': False, 'message': f'Failed to list readers: {resp.status_code}', 'readers': []}

            data = resp.json()
            link_list = data if isinstance(data, list) else data.get('data', [])
            readers = []
            for link in link_list:
                readers.append({
                    'id': link.get('linkId', link.get('id', '')),
                    'label': link.get('name', 'PayPal Reader'),
                    'type': 'paypal_reader',
                    'serial_number': '',
                    'status': 'online',
                })

            return {'success': True, 'readers': readers}
        except Exception as e:
            logger.error(f"Zettle list readers error: {e}")
            return {'success': False, 'message': str(e), 'readers': []}

    def link_reader(self, pairing_code):
        """Link a new PayPal Reader using its pairing code."""
        try:
            url = f"{READER_CONNECT_URL}/link-offers/claim"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json={'pairingCode': pairing_code},
                timeout=30,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    'success': True,
                    'link_id': data.get('linkId', data.get('id', '')),
                }
            else:
                error_data = resp.json() if resp.content else {}
                return {
                    'success': False,
                    'message': error_data.get('message', f'Failed to link reader: {resp.status_code}'),
                }
        except Exception as e:
            logger.error(f"Zettle link reader error: {e}")
            return {'success': False, 'message': str(e)}

    # ── Cloud Payment Operations ───────────────────────────────────

    def initiate_cloud_payment(self, amount, currency, reader_id, metadata=None):
        """
        Initiate a payment via Zettle Reader Connect.

        This creates a session and sends a payment request. The Reader Connect
        API uses WebSocket for real-time communication, but for the cloud
        provider pattern, we create the session and return the session ID
        for status polling.

        For synchronous flow, we use a blocking approach: create session,
        connect WebSocket, send payment, wait for result.
        """
        try:
            # Step 1: Create a session for the linked reader
            session_url = f"{READER_CONNECT_URL}/sessions"
            session_resp = requests.post(
                session_url,
                headers=self._get_headers(),
                json={'linkId': reader_id},
                timeout=15,
            )

            if session_resp.status_code not in (200, 201):
                return {
                    'success': False,
                    'error_code': 'CLOUD_PAYMENT_FAILED',
                    'message': f'Failed to create reader session: {session_resp.status_code}',
                }

            session_data = session_resp.json()
            session_id = session_data.get('id', session_data.get('sessionId', ''))
            ws_url = session_data.get('location', session_data.get('websocketUrl', ''))

            if not ws_url:
                return {
                    'success': False,
                    'error_code': 'CLOUD_PAYMENT_FAILED',
                    'message': 'No WebSocket URL returned from session creation',
                }

            # Step 2: Use WebSocket to send payment and wait for result
            # Import here to avoid import errors if websockets not installed
            try:
                import websockets
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(
                    self._websocket_payment(ws_url, reader_id, amount, currency, metadata)
                )
                return result
            except ImportError:
                # Fallback: return the session for polling
                logger.warning("websockets package not installed. Returning session for polling.")
                return {
                    'success': True,
                    'transaction_id': session_id,
                    'status': 'pending',
                    'websocket_url': ws_url,
                }
            except RuntimeError:
                # No event loop available (common in Django)
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        self._websocket_payment(ws_url, reader_id, amount, currency, metadata)
                    )
                    return result
                finally:
                    loop.close()

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error_code': 'TIMEOUT',
                'message': 'Timed out creating reader session',
            }
        except Exception as e:
            logger.error(f"Zettle cloud payment error: {e}")
            return {'success': False, 'message': str(e)}

    async def _websocket_payment(self, ws_url, reader_id, amount, currency, metadata=None):
        """Handle the WebSocket payment flow with the Zettle reader."""
        import websockets
        import asyncio

        amount_minor = int(Decimal(str(amount)) * 100)

        try:
            async with websockets.connect(ws_url, additional_headers={
                'Authorization': f'Bearer {self._access_token}',
            }) as ws:
                # Wait for reader ready status
                ready = False
                for _ in range(30):  # Wait up to 30 seconds for READY
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    if data.get('status') == 'READY':
                        ready = True
                        break

                if not ready:
                    return {
                        'success': False,
                        'error_code': 'READER_NOT_READY',
                        'message': 'Reader did not become ready in time',
                    }

                # Send payment request
                payment_msg = {
                    'type': 'payment',
                    'linkId': reader_id,
                    'amount': amount_minor,
                    'currency': currency.upper(),
                }
                if metadata and metadata.get('order_reference'):
                    payment_msg['reference'] = str(metadata['order_reference'])

                await ws.send(json.dumps(payment_msg))

                # Wait for payment result (up to 120 seconds)
                for _ in range(60):
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)

                    if data.get('type') == 'paymentResult':
                        if data.get('result') == 'completed':
                            return {
                                'success': True,
                                'transaction_id': data.get('transactionId', ''),
                                'status': 'succeeded',
                                'card_brand': (data.get('cardType', '') or '').lower(),
                                'last4': data.get('maskedPan', '')[-4:] if data.get('maskedPan') else '',
                                'amount': amount,
                            }
                        else:
                            return {
                                'success': False,
                                'error_code': data.get('failureReason', 'PAYMENT_FAILED'),
                                'message': data.get('message', 'Payment failed'),
                            }

                return {
                    'success': False,
                    'error_code': 'TIMEOUT',
                    'message': 'Payment timed out waiting for reader response',
                }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error_code': 'TIMEOUT',
                'message': 'WebSocket communication timed out',
            }
        except Exception as e:
            logger.error(f"Zettle WebSocket payment error: {e}")
            return {'success': False, 'message': str(e)}

    def check_payment_status(self, transaction_id):
        """
        Zettle uses WebSocket for real-time status, so this is a fallback.
        Check the Purchase API for transaction history.
        """
        try:
            url = f"{PURCHASE_URL}/purchases/v2"
            resp = requests.get(
                url,
                headers=self._get_headers(),
                params={'limit': 1},
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                purchases = data.get('purchases', [])
                if purchases:
                    purchase = purchases[0]
                    return {
                        'success': True,
                        'status': 'succeeded',
                        'payment_id': purchase.get('purchaseUUID1', ''),
                        'amount': Decimal(str(purchase.get('amount', 0))) / 100,
                    }
            return {
                'success': True,
                'status': 'pending',
                'message': 'Zettle uses WebSocket for real-time status updates.',
            }
        except Exception as e:
            logger.error(f"Zettle check status error: {e}")
            return {'success': False, 'status': 'failed', 'message': str(e)}

    def cancel_cloud_payment(self, transaction_id):
        """
        Zettle payment cancellation happens via WebSocket during the payment flow.
        Once the WebSocket connection is closed, the reader automatically cancels.
        """
        return {'success': True, 'message': 'Zettle payments cancel when WebSocket session ends.'}

    def cancel_payment_intent(self, payment_intent_id):
        return self.cancel_cloud_payment(payment_intent_id)

    # ── Refunds ────────────────────────────────────────────────────

    def refund_payment(self, payment_intent_id, amount=None):
        """
        Zettle does not support programmatic refunds via API for card-present payments.
        Refunds must be initiated through the Zettle dashboard or app.
        """
        return {
            'success': False,
            'message': 'Zettle card-present refunds must be initiated through the Zettle dashboard or app.',
        }
