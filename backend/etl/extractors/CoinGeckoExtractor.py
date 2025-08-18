import requests

from typing import List, Dict, Any
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.core.VortexLogger import VortexLogger


class CoinGeckoExtractor(BaseExtractor):

    def __init__(self):
        super().__init__(
            api_base_url="https://api.coingecko.com/api/v3",
            target_table_name="coingecko_market_data",
            historical_data_target_table_name="coingecko_historical_data"
        )
        self.logger = VortexLogger("CoinGecko Extractor", "DEBUG")

    def get_listed_assets(self) -> List[Dict[str, Any]]:
        url = f"{self.api_base_url}/coins/list"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_historical_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        vs_currency = kwargs.get("vs_currency", "usd")
        days = kwargs.get("days", 30)                  # default if caller omits
        interval = kwargs.get("interval")              # optional

        results: Dict[str, Any] = {}
        for asset_id in asset_ids:
            url = f"{self.api_base_url}/coins/{asset_id}/market_chart"
            params = {"vs_currency": vs_currency, "days": days}
            if interval:
                params["interval"] = interval
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            results[asset_id] = resp.json()
        return results

    def get_market_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        url = f"{self.api_base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": ",".join(asset_ids)
        }
        params.update(kwargs)
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return {asset["id"]: asset for asset in resp.json()}

    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
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
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def run_extraction(self):
        # Example: get latest data for top 3 coins
        self.logger.info("Running CoinGecko extraction...")
        assets = ["bitcoin", "ethereum", "solana"]
        latest_data = self.get_latest_data_for_assets(assets)
        self.logger.info(str(latest_data))
