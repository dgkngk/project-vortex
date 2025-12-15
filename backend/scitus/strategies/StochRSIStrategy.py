import numpy as np
import pandas as pd

from backend.core.enums.SignalTypes import SignalTypes
from backend.scitus.BaseStrategy import BaseStrategy


class StochRSIStrategy(BaseStrategy):
    """
    Generates trading signals based on the Stochastic RSI indicator.
    """

    def __init__(self, config: dict):
        """
        Initializes the StochRSIStrategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy.
                    - k_col: Name of the %K line column.
                    - d_col: Name of the %D line column.
                    - overbought_threshold: Threshold for overbought condition.
                    - oversold_threshold: Threshold for oversold condition.
        """
        super().__init__(config)
        self.k_col = self.config.get("k_col", "STOCHRSIk_14_14_3_3")
        self.d_col = self.config.get("d_col", "STOCHRSId_14_14_3_3")
        self.overbought_threshold = self.config.get("overbought_threshold", 80)
        self.oversold_threshold = self.config.get("oversold_threshold", 20)

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given market data.

        Args:
            data: A pandas DataFrame containing market data with StochRSI values.

        Returns:
            A pandas DataFrame with the calculated trading signals in a 'signal' column.
        """
        df = data.copy()

        k = df[self.k_col]
        d = df[self.d_col]

        # Valuation signal
        conditions_valuation = [
            (k < self.oversold_threshold) & (d < self.oversold_threshold),
            (k > self.overbought_threshold) & (d > self.overbought_threshold),
        ]
        choices_valuation = [
            SignalTypes.UNDERPRICED.value,
            SignalTypes.OVERPRICED.value,
        ]
        valuation_signal = np.select(
            conditions_valuation, choices_valuation, default=SignalTypes.HOLD.value
        )

        # Trend signal
        trend_signal = np.where(
            k >= d, SignalTypes.BUY.value, SignalTypes.SELL.value
        )

        # Combine signals
        combined_signal = valuation_signal + trend_signal

        # Clip to range of enum values
        df["signal"] = np.clip(
            combined_signal,
            SignalTypes.OVERPRICED.value,
            SignalTypes.UNDERPRICED.value,
        )

        return df
