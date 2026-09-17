"""Retry utilities with exponential backoff and jitter for API calls."""

import random
import time
from functools import wraps
from typing import Callable, TypeVar, Any

from openai import OpenAIError


T = TypeVar("T")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_jitter: float = 1.0,
    retriable_errors: tuple = (429, 502, 503, 529),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying API calls with exponential backoff and jitter.

    Strategy:
    - Exponential backoff: wait = base_delay * (2 ** attempt)
    - Random jitter: add 0 to max_jitter seconds
    - Special handling for 402 (budget exhausted): check Retry-After header

    Args:
        max_retries: Maximum number of retry attempts (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 1.0)
        max_jitter: Maximum random jitter to add in seconds (default 1.0)
        retriable_errors: HTTP status codes that trigger retry (default: 429, 502, 503, 529)

    Returns:
        Decorated function that retries on specified errors

    Raises:
        OpenAIError: After all retries exhausted
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)

                except OpenAIError as e:
                    last_exception = e
                    error_str = str(e)

                    # Extract status code from error message
                    status_code = None
                    for code in [400, 401, 402, 404, 429, 502, 503, 529]:
                        if str(code) in error_str:
                            status_code = code
                            break

                    # Non-retriable errors: fail immediately
                    if status_code in (400, 401, 404):
                        raise

                    # Last attempt: raise the error
                    if attempt == max_retries:
                        raise

                    # Special handling for 402 (budget exhausted)
                    if status_code == 402:
                        # Look for Retry-After header in error (OpenAI SDK may include it)
                        # Default to 60s if not found
                        retry_after = 60.0
                        if "retry-after" in error_str.lower():
                            try:
                                # Try to extract number from error message
                                import re

                                match = re.search(r"retry[- ]after:?\s*(\d+)", error_str, re.I)
                                if match:
                                    retry_after = float(match.group(1))
                            except Exception:
                                pass  # Use default

                        time.sleep(retry_after)
                        continue  # Retry once after waiting

                    # Retriable error (429, 502, 503, 529)
                    if status_code in retriable_errors or status_code is None:
                        # Exponential backoff: 2^attempt * base_delay
                        backoff = base_delay * (2**attempt)

                        # Add random jitter: 0 to max_jitter seconds
                        jitter = random.uniform(0, max_jitter)

                        wait_time = backoff + jitter

                        time.sleep(wait_time)
                        continue  # Retry

                    # Unknown error type: raise
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator
