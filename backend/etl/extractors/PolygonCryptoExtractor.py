from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.ExchangeEnums import Exchange
from backend.etl.extractors.PolygonBaseExtractor import PolygonBaseExtractor


class PolygonCryptoExtractor(PolygonBaseExtractor):
    """
    Extractor implementation for Polygon.io Crypto data.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exchange = Exchange.POLYGON_CRYPTO.value

    def get_listed_assets(self, market: str = "crypto", active: bool = True, limit: int = 1000, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch a list of available tickers for the crypto market.
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
                        "market": t.market,
                        "active": t.active,
                        "currency_name": getattr(t, "currency_name", "Unknown"),
                        "base_currency_symbol": getattr(t, "base_currency_symbol", None),
                    }
                )
                if len(data) >= limit:
                    break
            return data
        except Exception as e:
            self.logger.exception(f"Error fetching listed crypto assets from Polygon: {e}")
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
                self.logger.error(f"Error fetching historical crypto data for {asset_id}: {e}")
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
                self.logger.error(f"Error fetching market crypto data for {asset_id}: {e}")
                results[asset_id] = []
        return results

    def get_latest_data_for_assets(self, asset_ids: List[str], **kwargs) -> Dict[str, Any]:
        results = {}
        try:
            with self.rate_limiter_manager.get_limiter("default"):
                snapshot = self.client.get_snapshot_all(
                    market_type="crypto", 
                    tickers=",".join(asset_ids) if asset_ids else None
                )
            for s in snapshot:
                results[s.ticker] = vars(s)
        except Exception as e:
            self.logger.error(f"Error fetching latest crypto data for assets: {e}")
        return results

    def run_extraction(self):
        self.logger.info("Starting Polygon Crypto extraction pipeline...")
        assets = self.get_listed_assets(limit=10)
        if not assets:
            return
        asset_ids = [a["id"] for a in assets]
        return self.get_latest_data_for_assets(asset_ids)
