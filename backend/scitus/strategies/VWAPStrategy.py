import numpy as np
import pandas as pd

from backend.core.enums.SignalTypes import SignalTypes
from backend.scitus.BaseStrategy import BaseStrategy


class VWAPStrategy(BaseStrategy):
    """
    Generates trading signals based on the Volume Weighted Average Price (VWAP).
    """

    def __init__(self, config: dict):
        """
        Initializes the VWAPStrategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy.
                    - close_col: Name of the close price column.
                    - vwap_col: Name of the VWAP column.
                    - proximity_factor: Proximity factor for determining overbought/oversold.
        """
        super().__init__(config)
        self.close_col = self.config.get("close_col", "close")
        self.vwap_col = self.config.get("vwap_col", "VWAP_D")
        # Proximity factor as a percentage of the close price
        self.proximity_factor = self.config.get("proximity_factor", 0.01)

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given market data.

        Args:
            data: A pandas DataFrame containing market data with VWAP.

        Returns:
            A pandas DataFrame with the calculated trading signals in a 'signal' column.
        """
        df = data.copy()

        close = df[self.close_col]
        vwap = df[self.vwap_col]

        # Using a proximity factor relative to price is more robust.
        proximity_value = close * self.proximity_factor * 1.5

        # Trend signal
        is_bullish = vwap >= close
        trend_signal = np.where(
            is_bullish, SignalTypes.BUY.value, SignalTypes.SELL.value
        )

        # Valuation signal
        is_far = abs(vwap - close) > proximity_value
        conditions_valuation = [
            is_bullish & is_far,  # bullish and far -> underpriced
            ~is_bullish & is_far,  # bearish and far -> overpriced
        ]
        choices_valuation = [
            SignalTypes.UNDERPRICED.value,
            SignalTypes.OVERPRICED.value,
        ]
        valuation_signal = np.select(
            conditions_valuation, choices_valuation, default=SignalTypes.HOLD.value
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
