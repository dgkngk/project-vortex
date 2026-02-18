import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.DataDestinationClient import DataDestinationClient


class ParquetWriter(DataDestinationClient):
    """
    Writes DataFrames to a local Parquet store with Hive-style partitioning.
    Structure: base_dir / asset_class / asset_id / year=YYYY / month=MM / data.parquet

    Extends DataDestinationClient so it can be used as a destination in the
    ETL loader pipeline alongside cache clients and the StorageRouter.
    """

    def __init__(self, base_dir: str = None):
        super().__init__()
        path_str = base_dir or os.getenv("VORTEX_DATA_DIR", "data/parquet")
        self.base_dir = Path(path_str)
        self.logger = VortexLogger(name="ParquetWriter")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_data(self, data: Dict[str, Any]):
        """
        Adapts the DataDestinationClient interface for Parquet writes.

        Args:
            data: A dictionary with required keys:
                - 'df': The pandas DataFrame to persist.
                - 'asset_id': The asset identifier (e.g., 'BTCUSDT').
                - 'asset_class' (optional): Defaults to 'crypto'.

        Raises:
            ValueError: If required keys 'df' or 'asset_id' are missing.
        """
        if "df" not in data or "asset_id" not in data:
            raise ValueError(
                "Data for ParquetWriter must include 'df' (DataFrame) and 'asset_id'."
            )

        self.write(
            df=data["df"],
            asset_id=data["asset_id"],
            asset_class=data.get("asset_class", "crypto"),
        )

    def write(self, df: pd.DataFrame, asset_id: str, asset_class: str = "crypto"):
        """
        Write a DataFrame to the Parquet cold store with Hive-style partitioning.

        Args:
            df: OHLCV or similar DataFrame with a 'timestamp' column or DatetimeIndex.
            asset_id: Asset identifier (e.g., 'BTCUSDT').
            asset_class: Top-level partition directory (e.g., 'crypto', 'stocks').
        """
        if df.empty:
            self.logger.warning(f"No data to write for {asset_id}")
            return

        df_to_write = df.copy()

        # Ensure 'timestamp' is datetime-like before using .dt accessors
        if 'timestamp' in df_to_write.columns:
             df_to_write['timestamp'] = pd.to_datetime(df_to_write['timestamp'], errors='coerce')

        if 'timestamp' not in df_to_write.columns and isinstance(df_to_write.index, pd.DatetimeIndex):
            df_to_write['timestamp'] = df_to_write.index
        elif 'timestamp' not in df_to_write.columns:
            self.logger.error(f"DataFrame for {asset_id} missing 'timestamp' column or index.")
            return

        # Check for invalid timestamps after coercion
        if df_to_write['timestamp'].isna().any():
            invalid_count = df_to_write['timestamp'].isna().sum()
            self.logger.warning(f"Dropping {invalid_count} rows with invalid/NaT timestamps for {asset_id}.")
            df_to_write = df_to_write.dropna(subset=['timestamp'])

        if df_to_write.empty:
            self.logger.warning(f"No valid data remaining for {asset_id} after timestamp validation.")
            return

        df_to_write['year'] = df_to_write['timestamp'].dt.year
        df_to_write['month'] = df_to_write['timestamp'].dt.month

        output_path = self.base_dir / asset_class / asset_id

        try:
            df_to_write.to_parquet(
                path=output_path,
                partition_cols=['year', 'month'],
                index=False,
                existing_data_behavior='overwrite_or_ignore'
            )
            self.logger.info(f"Persisted {len(df_to_write)} rows for {asset_id} to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write Parquet for {asset_id}: {e}")