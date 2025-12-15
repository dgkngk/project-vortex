from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.

    This class provides a template for creating trading strategies. Subclasses
    are expected to implement the `generate_signal` method, which contains
    the core logic for generating trading signals based on market data.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the strategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy,
                    such as indicator settings (e.g., moving average periods).
        """
        self.config = config

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given market data.

        This method must be implemented by any subclass. It should take a
        DataFrame with OHLCV and potentially other indicator data, and return
        a DataFrame with an added 'signal' column indicating trading
        actions (e.g., 1 for buy, -1 for sell, 0 for hold).

        Args:
            data: A pandas DataFrame containing market data.

        Returns:
            A pandas DataFrame with the calculated trading signals.
        """
        pass
