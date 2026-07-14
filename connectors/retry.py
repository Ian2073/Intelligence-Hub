from __future__ import annotations

import logging
import time
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# HTTP status codes that are safe to retry.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

# Default retry configuration.
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BASE_DELAY: float = 1.0
DEFAULT_MAX_DELAY: float = 16.0


class RetryExhausted(RuntimeError):
    """Raised when all retry attempts have been exhausted."""
    pass


def retry_on_transient(
    func,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    operation_name: str = "HTTP request",
):
    """Execute *func* with automatic retry on transient HTTP errors.

    Retries on:
    - ``httpx.HTTPStatusError`` with status in ``RETRYABLE_STATUS_CODES``
    - ``httpx.TimeoutException``
    - ``httpx.ConnectError``

    All other exceptions propagate immediately.

    Parameters
    ----------
    func:
        A callable (no arguments) that performs the HTTP request and returns
        the result.  Example: ``lambda: httpx.get(url)``.
    max_retries:
        Maximum number of *additional* attempts after the first failure.
    base_delay:
        Initial delay in seconds before the first retry.  Doubles on each
        subsequent retry (exponential backoff).
    max_delay:
        Cap for the computed delay.
    operation_name:
        Human-readable label for log messages.

    Returns
    -------
    The return value of *func* on success.

    Raises
    ------
    RetryExhausted
        When all retry attempts fail.  The original exception is chained.
    """
    last_exception: Exception | None = None
    for attempt in range(1, max_retries + 2):  # 1-indexed, +1 for first try
        try:
            return func()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRYABLE_STATUS_CODES:
                raise  # non-retryable 4xx → propagate immediately
            last_exception = exc
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exception = exc
        except httpx.HTTPError as exc:
            # Catch-all for other transient httpx errors (e.g. pool timeout).
            last_exception = exc

        if attempt > max_retries:
            break

        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        # Respect Retry-After header when available.
        if isinstance(last_exception, httpx.HTTPStatusError):
            retry_after = _parse_retry_after(last_exception.response)
            if retry_after is not None:
                delay = min(retry_after, max_delay)

        logger.warning(
            "%s failed (attempt %d/%d): %s — retrying in %.1fs",
            operation_name,
            attempt,
            max_retries + 1,
            last_exception,
            delay,
        )
        time.sleep(delay)

    raise RetryExhausted(
        f"{operation_name} failed after {max_retries + 1} attempts: {last_exception}"
    ) from last_exception


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Extract ``Retry-After`` header value as seconds, or ``None``."""
    header = response.headers.get("retry-after")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None
