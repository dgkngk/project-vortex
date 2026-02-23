import pytest
import pandas as pd

from backend.scitus.backtest.execution.DataQueue import DataQueue


@pytest.fixture
def sample_data():
    dates = pd.date_range("2023-01-01", periods=5)
    return pd.DataFrame({
        "close": [100, 101, 102, 103, 104],
        "volume": [1000, 1100, 900, 1200, 1000],
    }, index=dates)


@pytest.mark.unit
def test_yields_all_bars(sample_data):
    """DataQueue iterates over all rows."""
    bars = list(DataQueue(sample_data))
    assert len(bars) == 5


@pytest.mark.unit
def test_validates_required_columns():
    """Raises ValueError if 'close' or 'volume' missing."""
    dates = pd.date_range("2023-01-01", periods=3)
    bad_data = pd.DataFrame({"price": [1, 2, 3]}, index=dates)
    with pytest.raises(ValueError, match="Missing required columns"):
        DataQueue(bad_data)


@pytest.mark.unit
def test_empty_dataframe():
    """Handles empty DataFrame without error."""
    empty = pd.DataFrame({"close": [], "volume": []})
    bars = list(DataQueue(empty))
    assert len(bars) == 0


@pytest.mark.unit
def test_bar_is_series(sample_data):
    """Each yielded bar is a pd.Series with timestamp name."""
    for bar in DataQueue(sample_data):
        assert isinstance(bar, pd.Series)
        assert bar.name is not None
        assert "close" in bar.index
        assert "volume" in bar.index
        break
