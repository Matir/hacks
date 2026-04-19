import asyncio
import time

import pytest

from trashdig.services.rate_limiter import RateLimiter


@pytest.mark.anyio
async def test_rpm_limit():
    # Limit to 600 RPM = 10 requests per second.
    # Refill rate is 10 tokens per second.
    limiter = RateLimiter(rpm_limit=600)
    limiter._rpm_tokens = 1.0 # Start with only 1 token

    # First request should be immediate, use the 1.0 token
    await limiter.wait_for_request()

    start = time.monotonic()
    # Second request should wait for 1.0 token (0.1s at 10/s refill)
    await limiter.wait_for_request()
    end = time.monotonic()

    assert end - start >= 0.05

@pytest.mark.anyio
async def test_tpm_limit():
    # Limit to 6000 TPM = 100 tokens per second.
    limiter = RateLimiter(tpm_limit=6000)
    limiter._tpm_tokens = 0.0

    # Use 100 tokens
    await limiter.wait_for_request()
    await limiter.update_usage(100)

    start = time.monotonic()
    # Next request should wait until _tpm_tokens >= 0.
    # At 100 tokens/sec, -100 to 0 takes 1 second.
    await limiter.wait_for_request()
    end = time.monotonic()

    assert end - start >= 0.9

@pytest.mark.anyio
async def test_no_limit():
    limiter = RateLimiter(rpm_limit=None, tpm_limit=None)

    start = time.monotonic()
    for _ in range(10):
        await limiter.wait_for_request()
    end = time.monotonic()

    # Should be very fast
    assert end - start < 0.1

@pytest.mark.anyio
async def test_concurrent_requests():
    # 600 RPM = 10 req/sec.
    limiter = RateLimiter(rpm_limit=600)
    limiter._rpm_tokens = 1.0 # Only 1 token to start

    async def make_request():
        await limiter.wait_for_request()
        return time.monotonic()

    start = time.monotonic()
    # Run 3 requests concurrently.
    # 1st: immediate, tokens -> 0
    # 2nd: waits 0.1s, tokens -> 0
    # 3rd: waits 0.2s, tokens -> 0
    await asyncio.gather(make_request(), make_request(), make_request())
    end = time.monotonic()

    assert end - start >= 0.15

@pytest.mark.anyio
async def test_low_rpm_limit():
    # 1 RPM = 1 token per 60 seconds.
    limiter = RateLimiter(rpm_limit=1)
    limiter._rpm_tokens = 0.0 # No tokens left

    # Should wait for a while. Let's just check if it waits at least 0.2s
    # (since we can't wait 60s in a test).
    # Actually we can mock time or just use a slightly higher limit.
    limiter = RateLimiter(rpm_limit=6) # 1 token per 10 seconds.
    limiter._rpm_tokens = 0.0

    # We'll use a task and cancel it if it takes too long,
    # but here we just want to see it doesn't return immediately.
    try:
        async with asyncio.timeout(0.2):
            await limiter.wait_for_request()
    except TimeoutError:
        pass # Expected to timeout
    else:
        pytest.fail("Should have timed out waiting for RPM token")

@pytest.mark.anyio
async def test_tpm_negative_tokens():
    # 6000 TPM = 100 tokens per second.
    limiter = RateLimiter(tpm_limit=6000)
    limiter._tpm_tokens = -50.0 # Already 50 tokens in debt

    start = time.monotonic()
    # Should wait 0.5s to reach 0 tokens.
    await limiter.wait_for_request()
    end = time.monotonic()

    assert end - start >= 0.4


def test_tpm_initial_tokens_zero():
    # Bucket must start at 0 so the first minute can't use 2x the TPM limit.
    limiter = RateLimiter(tpm_limit=100_000)
    assert limiter._tpm_tokens == 0.0


@pytest.mark.anyio
async def test_tpm_first_request_proceeds_immediately():
    # With _tpm_tokens at 0, the first request should not wait.
    limiter = RateLimiter(tpm_limit=6000)
    start = time.monotonic()
    await limiter.wait_for_request()
    assert time.monotonic() - start < 0.1
