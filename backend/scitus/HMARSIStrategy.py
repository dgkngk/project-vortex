import numpy as np
import pandas as pd
import pandas_ta as ta

from backend.core.enums.SignalTypes import SignalTypes
from backend.scitus.BaseStrategy import BaseStrategy


class HMARSIStrategy(BaseStrategy):
    """
    A dual-strategy approach using Hull Moving Average (HMA) and Relative Strength Index (RSI).
    It combines a trend-following component with a momentum component.
    """

    def __init__(self, config: dict):
        """
        Initializes the HMARSIStrategy with a given configuration.

        Args:
            config: A dictionary containing parameters for the strategy.
                    - close_col: Name of the close price column.
                    - hma_col: Name of the HMA of price column.
                    - rsi_col: Name of the RSI column.
                    - rsi_hma_period: Period for calculating HMA on RSI.
                    - rsi_buy_threshold: RSI threshold for buy signals.
                    - rsi_sell_threshold: RSI threshold for sell signals.
        """
        super().__init__(config)
        self.close_col = self.config.get("close_col", "close")
        self.hma_col = self.config.get("hma_col", "HMA_50")
        self.rsi_col = self.config.get("rsi_col", "RSI_14")
        self.rsi_hma_period = self.config.get("rsi_hma_period", 14)
        self.rsi_buy_threshold = self.config.get("rsi_buy_threshold", 40)
        self.rsi_sell_threshold = self.config.get("rsi_sell_threshold", 60)

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals based on the HMA/RSI double strategy.

        Args:
            data: A pandas DataFrame containing market data with close, HMA, and RSI.

        Returns:
            A pandas DataFrame with the calculated trading signals in a 'signal' column.
        """
        df = data.copy()

        # --- STRATEGY 2: HMA on RSI (Smoothed Momentum) ---
        # Calculate HMA of the RSI column
        df["rsi_hma"] = ta.hma(df[self.rsi_col], length=self.rsi_hma_period)

        # --- Crossover Signals for RSI and its HMA ---
        # Previous values
        rsi_prev = df[self.rsi_col].shift(1)
        rsi_hma_prev = df["rsi_hma"].shift(1)

        # Crossover conditions
        rsi_cross_above_hma = (rsi_prev < rsi_hma_prev) & (
            df[self.rsi_col] > df["rsi_hma"]
        )
        rsi_cross_below_hma = (rsi_prev > rsi_hma_prev) & (
            df[self.rsi_col] < df["rsi_hma"]
        )

        # --- STRATEGY 1: Trend Filter Logic ---
        # Long Condition: Price > HMA (Trend Up) AND RSI < 40 (Dip)
        # Short Condition: Price < HMA (Trend Down) AND RSI > 60 (Rally)

        # --- Combined Signal Logic ---
        buy_condition = (
            (df[self.close_col] > df[self.hma_col])
            & (df[self.rsi_col] < self.rsi_buy_threshold)
            & rsi_cross_above_hma
        )

        sell_condition = (
            (df[self.close_col] < df[self.hma_col])
            & (df[self.rsi_col] > self.rsi_sell_threshold)
            & rsi_cross_below_hma
        )

        conditions = [buy_condition, sell_condition]
        choices = [SignalTypes.BUY.value, SignalTypes.SELL.value]

        df["signal"] = np.select(conditions, choices, default=SignalTypes.HOLD.value)

        return df
