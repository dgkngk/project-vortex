from typing import Optional

import pandas as pd

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.storage.ParquetWriter import ParquetWriter


class MigrationScripts:
    """
    Utility module for data migration and archival jobs.

    Provides methods to backfill historical data into the Parquet cold store
    and (in future) archive warm-tier data into cold storage.
    """

    def __init__(self, logger: Optional[VortexLogger] = None):
        self.logger = logger or VortexLogger(name="MigrationScripts")

    def backfill_to_parquet(
        self,
        source_df: pd.DataFrame,
        parquet_writer: ParquetWriter,
        asset_id: str,
        asset_class: str = "crypto",
    ):
        """
        Write a source DataFrame into the Parquet cold store.

        This is the primary entry-point for one-off backfill operations, e.g.
        migrating data from an existing InfluxDB or Postgres database.

        Args:
            source_df: The DataFrame to persist.
            parquet_writer: A configured ParquetWriter instance.
            asset_id: Asset identifier (e.g., 'BTCUSDT').
            asset_class: Top-level partition directory (default: 'crypto').
        """
        if source_df.empty:
            self.logger.warning(
                f"Backfill skipped for {asset_id}: source DataFrame is empty."
            )
            return

        self.logger.info(
            f"Starting backfill of {len(source_df)} rows for "
            f"{asset_class}/{asset_id}."
        )
        parquet_writer.write(
            df=source_df,
            asset_id=asset_id,
            asset_class=asset_class,
        )
        self.logger.info(f"Backfill complete for {asset_class}/{asset_id}.")

    def archive_warm_to_cold(self):
        """
        Archive data from the Warm tier (InfluxDB) to the Cold tier (Parquet).

        Not yet implemented — requires InfluxDB Warm tier integration (future work).

        Raises:
            NotImplementedError: Always, until the Warm tier is available.
        """
        raise NotImplementedError(
            "Warm tier (InfluxDB) is not yet integrated. "
            "This method will be implemented when the Warm tier is available."
        )
