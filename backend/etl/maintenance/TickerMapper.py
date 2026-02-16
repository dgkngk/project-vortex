from typing import Dict, Optional, cast, Union
import pandas as pd

class TickerMapper:
    """
    Maintains a mapping of ticker changes (renames, migrations).
    Resolution is point-in-time: what was the ticker for this asset ON this date?
    """
    
    def __init__(self):
        # Format: "CANONICAL/NEW": {"start_date": "YYYY-MM-DD", "old_ticker": "OLD"} 
        # OR "OLD": {"new_ticker": "NEW", "date": "YYYY-MM-DD"} <-- This seems easier to lookup "what did LEND become?"
        
        # Let's use the format that supports "given input ticker and date, what is the correct ticker?"
        # Actually usually we want to query by the *current* canonical ticker to find its history, 
        # OR we query by the ticker as it existed then.
        
        # If I have "LEND" in my raw data, I want to map it to "AAVE" eventually? 
        # Or if I ask for "AAVE" history, I want it to fetch "LEND" for older dates?
        
        # The requirement in plan: "resolve(ticker: str, date: datetime) -> str returns the canonical ticker at that point in time."
        
        # If I pass "LEND" and "2020-01-01", it should return "LEND".
        # If I pass "LEND" and "2021-01-01" (post rename), it should probably return "AAVE"? 
        # Or does it imply "What was LEND called on 2021-01-01?" -> It didn't exist (it was AAVE).
        
        # Let's implement the logic used in the test:
        # Mappings: LEND -> AAVE on 2020-10-02.
        # input: "LEND", date < 2020-10-02 -> "LEND"
        # input: "LEND", date > 2020-10-02 -> "AAVE" (The mapping knows LEND became AAVE)
        
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
