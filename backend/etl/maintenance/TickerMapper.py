from typing import Dict, Optional, cast, Union
import pandas as pd

class TickerMapper:
    """
    Maintains a mapping of ticker changes (renames, migrations).
    Resolution is point-in-time: what was the ticker for this asset ON this date?
    """
    
    def __init__(self):
        # Mappings: LEND -> AAVE on 2020-10-02.
        # input: "LEND", date < 2020-10-02 -> "LEND"
        # input: "LEND", date > 2020-10-02 -> "AAVE" (The mapping knows LEND became AAVE)
        pass
        
        self.mappings: Dict[str, Dict] = {
            "LEND": {"new_ticker": "AAVE", "date": pd.Timestamp("2020-10-02")},
            "MATIC": {"new_ticker": "POL", "date": pd.Timestamp("2024-09-01")}
        }

    def resolve(self, ticker: str, date: Union[str, pd.Timestamp]) -> str:
        """
        Resolves the ticker symbol for a given date.
        If the ticker was renamed, returns the NEW name if date >= rename_date.
        
        Wait, if I ask for "LEND" in 2024, it should tell me "AAVE"?
        The test says:
        resolve("LEND", "2020-10-03") == "AAVE"
        
        This implies forward resolution.
        """
        if isinstance(date, str):
            date = cast(pd.Timestamp, pd.Timestamp(date))
            
        if ticker in self.mappings:
            mapping = self.mappings[ticker]
            if date >= mapping["date"]:
                return mapping["new_ticker"]
                
        return ticker
