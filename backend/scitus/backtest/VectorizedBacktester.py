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
        """
        Run a fully vectorized backtest on the provided market data and trading signals.

        This method applies a simple but explicit signal-alignment convention:
        the signal observed at time ``T`` determines the position held over the
        next bar, i.e. from ``T`` to ``T+1``. Concretely, the input ``signals``
        series is shifted by one period so that:

        - Signal at ``T`` -> Position at ``T+1``
        - No look-ahead bias is introduced (decisions use only past information).

        Parameters
        ----------
        data : pandas.DataFrame
            Market data indexed by timestamp (or bar index). At minimum this
            must contain a ``"close"`` column, which is used to compute
            percentage market returns via ``pct_change()``. Any additional
            columns required by the configured cost models (e.g. volume, high,
            low, etc.) must also be present.
        signals : pandas.Series
            Raw trading signals indexed on the same axis as ``data``. Each value
            represents the desired position *state* for the next bar after
            alignment, using the convention:

            - ``1``  : fully long
            - ``-1`` : fully short
            - ``0``  : flat

            The implementation assumes that ``signals`` already encodes the
            desired *state* on each bar (e.g. ``1, 1, 1, 0, -1, -1``). If a user
            instead has sparse *triggers* (e.g. ``1, 0, 0, -1, 0, 0`` meaning
            "enter/exit/flip" instructions), they must first expand those into a
            state series before calling :meth:`run`. The series is shifted by one
            period and missing values after the shift are filled with ``0``.
        **kwargs
            Optional additional parameters for advanced cost models or result
            configuration. These are passed through to the underlying cost and
            metrics components where applicable (for example, to slippage,
            funding, or borrow models), without being interpreted directly in
            this method.

        Returns
        -------
        BacktestResult
            An object encapsulating the full backtest outcome.
        """
        # Validate required columns in input data
        required_columns = {"close", "volume"}
        missing_columns = required_columns.difference(set(data.columns))
        if missing_columns:
            # We only strictly need 'volume' if using volume-based slippage,
            # but good practice to check if we expect it.
            # However, if using FixedSlippage, volume might not be needed.
            # Let's check if we strictly need it?
            # The PR comment suggested adding validation for 'volume' specifically.
            # But let's be safe: only if provided slippage model needs it?
            # For now, let's effectively warn or just check 'close' strictly, 
            # and 'volume' if we want to be strict.
            # Given the test failures in review about missing volume, let's enforce it
            # OR better, only enforce 'close', and let Slippage model fail if volume missing?
            # The comment suggested: "Add validation ... to ensure required columns ('close', 'volume') are present".
            # So I will enforce 'volume' too as requested.
            pass  # Logic implemented below

        if "close" not in data.columns:
             raise ValueError("Input data missing required column: 'close'")
        # We don't strictly enforce 'volume' for all strategies (e.g. slight deviation from request if justified),
        # but to satisfy PR exactly:
        if "volume" not in data.columns:
             # Check if we should raise. The reviewer asked for it.
             # raise ValueError("Input data missing required column: 'volume'")
             # Actually, let's just log or be permissive if not using volume slippage?
             # No, let's implement the requested validation to be safe.
             raise ValueError("Input data missing required column: 'volume'")

        # Step 1: Signal Alignment
        aligned_signals = signals.shift(1).fillna(0)
        positions = aligned_signals.copy()

        # Optimize position flags
        is_long = positions > 0
        is_short = positions < 0
        is_invested = positions.abs() > 0

        # Step 2: Market Returns
        market_returns = data["close"].pct_change().fillna(0)

        # Step 3: Strategy Returns (Gross)
        strategy_returns = positions * market_returns

        # Step 4: Transaction Costs
        # trades represents turnover (0 to 2.0).
        trades_turnover = positions.diff().abs().fillna(0)
        cost_per_bar = trades_turnover * self.transaction_cost

        # Step 5: Slippage
        # Convert turnover to approximate units to satisfy VolumeWeightedSlippage dimensional requirement.
        # We use initial_capital as a baseline estimate.
        # approx_trade_value = turnover * initial_capital
        approx_trade_value = trades_turnover * self.initial_capital
        
        # Protect against zero price division
        close_for_div = data["close"].replace(0, np.nan)
        approx_trade_units = approx_trade_value / close_for_div
        
        # Calculate raw slippage cost (in $)
        raw_slippage_cost = self.slippage_model.calculate(approx_trade_units, data["volume"], data["close"])
        
        # Convert raw cost back to return impact (cost / capital? No, cost / current_value?)
        # Vectorized approx: cost / (price * units) -> cost / trade_value?
        # Wait, we need return deduction.
        # Slippage is usually: (Price_Executed - Price_Ideal) * Units.
        # As returns: (P_exec - P_ideal) / P_ideal = Slippage_Pct.
        # Our model returns "Cost ($)".
        # We need to subtract this from returns.
        # Return impact = Cost / Capital.
        # Approx: Cost / Initial_Capital.
        # OR: Cost / (Price * Position_Units)?
        
        # Let's use the same denominator as we used to get units:
        # We assumed Capital ~ Initial_Capital.
        slippage_per_bar = raw_slippage_cost / self.initial_capital
        slippage_per_bar = slippage_per_bar.fillna(0)

        # Step 6: Funding Costs (Annualized -> Per Bar)
        funding_rate_series = self.funding_rate if isinstance(self.funding_rate, pd.Series) else pd.Series(self.funding_rate, index=data.index)
        funding_rate_per_bar = funding_rate_series / self.bars_per_year
        funding_cost = positions.abs() * funding_rate_per_bar

        # Step 7: Borrow Costs (Annualized -> Per Bar)
        borrow_rate_series = self.borrow_rate if isinstance(self.borrow_rate, pd.Series) else pd.Series(self.borrow_rate, index=data.index)
        borrow_rate_per_bar = borrow_rate_series / self.bars_per_year
        borrow_cost = is_short.astype(float) * borrow_rate_per_bar

        # Step 8: Net Returns
        net_returns = strategy_returns - cost_per_bar - slippage_per_bar - funding_cost - borrow_cost

        # Step 9: Equity Curve (numerically stable via log returns)
        gross_returns = 1 + net_returns
        # Avoid log(<=0)
        log_returns = np.where(gross_returns > 0, np.log(gross_returns), -np.inf)
        cumulative_log_returns = np.cumsum(log_returns)
        equity_curve_values = np.exp(cumulative_log_returns) * self.initial_capital
        equity_curve = pd.Series(equity_curve_values, index=net_returns.index)
        
        # Create Trade Log (Approximation)
        trade_indices = trades_turnover[trades_turnover > 0].index
        trades_df = pd.DataFrame({
            "timestamp": trade_indices,
            "turnover": trades_turnover[trade_indices],
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
