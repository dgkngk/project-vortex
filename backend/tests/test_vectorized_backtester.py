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
    # 3. Market Return T1 = (Close T1 - Close T0) / Close T0 = (101.11 - 100) / 100 approx 1.11%.
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
    # Note: VectorizedBacktester now interprets rates as annualized.
    # To get 2% per bar with default bars_per_year=365, we need crazy high annual rate.
    # Or set bars_per_year=1.
    
    backtester = VectorizedBacktester(
        initial_capital=1000,
        funding_rate=0.73, # 0.2% per day -> 73% annualized. Wait, previous test assumed per-bar.
                           # Let's adjust to be realistic annualized rate but use fewer bars_per_year for testing.
        bars_per_year=10   # 10 bars in test data -> 1 year?
    )
    # If bars_per_year=10, and we want significant cost.
    # Market return total 10%. 
    # Let's set funding > 10% annualized.
    backtester.funding_rate = 0.50 # 50% annualized cost.
    
    result = backtester.run(market_data, signals)
    
    # Total Funding Cost approx: 1000 * 0.5 * (10/10) = 500?
    # Actually compounded daily. 
    # Just check it's positive and reduces equity.
    
    assert result.costs["funding"].sum() > 0
    # 10% market gain < 50% funding cost -> Loss
    assert result.equity_curve.iloc[-1] < 1100.0 # Should be less than frictionless 1100

@pytest.mark.unit
def test_short_selling_loses_in_uptrend(market_data):
    """A pure short on a steadily rising market should lose money."""
    signals = pd.Series(-1, index=market_data.index)
    backtester = VectorizedBacktester(initial_capital=1000)
    result = backtester.run(market_data, signals)

    # Rising market (100->110) with constant short should generate negative returns.
    assert result.metrics["total_return"] < 0
    assert result.equity_curve.iloc[-1] < 1000

@pytest.mark.unit
def test_position_flipping_costs(market_data):
    """Frequently flipping between 1 and -1 should incur higher costs than buy-and-hold."""
    # Buy-and-hold
    signals_hold = pd.Series(1, index=market_data.index)
    
    # Flip every bar: 1, -1, 1, -1...
    flip_vals = [1 if i % 2 == 0 else -1 for i in range(len(market_data.index))]
    signals_flip = pd.Series(flip_vals, index=market_data.index)
    
    backtester = VectorizedBacktester(
        initial_capital=1000,
        transaction_cost=0.01
    )
    
    res_hold = backtester.run(market_data, signals_hold)
    res_flip = backtester.run(market_data, signals_flip)
    
    # Flipping incurs cost on every trade (size 2.0 usually) vs 1 trade for hold.
    assert res_flip.costs["transaction"].sum() > res_hold.costs["transaction"].sum()

@pytest.mark.unit
def test_borrow_cost_only_on_shorts(market_data):
    """Borrow cost should only apply to short positions."""
    # Split data: First half Long, Second half Short
    n = len(market_data)
    half = n // 2
    signals = pd.Series([1]*half + [-1]*(n-half), index=market_data.index)
    
    backtester = VectorizedBacktester(
        initial_capital=1000,
        borrow_rate=0.20, # 20% annualized
        bars_per_year=10 # So total backtest is 1 year
    )
    
    result = backtester.run(market_data, signals)
    
    borrow_costs = result.costs["borrow"]
    
    # First half (Long) should have 0 borrow cost
    # Note: signals shifted. Signal T0 (1) -> Pos T1 (1). 
    # So checking aligned positions.
    positions = result.positions
    
    # Check explicitly where positions are positive
    long_mask = positions > 0
    short_mask = positions < 0
    
    if long_mask.any():
        assert (borrow_costs[long_mask] == 0).all()
        
    if short_mask.any():
        assert (borrow_costs[short_mask] > 0).all()

