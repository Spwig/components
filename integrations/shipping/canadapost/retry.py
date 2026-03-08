"""
Canada Post Provider Retry Logic

Implements retry decorator with exponential backoff for Canada Post API requests.
Handles transient failures and rate limiting.

Author: Spwig
Version: 1.0.0
"""
import time
import random
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type
from dataclasses import dataclass

import requests

from .exceptions import CanadaPostRateLimitError, CanadaPostServiceUnavailableError


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 32.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.25  # ±25%

    # HTTP status codes that should trigger retry
    retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)

    # Exception types that should trigger retry
    retry_exceptions: Tuple[Type[Exception], ...] = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        CanadaPostServiceUnavailableError,
        CanadaPostRateLimitError,
    )


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying function calls with exponential backoff.

    Args:
        config: Retry configuration (uses default if None)
        on_retry: Optional callback function(attempt, delay, exception)

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(config=RetryConfig(max_attempts=5))
        def make_api_call():
            return requests.post('https://soa-gw.canadapost.ca/...')
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
    """
    # Check for Retry-After header (rate limiting)
    if isinstance(exception, CanadaPostRateLimitError) and exception.retry_after:
        delay = float(exception.retry_after)
        logger.debug(f"Using Retry-After delay: {delay}s")
        return delay

    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay + jitter)

    return delay
