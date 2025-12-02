import numpy as np
import pandas as pd

from backend.core.enums.SignalTypes import SignalTypes
from backend.scitus.BaseStrategy import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """
    Generates trading signals based on Bollinger Bands.
    """

    def __init__(self, config: dict):
        """
        Initializes the BollingerBandsStrategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy.
                    - close_col: Name of the close price column.
                    - bbh_col: Name of the upper Bollinger Band column.
                    - bbm_col: Name of the middle Bollinger Band column.
                    - bbl_col: Name of the lower Bollinger Band column.
                    - proximity_factor: Proximity factor as a percentage of BB width.
        """
        super().__init__(config)
        self.close_col = self.config.get("close_col", "close")
        self.bbh_col = self.config.get("bbh_col", "BBH_20_2.0")
        self.bbm_col = self.config.get("bbm_col", "BBM_20_2.0")
        self.bbl_col = self.config.get("bbl_col", "BBL_20_2.0")
        # Proximity factor as a percentage of the Bollinger Band width
        self.proximity_factor = self.config.get("proximity_factor", 0.05)

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals for the given market data.

        Args:
            data: A pandas DataFrame containing market data with Bollinger Bands.

        Returns:
            A pandas DataFrame with the calculated trading signals in a 'signal' column.
        """
        df = data.copy()

        close = df[self.close_col]
        bbh = df[self.bbh_col]
        bbm = df[self.bbm_col]
        bbl = df[self.bbl_col]

        # Using a proximity factor relative to the BB width is more robust
        # than a fixed absolute value as in the original code.
        proximity_value = (bbh - bbl) * self.proximity_factor

        # Valuation signal
        conditions_valuation = [
            abs(close - bbl)
            < proximity_value,  # close is near lower band -> underpriced
            abs(bbh - close)
            < proximity_value,  # close is near upper band -> overpriced
        ]
        choices_valuation = [
            SignalTypes.UNDERPRICED.value,
            SignalTypes.OVERPRICED.value,
        ]
        valuation_signal = np.select(
            conditions_valuation, choices_valuation, default=SignalTypes.NEUTRAL.value
        )

        # Trend signal
        conditions_trend = [
            (bbh > close) & (close > bbm),
            (close > bbl) & (bbm > close),
        ]
        choices_trend = [SignalTypes.BULLISH.value, SignalTypes.BEARISH.value]
        trend_signal = np.select(
            conditions_trend, choices_trend, default=SignalTypes.NEUTRAL.value
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
