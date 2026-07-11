from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import Lock
from typing import Protocol, TypeVar, cast

import requests

TRANSIENT_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


class HttpResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]

    def raise_for_status(self) -> None: ...

    def close(self) -> None: ...


ResponseT = TypeVar("ResponseT")


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry behavior for transient HTTP failures."""

    max_attempts: int = 3
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be nonnegative")
        if self.max_backoff_seconds < 0:
            raise ValueError("max_backoff_seconds must be nonnegative")


DEFAULT_RETRY_POLICY = RetryPolicy()


class RequestRateLimiter:
    """Serialize requests and enforce a minimum process-local interval."""

    def __init__(
        self,
        minimum_interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds must be nonnegative")
        self.minimum_interval_seconds = minimum_interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._next_request_at = 0.0
        self._lock = Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            delay = max(0.0, self._next_request_at - now)
            if delay:
                self._sleeper(delay)
                now = self._clock()
            self._next_request_at = max(now, self._next_request_at) + (
                self.minimum_interval_seconds
            )


def get_with_retry(
    url: str,
    *,
    request_get: Callable[..., ResponseT],
    timeout: float,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    rate_limiter: RequestRateLimiter | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    **kwargs: object,
) -> ResponseT:
    """Issue a GET request with bounded retries for transient failures only."""
    for attempt in range(1, retry_policy.max_attempts + 1):
        retry_after = 0.0
        if rate_limiter is not None:
            rate_limiter.wait()
        try:
            response = request_get(url, timeout=timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == retry_policy.max_attempts:
                raise
        else:
            http_response = cast(HttpResponse, response)
            status_code = int(getattr(response, "status_code", 200))
            if status_code not in TRANSIENT_HTTP_STATUS_CODES:
                http_response.raise_for_status()
                return response
            if attempt == retry_policy.max_attempts:
                http_response.raise_for_status()
                return response
            retry_after = _retry_after_seconds(getattr(response, "headers", {}))
            close = getattr(response, "close", None)
            if callable(close):
                close()
        delay = min(
            retry_policy.max_backoff_seconds,
            retry_policy.backoff_seconds * (2 ** (attempt - 1)),
        )
        delay = max(delay, retry_after)
        if delay:
            sleeper(delay)
    raise RuntimeError("unreachable HTTP retry state")


def _retry_after_seconds(headers: Mapping[str, str]) -> float:
    value = headers.get("Retry-After")
    if value is None:
        return 0.0
    try:
        return max(0.0, float(value))
    except ValueError:
        return 0.0
