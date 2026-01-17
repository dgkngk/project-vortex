import json
from typing import Any, Dict, List

from backend.core.Config import AppConfig
from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.BinanceEnums import SymbolStatus
from backend.core.enums.ExchangeEnums import Exchange
from backend.core.VortexLogger import VortexLogger
from backend.etl.extractors.BaseExtractor import BaseExtractor


class BinanceExtractor(BaseExtractor):
    """
    Extractor implementation for Binance API.
    """

    def __init__(self, **kwargs):
        self.config = AppConfig()

        # Binance API rate limits: 1200 requests per minute.
        rate_limit_configs = {"default": {"requests_per_minute": 1200}}

        super().__init__(
            api_base_url="https://api.binance.com",
            rate_limit_configs=rate_limit_configs,
            logger=VortexLogger(name="BinanceExtractor", level="INFO"),
            **kwargs,
        )

        self.api_key = self.config.binance_api_key
        self.api_secret = self.config.binance_api_secret
        self.exchange = Exchange.BINANCE.value

    def get_listed_assets(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.api_base_url}/api/v3/exchangeInfo"
            response_data = self._make_sync_request(url)
            data = []

            for symbol_data in response_data.get("symbols", []):
                if (
                    symbol_data["status"] == SymbolStatus.TRADING.value
                    and symbol_data["isSpotTradingAllowed"]
                ):
                    data.append(
                        {
                            "id": symbol_data["symbol"],
                            "name": symbol_data["symbol"],
                            "type": "crypto",
                            "exchange": "Binance",
                            "base_asset": symbol_data["baseAsset"],
                            "quote_asset": symbol_data["quoteAsset"],
                        }
                    )

            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed assets: {e}")
            return []

    def get_all_exchange_info(self) -> Dict[str, Any]:
        try:
            url = f"{self.api_base_url}/api/v3/exchangeInfo"
            return self._make_sync_request(url)
        except Exception as e:
            self.logger.exception(f"Error fetching exchange info: {e}")
            return {}

    def get_historical_data_for_assets(
        self,
        asset_ids: List[str],
        interval: DataIntervals = DataIntervals.ONE_DAY,
        limit=100,
        **kwargs,
    ) -> Dict[str, Any]:
        url = f"{self.api_base_url}/api/v3/klines"
        requests_with_keys = []
        for asset_id in asset_ids:
            params = {
                "symbol": asset_id,
                "interval": interval.value,
                "limit": limit,
            }
            requests_with_keys.append((asset_id, url, params))

        return self.fetch_all_async_data(requests_with_keys)

    def get_trades(self, asset_ids: List[str], limit=500, **kwargs) -> Dict[str, Any]:
        url = f"{self.api_base_url}/api/v3/trades"
        requests_with_keys = []
        for asset_id in asset_ids:
            params = {"symbol": asset_id, "limit": limit}
            requests_with_keys.append((asset_id, url, params))

        return self.fetch_all_async_data(requests_with_keys)

    def get_order_book(
        self, asset_ids: List[str], limit=100, **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.api_base_url}/api/v3/depth"
        requests_with_keys = []
        for asset_id in asset_ids:
            params = {"symbol": asset_id, "limit": limit}
            requests_with_keys.append((asset_id, url, params))

        return self.fetch_all_async_data(requests_with_keys)

    def get_order_book_ticker(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/bookTicker"
            params = {"symbols": json.dumps(asset_ids).replace(" ", "")}
            response_data = self._make_sync_request(url, params)
            result = {
                a["symbol"]: {k: v for k, v in a.items() if k != "symbol"}
                for a in response_data
            }
        except Exception as e:
            self.logger.exception(f"Error fetching latest prices: {e}")
        return result

    def get_full_order_book_ticker(self, **kwargs) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/bookTicker"
            response_data = self._make_sync_request(url)
            result = {
                a["symbol"]: {k: v for k, v in a.items() if k != "symbol"}
                for a in response_data
            }
        except Exception as e:
            self.logger.exception(f"Error fetching full order book ticker: {e}")
        return result

    def get_latest_market_data_for_all_assets_24hr(self, **kwargs) -> Dict[str, Any]:
        result = {}
        url = f"{self.api_base_url}/api/v3/ticker/24hr"
        try:
            result = self._make_sync_request(url)
        except Exception as e:
            self.logger.exception(f"Error fetching latest market data: {e}")
        return result

    def get_market_data_for_assets(
        self,
        asset_ids: List[str],
        interval: DataIntervals = DataIntervals.ONE_DAY,
        **kwargs,
    ) -> Dict[str, Any]:
        """OHLC single window for given assets and interval. Weight is 4 per asset_id. Max len(asset_ids)=100"""
        result = {}
        url = f"{self.api_base_url}/api/v3/ticker"

        try:
            params = {
                "symbols": json.dumps(asset_ids).replace(" ", ""),
                "windowSize": interval.value,
            }
            response_data = self._make_sync_request(url, params)
            result = {a["symbol"]: a for a in response_data}
        except Exception as e:
            self.logger.exception(
                f"Error fetching latest market data for {asset_ids}: {e}"
            )

        return result

    def get_latest_data_for_assets(
        self, asset_ids: List[str], **kwargs
    ) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/price"
            params = {"symbols": json.dumps(asset_ids).replace(" ", "")}
            response_data = self._make_sync_request(url, params)
            result = {a["symbol"]: a["price"] for a in response_data}
        except Exception as e:
            self.logger.exception(f"Error fetching latest prices: {e}")
        return result

    def get_all_ticker_price(self, **kwargs) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/price"
            json_list = self._make_sync_request(url)
            result = {a["symbol"]: a["price"] for a in json_list}
        except Exception as e:
            self.logger.exception(f"Error fetching latest prices: {e}")
        return result

    def run_extraction(self):
        """
        Example pipeline run: fetch listed assets and their latest data.
        """
        self.logger.info("Starting Binance extraction pipeline...")
        assets = self.get_listed_assets()
        if not assets:
            self.logger.warning("No assets retrieved from Binance.")
            return

        asset_ids = [a["id"] for a in assets[:5]]  # Limit for demo
        latest_data = self.get_latest_data_for_assets(asset_ids)
        self.logger.info(f"Extracted latest data for {len(asset_ids)} assets.")
        self.logger.info(f"{latest_data}")
        return latest_data
