from unittest.mock import MagicMock, call

import pandas as pd
import pytest

from backend.etl.data_access.storage.MigrationScripts import MigrationScripts
from backend.etl.data_access.storage.ParquetWriter import ParquetWriter


@pytest.fixture
def mock_parquet_writer() -> MagicMock:
    return MagicMock(spec=ParquetWriter)


@pytest.fixture
def migration() -> MigrationScripts:
    return MigrationScripts()


@pytest.mark.unit
class TestMigrationScripts:
    """Unit tests for MigrationScripts."""

    def test_backfill_to_parquet_calls_writer(
        self, migration: MigrationScripts, mock_parquet_writer: MagicMock
    ):
        """backfill_to_parquet should call writer.write with correct args."""
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "close": [100.0, 101.0],
        })

        migration.backfill_to_parquet(
            source_df=df,
            parquet_writer=mock_parquet_writer,
            asset_id="BTCUSDT",
            asset_class="crypto",
        )

        mock_parquet_writer.write.assert_called_once()
        call_kwargs = mock_parquet_writer.write.call_args
        pd.testing.assert_frame_equal(call_kwargs.kwargs["df"], df)
        assert call_kwargs.kwargs["asset_id"] == "BTCUSDT"
        assert call_kwargs.kwargs["asset_class"] == "crypto"

    def test_backfill_empty_dataframe_skips(
        self, migration: MigrationScripts, mock_parquet_writer: MagicMock
    ):
        """An empty source DataFrame should skip the write entirely."""
        migration.backfill_to_parquet(
            source_df=pd.DataFrame(),
            parquet_writer=mock_parquet_writer,
            asset_id="BTCUSDT",
        )

        mock_parquet_writer.write.assert_not_called()

    def test_archive_warm_to_cold_not_implemented(
        self, migration: MigrationScripts
    ):
        """archive_warm_to_cold should raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Warm tier"):
            migration.archive_warm_to_cold()
