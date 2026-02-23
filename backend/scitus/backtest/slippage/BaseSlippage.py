import pandas as pd
from abc import ABC, abstractmethod

class BaseSlippage(ABC):
    """Abstract base class for slippage models."""

    @abstractmethod
    def calculate(self, trades: pd.Series, volume: pd.Series, close: pd.Series) -> pd.Series:
        """
        Calculate slippage cost per bar.

        Args:
            trades: Series of trade sizes (absolute units).
            volume: Series of market volume.
            close: Series of close prices.

        Returns:
            Series of slippage cost in quote currency (e.g., USDT).
        """
        pass

    def calculate_single(self, trade_qty: float, volume: float, price: float) -> float:
        """
        Calculate slippage cost for a single order.
        Default: wraps inputs into 1-element Series and delegates to calculate().
        Subclasses may override for efficiency.
        """
        idx = pd.RangeIndex(1)
        trades_s = pd.Series([trade_qty], index=idx)
        volume_s = pd.Series([volume], index=idx)
        close_s = pd.Series([price], index=idx)
        return float(self.calculate(trades_s, volume_s, close_s).iloc[0])

