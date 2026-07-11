import requests

from radshock.http import RequestRateLimiter, RetryPolicy, get_with_retry


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def close(self) -> None:
        self.closed = True


def test_get_with_retry_recovers_from_transient_response() -> None:
    responses = [FakeResponse(503), FakeResponse(200)]
    sleeps: list[float] = []

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        return responses.pop(0)

    result = get_with_retry(
        "https://example.test/data",
        request_get=fake_get,
        timeout=5,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.25),
        sleeper=sleeps.append,
    )

    assert result.status_code == 200
    assert sleeps == [0.25]


def test_get_with_retry_honors_retry_after_and_closes_response() -> None:
    throttled = FakeResponse(429, headers={"Retry-After": "2"})
    responses = [throttled, FakeResponse(200)]
    sleeps: list[float] = []

    result = get_with_retry(
        "https://example.test/data",
        request_get=lambda *args, **kwargs: responses.pop(0),
        timeout=5,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.25),
        sleeper=sleeps.append,
    )

    assert result.status_code == 200
    assert throttled.closed
    assert sleeps == [2.0]


def test_get_with_retry_does_not_retry_client_error() -> None:
    calls = 0

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(400)

    try:
        get_with_retry(
            "https://example.test/data",
            request_get=fake_get,
            timeout=5,
            retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0),
        )
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("HTTP 400 should be raised")

    assert calls == 1


def test_get_with_retry_retries_connection_error() -> None:
    calls = 0

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.ConnectionError("temporary failure")
        return FakeResponse(200)

    result = get_with_retry(
        "https://example.test/data",
        request_get=fake_get,
        timeout=5,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
    )

    assert result.status_code == 200
    assert calls == 2


def test_request_rate_limiter_spaces_consecutive_requests() -> None:
    now = [10.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = RequestRateLimiter(
        0.5,
        clock=lambda: now[0],
        sleeper=sleep,
    )

    limiter.wait()
    limiter.wait()

    assert sleeps == [0.5]
