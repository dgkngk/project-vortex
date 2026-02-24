import pytest
import pandas as pd
import numpy as np
from backend.scitus.backtest.MetricsCalculator import MetricsCalculator

@pytest.fixture
def sample_metrics_data():
    dates = pd.date_range("2023-01-01", periods=10)
    # Simple steady growth
    equity = pd.Series(np.linspace(100, 110, 10), index=dates) 
    returns = equity.pct_change().fillna(0)
    positions = pd.Series([1]*10, index=dates)
    return returns, equity, positions

@pytest.mark.unit
def test_total_return(sample_metrics_data):
    returns, equity, positions = sample_metrics_data
    metrics = MetricsCalculator.calculate(returns, equity, positions, bars_per_year=365)
    
    # 100 -> 110 is 10% return
    assert metrics["total_return"] == pytest.approx(0.10)

@pytest.mark.unit
def test_max_drawdown():
    # 100 -> 110 -> 99 -> 120
    # Equities: 100, 110, 99 (DD from 110 is -11/110 = -10%), 120
    equity = pd.Series([100, 110, 99, 120])
    returns = equity.pct_change().fillna(0)
    
    metrics = MetricsCalculator.calculate(returns, equity, pd.Series([1]*4), bars_per_year=365)
    assert metrics["max_drawdown"] == pytest.approx(0.10)

@pytest.mark.unit
def test_win_rate_profit_factor():
    # Returns: +10, -5, +10, -5. 
    # Wins: 2, Losses: 2. Win Rate 50%.
    # Gross Profit: 20. Gross Loss: 10. PF: 2.0.
    returns = pd.Series([0.1, -0.05, 0.1, -0.05])
    # Equity doesn't match returns exactly for this simplified test, calculating strictly on returns
    equity = pd.Series([1]*4) 
    
    metrics = MetricsCalculator.calculate(returns, equity, pd.Series([1]*4), bars_per_year=365)
    
    assert metrics["win_rate"] == 0.5
    assert metrics["profit_factor"] == 2.0

@pytest.mark.unit
def test_sharpe_ratio_zero_vol():
    # Constant returns -> std = 0 -> Sharpe should be handled (usually 0 or inf, we implemented 0)
    returns = pd.Series([0.01, 0.01, 0.01])
    sharpe = MetricsCalculator._sharpe(returns, 365)
    assert sharpe == 0.0

@pytest.mark.unit
def test_trade_based_metrics():
    # Mock a trades dataframe with 4 completed trades: 3 wins, 1 loss
    trades_df = pd.DataFrame({
        "pnl": [0.05, 0.10, -0.05, 0.02],
        "duration": [5, 10, 2, 3] # lengths in bars
    })
    
    returns = pd.Series([0.0]*10) # dummy returns
    equity = pd.Series([100]*10)  # dummy equity
    positions = pd.Series([0]*10) # dummy positions
    
    metrics = MetricsCalculator.calculate(returns, equity, positions, trades_df=trades_df)
    
    # Win rate = 3 wins / 4 total trades = 0.75
    assert metrics["win_rate"] == 0.75
    
    # Profit Factor = Gross Profit / Gross Loss = (0.05 + 0.10 + 0.02) / |-0.05| = 0.17 / 0.05 = 3.4
    assert metrics["profit_factor"] == pytest.approx(3.4)
    
    # Avg Trade Duration = (5 + 10 + 2 + 3) / 4 = 20 / 4 = 5.0
    assert metrics["avg_trade_duration"] == 5.0

@pytest.mark.unit
def test_cost_metrics():
    returns = pd.Series([0.0]*10)
    equity = pd.Series([100]*10)
    positions = pd.Series([0]*10)
    
    costs = {
        "transaction": pd.Series([0.01, 0.02, 0.01]),
        "slippage": pd.Series([0.05, 0.0, 0.05]),
        "funding": pd.Series([0.0, 0.0, 0.0]),
        "borrow": pd.Series([0.1, 0.0, 0.1])
    }
    
    metrics = MetricsCalculator.calculate(returns, equity, positions, costs=costs)
    
    # Total costs = 0.04 (transaction) + 0.10 (slippage) + 0.0 (funding) + 0.20 (borrow) = 0.34
    assert metrics["total_costs"] == pytest.approx(0.34)
