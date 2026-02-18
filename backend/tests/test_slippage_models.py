import pytest
import pandas as pd
import numpy as np
from backend.scitus.backtest.slippage.FixedSlippage import FixedSlippage
from backend.scitus.backtest.slippage.VolumeWeightedSlippage import VolumeWeightedSlippage
from backend.scitus.backtest.slippage.VolatilitySlippage import VolatilitySlippage

@pytest.fixture
def sample_data():
    dates = pd.date_range("2023-01-01", periods=5)
    return {
        "trades": pd.Series([1.0, 0.0, 2.0, 0.5, 0.0], index=dates), # Turnover/Units
        "volume": pd.Series([1000, 1000, 1000, 500, 1000], index=dates),
        "close": pd.Series([100, 101, 102, 103, 104], index=dates)
    }

@pytest.mark.unit
def test_fixed_slippage_constant(sample_data):
    # 0.1% slippage
    model = FixedSlippage(slippage_pct=0.001)
    
    cost = model.calculate(sample_data["trades"], sample_data["volume"], sample_data["close"])
    
    # Expected: trades * close * 0.001
    # Day 1: 1.0 * 100 * 0.001 = 0.1
    assert cost.iloc[0] == 0.1
    # Day 3: 2.0 * 102 * 0.001 = 0.204
    assert cost.iloc[2] == pytest.approx(0.204)
    # Day 2: 0 trades -> 0 cost
    assert cost.iloc[1] == 0.0

@pytest.mark.unit
def test_volume_weighted_slippage(sample_data):
    model = VolumeWeightedSlippage(base_slippage=0.01)
    
    cost = model.calculate(sample_data["trades"], sample_data["volume"], sample_data["close"])
    
    # Day 1: sqrt(1/1000) * 0.01 = impact_rate. Cost = 1.0 * 100 * impact_rate
    impact = np.sqrt(1/1000) * 0.01
    expected = 100 * impact
    assert cost.iloc[0] == pytest.approx(expected)
    
    # Day 4: trade 0.5, vol 500. sqrt(0.5/500)=sqrt(0.001)=0.0316. 
    # Impact rate = 0.0316 * 0.01. Cost = 0.5 * 103 * rate
    impact4 = np.sqrt(0.5/500) * 0.01
    expected4 = 0.5 * 103 * impact4
    assert cost.iloc[3] == pytest.approx(expected4)

@pytest.mark.unit
def test_volatility_slippage(sample_data):
    # Mock return series for internal calc
    # Close: 100, 101, 102, 103, 104 -> ~1% returns each step
    model = VolatilitySlippage(atr_period=2, multiplier=1.0)
    
    cost = model.calculate(sample_data["trades"], sample_data["volume"], sample_data["close"])
    
    # First few should be 0 (not enough data for period=2)
    # Period 2 needs valid std dev. 
    # Returns: NaN, 0.01, 0.0099, 0.0098, 0.0097
    # Rolling(2).std() available from index 2?
    
    # Check that it returns a series of same length
    assert len(cost) == 5
    # Check that if trades are 0, cost is 0
    assert cost.iloc[1] == 0.0
