"""
NinjaVan Shipping Provider Plugin

OAuth 2.0-based integration with NinjaVan Plugin APIs for Southeast Asian logistics.

This provider acts on behalf of shippers who have connected their NinjaVan accounts
via OAuth authorization code flow. It supports order creation, label generation,
order cancellation, and webhook-based tracking.

Supported Countries:
- SG - Singapore
- MY - Malaysia
- TH - Thailand
- ID - Indonesia
- VN - Vietnam
- PH - Philippines
- MM - Myanmar

Key Features:
- OAuth 2.0 authorization code grant flow
- Automatic token refresh
- Multi-country support
- Webhook-based tracking
- COD support
- Pickup scheduling
- Return service type
- Integration audit compliance

Note: This provider does NOT support rate calculation as Plugin APIs
do not expose pricing endpoints. Merchants already have NinjaVan pricing
through their existing accounts.
"""

__version__ = '1.0.0'
__author__ = 'Spwig'

from .provider import NinjaVanProvider

__all__ = ['NinjaVanProvider']
