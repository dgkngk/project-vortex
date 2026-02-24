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

    def run(self, data: pd.DataFrame, *, signals: pd.Series, **kwargs) -> BacktestResult:
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

        if "close" not in data.columns:
             raise ValueError("Input data missing required column: 'close'")
        if "volume" not in data.columns:
             raise ValueError("Input data missing required column: 'volume'")

        # Step 1: Signal Alignment and Position Calculation
        # The signals array encodes the desired trade state or action: 
        # 1 = Go Long, -1 = Go Short, 0 = Hold previous state.
        # We shift by 1 to prevent lookahead bias (actions trigger on the *next* bar).
        # We map 0 to NaN and forward-fill to maintain the current position when a Hold is signaled.
        aligned_signals = signals.shift(1).fillna(0)
        positions = aligned_signals.replace(0, np.nan).ffill().fillna(0)

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
        approx_trade_value = trades_turnover * self.initial_capital
        close_for_div = data["close"].replace(0, np.nan)
        approx_trade_units = approx_trade_value / close_for_div
        
        raw_slippage_cost = self.slippage_model.calculate(approx_trade_units, data["volume"], data["close"])
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
        log_returns = np.where(gross_returns > 0, np.log(gross_returns), -np.inf)
        cumulative_log_returns = np.cumsum(log_returns)
        equity_curve_values = np.exp(cumulative_log_returns) * self.initial_capital
        equity_curve = pd.Series(equity_curve_values, index=net_returns.index)
        
        # Build Accurate Trade Log
        # Find points where position changes
        trade_points = positions[positions.diff() != 0]
        # Ignore the first dummy difference if it's 0 changing to 0
        if trade_points.iloc[0] == 0:
            trade_points = trade_points.iloc[1:]
            
        trades_list = []
        entry_time = None
        entry_price = 0
        entry_idx = 0
        current_pos = 0
        
        costs_dict = {
            "transaction": cost_per_bar,
            "slippage": slippage_per_bar,
            "funding": funding_cost,
            "borrow": borrow_cost
        }

        for i in range(len(positions)):
            pos = positions.iloc[i]
            if pos != current_pos:
                # We have a trade (entry, exit, or flip)
                
                # If we were in a position, close it out completely 
                # (if flipping from Long to Short, we first close the Long)
                if current_pos != 0:
                    exit_time = positions.index[i]
                    exit_price = data["close"].iloc[i]
                    duration = i - entry_idx
                    
                    # Return accumulated between entry and exit
                    net_return_slice = net_returns.iloc[entry_idx+1:i+1] 
                    # Compounded PnL (percentage)
                    pts = np.exp(np.sum(np.log(1 + net_return_slice))) - 1 if len(net_return_slice) > 0 else 0
                    
                    trades_list.append({
                        "entry_time": entry_time,
                        "exit_time": exit_time,
                        "duration": duration,
                        "direction": "Long" if current_pos > 0 else "Short",
                        "size": abs(current_pos),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pts
                    })
                
                # If opening a new position (including the flip side)
                if pos != 0:
                    entry_time = positions.index[i]
                    entry_price = data["close"].iloc[i]
                    entry_idx = i
                    
                current_pos = pos
                
        # If open at the end, mark to market
        if current_pos != 0:
             exit_time = positions.index[-1]
             exit_price = data["close"].iloc[-1]
             duration = len(positions) - 1 - entry_idx
             net_return_slice = net_returns.iloc[entry_idx+1:] 
             pts = np.exp(np.sum(np.log(1 + net_return_slice))) - 1 if len(net_return_slice) > 0 else 0
             trades_list.append({
                  "entry_time": entry_time,
                  "exit_time": exit_time,
                  "duration": duration,
                  "direction": "Long" if current_pos > 0 else "Short",
                  "size": abs(current_pos),
                  "entry_price": entry_price,
                  "exit_price": exit_price,
                  "pnl": pts
             })

        trades_df = pd.DataFrame(trades_list)

        # Calculate metrics
        metrics = MetricsCalculator.calculate(
            returns=net_returns,
            equity=equity_curve,
            positions=positions,
            trades_df=trades_df,
            costs=costs_dict,
            bars_per_year=self.bars_per_year
        )
        return BacktestResult(
            equity_curve=equity_curve,
            returns=net_returns,
            positions=positions,
            trades=trades_df,
            metrics=metrics,
            costs=costs_dict,
            metadata={"type": "vectorized"}
        )
