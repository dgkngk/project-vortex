from typing import Union

import pandas as pd

from backend.scitus.backtest.BaseBacktester import BaseBacktester
from backend.scitus.backtest.BacktestResult import BacktestResult
from backend.scitus.backtest.MetricsCalculator import MetricsCalculator
from backend.scitus.backtest.EventStrategy import EventStrategy
from backend.scitus.backtest.execution.DataQueue import DataQueue
from backend.scitus.backtest.execution.Portfolio import Portfolio
from backend.scitus.backtest.execution.ExecutionHandler import ExecutionHandler
from backend.scitus.backtest.execution.Order import OrderType


class EventBacktester(BaseBacktester):
    """
    Event-driven backtesting engine.

    Processes market data bar-by-bar, simulating realistic order execution
    with slippage, transaction costs, funding rates, and borrow costs.
    Supports MARKET, LIMIT, and STOP orders.
    """

    def run(self, data: pd.DataFrame, *, strategy: EventStrategy, **kwargs) -> BacktestResult:
        """
        Run an event-driven backtest.

        Args:
            data: OHLCV DataFrame with at least 'close' and 'volume' columns.
            strategy: An EventStrategy instance that generates orders per bar.

        Returns:
            BacktestResult with equity curve, trades, and metrics.
        """
        portfolio = Portfolio(initial_capital=self.initial_capital)
        execution = ExecutionHandler(
            slippage_model=self.slippage_model,
            transaction_cost=self.transaction_cost,
        )

        funding_rate_per_bar = self._resolve_rate(self.funding_rate, data.index)
        borrow_rate_per_bar = self._resolve_rate(self.borrow_rate, data.index)

        position_history = []
        for i, bar in enumerate(DataQueue(data)):
            timestamp = bar.name

            # 1. Mark-to-market
            portfolio.update_market_value(bar)

            # 2. Apply carry costs
            portfolio.apply_carry_costs(
                funding_rate_per_bar.iloc[i],
                borrow_rate_per_bar.iloc[i],
            )

            # 3. Check pending orders (stop-loss, take-profit, limit orders)
            triggered_fills = execution.check_pending_orders(bar)
            for fill in triggered_fills:
                portfolio.apply_fill(fill)

            # 4. Strategy generates signal from current bar
            order = strategy.on_bar(bar, portfolio)

            # 5. Execute or queue order
            if order is not None:
                if order.order_type == OrderType.MARKET:
                    fill = execution.execute(order, bar)
                    if fill:
                        portfolio.apply_fill(fill)
                else:
                    execution.submit_pending(order)

            # 6. Record equity snapshot
            # 6. Record equity and position snapshot
            portfolio.record_snapshot(timestamp)
            net_position = sum(
                pos.quantity if pos.side.value == "BUY" else -pos.quantity
                for pos in portfolio.positions.values()
            )
            position_history.append((timestamp, net_position))

        return self._build_result(portfolio, position_history)

    def _resolve_rate(self, rate: Union[float, pd.Series],
                      index: pd.DatetimeIndex) -> pd.Series:
        """Convert scalar or Series annualized rate to per-bar Series."""
        if isinstance(rate, pd.Series):
            return rate / self.bars_per_year
        return pd.Series(rate / self.bars_per_year, index=index)

    def _build_result(self, portfolio: Portfolio, position_history: list) -> BacktestResult:
        """Assemble BacktestResult from portfolio state."""
        equity = portfolio.equity_series
        returns = equity.pct_change().fillna(0)

        if portfolio.trade_log:
            trades_df = pd.DataFrame([
                {
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "entry_time": trade.entry_time,
                    "exit_time": trade.exit_time,
                    "pnl": trade.pnl,
                    "commission": trade.commission,
                    "slippage": trade.slippage,
                    "holding_bars": trade.holding_bars,
                }
                for trade in portfolio.trade_log
            ])
        else:
            trades_df = pd.DataFrame()

        # Build positions series
        if position_history:
            ids, values = zip(*position_history)
            positions = pd.Series(values, index=pd.DatetimeIndex(ids))
        else:
            positions = pd.Series(0.0, index=equity.index)

        metrics = MetricsCalculator.calculate(
            returns=returns,
            equity=equity,
            positions=positions,
            bars_per_year=self.bars_per_year,
        )

        return BacktestResult(
            equity_curve=equity,
            returns=returns,
            positions=positions,
            trades=trades_df,
            metrics=metrics,
            costs={},
            metadata={"type": "event_driven"},
        )
