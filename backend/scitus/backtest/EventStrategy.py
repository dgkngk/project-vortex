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
    def on_bar(self, history: pd.DataFrame, portfolio: Portfolio) -> Optional[Order]:
        """
        Called once per bar during the event loop.

        Args:
            history: DataFrame of all bars seen so far (up to and including
                     current bar). The strategy must NOT access future data.
            portfolio: Current portfolio state (cash, positions, equity).

        Returns:
            An Order to submit, or None to do nothing this bar.
        """
        pass

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """Not used in event-driven mode."""
        raise NotImplementedError("EventStrategy uses on_bar(), not generate_signal()")
