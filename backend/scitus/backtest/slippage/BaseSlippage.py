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
