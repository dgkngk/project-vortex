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

        # Sort actions by date descending to apply from most recent to oldest?
        # Standard approach:
        # For backtesting, we usually want "Backward-Adjusted Data".
        # Current price is real. Past prices are adjusted down.
        # If a 2:1 split happened today (ratio 2.0), yesterday's price of 100 becomes 50.
        # So we divide pre-split prices by the ratio.
        
        cumulative_ratio = 1.0
        
        # Sort actions by date descending (newest first)
        # Actually it doesn't matter if we process them sequentially or cumulatively, 
        # but let's do it per action to be clear.
        
        # Optimization: calculate a 'factor' column.
        # Start with factor = 1.0
        # For each action: mask = dates < action.ex_date
        # factor[mask] *= action.ratio
        
        start_factor = pd.Series(1.0, index=df.index)
        
        for action in actions:
            if action.action_type == "split":
                # If 2:1 split (ratio 2.0), we divide past prices by 2.0.
                # So the adjustment factor for past prices is 1/ratio.
                # Wait, if we use the factor to MULTIPLY, then factor = 1/2.0 = 0.5.
                # Let's verify standard convention.
                # Yahoo Finance: Adjusted Close.
                # Split 2:1. Old Close 100. New Close 50.
                # To make old close comparable, we adjust 100 -> 50.
                # So we divide by the ratio.
                
                # Identify rows strictly BEFORE the ex-date
                mask = dates < action.ex_date
                
                # We need to divide prices by ratio, or multiply by (1/ratio).
                # To handle cumulative, we multiply our adjustment factor.
                # Let's say we have a factor series initialized to 1.0.
                # For rows < ex_date, factor *= (1 / ratio).
                
                # However, accessing by boolean mask on a series when index might not be aligned is tricky if not careful.
                # Let's align by index.
                
                # Assuming df index is aligned with 'dates' if we extracted it.
                # If dates is a Series from df["timestamp"], the index matches.
                
                # Let's use numpy where for speed if possible, or just pandas loc.
                
                # Apply to factor column
                # We'll build a global 'adjustment_factor' vector.
                pass

        # Let's try a simpler robust loop for now.
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
