import numpy as np
import pandas as pd

from backend.core.enums.SignalTypes import SignalTypes
from backend.scitus.BaseStrategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """
    Generates trading signals based on the MACD indicator.
    """

    def __init__(self, config: dict):
        """
        Initializes the MACDStrategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy.
                    - macd_col: Name of the MACD line column.
                    - macd_signal_col: Name of the MACD signal line column.
                    - overbought_threshold: Threshold for overbought condition.
                    - oversold_threshold: Threshold for oversold condition.
        """
        super().__init__(config)
        self.macd_col = self.config.get("macd_col", "MACD_12_26_9")
        self.macd_signal_col = self.config.get("macd_signal_col", "MACDs_12_26_9")
        self.overbought_threshold = self.config.get("overbought_threshold", 2)
        self.oversold_threshold = self.config.get("oversold_threshold", -2)

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given market data.

        Args:
            data: A pandas DataFrame containing market data with MACD values.

        Returns:
            A pandas DataFrame with the calculated trading signals in a 'signal' column.
        """
        df = data.copy()

        macd = df[self.macd_col]
        macd_s = df[self.macd_signal_col]

        # Valuation signal
        conditions_valuation = [
            (macd > self.overbought_threshold) & (macd_s > self.overbought_threshold),
            (macd < self.oversold_threshold) & (macd_s < self.oversold_threshold),
        ]
        choices_valuation = [
            SignalTypes.OVERPRICED.value,
            SignalTypes.UNDERPRICED.value,
        ]
        valuation_signal = np.select(
            conditions_valuation, choices_valuation, default=SignalTypes.NEUTRAL.value
        )

        # Trend signal
        trend_signal = np.where(
            macd >= macd_s, SignalTypes.BULLISH.value, SignalTypes.BEARISH.value
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
