import duckdb
import os
import pandas as pd
from pathlib import Path
from backend.core.VortexLogger import VortexLogger

class HistoricalDataStore:
    """
    Read-optimized interface for querying historical data using DuckDB.
    """
    def __init__(self, base_dir: str = None):
        # Default to env var or local path
        path_str = base_dir or os.getenv("VORTEX_DATA_DIR", "data/parquet")
        self.base_dir = Path(path_str)
        self.logger = VortexLogger(name="HistoricalDataStore")
        # In-memory DuckDB connection; it acts as a query engine over the files
        self.conn = duckdb.connect(database=":memory:")

    def query(self, asset_id: str, start_date: str = None, end_date: str = None, asset_class: str = "crypto") -> pd.DataFrame:
        """
        Query data for a specific asset within a date range.
        """
        # Construct the glob pattern to find all parquet files for this asset
        # Pattern: data/parquet/crypto/BTCUSDT/**/*.parquet
        file_pattern = self.base_dir / asset_class / asset_id / "**" / "*.parquet"
        
        # DuckDB SQL query
        # hive_partitioning=1 allows DuckDB to understand year=2024/month=01 folders
        query = f"""
            SELECT * 
            FROM read_parquet('{file_pattern}', hive_partitioning=1)
        """
        
        conditions = []
        if start_date:
            conditions.append(f"timestamp >= '{start_date}'")
        if end_date:
            conditions.append(f"timestamp <= '{end_date}'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp ASC"

        try:
            return self.conn.execute(query).df()
        except Exception as e:
            self.logger.error(f"Error querying data for {asset_id}: {e}")
            return pd.DataFrame()