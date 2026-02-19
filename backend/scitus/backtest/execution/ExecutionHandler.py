from typing import List, Optional

import pandas as pd

from backend.scitus.backtest.execution.Order import Order, OrderSide, OrderType
from backend.scitus.backtest.execution.Fill import Fill
from backend.scitus.backtest.slippage.BaseSlippage import BaseSlippage


class ExecutionHandler:
    """
    Simulates order matching against bar data.
    Manages pending stop/limit orders and applies slippage + commission.
    """

    def __init__(self, slippage_model: BaseSlippage, transaction_cost: float):
        self.slippage_model = slippage_model
        self.transaction_cost = transaction_cost
        self.pending_orders: List[Order] = []

    def execute(self, order: Order, bar: pd.Series) -> Optional[Fill]:
        """
        Execute a MARKET order immediately against the current bar.

        Fill price = close +/- slippage depending on side.
        Commission = order_value * transaction_cost.
        Returns None if order quantity is invalid.
        """
        if order.quantity <= 0:
            return None

        close = bar["close"]
        volume = bar["volume"]
        timestamp = bar.name

        slippage_cost = self.slippage_model.calculate_single(
            order.quantity, volume, close
        )
        slippage_per_unit = slippage_cost / (order.quantity * close) * close if close > 0 else 0

        if order.side == OrderSide.BUY:
            fill_price = close + slippage_per_unit
        else:
            fill_price = close - slippage_per_unit

        order_value = fill_price * order.quantity
        commission = order_value * self.transaction_cost

        return Fill(
            order_id=order.id,
            side=order.side,
            quantity=order.quantity,
            fill_price=fill_price,
            timestamp=timestamp,
            commission=commission,
            slippage_cost=slippage_cost,
        )

    def submit_pending(self, order: Order):
        """Add a LIMIT or STOP order to the pending queue."""
        self.pending_orders.append(order)

    def check_pending_orders(self, bar: pd.Series) -> List[Fill]:
        """
        Check if any pending orders are triggered by the current bar.

        STOP BUY:   triggers if bar["high"] >= stop_price
        STOP SELL:  triggers if bar["low"]  <= stop_price
        LIMIT BUY:  triggers if bar["low"]  <= limit_price
        LIMIT SELL: triggers if bar["high"] >= limit_price

        Triggered orders are converted to fills and removed from the queue.
        """
        triggered_fills: List[Fill] = []
        remaining_orders: List[Order] = []

        high = bar.get("high", bar["close"])
        low = bar.get("low", bar["close"])

        for order in self.pending_orders:
            fill = self._try_trigger(order, bar, high, low)
            if fill is not None:
                triggered_fills.append(fill)
            else:
                remaining_orders.append(order)

        self.pending_orders = remaining_orders
        return triggered_fills

    def _try_trigger(self, order: Order, bar: pd.Series,
                     high: float, low: float) -> Optional[Fill]:
        """Attempt to trigger a pending order. Returns Fill if triggered, else None."""
        triggered = False
        fill_price_base = bar["close"]

        if order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY and high >= order.stop_price:
                triggered = True
                fill_price_base = order.stop_price
            elif order.side == OrderSide.SELL and low <= order.stop_price:
                triggered = True
                fill_price_base = order.stop_price

        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and low <= order.limit_price:
                triggered = True
                fill_price_base = order.limit_price
            elif order.side == OrderSide.SELL and high >= order.limit_price:
                triggered = True
                fill_price_base = order.limit_price

        if not triggered:
            return None

        volume = bar["volume"]
        slippage_cost = self.slippage_model.calculate_single(
            order.quantity, volume, fill_price_base
        )

        order_value = fill_price_base * order.quantity
        commission = order_value * self.transaction_cost

        return Fill(
            order_id=order.id,
            side=order.side,
            quantity=order.quantity,
            fill_price=fill_price_base,
            timestamp=bar.name,
            commission=commission,
            slippage_cost=slippage_cost,
        )

    def cancel_all_pending(self):
        """Clear the pending order queue."""
        self.pending_orders.clear()
