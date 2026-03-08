"""
UPS Shipping Provider

OAuth 2.0 authenticated shipping provider for UPS REST API.
Implements rate calculation, label generation, and tracking.

Author: Spwig
Version: 1.0.0
"""

__version__ = '1.0.0'
__author__ = 'Spwig'

from .provider import UPSProvider

__all__ = ['UPSProvider']
