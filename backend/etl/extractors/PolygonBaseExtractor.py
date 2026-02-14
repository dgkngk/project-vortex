import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from massive import RESTClient

from backend.core.Config import AppConfig
from backend.core.enums.AssetEnums import DataIntervals
from backend.core.VortexLogger import VortexLogger
from backend.etl.extractors.BaseExtractor import BaseExtractor


class PolygonBaseExtractor(BaseExtractor):
    """
    Base class for Polygon.io extractors using the Massive library.
    """

    INTERVAL_MAP = {
        DataIntervals.ONE_MINUTE: (1, "minute"),
        DataIntervals.FIVE_MINUTE: (5, "minute"),
        DataIntervals.TEN_MINUTE: (10, "minute"),
        DataIntervals.FIFTEEN_MINUTE: (15, "minute"),
        DataIntervals.THIRTY_MINUTE: (30, "minute"),
        DataIntervals.ONE_HOUR: (1, "hour"),
        DataIntervals.ONE_DAY: (1, "day"),
        DataIntervals.ONE_WEEK: (1, "week"),
        DataIntervals.ONE_MONTH: (1, "month"),
    }

    def __init__(self, **kwargs):
        self.config = AppConfig()
        self.api_key = self.config.polygon_api_key or os.getenv("MASSIVE_API_KEY")

        if not self.api_key:
            VortexLogger(name=self.__class__.__name__).warning(
                "Polygon API key not found in config or environment."
            )

        self.client = RESTClient(api_key=self.api_key)
        self.market_type = None  # To be set by subclasses

        super().__init__(
            api_base_url="https://api.massive.com",
            # Default rate limit for free tier
            rate_limit_configs={"default": {"requests_per_minute": 5}},
            logger=VortexLogger(name=self.__class__.__name__, level="INFO"),
            **kwargs,
        )

    def _map_interval(self, interval: DataIntervals):
        return self.INTERVAL_MAP.get(interval, (1, "day"))

    def _fetch_paged_tickers(self, market: str, active: bool, total_limit: int, **kwargs) -> List[Dict[str, Any]]:
        """
        Helper to fetch tickers with manual pagination and rate limiting.
        """
        assets = []
        url = f"{self.api_base_url}/v3/reference/tickers"
        params = {
            "market": market,
            "active": str(active).lower(),
            "apiKey": self.api_key
        }
        params.update(kwargs)
        
        # Set page size. Max is usually 1000.
        params["limit"] = min(total_limit, 1000)

        while len(assets) < total_limit:
            try:
                response = self._make_sync_request(url, params=params)
                
                results = response.get("results", [])
                assets.extend(results)
                
                if len(assets) >= total_limit:
                    break

                if response.get("next_url"):
                    url = response["next_url"]
                    
                    # Security check for SSRF
                    if not url.startswith(self.api_base_url):
                        self.logger.error(f"Potential SSRF detected. Refusing to follow next_url: {url}")
                        break

                    params = {}
                    if "apiKey" not in url and self.api_key:
                        params["apiKey"] = self.api_key
                else:
                    break

            except Exception as e:
                self.logger.exception(f"Error fetching listed assets from Polygon: {e}")
                break
        
        return assets[:total_limit]

    def get_historical_data_for_assets(
        self,
        asset_ids: List[str],
        interval: DataIntervals = DataIntervals.ONE_DAY,
        from_date: Optional[Union[str, datetime]] = None,
        to_date: Optional[Union[str, datetime]] = None,
        limit: int = 5000,
        **kwargs,
    ) -> Dict[str, Any]:
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")

        multiplier, timespan = self._map_interval(interval)
        
        results = {}
        for asset_id in asset_ids:
            try:
                with self.rate_limiter_manager.get_limiter("default"):
                    aggs = self.client.get_aggs(
                        ticker=asset_id,
                        multiplier=multiplier,
                        timespan=timespan,
                        from_=from_date,
                        to=to_date,
                        limit=limit,
                        **kwargs
                    )
                results[asset_id] = [vars(a) for a in aggs] if aggs else []
            except Exception as e:
                self.logger.error(f"Error fetching historical data for {asset_id}: {e}")
                results[asset_id] = []
        
        return results

    def get_market_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        results = {}
        for asset_id in asset_ids:
            try:
                with self.rate_limiter_manager.get_limiter("default"):
                    prev_close = self.client.get_previous_close_agg(ticker=asset_id)
                results[asset_id] = [vars(a) for a in prev_close] if prev_close else []
            except Exception as e:
                self.logger.error(f"Error fetching market data for {asset_id}: {e}")
                results[asset_id] = []
        return results

    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        results = {}
        if not self.market_type:
             self.logger.warning("market_type not set in extractor. Skipping get_latest_data_for_assets.")
             return results

        try:
            with self.rate_limiter_manager.get_limiter("default"):
                snapshot = self.client.get_snapshot_all(
                    market_type=self.market_type, 
                    tickers=",".join(asset_ids) if asset_ids else None
                )
            for s in snapshot:
                results[s.ticker] = vars(s)
        except Exception as e:
            self.logger.error(f"Error fetching latest {self.market_type} data for assets: {e}")
        return results
