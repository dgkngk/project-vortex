import pandas as pd
from backend.scitus.backtest.slippage.BaseSlippage import BaseSlippage

class FixedSlippage(BaseSlippage):
    """
    Constant percentage slippage per trade.
    Example: 0.05% slippage on every trade value.
    """

    def __init__(self, slippage_pct: float = 0.0005):
        self.slippage_pct = slippage_pct

    def calculate(self, trades: pd.Series, volume: pd.Series, close: pd.Series) -> pd.Series:
        # Slippage = Trade Value * Percentage
        return (trades * close) * self.slippage_pct
