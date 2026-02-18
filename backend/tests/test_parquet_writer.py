from pathlib import Path

import pandas as pd
import pytest

from backend.etl.data_access.DataDestinationClient import DataDestinationClient
from backend.etl.data_access.storage.ParquetWriter import ParquetWriter


@pytest.fixture
def parquet_dir(tmp_path: Path) -> Path:
    """Provides a temporary directory for Parquet output."""
    return tmp_path / "parquet_store"


@pytest.fixture
def parquet_writer(parquet_dir: Path) -> ParquetWriter:
    """Creates a ParquetWriter rooted at a temporary directory."""
    return ParquetWriter(base_dir=str(parquet_dir))


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """A minimal OHLCV DataFrame with timestamps spanning two months."""
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-15 10:00:00",
            "2024-01-16 10:00:00",
            "2024-02-01 10:00:00",
        ]),
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [99.0, 100.0, 101.0],
        "close": [104.0, 105.0, 106.0],
        "volume": [1000, 1100, 1200],
    })


@pytest.mark.unit
class TestParquetWriter:
    """Unit tests for ParquetWriter."""

    def test_is_data_destination_client(self, parquet_writer: ParquetWriter):
        """ParquetWriter must be a DataDestinationClient subclass."""
        assert isinstance(parquet_writer, DataDestinationClient)

    def test_write_creates_partitioned_parquet(
        self, parquet_writer: ParquetWriter, parquet_dir: Path, sample_dataframe: pd.DataFrame
    ):
        """Writing a DataFrame should create Hive-partitioned directories."""
        parquet_writer.write(sample_dataframe, asset_id="BTCUSDT")

        asset_dir = parquet_dir / "crypto" / "BTCUSDT"
        assert asset_dir.exists()

        # Should have year=2024 partition
        year_dirs = list(asset_dir.glob("year=*"))
        assert len(year_dirs) >= 1

        # Should have month partitions under year
        month_dirs = list(asset_dir.glob("year=*/month=*"))
        assert len(month_dirs) == 2  # Jan and Feb

    def test_write_empty_dataframe_does_nothing(
        self, parquet_writer: ParquetWriter, parquet_dir: Path
    ):
        """An empty DataFrame should not create any files or directories."""
        parquet_writer.write(pd.DataFrame(), asset_id="BTCUSDT")

        asset_dir = parquet_dir / "crypto" / "BTCUSDT"
        assert not asset_dir.exists()

    def test_write_missing_timestamp_logs_error(
        self, parquet_writer: ParquetWriter, parquet_dir: Path
    ):
        """A DataFrame without 'timestamp' column or DatetimeIndex should not write."""
        df_no_ts = pd.DataFrame({"price": [1, 2, 3]})
        parquet_writer.write(df_no_ts, asset_id="BTCUSDT")

        asset_dir = parquet_dir / "crypto" / "BTCUSDT"
        assert not asset_dir.exists()

    def test_save_data_delegates_to_write(
        self, parquet_writer: ParquetWriter, parquet_dir: Path, sample_dataframe: pd.DataFrame
    ):
        """save_data should delegate to write() and produce the same output."""
        parquet_writer.save_data({
            "df": sample_dataframe,
            "asset_id": "ETHUSDT",
            "asset_class": "crypto",
        })

        asset_dir = parquet_dir / "crypto" / "ETHUSDT"
        assert asset_dir.exists()
        parquet_files = list(asset_dir.rglob("*.parquet"))
        assert len(parquet_files) > 0

    def test_save_data_missing_keys_raises(self, parquet_writer: ParquetWriter):
        """save_data must raise ValueError when required keys are missing."""
        with pytest.raises(ValueError, match="must include"):
            parquet_writer.save_data({"df": pd.DataFrame()})

        with pytest.raises(ValueError, match="must include"):
            parquet_writer.save_data({"asset_id": "BTC"})

    def test_save_data_defaults_asset_class_to_crypto(
        self, parquet_writer: ParquetWriter, parquet_dir: Path, sample_dataframe: pd.DataFrame
    ):
        """save_data without 'asset_class' key should default to 'crypto'."""
        parquet_writer.save_data({
            "df": sample_dataframe,
            "asset_id": "SOLUSDT",
        })

        asset_dir = parquet_dir / "crypto" / "SOLUSDT"
        assert asset_dir.exists()
