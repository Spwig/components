"""
Australia Post Shipping Provider Package

HTTP Basic Auth authenticated shipping provider for Australia Post Shipping API.

Key Features:
- API Key authentication (UUID format)
- Account number padding (10-digit Australia Post, 8-digit StarTrack)
- Two-step label generation (create shipment, then create labels)
- Rate limiting for tracking API (10 requests/60 seconds)
- JSON request/response format
- Exponential backoff retry logic

Author: Spwig
Version: 2.0.2
"""

__version__ = '2.0.2'
__author__ = 'Spwig'

from .provider import AustraliaPostProvider

__all__ = ['AustraliaPostProvider']
