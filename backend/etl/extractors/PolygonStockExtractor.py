from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.ExchangeEnums import Exchange
from backend.etl.extractors.PolygonBaseExtractor import PolygonBaseExtractor


class PolygonStockExtractor(PolygonBaseExtractor):
    """
    Extractor implementation for Polygon.io Stock data.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exchange = Exchange.POLYGON_STOCK.value
        self.market_type = "stocks"

    def get_listed_assets(self, market: str = "stocks", active: bool = True, limit: int = 1000, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch a list of available tickers for the stocks market.
        """
        try:
            tickers = self._fetch_paged_tickers(market=market, active=active, total_limit=limit, **kwargs)
            data = []
            for t in tickers:
                data.append(
                    {
                        "id": t.get("ticker"),
                        "name": t.get("name"),
                        "type": t.get("type"),
                        "exchange": t.get("primary_exchange", "Unknown"),
                        "market": t.get("market"),
                        "active": t.get("active"),
                        "currency_name": t.get("currency_name", "USD"),
                    }
                )
            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed assets from Polygon: {e}")
            return []

    def run_extraction(self):
        """
        Basic extraction pipeline for Polygon stocks.
        """
        self.logger.info("Starting Polygon Stock extraction pipeline...")
        assets = self.get_listed_assets(limit=10)
        if not assets:
            self.logger.warning("No assets retrieved from Polygon Stocks.")
            return

        asset_ids = [a["id"] for a in assets]
        latest_data = self.get_latest_data_for_assets(asset_ids)
        self.logger.info(f"Extracted latest data for {len(latest_data)} stock tickers.")
        return latest_data
