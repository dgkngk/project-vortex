from typing import List, Optional
import pandas as pd
from backend.etl.maintenance.TickerMapper import TickerMapper

class UniverseBuilder:
    """
    Constructs the tradeable universe for a given date, handling survivorship bias.
    """
    
    def __init__(self, ticker_mapper: Optional[TickerMapper] = None):
        self.ticker_mapper = ticker_mapper or TickerMapper()

    def get_universe(self, date: pd.Timestamp, asset_class: str = "crypto") -> List[str]:
        """
        Returns the list of valid, tradeable tickers for the given date and asset class.
        
        In a real implementation, this would query a Reference Data master (e.g., Postgres table 
        containing listing status per date).
        
        For now, this is a mock implementation returning a static universe for testing/PoC.
        """
        # Mock universe
        if asset_class == "crypto":
            # For POC, just returning major pairs.
            # In future, we verify if they were listed on 'date'.
            return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            
        return []
