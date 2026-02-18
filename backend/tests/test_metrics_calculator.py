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
    
    metrics = MetricsCalculator.calculate(returns, equity, pd.Series([1]*4), 365)
    assert metrics["max_drawdown"] == pytest.approx(0.10)

@pytest.mark.unit
def test_win_rate_profit_factor():
    # Returns: +10, -5, +10, -5. 
    # Wins: 2, Losses: 2. Win Rate 50%.
    # Gross Profit: 20. Gross Loss: 10. PF: 2.0.
    returns = pd.Series([0.1, -0.05, 0.1, -0.05])
    # Equity doesn't match returns exactly for this simplified test, calculating strictly on returns
    equity = pd.Series([1]*4) 
    
    metrics = MetricsCalculator.calculate(returns, equity, pd.Series([1]*4), 365)
    
    assert metrics["win_rate"] == 0.5
    assert metrics["profit_factor"] == 2.0

@pytest.mark.unit
def test_sharpe_ratio_zero_vol():
    # Constant returns -> std = 0 -> Sharpe should be handled (usually 0 or inf, we implemented 0)
    returns = pd.Series([0.01, 0.01, 0.01])
    sharpe = MetricsCalculator._sharpe(returns, 365)
    assert sharpe == 0.0
