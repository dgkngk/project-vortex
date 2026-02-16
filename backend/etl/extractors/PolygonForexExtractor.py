from typing import Any, Dict, List

from backend.core.enums.ExchangeEnums import Exchange
from backend.etl.extractors.PolygonBaseExtractor import PolygonBaseExtractor


class PolygonForexExtractor(PolygonBaseExtractor):
    """
    Extractor implementation for Polygon.io Forex data.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exchange = Exchange.POLYGON_FOREX.value
        self.market_type = "forex"

    def get_listed_assets(self, market: str = "fx", active: bool = True, limit: int = 1000, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch a list of available tickers for the forex market.
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
                        "market": t.get("market"),
                        "active": t.get("active"),
                        "currency_name": t.get("currency_name", "Unknown"),
                    }
                )
            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed forex assets from Polygon: {e}")
            return []

    def run_extraction(self):
        self.logger.info("Starting Polygon Forex extraction pipeline...")
        assets = self.get_listed_assets(limit=10)
        if not assets:
            return
        asset_ids = [a["id"] for a in assets]
        return self.get_latest_data_for_assets(asset_ids)
