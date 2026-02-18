import pandas as pd
import numpy as np

from backend.scitus.backtest.BaseBacktester import BaseBacktester
from backend.scitus.backtest.BacktestResult import BacktestResult
from backend.scitus.backtest.MetricsCalculator import MetricsCalculator

class VectorizedBacktester(BaseBacktester):
    """
    Fast, pandas-based vectorized backtester.
    Performs full cost modeling using matrix operations.
    """

    def run(self, data: pd.DataFrame, signals: pd.Series, **kwargs) -> BacktestResult:
        # Step 1: Signal Alignment (Shift to avoid lookahead)
        # Signal at T triggers Trade at T+1 (Open/Close depending on assumptions).
        # We assume Signal T -> Position T+1.
        aligned_signals = signals.shift(1).fillna(0)

        # Step 2: Position Calculation (Forward fill positions)
        # If signal is 0, we assume 'flat' or 'hold'?
        # Convention: 1=Long, -1=Short, 0=Flat.
        # If the user means "0 = Hold previous", they should have ffilled BEFORE passing signals.
        # But commonly signals are sparse (1, 0, 0, -1). 
        # Let's assume input signals are STATE (e.g. 1 means "be long").
        # If input is sparse triggers, the caller must expand them.
        positions = aligned_signals.copy()

        # Step 3: Market Returns
        # Return at T is (Close_T - Close_T-1) / Close_T-1
        market_returns = data["close"].pct_change().fillna(0)

        # Step 4: Strategy Returns (Gross)
        # If I am long at T (based on signal T-1), I get market return at T.
        strategy_returns = positions * market_returns

        # Step 5: Transaction Costs
        # Trade occurs when position changes.
        trades = positions.diff().abs().fillna(0)
        # Cost = trade_size * transaction_cost
        # Note: 'positions' here represents % of capital or units?
        # Vectorized usually assumes fully invested (1.0) or nothing (0.0).
        # So 'trades' is 0, 1, or 2 (flip long to short).
        cost_per_bar = trades * self.transaction_cost

        # Step 6: Slippage
        # Pass (trade_units, volume, close).
        # We need to estimate trade_units.
        # Assuming position=1.0 means "1 unit of capital"? No, "100% of capital".
        # Let's approximate: trade_value = trades * current_capital.
        # But current_capital changes. Vectorized approx: trade_value ~ trades * initial_capital?
        # Or just work in percentage returns space.
        # Slippage Model returns specific cost derived from (trades, volume, close).
        # Our base models handle the abstraction. 
        # Let's assume inputs are raw quantities if possible, or % terms.
        # Our models defined in step 1 use (trades * close).
        # If 'trades' here is %, then (trades * close) is nonsense.
        
        # CORRECT APPROACH for Vectorized Pct-Based:
        # We interpret `slippage_model.calculate` as returning a PERCENTAGE penalty.
        # FixedSlippage: returns (trades * close) * pct.
        # If inputs are not units, we must adapt.
        
        # Adaptation: We will treat `trades` as % turnover.
        # We need slippage expressed as a return deduction.
        # FixedSlippage should return: turnover * slippage_pct.
        
        # Let's override/adapt slightly for Vectorized usage logic vs Event-Driven units:
        # In Vectorized, everything is a return penalty.
        # Cost = trades (turnover) * transaction_cost (rate). Correct.
        
        # Slippage:
        # If Fixed: turnover * rate.
        # If Volatility: returns * multiplier?
        # If Volume: This is hard in vectorized without assuming AUM.
        # We will assume a nominal AUM=1.0 for impact calculations if needed, or pass AUM.
        
        # Refactoring Slippage Model usage for Vectorized:
        # We'll pass `trades` as turnover fraction.
        # `volume` as raw volume.
        # `close` as price.
        # The result from `calculate` is "Cost Value". 
        # We need "Cost Fraction" = Cost Value / (Price * 1.0)? 
        
        # To keep it simple for Phase 1:
        # We assume SlippageModel returns a RATE (decimal) to satisfy the vector equation.
        # But our FixedSlippage implementation returns `(trades * close) * pct`.
        # If trade=1 (turnover), cost = price * pct. 
        # As a return drag: cost / price = pct.
        # So we should DIVIDE the slippage model output by 'close' to get return impact.
        
        raw_slippage_cost = self.slippage_model.calculate(trades, data["volume"], data["close"])
        # Normalize to return space
        slippage_per_bar = raw_slippage_cost / data["close"]
        slippage_per_bar = slippage_per_bar.fillna(0)

        # Step 7: Funding Costs
        # Rate per period * position size (abs)
        # If funding_rate is a series, align it.
        funding_rate_series = self.funding_rate if isinstance(self.funding_rate, pd.Series) else pd.Series(self.funding_rate, index=data.index)
        funding_cost = positions.abs() * funding_rate_series

        # Step 8: Borrow Costs
        # Only on short positions (position < 0)
        # Borrow rate is annualized, need per-bar.
        # Rate / bars_per_year
        borrow_rate_series = self.borrow_rate if isinstance(self.borrow_rate, pd.Series) else pd.Series(self.borrow_rate, index=data.index)
        borrow_cost_per_bar = borrow_rate_series / self.bars_per_year
        borrow_cost = (positions < 0).astype(float) * borrow_cost_per_bar

        # Step 9: Net Returns
        net_returns = strategy_returns - cost_per_bar - slippage_per_bar - funding_cost - borrow_cost

        # Step 10: Equity Curve
        equity_curve = (1 + net_returns).cumprod() * self.initial_capital
        
        # Create Trade Log (Approximation for vectorized)
        # Identify trade timestamps
        trade_indices = trades[trades > 0].index
        trades_df = pd.DataFrame({
            "timestamp": trade_indices,
            "size": trades[trade_indices],
            "price": data.loc[trade_indices, "close"],
            "cost": cost_per_bar[trade_indices],
            "slippage": slippage_per_bar[trade_indices]
        })

        # Calculate metrics
        metrics = MetricsCalculator.calculate(
            net_returns,
            equity_curve,
            positions,
            bars_per_year=self.bars_per_year
        )
        return BacktestResult(
            equity_curve=equity_curve,
            returns=net_returns,
            positions=positions,
            trades=trades_df,
            metrics=metrics,
            costs={
                "transaction": cost_per_bar,
                "slippage": slippage_per_bar,
                "funding": funding_cost,
                "borrow": borrow_cost
            },
            metadata={"type": "vectorized"}
        )
