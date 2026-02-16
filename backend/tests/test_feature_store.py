from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from backend.scitus.features.FeatureRegistry import FeatureDef, FeatureRegistry
from backend.scitus.features.FeatureStore import FeatureStore


@pytest.fixture
def mock_data_store():
    """Mock HistoricalDataStore returning synthetic OHLCV data."""
    store = MagicMock()
    dates = pd.date_range("2023-06-01", periods=100, freq="D")
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(100) * 0.5)
    df = pd.DataFrame({
        "timestamp": dates,
        "open": closes - 0.5,
        "high": closes + 1.0,
        "low": closes - 1.0,
        "close": closes,
        "volume": np.random.randint(1000, 5000, size=100),
    })
    store.query.return_value = df
    return store


@pytest.fixture
def feature_store(mock_data_store):
    registry = FeatureRegistry()
    return FeatureStore(registry=registry, data_store=mock_data_store)


@pytest.mark.unit
class TestFeatureStore:
    def test_compute_returns_dataframe(self, feature_store):
        """compute() should return a DataFrame with requested feature columns."""
        result = feature_store.compute(
            asset_id="BTCUSDT",
            feature_names=["rsi_14", "sma_20"],
            start="2023-08-01",
            end="2023-09-08",
        )
        assert isinstance(result, pd.DataFrame)
        assert "rsi_14" in result.columns
        assert "sma_20" in result.columns

    def test_compute_calls_data_store_with_lookback(self, feature_store, mock_data_store):
        """compute() should fetch data with enough lookback for the longest indicator."""
        feature_store.compute(
            asset_id="BTCUSDT",
            feature_names=["sma_50"],
            start="2023-08-01",
            end="2023-09-08",
        )

        call_args = mock_data_store.query.call_args
        fetched_start = call_args.kwargs.get("start_date") or call_args[1].get("start_date")
        # sma_50 window=50, buffer=2x -> 100 days lookback
        # So fetched_start should be well before 2023-08-01
        assert fetched_start < "2023-08-01"

    def test_compute_point_in_time_no_future_data(self, feature_store, mock_data_store):
        """compute() should not include data after end date in results."""
        feature_store.compute(
            asset_id="BTCUSDT",
            feature_names=["rsi_14"],
            start="2023-08-01",
            end="2023-09-08",
        )

        call_args = mock_data_store.query.call_args
        fetched_end = call_args.kwargs.get("end_date") or call_args[1].get("end_date")
        assert fetched_end == "2023-09-08"

    def test_compute_empty_data_returns_empty(self, feature_store, mock_data_store):
        """If no raw data is available, compute() should return an empty DataFrame."""
        mock_data_store.query.return_value = pd.DataFrame()

        result = feature_store.compute(
            asset_id="UNKNOWN",
            feature_names=["rsi_14"],
            start="2023-08-01",
            end="2023-09-08",
        )
        assert result.empty
        assert "rsi_14" in result.columns

    def test_compute_with_failing_feature(self, feature_store):
        """If a feature calculation fails, the column should be filled with NA."""
        bad_feature = FeatureDef(
            name="bad_feature",
            description="Always fails",
            function=lambda df: (_ for _ in ()).throw(ValueError("boom")),
            window=1,
        )
        feature_store.registry.register(bad_feature)

        result = feature_store.compute(
            asset_id="BTCUSDT",
            feature_names=["bad_feature"],
            start="2023-08-01",
            end="2023-09-08",
        )
        assert "bad_feature" in result.columns
