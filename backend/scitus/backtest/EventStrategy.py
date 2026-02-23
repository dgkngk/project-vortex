from abc import abstractmethod
from typing import Optional

import pandas as pd

from backend.scitus.BaseStrategy import BaseStrategy
from backend.scitus.backtest.execution.Order import Order
from backend.scitus.backtest.execution.Portfolio import Portfolio


class EventStrategy(BaseStrategy):
    """
    Abstract base for event-driven strategies.

    Unlike BaseStrategy.generate_signal() which processes the entire dataset
    at once, on_bar() receives one bar of history at a time and must make
    decisions using only past data.
    """

    @abstractmethod
    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        """
        Called once per bar during the event loop.
        
        Parameters:
            bar: The current bar data (Series with at least 'close' and 'volume';
                 'open', 'high', and 'low' may also be present if available).
            portfolio: Current portfolio state (cash, positions, equity).
        
        Returns:
            An Order to submit, or None to do nothing this bar.
        """
        pass

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """Not used in event-driven mode."""
        raise NotImplementedError("EventStrategy uses on_bar(), not generate_signal()")
