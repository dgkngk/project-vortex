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

    def get_listed_assets(self, market: str = "stocks", active: bool = True, limit: int = 1000, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch a list of available tickers for the stocks market.
        """
        try:
            with self.rate_limiter_manager.get_limiter("default"):
                tickers = self.client.list_tickers(
                    market=market, active=active, limit=limit, **kwargs
                )
            data = []
            for t in tickers:
                data.append(
                    {
                        "id": t.ticker,
                        "name": t.name,
                        "type": t.type,
                        "exchange": getattr(t, "primary_exchange", "Unknown"),
                        "market": t.market,
                        "active": t.active,
                        "currency_name": getattr(t, "currency_name", "USD"),
                    }
                )
                if len(data) >= limit:
                    break
            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed assets from Polygon: {e}")
            return []

    def get_historical_data_for_assets(
        self,
        asset_ids: List[str],
        interval: DataIntervals = DataIntervals.ONE_DAY,
        from_date: Optional[Union[str, datetime]] = None,
        to_date: Optional[Union[str, datetime]] = None,
        limit: int = 5000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Fetch historical aggregate bars for given stock tickers.
        """
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
        """
        Fetch previous close as 'market data'.
        """
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
        """
        Fetch the latest price/snapshot for given assets.
        """
        results = {}
        try:
            with self.rate_limiter_manager.get_limiter("default"):
                snapshot = self.client.get_snapshot_all(
                    market_type="stocks", 
                    tickers=",".join(asset_ids) if asset_ids else None
                )
            for s in snapshot:
                results[s.ticker] = vars(s)
        except Exception as e:
            self.logger.error(f"Error fetching latest data for assets: {e}")
        return results

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