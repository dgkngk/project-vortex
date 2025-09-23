import requests
import asyncio 
import aiohttp
import json

from typing import List, Dict, Any
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.core.Config import AppConfig
from backend.core.VortexLogger import VortexLogger
from backend.core.enums.ExchangeEnums import Exchange
from backend.core.enums.BinanceEnums import SymbolStatus, AccountPermissions
from backend.core.enums.AssetEnums import DataIntervals


class BinanceExtractor(BaseExtractor):
    """
    Extractor implementation for Binance API.
    """

    def __init__(self):
        self.config = AppConfig()
        self.logger = VortexLogger(name="BinanceExtractor", level="INFO")

        super().__init__(
            api_base_url="https://api.binance.com",
            target_table_name="binance_market_data",
            historical_data_target_table_name="binance_historical_data"
        )

        self.api_key = self.config.binance_api_key
        self.api_secret = self.config.binance_api_secret
        self.exchange = Exchange.BINANCE.value
        self.async_loop = asyncio.get_event_loop()
        self.async_session = aiohttp.ClientSession(loop=self.async_loop)

    def get_listed_assets(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.api_base_url}/api/v3/exchangeInfo"
            resp = requests.get(url)
            resp.raise_for_status()
            data = []

            for symbol_data in resp.json().get("symbols", []):
                if (
                    symbol_data["status"] == SymbolStatus.TRADING.value and
                    symbol_data["isSpotTradingAllowed"]
                    ):
                    data.append({
                        "id": symbol_data["symbol"],
                        "name": symbol_data["symbol"],
                        "type": "crypto",
                        "exchange": "Binance",
                        "base_asset": symbol_data["baseAsset"],
                        "quote_asset": symbol_data["quoteAsset"],
                        
                    })

            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed assets: {e}")
            return []

    def get_all_exchange_info(self) -> Dict[str, Any]:
        try:
            url = f"{self.api_base_url}/api/v3/exchangeInfo"
            resp = requests.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.exception(f"Error fetching exchange info: {e}")
            return {}

    def get_historical_data_for_assets(self, asset_ids: List[str], interval="1d", limit=100, **kwargs) -> Dict[str, Any]:
        results = {}
        for symbol in asset_ids:
            url = f"{self.api_base_url}/api/v3/klines"
            try:
                params = {"symbol": symbol, "interval": interval, "limit": limit}
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                results[symbol] = resp.json()
            except Exception as e:
                self.logger.exception(f"Error fetching historical data for {symbol}: {e}")
        return results

    def get_latest_market_data_for_all_assets_24hr(self, **kwargs) -> Dict[str, Any]:
        result = {}
        url = f"{self.api_base_url}/api/v3/ticker/24hr"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            self.logger.exception(f"Error fetching latest market data: {e}")
        return result
    
    def get_market_data_for_assets(self, asset_ids: List[str], windowSize: DataIntervals = DataIntervals.ONE_DAY, **kwargs) -> Dict[str, Any]:
        """ OHLC single window for given assets and windowsSize. Weight is 4 per asset_id. Max len(asset_ids)=100"""
        result = {}
        url = f"{self.api_base_url}/api/v3/ticker"
        
        try:
            params = {"symbols":json.dumps(asset_ids).replace(" ", ""), "windowSize":windowSize.value}
            resp = requests.get(url, params)
            resp.raise_for_status()
            result = {a["symbol"]: a for a in resp.json()}
        except Exception as e:
            self.logger.exception(f"Error fetching latest market data for {asset_ids}: {e}")

        return result

    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/price" 
            params = {"symbols":json.dumps(asset_ids).replace(" ", "")}
            resp = requests.get(url, params)
            resp.raise_for_status()
            result = {a["symbol"]: a["price"] for a in resp.json()}
        except Exception as e:
            self.logger.exception(f"Error fetching latest prices: {e}")
        return result
    
    def get_all_ticker_price(self, **kwargs) -> Dict[str, Any]:
        result = {}
        try:
            url = f"{self.api_base_url}/api/v3/ticker/price" 
            resp = requests.get(url)
            resp.raise_for_status()
            json_list = resp.json()
            result = {a["symbol"]:a["price"] for a in json_list}
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
