from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.scitus.backtest.execution.Order import OrderSide
from backend.scitus.backtest.execution.Fill import Fill
from backend.scitus.backtest.execution.Position import Position
from backend.scitus.backtest.execution.TradeRecord import TradeRecord


class Portfolio:
    """
    Central state manager for the event-driven backtester.
    Tracks cash, open positions, closed trades, and equity history.
    """

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_log: List[TradeRecord] = []
        self.equity_history: List[Tuple[pd.Timestamp, float]] = []
        self._bar_count = 0

    def update_market_value(self, bar: pd.Series):
        """Mark-to-market all positions using bar's close price."""
        current_price = bar["close"]
        for position in self.positions.values():
            position.update_market_value(current_price)

    def apply_fill(self, fill: Fill):
        """
        Process a fill:
        - No position exists -> open new position.
        - Position exists, same side -> increase (average entry price).
        - Position exists, opposite side -> reduce/close/flip.
        """
        symbol = fill.symbol
        self.cash -= fill.commission

        if symbol not in self.positions:
            self._open_position(symbol, fill)
            return

        existing = self.positions[symbol]
        same_side = existing.side == fill.side

        if same_side:
            self._increase_position(existing, fill)
        else:
            self._reduce_or_flip_position(symbol, existing, fill)

    def _open_position(self, symbol: str, fill: Fill):
        """Open a new position from a fill."""
        if fill.side == OrderSide.BUY:
            self.cash -= fill.fill_price * fill.quantity
        else:
            self.cash += fill.fill_price * fill.quantity

        pos = Position(
            symbol=symbol,
            side=fill.side,
            quantity=fill.quantity,
            entry_price=fill.fill_price,
            entry_time=fill.timestamp,
        )
        pos.entry_bar_index = self._bar_count
        # Initialize market value so equity is correct before next MtM cycle
        pos.update_market_value(fill.fill_price)
        self.positions[symbol] = pos

    def _increase_position(self, position: Position, fill: Fill):
        """Increase an existing position (same side). Updates average entry price."""
        if fill.side == OrderSide.BUY:
            self.cash -= fill.fill_price * fill.quantity
        else:
            self.cash += fill.fill_price * fill.quantity

        total_qty = position.quantity + fill.quantity
        position.entry_price = (
            (position.entry_price * position.quantity + fill.fill_price * fill.quantity)
            / total_qty
        )
        position.quantity = total_qty
        # Keep market value in sync so equity is correct before next MtM cycle
        position.update_market_value(fill.fill_price)

    def _reduce_or_flip_position(self, symbol: str, position: Position, fill: Fill):
        """Reduce, close, or flip a position (opposite side fill)."""
        close_qty = min(position.quantity, fill.quantity)
        remainder = fill.quantity - close_qty

        # Calculate PnL for the closed portion
        if position.side == OrderSide.BUY:
            pnl = (fill.fill_price - position.entry_price) * close_qty
            self.cash += fill.fill_price * close_qty
        else:
            pnl = (position.entry_price - fill.fill_price) * close_qty
            self.cash -= fill.fill_price * close_qty

        # Pro-rate costs based on quantity closed vs total fill quantity
        fill_ratio = close_qty / fill.quantity if fill.quantity > 0 else 1.0
        
        # Calculate holding period
        holding_bars = self._bar_count - position.entry_bar_index

        self.trade_log.append(TradeRecord(
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=fill.fill_price,
            quantity=close_qty,
            entry_time=position.entry_time,
            exit_time=fill.timestamp,
            pnl=pnl,
            commission=fill.commission * fill_ratio,
            slippage=fill.slippage_cost * fill_ratio,
            holding_bars=holding_bars,
        ))

        if close_qty >= position.quantity:
            del self.positions[symbol]
        else:
            position.quantity -= close_qty

        # If fill is larger than existing position, open opposite side
        if remainder > 0:
            flipped_fill = Fill(
                order_id=fill.order_id,
                symbol=symbol,
                side=fill.side,
                quantity=remainder,
                fill_price=fill.fill_price,
                timestamp=fill.timestamp,
                commission=0.0,
                slippage_cost=0.0,
            )
            self._open_position(symbol, flipped_fill)

    def apply_carry_costs(self, funding_rate_per_bar: float, borrow_rate_per_bar: float):
        """
        Deduct carry costs from cash:
        - Funding: |position_value| * funding_rate_per_bar (all positions)
        - Borrow: position_value * borrow_rate_per_bar (short positions only)
        """
        for position in self.positions.values():
            # Funding on all positions (use absolute notional, signed rate)
            funding_cost = position.market_value * funding_rate_per_bar
            self.cash -= funding_cost

            # Borrow cost only on short positions (use absolute notional, signed rate)
            if position.side == OrderSide.SELL:
                borrow_cost = abs(position.market_value) * borrow_rate_per_bar
                self.cash -= borrow_cost

    @property
    def total_equity(self) -> float:
        """
        Total portfolio value.
        Long positions: cash + market_value (we own the asset)
        Short positions: cash - market_value (we owe the asset)
        """
        equity = self.cash
        for pos in self.positions.values():
            if pos.side == OrderSide.BUY:
                equity += pos.market_value
            else:
                equity -= pos.market_value
        return equity

    @property
    def equity_series(self) -> pd.Series:
        """Convert equity_history list to indexed pd.Series."""
        if not self.equity_history:
            return pd.Series(dtype=float)
        timestamps, values = zip(*self.equity_history)
        return pd.Series(values, index=pd.DatetimeIndex(timestamps))

    def record_snapshot(self, timestamp: pd.Timestamp):
        """Append (timestamp, total_equity) to equity_history."""
        self.equity_history.append((timestamp, self.total_equity))
        self._bar_count += 1
