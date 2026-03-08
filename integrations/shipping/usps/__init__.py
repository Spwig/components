"""
USPS Shipping Provider

Integration with USPS REST API v3 for shipping rates, label generation,
and tracking services.

Author: Spwig
Version: 1.0.0
"""

__version__ = '1.0.0'
__author__ = 'Spwig'

from .provider import USPSProvider

__all__ = ['USPSProvider']
