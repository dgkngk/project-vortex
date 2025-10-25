import asyncio
import aiohttp
import json

from typing import List, Dict, Any
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.core.Config import AppConfig
from backend.core.VortexLogger import VortexLogger
from backend.core.enums.ExchangeEnums import Exchange
from backend.core.enums.BinanceEnums import SymbolStatus
from backend.core.enums.AssetEnums import DataIntervals


class BinanceExtractor(BaseExtractor):
    """
    Extractor implementation for Binance API.
    """

    def __init__(self):
        self.config = AppConfig()
        self.logger = VortexLogger(name="BinanceExtractor", level="INFO")

        # Binance API rate limits: 1200 requests per minute.
        rate_limit_configs = {"default": {"requests_per_minute": 1200}}

        super().__init__(
            api_base_url="https://api.binance.com",
            target_table_name="binance_market_data",
            historical_data_target_table_name="binance_historical_data",
            rate_limit_configs=rate_limit_configs,
            logger=self.logger,
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
        results = {}

        async def fetch_all():
            async with aiohttp.ClientSession() as session:

                async def fetch_klines(symbol):
                    url = f"{self.api_base_url}/api/v3/klines"
                    try:
                        params = {
                            "symbol": symbol,
                            "interval": interval.value,
                            "limit": limit,
                        }
                        data = await self._make_async_request(
                            session, url, params=params
                        )
                        return symbol, data
                    except Exception as e:
                        self.logger.exception(
                            f"Error fetching historical data for {symbol}: {e}"
                        )
                        return symbol, None

                tasks = [fetch_klines(symbol) for symbol in asset_ids]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)

                for symbol, data in zip(asset_ids, results_list):
                    if isinstance(data, Exception):
                        self.logger.warning(
                            f"Failed to fetch klines for {symbol}: {data}"
                        )
                        continue
                    if data is not None:
                        results[symbol] = data
                return results

        return asyncio.run(fetch_all())

    def get_trades(self, asset_ids: List[str], limit=500, **kwargs) -> Dict[str, Any]:
        results = {}

        async def fetch_all():
            async with aiohttp.ClientSession() as session:

                async def fetch_klines(symbol):
                    url = f"{self.api_base_url}/api/v3/trades"
                    try:
                        params = {"symbol": symbol, "limit": limit}
                        data = await self._make_async_request(
                            session, url, params=params
                        )
                        return symbol, data
                    except Exception as e:
                        self.logger.exception(
                            f"Error fetching trades data for {symbol}: {e}"
                        )
                        return symbol, None

                tasks = [fetch_klines(symbol) for symbol in asset_ids]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)

                for symbol, data in zip(asset_ids, results_list):
                    if isinstance(data, Exception):
                        self.logger.warning(
                            f"Failed to fetch trades for {symbol}: {data}"
                        )
                        continue
                    if data is not None:
                        results[symbol] = data
                return results

        return asyncio.run(fetch_all())

    def get_order_book(
        self, asset_ids: List[str], limit=100, **kwargs
    ) -> Dict[str, Any]:
        results = {}

        async def fetch_all():
            async with aiohttp.ClientSession() as session:

                async def fetch_request(symbol):
                    url = f"{self.api_base_url}/api/v3/depth"
                    try:
                        params = {"symbol": symbol, "limit": limit}
                        data = await self._make_async_request(
                            session, url, params=params
                        )
                        return symbol, data
                    except Exception as e:
                        self.logger.exception(
                            f"Error fetching order book data for {symbol}: {e}"
                        )
                        return symbol, None

                tasks = [fetch_request(symbol) for symbol in asset_ids]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)

                for symbol, data in zip(asset_ids, results_list):
                    if isinstance(data, Exception):
                        self.logger.warning(
                            f"Failed to fetch book data for {symbol}: {data}"
                        )
                        continue
                    if data is not None:
                        results[symbol] = data
                return results

        return asyncio.run(fetch_all())

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
        window_size: DataIntervals = DataIntervals.ONE_DAY,
        **kwargs,
    ) -> Dict[str, Any]:
        """OHLC single window for given assets and window_size. Weight is 4 per asset_id. Max len(asset_ids)=100"""
        result = {}
        url = f"{self.api_base_url}/api/v3/ticker"

        try:
            params = {
                "symbols": json.dumps(asset_ids).replace(" ", ""),
                "window_size": window_size.value,
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

        asset_ids = [a["symbol"] for a in assets[:5]]  # Limit for demo
        latest_data = self.get_latest_data_for_assets(asset_ids)
        self.logger.info(f"Extracted latest data for {len(asset_ids)} assets.")
        self.logger.info(f"{latest_data}")
