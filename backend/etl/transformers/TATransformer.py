import asyncio
from typing import Dict, List

import pandas as pd
import pandas_ta as ta

from backend.core.enums.TAStudies import TAStudies
from backend.core.VortexLogger import VortexLogger
from backend.etl.transformers.BaseTransformer import BaseTransformer


class TATransformer(BaseTransformer):
    """
    Calculates technical analysis indicators on OHLCV dataframes using pandas-ta studies.
    It takes a dictionary of dataframes and applies a list of TAStudies concurrently.
    """

    def __init__(self, raw_data: Dict[str, pd.DataFrame], studies: List[TAStudies]):
        """
        Initializes the TATransformer.

        Args:
            raw_data: A dictionary of pandas DataFrames from a transformer like
                      BinanceHDTransformer, where keys are asset IDs and values
                      are OHLCV DataFrames.
            studies: A list of TAStudies enums to be calculated.
        """
        super().__init__(raw_data)
        self.studies = studies
        self.logger = VortexLogger(name=self.__class__.__name__, level="DEBUG")

        ta_configs = [study.value for study in self.studies]
        self.study = ta.Study(
            name="Vortex TA Study", ta=ta_configs, cores=0
        )  # faster without multiproc

    def _calculate_indicators_for_asset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Synchronous function to calculate all specified indicators for a single asset's DataFrame
        using a pandas-ta Study.
        This function is designed to be run in a separate thread or process.

        Args:
            df: The OHLCV DataFrame for a single asset.

        Returns:
            A new DataFrame containing the calculated indicator columns and the 'close' column.
            Returns an empty DataFrame if the study application fails.
        """
        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame()

        original_columns = set(df.columns)
        df_copy = df.copy()

        try:
            # Apply the study. This appends indicators to df_copy in-place.
            df_copy.ta.study(self.study)
        except Exception as e:
            self.logger.exception(f"Error applying TA study for one asset: {e}")
            return pd.DataFrame()

        new_columns = list(set(df_copy.columns) - original_columns)

        columns_to_return = new_columns
        if "close" in df_copy.columns:
            if "close" not in columns_to_return:
                columns_to_return.append("close")

        # Handle case where study did not add any new columns
        if not new_columns:
            if "close" in df_copy.columns:
                return df_copy[["close"]].copy()
            else:
                return pd.DataFrame()

        return df_copy[columns_to_return]

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
        Transforms the OHLCV data by calculating and adding technical indicators via studies.
        This is the main entry point, which orchestrates the async execution.

        Returns:
            A dictionary where keys are asset IDs and values are DataFrames
            containing the calculated indicators and the 'close' column.
        """
        if not self.raw_data or not self.studies:
            return {}

        # Run the async orchestrator and return the results
        return asyncio.run(self._run_async_calculations())
