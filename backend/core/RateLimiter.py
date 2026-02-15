import time
import asyncio
import threading
from typing import Dict, Optional


class RateLimiter:
    """
    A thread-safe and async-safe rate limiter using a token bucket algorithm.
    It can handle multiple rate limit rules (e.g., requests per minute, requests per second).
    """

    def __init__(self, limits: Dict[str, int], logger=None):
        """
        Initializes the RateLimiter.
        Args:
            limits: A dictionary defining the rate limits.
                    Example: {"requests_per_second": 10, "requests_per_minute": 1200}
            logger: Optional logger instance for debug messages.
        """
        self.rules = []
        if "requests_per_second" in limits:
            self.rules.append({"period": 1, "limit": limits["requests_per_second"]})
        if "requests_per_minute" in limits:
            self.rules.append({"period": 60, "limit": limits["requests_per_minute"]})
        if "requests_per_hour" in limits:
            self.rules.append({"period": 3600, "limit": limits["requests_per_hour"]})

        if not self.rules:
            raise ValueError(
                "No valid rate limits provided. Use 'requests_per_second', 'requests_per_minute', or 'requests_per_hour'."
            )

        # Sort rules by period to handle more restrictive limits correctly.
        self.rules.sort(key=lambda x: x["period"])

        self.tokens = {rule["period"]: float(rule["limit"]) for rule in self.rules}
        self.last_refill = {rule["period"]: time.monotonic() for rule in self.rules}

        self.sync_lock = threading.Lock()
        self.async_lock = asyncio.Lock()
        self.logger = logger

    def _refill_tokens(self, period: int):
        """Refills tokens for a given period based on the elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill[period]
        limit = next(rule["limit"] for rule in self.rules if rule["period"] == period)
        refill_rate = limit / period

        tokens_to_add = elapsed * refill_rate

        self.tokens[period] = min(float(limit), self.tokens[period] + tokens_to_add)
        self.last_refill[period] = now

    def _get_wait_time(self) -> float:
        """
        Calculates the necessary wait time to respect all rate limits.
        It checks each rule and determines the maximum wait time required.
        """
        wait_time = 0.0
        for rule in self.rules:
            period = rule["period"]
            limit = rule["limit"]

            self._refill_tokens(period)

            if self.tokens[period] < 1:
                tokens_needed = 1 - self.tokens[period]
                refill_rate = limit / period
                required_wait = tokens_needed / refill_rate
                wait_time = max(wait_time, required_wait)

        return wait_time

    def acquire(self):
        """
        Acquires a token for a synchronous operation.
        Blocks if necessary until a token is available.
        """
        with self.sync_lock:
            wait_time = self._get_wait_time()
            if wait_time > 0:
                if self.logger:
                    self.logger.debug(
                        f"Rate limit reached. Waiting for {wait_time:.2f} seconds."
                    )
                time.sleep(wait_time)

            for rule in self.rules:
                self._refill_tokens(rule["period"])
                self.tokens[rule["period"]] -= 1

    async def async_acquire(self):
        """
        Acquires a token for an asynchronous operation.
        Asynchronously waits if necessary until a token is available.
        """
        async with self.async_lock:
            wait_time = self._get_wait_time()
            if wait_time > 0:
                if self.logger:
                    self.logger.debug(
                        f"Rate limit reached. Waiting for {wait_time:.2f} seconds."
                    )
                await asyncio.sleep(wait_time)

            for rule in self.rules:
                self._refill_tokens(rule["period"])
                self.tokens[rule["period"]] -= 1

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        await self.async_acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class RateLimiterRegistry:
    """
    A globally accessible registry for RateLimiter instances.
    Ensures that rate limiters with the same name share the same token bucket across the process.
    """

    _registry: Dict[str, "RateLimiter"] = {}
    _lock = threading.Lock()

    @classmethod
    def get_or_create(cls, name: str, limits: Dict[str, int], logger=None) -> "RateLimiter":
        with cls._lock:
            if name not in cls._registry:
                cls._registry[name] = RateLimiter(limits, logger)
            return cls._registry[name]

    @classmethod
    def reset(cls):
        """Resets the registry (useful for tests)."""
        with cls._lock:
            cls._registry.clear()


class RateLimiterManager:
    """Manages multiple RateLimiter instances for different API endpoint categories."""

    def __init__(self, configs: Dict[str, Dict[str, int]], logger=None):
        """
        Initializes the RateLimiterManager.
        Args:
            configs: A dictionary where keys are categories (e.g., 'default', 'market_data')
                     and values are rate limit configurations for the RateLimiter.
            logger: An optional logger instance.
        """
        if "default" not in configs and len(configs) == 0:
             # Only raise if configs is empty. If it has other keys, that's fine,
             # but the user of this manager must know which key to ask for.
             # However, BaseExtractor historically expects "default".
             # We will relax this check or ensure "default" is handled by the caller.
             pass

        self.limiters: dict = {}
        for category, limits in configs.items():
            # Use the category name as the unique key in the global registry
            self.limiters[category] = RateLimiterRegistry.get_or_create(category, limits, logger)
        self.logger = logger
        if self.logger:
            self.logger.debug(
                f"RateLimiterManager initialized with categories: {list(self.limiters.keys())}"
            )

    def get_limiter(self, category: Optional[str] = "default") -> RateLimiter:
        """
        Retrieves a RateLimiter for a specific category.
        If the category is not found, it falls back to the 'default' limiter.
        """
        if category in self.limiters:
            return self.limiters[category]
        
        if "default" in self.limiters:
            if self.logger:
                self.logger.debug(
                    f"No specific rate limiter for category '{category}', using 'default'."
                )
            return self.limiters["default"]

        raise KeyError(f"Rate limiter category '{category}' not found and no 'default' fallback available.")
