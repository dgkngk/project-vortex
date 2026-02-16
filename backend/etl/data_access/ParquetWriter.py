import os
from pathlib import Path
import pandas as pd
from backend.core.VortexLogger import VortexLogger

class ParquetWriter:
    """
    Writes DataFrames to a local Parquet store with Hive-style partitioning.
    Structure: base_dir / asset_class / asset_id / year=YYYY / month=MM / data.parquet
    """
    def __init__(self, base_dir: str = None):
        # Default to env var or local path
        path_str = base_dir or os.getenv("VORTEX_DATA_DIR", "data/parquet")
        self.base_dir = Path(path_str)
        self.logger = VortexLogger(name="ParquetWriter")
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, df: pd.DataFrame, asset_id: str, asset_class: str = "crypto"):
        if df.empty:
            self.logger.warning(f"No data to write for {asset_id}")
            return

        # Work on a copy to avoid modifying the original dataframe in the pipeline
        df_to_write = df.copy()

        # Ensure we have a timestamp column for partitioning
        if 'timestamp' not in df_to_write.columns and isinstance(df_to_write.index, pd.DatetimeIndex):
            df_to_write['timestamp'] = df_to_write.index
        elif 'timestamp' not in df_to_write.columns:
            self.logger.error(f"DataFrame for {asset_id} missing 'timestamp' column or index.")
            return

        # Create partition columns
        df_to_write['year'] = df_to_write['timestamp'].dt.year
        df_to_write['month'] = df_to_write['timestamp'].dt.month

        # Define output path: data/parquet/crypto/BTCUSDT
        output_path = self.base_dir / asset_class / asset_id

        try:
            # Write partitioned parquet
            # This creates folders like: .../BTCUSDT/year=2024/month=1/
            df_to_write.to_parquet(
                path=output_path,
                partition_cols=['year', 'month'],
                index=False  # We usually query by column, index is reconstructed if needed
            )
            self.logger.info(f"Persisted {len(df_to_write)} rows for {asset_id} to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to write Parquet for {asset_id}: {e}")