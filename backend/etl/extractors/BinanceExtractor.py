import requests
from typing import List, Dict, Any
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.core.Config import AppConfig
from backend.core.VortexLogger import VortexLogger
from backend.core.enums.ExchangeEnums import Exchange
from backend.core.enums.BinanceEnums import SymbolStatus, AccountPermissions


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
            try:
                url = f"{self.api_base_url}/api/v3/klines"
                params = {"symbol": symbol, "interval": interval, "limit": limit}
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                results[symbol] = resp.json()
            except Exception as e:
                self.logger.exception(f"Error fetching historical data for {symbol}: {e}")
        return results

    def get_market_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        results = {}
        for symbol in asset_ids:
            try:
                url = f"{self.api_base_url}/api/v3/ticker/24hr"
                params = {"symbol": symbol}
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                results[symbol] = resp.json()
            except Exception as e:
                self.logger.exception(f"Error fetching market data for {symbol}: {e}")
        return results

    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        results = {}
        for symbol in asset_ids:
            try:
                url = f"{self.api_base_url}/api/v3/ticker/price"
                params = {"symbol": symbol}
                resp = requests.get(url, params=params)
                resp.raise_for_status()
                results[symbol] = resp.json()
            except Exception as e:
                self.logger.exception(f"Error fetching latest price for {symbol}: {e}")
        return results

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
