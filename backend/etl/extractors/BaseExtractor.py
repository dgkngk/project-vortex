import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import requests

from backend.core.RateLimiter import RateLimiterManager
from backend.core.VortexLogger import VortexLogger


class BaseExtractor(ABC):
    """
    Abstract base class for all data extractors.
    Ensures a common interface and structure for specialized extractors.
    """

    def __init__(
        self,
        api_base_url: str,
        rate_limit_configs: Optional[Dict[str, Dict[str, int]]] = None,
        logger: Optional[VortexLogger] = None,
        default_limiter_category: str = "default",
        **kwargs,
    ):
        self.api_base_url = api_base_url
        self.default_limiter_category = default_limiter_category
        self.logger = logger or VortexLogger(
            name=self.__class__.__name__, level="DEBUG"
        )

        if rate_limit_configs is None:
            rate_limit_configs = {"default": {"requests_per_minute": 1200}}

        self.rate_limiter_manager = RateLimiterManager(
            configs=rate_limit_configs, logger=self.logger
        )

    def _make_sync_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> dict:
        """
        Makes a synchronous HTTP GET request with rate limiting and retry logic.
        """
        limiter = self.rate_limiter_manager.get_limiter(category or self.default_limiter_category)
        for attempt in range(retries):
            with limiter:
                try:
                    response = requests.get(url, params=params)
                    if response.status_code == 429:  # Too Many Requests
                        self.logger.warning(
                            f"Rate limit hit (429). Retrying... Attempt {attempt + 1}/{retries}"
                        )
                        if attempt < retries - 1:
                            retry_after = int(response.headers.get("Retry-After", 1))
                            time.sleep(retry_after)
                            continue

                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    self.logger.error(
                        f"HTTP Request failed on attempt {attempt + 1}: {e}"
                    )
                    if attempt < retries - 1:
                        time.sleep(backoff_factor * (2**attempt))
                    else:
                        raise e
        return {}

    async def _make_async_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """
        Makes an asynchronous HTTP GET request within a session, with rate limiting and retry logic.
        """
        limiter = self.rate_limiter_manager.get_limiter(category or self.default_limiter_category)
        for attempt in range(retries):
            async with limiter:
                try:
                    async with session.get(url, params=params) as response:
                        if response.status == 429:
                            self.logger.warning(
                                f"Async rate limit hit (429). Retrying... Attempt {attempt + 1}/{retries}"
                            )
                            if attempt < retries - 1:
                                retry_after = int(
                                    response.headers.get("Retry-After", 1)
                                )
                                await asyncio.sleep(retry_after)
                                continue

                        response.raise_for_status()
                        return await response.json()
                except aiohttp.ClientError as e:
                    self.logger.error(
                        f"Async HTTP Request failed on attempt {attempt + 1}: {e}"
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff_factor * (2**attempt))
                    else:
                        raise e
        return None

    async def _fetch_all_async_data(
        self,
        requests_with_keys: List[Tuple[str, str, Optional[Dict[str, Any]]]],
    ) -> Dict[str, Any]:
        """
        A generic asynchronous fetcher for multiple requests.
        """
        results = {}

        async with aiohttp.ClientSession() as session:

            async def fetch_request(url: str, params: Optional[Dict[str, Any]]):
                return await self._make_async_request(session, url, params=params)

            tasks = [
                fetch_request(url, params) for _, url, params in requests_with_keys
            ]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            for request_info, data in zip(requests_with_keys, results_list):
                key, url, _ = request_info
                if isinstance(data, Exception):
                    self.logger.error(
                        f"Error fetching data for {key} from {url}: {data}"
                    )
                    self.logger.warning(f"Failed to fetch data for {key}: {data}")
                    continue
                if data is not None:
                    results[key] = data
        return results

    def fetch_all_async_data(
        self,
        requests_with_keys: List[Tuple[str, str, Optional[Dict[str, Any]]]],
    ) -> Dict[str, Any]:
        """
        Runs the generic asynchronous fetcher.
        """
        return asyncio.run(self._fetch_all_async_data(requests_with_keys))

    @abstractmethod
    def get_listed_assets(self) -> List[Dict[str, Any]]:
        """
        Fetch a list of all available assets from the API.
        Returns:
            A list of dictionaries containing asset metadata (id, symbol, name, etc.).
        """
        pass

    @abstractmethod
    def get_historical_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch historical price/market data for the given assets.
        Args:
            asset_ids: List of asset identifiers.
            kwargs: Additional parameters for the request (e.g., date ranges).
        Returns:
            Dictionary keyed by asset id, with historical data.
        """
        pass

    @abstractmethod
    def get_market_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch detailed market data for the given assets (market cap, volume, etc.).
        Args:
            asset_ids: List of asset identifiers.
            kwargs: Additional request params.
        Returns:
            Dictionary keyed by asset id, with market data.
        """
        pass

    @abstractmethod
    def get_latest_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch the latest ticker/price data for the given assets.
        Args:
            asset_ids: List of asset identifiers.
        Returns:
            Dictionary keyed by asset id, with latest prices.
        """
        pass

    @abstractmethod
    def run_extraction(self):
        """
        Main method that coordinates extraction from the API.
        Should internally call other methods as needed and prepare data for transformation/loading.
        """
        pass
