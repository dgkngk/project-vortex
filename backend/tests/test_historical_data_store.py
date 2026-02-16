from pathlib import Path

import pandas as pd
import pytest

from backend.etl.data_access.storage.HistoricalDataStore import HistoricalDataStore
from backend.etl.data_access.storage.ParquetWriter import ParquetWriter


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Shared temporary directory for writer and reader."""
    return tmp_path / "parquet_store"


@pytest.fixture
def parquet_writer(data_dir: Path) -> ParquetWriter:
    return ParquetWriter(base_dir=str(data_dir))


@pytest.fixture
def data_store(data_dir: Path) -> HistoricalDataStore:
    return HistoricalDataStore(base_dir=str(data_dir))


@pytest.fixture
def seeded_store(
    parquet_writer: ParquetWriter, data_store: HistoricalDataStore
) -> HistoricalDataStore:
    """A HistoricalDataStore with pre-written test data."""
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-10 08:00:00",
            "2024-01-15 12:00:00",
            "2024-02-20 16:00:00",
        ]),
        "close": [100.0, 105.0, 110.0],
        "volume": [500, 600, 700],
    })
    parquet_writer.write(df, asset_id="BTCUSDT")
    return data_store


class TestHistoricalDataStore:
    """Unit tests for HistoricalDataStore."""

    def test_query_returns_dataframe(self, seeded_store: HistoricalDataStore):
        """Querying a seeded asset should return a non-empty DataFrame."""
        result = seeded_store.query(asset_id="BTCUSDT")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "close" in result.columns

    def test_query_with_date_range_filters(
        self, seeded_store: HistoricalDataStore
    ):
        """Date-range filters should restrict the returned rows."""
        result = seeded_store.query(
            asset_id="BTCUSDT",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        assert not result.empty
        # All rows should be in January 2024
        timestamps = pd.to_datetime(result["timestamp"])
        assert all(ts.month == 1 for ts in timestamps)

    def test_query_with_timeframe_parameter(
        self, seeded_store: HistoricalDataStore
    ):
        """Timeframe filter on data without a 'timeframe' column returns empty."""
        result = seeded_store.query(
            asset_id="BTCUSDT", timeframe="1h"
        )
        # The seeded data has no 'timeframe' column, so this should fail
        # gracefully and return an empty DataFrame.
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_query_missing_files_returns_empty(
        self, data_store: HistoricalDataStore
    ):
        """Querying an asset with no data directory should return empty DataFrame."""
        result = data_store.query(asset_id="NONEXISTENT")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_query_is_ordered_by_timestamp(
        self, seeded_store: HistoricalDataStore
    ):
        """Results should be sorted by timestamp ascending."""
        result = seeded_store.query(asset_id="BTCUSDT")
        timestamps = pd.to_datetime(result["timestamp"])
        assert list(timestamps) == sorted(timestamps)
