from typing import Any, Dict

import pandas as pd

from backend.core.VortexLogger import VortexLogger
from backend.etl.transformers.BaseTransformer import BaseTransformer


class BinanceHDTransformer(BaseTransformer):
    """
    Transforms raw Binance historical k-line data into a structured pandas DataFrame.
    """

    def __init__(self, raw_data: Dict[str, Any], **kwargs):
        super().__init__(raw_data)
        self.logger = VortexLogger(name=self.__class__.__name__, level="DEBUG")

    def transform(self) -> Dict[str, pd.DataFrame]:
        """
        Transforms the raw k-line data for multiple assets into a dictionary of pandas DataFrames.

        The raw_data is expected to be a dictionary where keys are asset symbols (e.g., 'BTCUSDT')
        and values are lists of k-line data from the Binance API.

        Each k-line is a list with the following structure:
        [
            1499040000000,      // Kline open time
            "0.01634790",       // Open price
            "0.80000000",       // High price
            "0.01575800",       // Low price
            "0.01577100",       // Close price
            "148976.11427815",  // Volume
            ...
        ]

        Returns:
            A dictionary where keys are asset symbols and values are pandas DataFrames
            with columns: 'timestamp', 'open', 'high', 'low', 'close', 'volume'.
        """
        transformed_data = {}
        if not isinstance(self.raw_data, dict):
            return transformed_data

        for asset_id, klines in self.raw_data.items():
            if not klines or not isinstance(klines, list):
                continue

            try:
                df = pd.DataFrame(klines)
                df = self._structure_dataframe(df)
                if not df.empty:
                    transformed_data[asset_id] = df
            except Exception as e:
                self.logger.exception(
                    f"Error transforming data for asset {asset_id}: {e}"
                )
                continue

        return transformed_data

    def _structure_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Structures the raw DataFrame from Binance API into the desired format.
        """
        if df.empty or df.shape[1] < 6:
            return pd.DataFrame()

        # We only need the first 6 columns as per the requirement
        df = df.iloc[:, :6]
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]

        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Set timestamp as index
        df.set_index("timestamp", inplace=True)

        # Convert data types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])

        return df
