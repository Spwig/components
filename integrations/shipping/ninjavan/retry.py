"""
NinjaVan Retry Logic with Exponential Backoff

This module implements retry logic for transient failures when communicating
with the NinjaVan API, using exponential backoff with jitter to avoid
thundering herd problems.
"""

import time
import random
from functools import wraps
from typing import Callable, Any, Tuple, Type
import logging

from .exceptions import (
    NinjaVanError,
    NinjaVanAPIError,
    NinjaVanNetworkError,
    NinjaVanRateLimitError,
    NinjaVanAuthenticationError,
    NinjaVanValidationError,
    NinjaVanForbiddenError,
    NinjaVanNotFoundError,
)

logger = logging.getLogger(__name__)


# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    NinjaVanAPIError,       # 5xx errors
    NinjaVanNetworkError,   # Network/connection errors
    NinjaVanRateLimitError, # 429 errors
)

# Exceptions that should never be retried
NON_RETRYABLE_EXCEPTIONS = (
    NinjaVanValidationError,  # 400 errors (bad request)
    NinjaVanForbiddenError,   # 403 errors (permission issues)
    NinjaVanNotFoundError,    # 404 errors (resource not found)
)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Initial delay between retries in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 60.0)
            exponential_base: Base for exponential backoff calculation (default: 2.0)
            jitter: Whether to add randomization to delays (default: True)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number using exponential backoff.

        Formula: min(max_delay, base_delay * (exponential_base ^ attempt))

        If jitter is enabled, adds random variation: delay * (0.5 to 1.5)

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = min(
            self.max_delay,
            self.base_delay * (self.exponential_base ** attempt)
        )

        # Add jitter if enabled (randomize between 50% and 150% of delay)
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay


def should_retry(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: Exception that was raised

    Returns:
        True if the exception is retryable, False otherwise

    Rules:
    - Always retry: 5xx errors, network errors, rate limit errors
    - Never retry: 400 (validation), 403 (forbidden), 404 (not found)
    - Special case: 401 (authentication) - handled separately by auth refresh
    """
    # Check if exception is explicitly non-retryable
    if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
        return False

    # Check if exception is explicitly retryable
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    # 401 errors (authentication) should not be retried by this mechanism
    # They should trigger token refresh instead
    if isinstance(exception, NinjaVanAuthenticationError):
        return False

    # For unknown exceptions, don't retry
    return False


def with_retry(
    config: RetryConfig = None,
    on_retry: Callable[[Exception, int, float], None] = None,
) -> Callable:
    """
    Decorator to add retry logic with exponential backoff to a function.

    Args:
        config: RetryConfig instance (uses defaults if None)
        on_retry: Optional callback function called before each retry
                  Signature: (exception, attempt, delay) -> None

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(RetryConfig(max_retries=3))
        def make_api_call():
            # API call that might fail
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if this is the last attempt
                    if attempt >= config.max_retries:
                        logger.warning(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}. "
                            f"Raising exception: {type(e).__name__}: {str(e)}"
                        )
                        raise

                    # Check if exception is retryable
                    if not should_retry(e):
                        logger.debug(
                            f"Exception {type(e).__name__} is not retryable. "
                            f"Raising immediately."
                        )
                        raise

                    # Calculate delay for this attempt
                    delay = config.calculate_delay(attempt)

                    # Special handling for rate limit errors
                    if isinstance(e, NinjaVanRateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                        logger.warning(
                            f"Rate limit exceeded. Waiting {delay:.2f}s before retry "
                            f"(attempt {attempt + 1}/{config.max_retries})"
                        )

                    # Log retry attempt
                    logger.info(
                        f"Retrying {func.__name__} after {type(e).__name__}: {str(e)}. "
                        f"Attempt {attempt + 1}/{config.max_retries}. "
                        f"Waiting {delay:.2f}s..."
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except Exception as callback_error:
                            logger.error(
                                f"Error in on_retry callback: {callback_error}"
                            )

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class RetryableRequest:
    """
    Context manager for making retryable HTTP requests.

    Provides more granular control over retry logic than the decorator.

    Example:
        config = RetryConfig(max_retries=3)
        with RetryableRequest(config) as retry:
            response = retry.execute(lambda: requests.get(url))
    """

    def __init__(self, config: RetryConfig = None):
        """
        Initialize retryable request context.

        Args:
            config: RetryConfig instance (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        # Suppress exceptions handled by execute()
        return False

    def execute(self, func: Callable[[], Any]) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute (should take no arguments)

        Returns:
            Result of successful function execution

        Raises:
            Last exception if all retries exhausted or non-retryable error
        """
        for attempt in range(self.config.max_retries + 1):
            self.attempt = attempt

            try:
                return func()

            except Exception as e:
                self.last_exception = e

                # Check if this is the last attempt
                if attempt >= self.config.max_retries:
                    logger.warning(
                        f"Max retries ({self.config.max_retries}) exceeded. "
                        f"Raising exception: {type(e).__name__}: {str(e)}"
                    )
                    raise

                # Check if exception is retryable
                if not should_retry(e):
                    logger.debug(
                        f"Exception {type(e).__name__} is not retryable. "
                        f"Raising immediately."
                    )
                    raise

                # Calculate delay and wait
                delay = self.config.calculate_delay(attempt)

                # Special handling for rate limit errors
                if isinstance(e, NinjaVanRateLimitError) and e.retry_after:
                    delay = max(delay, e.retry_after)

                logger.info(
                    f"Retrying after {type(e).__name__}: {str(e)}. "
                    f"Attempt {attempt + 1}/{self.config.max_retries}. "
                    f"Waiting {delay:.2f}s..."
                )

                time.sleep(delay)

        # This should never be reached
        if self.last_exception:
            raise self.last_exception


def create_retry_config_from_environment(env: str = "production") -> RetryConfig:
    """
    Create retry configuration based on environment.

    Args:
        env: Environment name ('sandbox' or 'production')

    Returns:
        RetryConfig instance with environment-appropriate settings
    """
    if env == "sandbox":
        # More aggressive retries for sandbox (faster iteration)
        return RetryConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
        )
    else:
        # Conservative retries for production
        return RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
        )
