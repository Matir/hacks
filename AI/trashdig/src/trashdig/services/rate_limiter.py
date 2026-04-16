import asyncio
import time
from typing import Optional


class RateLimiter:
    """A global rate limiter for LLM requests (RPM and TPM).
    
    This implementation uses a token bucket-like approach. 
    RPM is handled by waiting until a request slot is available.
    TPM is handled by tracking token usage and waiting if the limit is exceeded.
    """

    def __init__(self, rpm_limit: Optional[int] = None, tpm_limit: Optional[int] = None):
        """Initializes the RateLimiter.

        Args:
            rpm_limit: Requests per minute limit.
            tpm_limit: Tokens per minute limit.
        """
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit

        self._rpm_tokens = float(rpm_limit) if rpm_limit else 0.0
        self._tpm_tokens = float(tpm_limit) if tpm_limit else 0.0
        
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refills the token buckets based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now

        if self.rpm_limit:
            # Refill RPM: rpm_limit / 60.0 tokens per second
            self._rpm_tokens = min(
                float(self.rpm_limit),
                self._rpm_tokens + elapsed * (self.rpm_limit / 60.0)
            )

        if self.tpm_limit:
            # Refill TPM: tpm_limit / 60.0 tokens per second
            self._tpm_tokens = min(
                float(self.tpm_limit),
                self._tpm_tokens + elapsed * (self.tpm_limit / 60.0)
            )

    async def wait_for_request(self) -> None:
        """Waits until a request can be made according to the RPM and TPM limits."""
        if not self.rpm_limit and not self.tpm_limit:
            return

        while True:
            async with self._lock:
                self._refill()

                rpm_wait = 0.0
                if self.rpm_limit:
                    if self._rpm_tokens >= 1.0:
                        pass
                    else:
                        # Time needed to reach 1.0 token
                        rpm_wait = (1.0 - self._rpm_tokens) / (self.rpm_limit / 60.0)

                tpm_wait = 0.0
                if self.tpm_limit:
                    if self._tpm_tokens < 0:
                        # Time needed to reach 0 tokens
                        tpm_wait = -self._tpm_tokens / (self.tpm_limit / 60.0)
                
                wait_time = max(rpm_wait, tpm_wait)
                if wait_time <= 0:
                    # Grant request slot
                    if self.rpm_limit:
                        self._rpm_tokens -= 1.0
                    return

            # Wait at least a bit to avoid tight loops, but try to be precise
            await asyncio.sleep(max(0.005, wait_time))

    async def update_usage(self, tokens: int) -> None:
        """Updates the TPM bucket after a request is completed.

        Args:
            tokens: The number of tokens used in the request.
        """
        if not self.tpm_limit:
            return

        async with self._lock:
            self._refill()
            self._tpm_tokens -= float(tokens)

# Global instance
_global_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> Optional[RateLimiter]:
    """Returns the global RateLimiter instance."""
    return _global_rate_limiter

def init_rate_limiter(rpm_limit: Optional[int] = None, tpm_limit: Optional[int] = None) -> None:
    """Initializes the global RateLimiter instance.

    Args:
        rpm_limit: Requests per minute limit.
        tpm_limit: Tokens per minute limit.
    """
    global _global_rate_limiter
    if rpm_limit or tpm_limit:
        _global_rate_limiter = RateLimiter(rpm_limit, tpm_limit)
    else:
        _global_rate_limiter = None
