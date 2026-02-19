from dataclasses import dataclass

import pandas as pd

from backend.scitus.backtest.execution.Order import OrderSide


@dataclass
class Position:
    """
    Tracks an open position in a single symbol.
    """
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    entry_time: pd.Timestamp
    unrealized_pnl: float = 0.0
    market_value: float = 0.0

    def update_market_value(self, current_price: float):
        """Recalculate unrealized PnL and market value using current price."""
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
        self.market_value = current_price * self.quantity
