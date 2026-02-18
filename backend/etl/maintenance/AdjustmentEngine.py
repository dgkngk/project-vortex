from dataclasses import dataclass
from typing import List
import pandas as pd

@dataclass
class CorporateAction:
    ticker: str
    ex_date: pd.Timestamp
    action_type: str  # 'split', 'dividend'
    ratio: float      # e.g., 2.0 for 2-for-1 split

class AdjustmentEngine:
    def adjust(self, raw_data: pd.DataFrame, actions: List[CorporateAction]) -> pd.DataFrame:
        """
        Adjusts OHLCV data for corporate actions (splits).
        
        Args:
            raw_data: DataFrame with index 'timestamp' or column 'timestamp' and OHLCV columns.
            actions: List of CorporateActions.
            
        Returns:
            Adjusted DataFrame.
        """
        if not actions:
            return raw_data.copy()
            
        df = raw_data.copy()
        
        # Ensure timestamp is available for comparison
        if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            dates = df["timestamp"]
        else:
            dates = pd.to_datetime(df.index)

        # Construct a vector of 1.0s
        factors = pd.Series(1.0, index=df.index)
        
        for action in actions:
            if action.action_type == "split":
                # Find indices strictly before ex_date
                mask = dates < action.ex_date
                # For these rows, we must divide by ratio (or multiply by 1/ratio)
                # If we have multiple splits, they compound.
                # Split 1 (2:1) on T2. Split 2 (2:1) on T4.
                # T1: Div by 2, then Div by 2? Yes. Total Div by 4.
                # T3: Div by 2 (from T4 split).
                # T5: No div.
                
                factors[mask] = factors[mask] * (1.0 / action.ratio)
                
        # Apply factors
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = df[col] * factors
                
        # Volume is usually multiplied by ratio (inverse of price adjustment)
        if "volume" in df.columns:
             # If price * (1/ratio), then volume * ratio
             # So volume * (1 / factor) ?
             # factor is (1/ratio). 1/factor is ratio.
             # Correct.
             df["volume"] = df["volume"] / factors
             
        return df
