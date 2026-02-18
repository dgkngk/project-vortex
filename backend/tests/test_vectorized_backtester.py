import pytest
import pandas as pd
import numpy as np
from backend.scitus.backtest.VectorizedBacktester import VectorizedBacktester

@pytest.fixture
def market_data():
    dates = pd.date_range("2023-01-01", periods=10)
    df = pd.DataFrame({
        "close": np.linspace(100, 110, 10), # Steady 10% rise
        "volume": [1000] * 10
    }, index=dates)
    return df

@pytest.mark.unit
@pytest.mark.unit
def test_buy_and_hold_perfect(market_data):
    """Test standard buy and hold without costs matching market return."""
    # Signal: Always Long (1)
    signals = pd.Series(1, index=market_data.index)
    
    backtester = VectorizedBacktester(
        initial_capital=1000,
        transaction_cost=0.0,
        slippage_model=None, # fixed 0
        funding_rate=0.0,
        borrow_rate=0.0
    )
    
    result = backtester.run(market_data, signals)
    
    # The market moves from 100 to 110 (10% total return).
    # The strategy signals LONG (1) at T0.
    # Vectorized logic:
    # 1. Signals are shifted by 1 to align with returns (Signal T0 -> Position T1).
    # 2. Position T1 = 1.
    # 3. Market Return T1 = (Close T1 - Close T0) / Close T0 = (101.11 - 100) / 100 = 1.11%.
    # 4. Strategy captures this return.
    # Since we are Long for the entire duration (signals=1 everywhere), 
    # we capture the full market move from 100 to 110.
    # Expected Final Equity = Initial * (Final / Initial) = 1000 * (110 / 100) = 1100.
    
    final_equity = result.equity_curve.iloc[-1]
    
    assert final_equity == pytest.approx(1100.0, rel=1e-3)
    assert result.metrics["total_return"] > 0.09

@pytest.mark.unit
def test_transaction_costs(market_data):
    """Test that costs reduce equity."""
    signals = pd.Series(1, index=market_data.index)
    
    # Costly backtester
    backtester = VectorizedBacktester(
        initial_capital=1000,
        transaction_cost=0.01, # 1% per trade
    )
    
    result = backtester.run(market_data, signals)
    
    # Strategy moves from Neutral (0) to Long (1) at T1 (due to shifted signal from T0).
    # This triggers a single transaction of size 1.0.
    # Transaction cost = 1.0 * 0.01 = 0.01 (1% of notional).
    # This cost is deducted from the return at T1.
    # Net Return T1 = Market Return T1 - 0.01.
    # In a frictionless buy & hold, total return is ~10%.
    # With a 1% initial cost, total return should be approximately 10% - 1% = 9%.
    # We assert it is strictly less than 9.5% to verify the cost impact.
    
    assert result.metrics["total_return"] < 0.095
    assert result.costs["transaction"].sum() > 0

@pytest.mark.unit
def test_empty_signals_flat_equity(market_data):
    signals = pd.Series(0, index=market_data.index)
    backtester = VectorizedBacktester(initial_capital=1000)
    result = backtester.run(market_data, signals)
    
    assert result.equity_curve.iloc[-1] == 1000.0
    assert result.metrics["total_return"] == 0.0

@pytest.mark.unit
def test_funding_costs(market_data):
    signals = pd.Series(1, index=market_data.index)
    
    # 2% funding per bar (Market is ~1.1% gain)
    # This ensures Net Return is negative (~ -0.9% per bar)
    backtester = VectorizedBacktester(
        initial_capital=1000,
        funding_rate=0.02
    )
    result = backtester.run(market_data, signals)
    
    # Should drag returns significantly
    assert result.costs["funding"].sum() > 0
    # 1000 start. Negative net returns. End < 1000.
    assert result.equity_curve.iloc[-1] < 1000
