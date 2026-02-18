import pandas as pd
import numpy as np
from backend.scitus.backtest.slippage.BaseSlippage import BaseSlippage

class VolumeWeightedSlippage(BaseSlippage):
    """
    Slippage scales with trade size relative to market volume.
    Model: slippage = base_slippage * sqrt(trade_size / volume)
    """

    def __init__(self, base_slippage: float = 0.0005):
        self.base_slippage = base_slippage

    def calculate(self, trades: pd.Series, volume: pd.Series, close: pd.Series) -> pd.Series:
        # Avoid division by zero
        safe_volume = volume.replace(0, np.nan)
        
        # Impact factor: sqrt(trade_units / volume_units)
        # Note: 'trades' is units, 'volume' is units.
        # Compute impact only where volume is valid to avoid dividing by zero/NaN.
        impact = pd.Series(0.0, index=trades.index)
        valid_mask = safe_volume.notna() & (safe_volume > 0) & trades.notna()
        impact.loc[valid_mask] = np.sqrt(trades.loc[valid_mask] / safe_volume.loc[valid_mask])
        
        # Slippage Rate = Base * Impact
        slippage_rate = self.base_slippage * impact
        
        # Cost = Trade Value * Slippage Rate
        return (trades * close) * slippage_rate
