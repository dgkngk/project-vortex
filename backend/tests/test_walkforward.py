import pytest
import pandas as pd
import numpy as np

from backend.scitus.validation.WalkForwardValidator import WalkForwardValidator
from backend.scitus.BaseStrategy import BaseStrategy
from backend.scitus.backtest.VectorizedBacktester import VectorizedBacktester

class DummyStrategy(BaseStrategy):
    """
    A minimal strategy for testing that always longs the asset.
    """
    def __init__(self, config=None):
        super().__init__(config or {})

    def generate_signal(self, data: pd.DataFrame) -> pd.Series:
        # Always output 1 for Buy and Hold
        return pd.Series([1] * len(data), index=data.index)

@pytest.fixture
def workflow_data():
    dates = pd.date_range("2020-01-01", periods=100)
    # create OHLCV mock data
    df = pd.DataFrame({
        "open": np.linspace(100, 150, 100),
        "high": np.linspace(105, 155, 100),
        "low": np.linspace(95, 145, 100),
        "close": np.linspace(100, 200, 100), # 100% return over 100 bars
        "volume": np.random.randint(100, 1000, 100)
    }, index=dates)
    return df

@pytest.mark.unit
def test_walk_forward_splits_generation(workflow_data):
    validator = WalkForwardValidator()
    # Data is 100 bars. Reserve 20% (last 20 bars). wf_data drops to 80 bars.
    # Train window: 20
    # Test window: 10
    # Step: 10
    # Splits expected:
    # 1: 0-20, 20-30
    # 2: 10-30, 30-40
    # 3: 20-40, 40-50
    # 4: 30-50, 50-60
    # 5: 40-60, 60-70
    # 6: 50-70, 70-80
    splits = validator.generate_splits(
        data=workflow_data,
        train_window=20,
        test_window=10,
        step=10
    )
    
    assert len(splits) == 6
    assert len(splits[0].train_data) == 20
    assert len(splits[0].test_data) == 10
    
    # Assert proper sliding
    assert splits[0].test_data.index[0] == splits[1].train_data.index[10]

@pytest.mark.unit
def test_walk_forward_validation_run(workflow_data):
    strategy = DummyStrategy()
    backtester = VectorizedBacktester(initial_capital=1000, transaction_cost=0.0)
    validator = WalkForwardValidator()
    
    res = validator.validate(
        strategy=strategy,
        data=workflow_data,
        backtester=backtester,
        train_window=20,
        test_window=10,
        step=10
    )
    
    # 6 splits means we have 6 OOS periods of length 10 stitched together
    # Total OOS length = 60
    assert len(res.splits_results) == 6
    assert len(res.oos_equity_curve) == 60
    assert "total_return" in res.aggregate_metrics
    
@pytest.mark.unit
def test_monte_carlo_robustness():
    validator = WalkForwardValidator()
    
    trades = pd.DataFrame({
        "pnl": [0.01, -0.01, 0.05, -0.02, 0.1]
    })
    
    mc_res = validator.monte_carlo(trades, n_simulations=100)
    assert "total_return_95_ci" in mc_res.confidence_intervals
    
    # Check that sum is correct (additive PnL logic in the Dummy for MC)
    total_expected = trades['pnl'].sum()
    assert mc_res.means["total_return_mean"] == pytest.approx(total_expected)

@pytest.mark.unit
def test_generate_splits_insufficient_data():
    """Splits should raise ValueError when data is too small for the windows."""
    dates = pd.date_range("2020-01-01", periods=10)
    small_data = pd.DataFrame({
        "open": [100]*10, "high": [105]*10, "low": [95]*10,
        "close": [100]*10, "volume": [500]*10
    }, index=dates)
    
    validator = WalkForwardValidator()
    with pytest.raises(ValueError, match="only 8 bars remain"):
        validator.generate_splits(small_data, train_window=20, test_window=10, step=10)

@pytest.mark.unit
def test_monte_carlo_empty_trades():
    """MC should return empty results for empty trades DataFrame."""
    validator = WalkForwardValidator()
    mc_res = validator.monte_carlo(pd.DataFrame(), n_simulations=100)
    assert mc_res.confidence_intervals == {}
    assert mc_res.means == {}

@pytest.mark.unit
def test_monte_carlo_single_trade():
    """MC with a single trade: all shuffles produce the same total."""
    validator = WalkForwardValidator()
    trades = pd.DataFrame({"pnl": [0.05]})
    mc_res = validator.monte_carlo(trades, n_simulations=50)
    
    ci = mc_res.confidence_intervals["total_return_95_ci"]
    assert ci[0] == pytest.approx(0.05)
    assert ci[1] == pytest.approx(0.05)

@pytest.mark.unit
def test_custom_oos_reserve(workflow_data):
    """Custom OOS reserve % should change the number of available splits."""
    validator_10 = WalkForwardValidator(oos_reserve_pct=0.1)
    validator_30 = WalkForwardValidator(oos_reserve_pct=0.3)
    
    splits_10 = validator_10.generate_splits(workflow_data, train_window=20, test_window=10, step=10)
    splits_30 = validator_30.generate_splits(workflow_data, train_window=20, test_window=10, step=10)
    
    # Less reserve = more data = more splits
    assert len(splits_10) > len(splits_30)

