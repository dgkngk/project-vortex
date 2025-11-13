from typing import Any, Dict, List, Optional

from backend.core.Config import AppConfig
from backend.core.VortexLogger import VortexLogger
from backend.etl.extractors.BaseExtractor import BaseExtractor


class CoinGeckoExtractor(BaseExtractor):
    def __init__(self):
        self.config = AppConfig()
        # Rate limit is 30 req per min, 10000 per month
        rate_limit_configs = {"default": {"requests_per_hour": 14}}
        super().__init__(
            api_base_url="https://api.coingecko.com/api/v3",
            rate_limit_configs=rate_limit_configs,
            logger=VortexLogger("CoinGecko Extractor", "INFO"),
        )

        self.key_mode = self.config.coingecko_key_mode
        self.api_key = self.config.coingecko_api_key

    def _prepare_params(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if params is None:
            params = {}
        if self.api_key:
            key_name = (
                "x_cg_pro_api_key" if self.key_mode == "pro" else "x_cg_demo_api_key"
            )
            params[key_name] = self.api_key
        return params

    def get_listed_assets(self) -> List[Dict[str, Any]]:
        url = f"{self.api_base_url}/coins/list"
        params = self._prepare_params()
        sync_result = []
        try:
            response_data = self._make_sync_request(url, params=params)
            for data in response_data:
                one_result = {}
                one_result[data["id"]] = data
                sync_result.append(one_result)
            return sync_result
        except Exception as e:
            self.logger.exception(f"Error fetching listed assets: {e}")
            return []

    def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        url = f"{self.api_base_url}/coins/{asset_id}"
        params = self._prepare_params()
        try:
            response_data = self._make_sync_request(url, params=params)
            return response_data
        except Exception as e:
            self.logger.exception(f"Error fetching asset details for {asset_id}: {e}")
            return {}

    def get_historical_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        vs_currency = kwargs.get("vs_currency", "usd")
        days = kwargs.get("days", 30)
        interval = kwargs.get("interval")

        requests_with_keys = []
        for asset_id in asset_ids:
            url = f"{self.api_base_url}/coins/{asset_id}/market_chart"
            params = {"vs_currency": vs_currency, "days": str(days)}
            if interval:
                params["interval"] = interval

            params = self._prepare_params(params)
            requests_with_keys.append((asset_id, url, params))

        try:
            return self.fetch_all_async_data(requests_with_keys)
        except Exception as e:
            self.logger.exception(f"Error fetching historical data for assets: {e}")
            return {}

    def get_historical_chart_data_range(
        self, asset_ids: List[str], from_timestamp: int, to_timestamp: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Get historical market data including price, market cap, and 24hr volume
        within a given date range.

        Args:
            asset_ids: List of asset identifiers.
            from_timestamp: The start of the data range (Unix timestamp).
            to_timestamp: The end of the data range (Unix timestamp).
            kwargs: Additional request params, e.g., vs_currency.

        Returns:
            Dictionary keyed by asset id, with historical data.
        """
        vs_currency = kwargs.get("vs_currency", "usd")

        requests_with_keys = []
        for asset_id in asset_ids:
            url = f"{self.api_base_url}/coins/{asset_id}/market_chart/range"
            params = {
                "vs_currency": vs_currency,
                "from": str(from_timestamp),
                "to": str(to_timestamp),
            }
            params = self._prepare_params(params)
            requests_with_keys.append((asset_id, url, params))

        try:
            return self.fetch_all_async_data(requests_with_keys)
        except Exception as e:
            self.logger.exception(
                f"Error fetching historical chart data in range for assets: {e}"
            )
            return {}

    def get_ohlc_data_for_assets(
        self, asset_ids: List[str], days: int, **kwargs
    ) -> Dict[str, Any]:
        """
        Get OHLC data for assets.

        Args:
            asset_ids: List of asset identifiers.
            days: Data up to number of days ago. Valid values: 1, 7, 14, 30, 90, 180, 365.
            kwargs: Additional request params, e.g., vs_currency.

        Returns:
            Dictionary keyed by asset id, with OHLC data.
        """
        vs_currency = kwargs.get("vs_currency", "usd")

        valid_days = [1, 7, 14, 30, 90, 180, 365]
        if days not in valid_days:
            self.logger.error(
                f"Invalid 'days' parameter for OHLC data: {days}. Valid values are: {valid_days}"
            )
            return {}

        requests_with_keys = []
        for asset_id in asset_ids:
            url = f"{self.api_base_url}/coins/{asset_id}/ohlc"
            params = {
                "vs_currency": vs_currency,
                "days": str(days),
            }
            params = self._prepare_params(params)
            requests_with_keys.append((asset_id, url, params))

        try:
            return self.fetch_all_async_data(requests_with_keys)
        except Exception as e:
            self.logger.exception(f"Error fetching OHLC data for assets: {e}")
            return {}

    def get_market_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.api_base_url}/coins/markets"
        params = {"vs_currency": "usd", "ids": ",".join(asset_ids)}
        params.update(kwargs)
        params = self._prepare_params(params)
        try:
            response_data = self._make_sync_request(url, params=params)
            return {asset["id"]: asset for asset in response_data}
        except Exception as e:
            self.logger.exception(f"Error fetching market data for assets: {e}")
            return {}

    def get_latest_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        vs_currency = kwargs.get("vs_currency", "usd")
        url = f"{self.api_base_url}/simple/price"
        params = {
            "ids": ",".join(asset_ids),
            "vs_currencies": vs_currency,
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        }
        params.update({k: v for k, v in kwargs.items() if k not in params})
        params = self._prepare_params(params)
        try:
            return self._make_sync_request(url, params=params)
        except Exception as e:
            self.logger.exception(f"Error fetching latest data for assets: {e}")
            return {}

    def run_extraction(self):
        # Example: get latest data for top 3 coins
        self.logger.info("Running CoinGecko extraction...")
        assets = ["bitcoin", "ethereum", "solana"]
        latest_data = self.get_latest_data_for_assets(assets)
        self.logger.info(str(latest_data))
