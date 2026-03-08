"""
Australia Post Provider Retry Logic

Implements retry decorator with exponential backoff for Australia Post API requests.
Handles transient failures, rate limiting, and service unavailability.
Follows Australia Post's recommended backoff policy.
"""
import time
import random
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type
from dataclasses import dataclass

import requests

from .exceptions import AustraliaPostRateLimitError, AustraliaPostServiceUnavailableError


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Australia Post recommends:
    - On elevated 5xx errors for >5 minutes: reduce to 1 request/minute
    - If persists >1 hour: check API status page
    - Resume normal calls after 5 minutes without errors
    """

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds (1 minute for severe issues)
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.25  # ±25%

    # HTTP status codes that should trigger retry
    retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)

    # Exception types that should trigger retry
    retry_exceptions: Tuple[Type[Exception], ...] = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        AustraliaPostServiceUnavailableError,
        AustraliaPostRateLimitError,
    )


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying function calls with exponential backoff.

    Implements Australia Post's recommended backoff policy for handling
    transient failures and service unavailability.

    Args:
        config: Retry configuration (uses default if None)
        on_retry: Optional callback function(attempt, delay, exception)

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(config=RetryConfig(max_attempts=5))
        def make_api_call():
            return requests.post('https://digitalapi.auspost.com.au/...')
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    # Attempt the function call
                    return func(*args, **kwargs)

                except config.retry_exceptions as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt >= config.max_attempts:
                        logger.warning(
                            f"Max retry attempts ({config.max_attempts}) reached for {func.__name__}"
                        )
                        raise

                    # Calculate delay
                    delay = calculate_delay(
                        attempt=attempt,
                        config=config,
                        exception=e
                    )

                    # Log retry
                    logger.info(
                        f"Retry attempt {attempt}/{config.max_attempts} "
                        f"for {func.__name__} after {delay:.2f}s delay "
                        f"(error: {type(e).__name__})"
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, delay, e)

                    # Wait before retry
                    time.sleep(delay)

                except requests.exceptions.HTTPError as e:
                    # Check if HTTP status code should trigger retry
                    if (
                        hasattr(e, 'response') and
                        e.response is not None and
                        e.response.status_code in config.retry_status_codes
                    ):
                        last_exception = e

                        # Don't retry on last attempt
                        if attempt >= config.max_attempts:
                            logger.warning(
                                f"Max retry attempts ({config.max_attempts}) reached for {func.__name__}"
                            )
                            raise

                        # Calculate delay
                        delay = calculate_delay(
                            attempt=attempt,
                            config=config,
                            exception=e
                        )

                        # Log retry
                        logger.info(
                            f"Retry attempt {attempt}/{config.max_attempts} "
                            f"for {func.__name__} after {delay:.2f}s delay "
                            f"(HTTP {e.response.status_code})"
                        )

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(attempt, delay, e)

                        # Wait before retry
                        time.sleep(delay)
                    else:
                        # Non-retryable HTTP error
                        raise

                except Exception:
                    # Non-retryable exception
                    raise

            # Should not reach here, but raise last exception if we do
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    exception: Optional[Exception] = None
) -> float:
    """
    Calculate delay before next retry attempt.

    Uses exponential backoff with optional jitter.
    Respects Retry-After header for rate limit errors.

    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration
        exception: Exception that triggered retry (optional)

    Returns:
        Delay in seconds

    Example:
        >>> config = RetryConfig()
        >>> calculate_delay(1, config)  # First retry
        # ~1.0 seconds (with jitter)
        >>> calculate_delay(2, config)  # Second retry
        # ~2.0 seconds (with jitter)
    """
    # Check for Retry-After header (rate limiting)
    if isinstance(exception, AustraliaPostRateLimitError) and exception.retry_after:
        delay = float(exception.retry_after)
        logger.debug(f"Using Retry-After delay: {delay}s")
        return delay

    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled (prevents thundering herd)
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay + jitter)

    return delay


class BackoffPolicy:
    """
    Implements Australia Post's recommended backoff policy for elevated errors.

    When receiving elevated 5xx errors for >5 minutes:
    - Reduce to 1 request per minute
    - After 1 hour, check API status page
    - Resume normal calls after 5 minutes without errors
    """

    def __init__(self):
        self.error_start_time = None
        self.last_success_time = None
        self.in_backoff_mode = False
        self.elevated_error_threshold = 300  # 5 minutes in seconds
        self.recovery_threshold = 300  # 5 minutes in seconds
        self.backoff_delay = 60  # 1 request per minute

    def record_error(self, status_code: int):
        """
        Record an error response.

        Args:
            status_code: HTTP status code
        """
        if status_code >= 500:
            if self.error_start_time is None:
                self.error_start_time = time.time()
                logger.info("Started tracking elevated error responses")

            # Check if we should enter backoff mode
            elapsed = time.time() - self.error_start_time
            if elapsed > self.elevated_error_threshold and not self.in_backoff_mode:
                self.in_backoff_mode = True
                logger.warning(
                    f"Entering backoff mode after {elapsed:.0f}s of elevated errors. "
                    f"Reducing to 1 request per {self.backoff_delay}s"
                )

    def record_success(self):
        """Record a successful response."""
        self.last_success_time = time.time()

        # Check if we can exit backoff mode
        if self.in_backoff_mode and self.error_start_time:
            elapsed_since_error = time.time() - self.error_start_time
            if elapsed_since_error > self.recovery_threshold:
                self.in_backoff_mode = False
                self.error_start_time = None
                logger.info("Exiting backoff mode after recovery period")

    def should_delay(self) -> bool:
        """
        Check if request should be delayed due to backoff policy.

        Returns:
            bool: True if should delay
        """
        return self.in_backoff_mode

    def get_delay(self) -> float:
        """
        Get delay duration if in backoff mode.

        Returns:
            float: Delay in seconds
        """
        if self.in_backoff_mode:
            return self.backoff_delay
        return 0.0
