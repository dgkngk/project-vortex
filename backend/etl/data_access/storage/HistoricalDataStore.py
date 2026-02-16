import os
from typing import Optional

import duckdb
import pandas as pd
from pathlib import Path

from backend.core.VortexLogger import VortexLogger


class HistoricalDataStore:
    """
    Read-only query engine for the Parquet cold storage tier.

    Wraps DuckDB to provide fast analytical queries over Hive-partitioned
    Parquet files written by ParquetWriter. This is the primary interface
    for the backtesting engine and Jupyter research notebooks.

    This class is intentionally NOT a DataDestinationClient — it only reads
    data. Writes go through ParquetWriter or StorageRouter.
    """

    def __init__(self, base_dir: str = None):
        path_str = base_dir or os.getenv("VORTEX_DATA_DIR", "data/parquet")
        self.base_dir = Path(path_str)
        self.logger = VortexLogger(name="HistoricalDataStore")
        self.conn = duckdb.connect(database=":memory:")

    def query(
        self,
        asset_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeframe: Optional[str] = None,
        asset_class: str = "crypto",
    ) -> pd.DataFrame:
        """
        Query historical data for a specific asset within a date range.

        Args:
            asset_id: Asset identifier (e.g., 'BTCUSDT').
            start_date: Inclusive start date filter (ISO format, e.g. '2024-01-01').
            end_date: Inclusive end date filter (ISO format, e.g. '2024-12-31').
            timeframe: Optional timeframe filter (e.g., '1h', '4h', '1d').
                        Filters on a 'timeframe' column if present in the data.
            asset_class: Top-level partition directory (default: 'crypto').

        Returns:
            pd.DataFrame sorted by timestamp ASC. Empty DataFrame if no data found.
        """
        asset_dir = self.base_dir / asset_class / asset_id

        if not asset_dir.exists():
            self.logger.warning(
                f"No data directory found for {asset_class}/{asset_id} "
                f"at {asset_dir}. Returning empty DataFrame."
            )
            return pd.DataFrame()

        file_pattern = (asset_dir / "**" / "*.parquet").as_posix()

        sql = f"""
            SELECT *
            FROM read_parquet('{file_pattern}', hive_partitioning=1)
        """

        conditions = []
        if start_date:
            conditions.append(f"timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"timestamp <= '{end_date}'")
        if timeframe:
            conditions.append(f"timeframe = '{timeframe}'")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY timestamp ASC"

        try:
            return self.conn.execute(sql).df()
        except duckdb.IOException as e:
            self.logger.warning(
                f"No Parquet files found for {asset_class}/{asset_id}: {e}"
            )
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error querying data for {asset_id}: {e}")
            return pd.DataFrame()