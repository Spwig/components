"""
Australia Post Rate Limiter

Implements token bucket rate limiting for Australia Post Tracking API.
Tracking API limit: 10 requests per 60 seconds.
"""

import time
import threading
import logging
from typing import Optional
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from .exceptions import AustraliaPostRateLimitError


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests: int = 10  # Maximum requests allowed
    time_window: int = 60  # Time window in seconds
    strict_mode: bool = True  # Raise exception vs wait


class RateLimiter:
    """
    Token bucket rate limiter for Australia Post Tracking API.

    Implements thread-safe rate limiting with token bucket algorithm.
    Australia Post Tracking API allows maximum 10 requests per 60 seconds.

    Example:
        limiter = RateLimiter(max_requests=10, time_window=60)

        # Before each tracking API call
        limiter.acquire()  # Blocks if limit reached
    """

    def __init__(
        self,
        max_requests: int = 10,
        time_window: int = 60,
        strict_mode: bool = True
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window (default: 10)
            time_window: Time window in seconds (default: 60)
            strict_mode: If True, raise exception when limit reached.
                        If False, wait until tokens available.
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.strict_mode = strict_mode

        # Token bucket state
        self.tokens = max_requests
        self.last_update = time.time()

        # Thread safety
        self._lock = threading.Lock()

        logger.debug(
            f"Initialized rate limiter: {max_requests} requests per {time_window}s "
            f"(strict_mode={strict_mode})"
        )

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time.

        Tokens are refilled at a constant rate:
        refill_rate = max_requests / time_window
        """
        now = time.time()
        elapsed = now - self.last_update

        # Calculate tokens to add
        refill_rate = self.max_requests / self.time_window
        tokens_to_add = elapsed * refill_rate

        # Refill tokens (cap at max)
        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_update = now

        logger.debug(f"Refilled tokens: {self.tokens:.2f}/{self.max_requests}")

    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens to make API request.

        In strict mode: Raises exception if insufficient tokens.
        In non-strict mode: Waits until tokens available.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            bool: True if tokens acquired

        Raises:
            AustraliaPostRateLimitError: If rate limit exceeded (strict mode)

        Example:
            limiter = RateLimiter(max_requests=10, time_window=60)
            limiter.acquire()  # Acquire 1 token
        """
        with self._lock:
            self._refill_tokens()

            if self.tokens >= tokens:
                # Sufficient tokens available
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} token(s). Remaining: {self.tokens:.2f}")
                return True

            # Insufficient tokens
            if self.strict_mode:
                # Calculate wait time
                wait_time = self._calculate_wait_time(tokens)

                raise AustraliaPostRateLimitError(
                    _(
                        "Rate limit exceeded for tracking API. "
                        "Maximum {max_requests} requests per {time_window} seconds. "
                        "Retry after {wait_time:.0f} seconds."
                    ).format(
                        max_requests=self.max_requests,
                        time_window=self.time_window,
                        wait_time=wait_time
                    ),
                    error_code="RATE_LIMIT_EXCEEDED",
                    retry_after=int(wait_time)
                )
            else:
                # Non-strict mode: wait for tokens
                wait_time = self._calculate_wait_time(tokens)
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s for tokens...")
                time.sleep(wait_time)

                # Try again after waiting
                return self.acquire(tokens)

    def _calculate_wait_time(self, tokens_needed: int) -> float:
        """
        Calculate time to wait for tokens to be available.

        Args:
            tokens_needed: Number of tokens needed

        Returns:
            float: Wait time in seconds
        """
        tokens_deficit = tokens_needed - self.tokens
        refill_rate = self.max_requests / self.time_window
        wait_time = tokens_deficit / refill_rate

        return max(0, wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting or raising exception.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            bool: True if tokens acquired, False if insufficient

        Example:
            if limiter.try_acquire():
                # Make API call
                make_tracking_request()
            else:
                # Rate limit reached, handle gracefully
                logger.warning("Rate limit reached")
        """
        with self._lock:
            self._refill_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def reset(self) -> None:
        """
        Reset rate limiter to initial state.

        Useful for testing or manual reset after long idle period.
        """
        with self._lock:
            self.tokens = self.max_requests
            self.last_update = time.time()
            logger.info("Rate limiter reset")

    def get_status(self) -> dict:
        """
        Get current rate limiter status.

        Returns:
            dict: Status information

        Example:
            >>> limiter.get_status()
            {
                'tokens_available': 8.5,
                'max_requests': 10,
                'time_window': 60,
                'wait_time': 0.0
            }
        """
        with self._lock:
            self._refill_tokens()

            wait_time = 0.0
            if self.tokens < 1:
                wait_time = self._calculate_wait_time(1)

            return {
                'tokens_available': round(self.tokens, 2),
                'max_requests': self.max_requests,
                'time_window': self.time_window,
                'wait_time': round(wait_time, 2)
            }


class TrackingRateLimiter(RateLimiter):
    """
    Pre-configured rate limiter for Australia Post Tracking API.

    Tracking API limit: 10 requests per 60 seconds.
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize tracking rate limiter.

        Args:
            strict_mode: If True, raise exception when limit reached.
                        If False, wait until tokens available (default).
        """
        super().__init__(
            max_requests=10,
            time_window=60,
            strict_mode=strict_mode
        )
        logger.info("Initialized tracking rate limiter (10 req/60s)")


# Global tracking rate limiter instance
_tracking_limiter: Optional[TrackingRateLimiter] = None
_limiter_lock = threading.Lock()


def get_tracking_limiter() -> TrackingRateLimiter:
    """
    Get or create global tracking rate limiter instance.

    Returns:
        TrackingRateLimiter: Global rate limiter instance

    Example:
        limiter = get_tracking_limiter()
        limiter.acquire()
        # Make tracking API call
    """
    global _tracking_limiter

    if _tracking_limiter is None:
        with _limiter_lock:
            if _tracking_limiter is None:
                _tracking_limiter = TrackingRateLimiter(strict_mode=False)

    return _tracking_limiter
