import asyncio
from typing import Any, Dict, List

import pandas as pd
import pandas_ta as ta

from backend.core.VortexLogger import VortexLogger
from backend.etl.transformers.BaseTransformer import BaseTransformer


class TATransformer(BaseTransformer):
    """
    Calculates technical analysis indicators on OHLCV dataframes.
    It takes a dictionary of dataframes and applies a list of indicators
    concurrently across all of them.
    """

    def __init__(self, raw_data: Dict[str, pd.DataFrame], indicators: List[str]):
        """
        Initializes the TATransformer.

        Args:
            raw_data: A dictionary of pandas DataFrames from a transformer like
                      BinanceHDTransformer, where keys are asset IDs and values
                      are OHLCV DataFrames.
            indicators: A list of indicator names to calculate (e.g., ['rsi', 'macd']).
                      These must match the function names in pandas-ta.
        """
        super().__init__(raw_data)
        self.indicators = indicators
        self.logger = VortexLogger(name=self.__class__.__name__, level="DEBUG")

    def _calculate_indicators_for_asset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Synchronous function to calculate all specified indicators for a single asset's DataFrame.
        This function is designed to be run in a separate thread or process to avoid
        blocking while waiting for CPU-bound calculations.

        Args:
            df: The OHLCV DataFrame for a single asset.

        Returns:
            A new DataFrame containing only the calculated indicator columns.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame()

        # Keep track of original columns to return only the new ones
        original_columns = set(df.columns)
        df_copy = df.copy()

        # Dynamically find and apply each indicator function from pandas-ta
        for indicator_name in self.indicators:
            try:
                # Get the indicator function from the 'ta' accessor on the DataFrame
                indicator_func = getattr(df_copy.ta, indicator_name)
                # Calculate and append the indicator(s) to the DataFrame
                indicator_func(append=True)
            except AttributeError:
                # This allows the process to continue if an invalid indicator is requested
                self.logger.warning(
                    f"Indicator '{indicator_name}' not found in pandas-ta. Skipping."
                )
            except Exception as e:
                self.logger.exception(
                    f"Error calculating indicator '{indicator_name}': {e}. Skipping."
                )

        new_columns = list(set(df_copy.columns) - original_columns)
        return df_copy[new_columns]

    async def _run_async_calculations(self) -> Dict[str, pd.DataFrame]:
        """
        Creates and runs asynchronous tasks to calculate indicators for all assets concurrently.
        """
        loop = asyncio.get_running_loop()

        # Create a list of futures, running the CPU-bound calculation in an executor
        # to prevent blocking the event loop and achieve concurrency.
        futures = [
            loop.run_in_executor(None, self._calculate_indicators_for_asset, df)
            for df in self.raw_data.values()
        ]

        # Wait for all calculations to complete
        results = await asyncio.gather(*futures)

        # Map the results back to their corresponding asset IDs
        return dict(zip(self.raw_data.keys(), results))

    def transform(self) -> Dict[str, pd.DataFrame]:
        """
        Transforms the OHLCV data by calculating and adding technical indicators.
        This is the main entry point, which orchestrates the async execution.

        Returns:
            A dictionary where keys are asset IDs and values are DataFrames
            containing the calculated indicators.
        """
        if not self.raw_data or not self.indicators:
            return {}

        # Run the async orchestrator and return the results
        return asyncio.run(self._run_async_calculations())
