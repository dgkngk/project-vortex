import pandas as pd
import pytest
from typing import cast
from backend.etl.maintenance.AdjustmentEngine import AdjustmentEngine, CorporateAction

@pytest.fixture
def adjustment_engine():
    return AdjustmentEngine()

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(start="2023-01-01", end="2023-01-05")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": [100.0, 102.0, 52.0, 53.0, 54.0],
        "high": [105.0, 106.0, 55.0, 56.0, 57.0],
        "low": [99.0, 100.0, 50.0, 51.0, 52.0],
        "close": [101.0, 103.0, 51.0, 52.0, 53.0],
        "volume": [1000, 1100, 2200, 2300, 2400]
    })
    return df

@pytest.mark.unit
class TestAdjustmentEngine:
    def test_adjust_splits(self, adjustment_engine, sample_ohlcv):
        """
        Test a 2-for-1 split occurring on 2023-01-03.
        Data strictly BEFORE the ex-date (2023-01-01, 2023-01-02) should be adjusted (divided by 2).
        Data ON or AFTER the ex-date (2023-01-03+) remains as is.
        Wait, standard adjustment logic for backtesting usually adjusts *past* data to match *current* price.
        So if a split happens today, we divide all historical prices by the split ratio.
        """
        split_action = CorporateAction(
            ticker="TEST",
            ex_date=cast(pd.Timestamp, pd.Timestamp("2023-01-03")),
            action_type="split",
            ratio=2.0 # 2-for-1 split. Old price 100 becomes 50.
        )
        
        # We expect historical prices (pre-split) to be divided by 2.
        # We expect historical volume to be multiplied by 2.
        
        adjusted_df = adjustment_engine.adjust(sample_ohlcv, [split_action])
        
        # Check pre-split date (2023-01-01)
        row0 = adjusted_df.iloc[0]
        assert row0["close"] == 101.0 / 2.0
        assert row0["volume"] == 1000 * 2
        
        # Check post-split date (2023-01-03) - should be untouched
        row2 = adjusted_df.iloc[2]
        assert row2["close"] == 51.0
        assert row2["volume"] == 2200

    def test_adjust_multiple_actions(self, adjustment_engine, sample_ohlcv):
        """Test cumulative effect of two 2:1 splits."""
        actions = [
            CorporateAction(ticker="TEST", ex_date=cast(pd.Timestamp, pd.Timestamp("2023-01-03")), action_type="split", ratio=2.0),
            CorporateAction(ticker="TEST", ex_date=cast(pd.Timestamp, pd.Timestamp("2023-01-05")), action_type="split", ratio=2.0)
        ]
        
        adjusted_df = adjustment_engine.adjust(sample_ohlcv, actions)
        
        # 2023-01-01: Affected by both splits (ratio 2 * 2 = 4). Close 101 -> 25.25
        assert adjusted_df.iloc[0]["close"] == 101.0 / 4.0
        
        # 2023-01-03: Affected only by the second split (ratio 2). Close 51 -> 25.5
        # The data on 2023-01-03 is ALREADY post the first split, but pre the second split.
        assert adjusted_df.iloc[2]["close"] == 51.0 / 2.0
        
        # 2023-01-05: Affected by neither.
        assert adjusted_df.iloc[4]["close"] == 53.0

    def test_adjust_no_actions(self, adjustment_engine, sample_ohlcv):
        """Test that data is returned unchanged when no actions are provided."""
        adjusted_df = adjustment_engine.adjust(sample_ohlcv, [])
        pd.testing.assert_frame_equal(sample_ohlcv, adjusted_df)
