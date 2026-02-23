import pytest
import pandas as pd

from backend.scitus.backtest.execution.ExecutionHandler import ExecutionHandler
from backend.scitus.backtest.execution.Order import Order, OrderSide, OrderType
from backend.scitus.backtest.slippage.FixedSlippage import FixedSlippage


@pytest.fixture
def handler():
    return ExecutionHandler(
        slippage_model=FixedSlippage(slippage_pct=0.001),
        transaction_cost=0.001,
    )


@pytest.fixture
def bar():
    return pd.Series(
        {"close": 100.0, "high": 105.0, "low": 95.0, "volume": 1000},
        name=pd.Timestamp("2023-01-01"),
    )


@pytest.mark.unit
def test_market_order_fills_at_close(handler, bar):
    """Market order filled near close price."""
    order = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10.0)
    fill = handler.execute(order, bar)

    assert fill is not None
    assert fill.quantity == 10.0
    assert fill.fill_price > 0


@pytest.mark.unit
def test_slippage_applied(handler, bar):
    """Fill price differs from close by slippage."""
    order = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10.0)
    fill = handler.execute(order, bar)

    # BUY slippage makes fill_price > close
    assert fill.fill_price >= bar["close"]
    assert fill.slippage_cost > 0


@pytest.mark.unit
def test_commission_calculated(handler, bar):
    """Commission = order_value * cost_rate."""
    order = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10.0)
    fill = handler.execute(order, bar)

    expected_commission = fill.fill_price * fill.quantity * 0.001
    assert fill.commission == pytest.approx(expected_commission, rel=1e-6)


@pytest.mark.unit
def test_stop_buy_triggers(handler, bar):
    """Stop buy triggers when high >= stop_price."""
    order = Order(
        side=OrderSide.BUY, order_type=OrderType.STOP,
        quantity=5.0, stop_price=104.0,
    )
    handler.submit_pending(order)
    fills = handler.check_pending_orders(bar)

    assert len(fills) == 1
    assert fills[0].side == OrderSide.BUY


@pytest.mark.unit
def test_stop_sell_triggers(handler, bar):
    """Stop sell triggers when low <= stop_price."""
    order = Order(
        side=OrderSide.SELL, order_type=OrderType.STOP,
        quantity=5.0, stop_price=96.0,
    )
    handler.submit_pending(order)
    fills = handler.check_pending_orders(bar)

    assert len(fills) == 1
    assert fills[0].side == OrderSide.SELL


@pytest.mark.unit
def test_limit_buy_triggers(handler, bar):
    """Limit buy triggers when low <= limit_price."""
    order = Order(
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=5.0, limit_price=96.0,
    )
    handler.submit_pending(order)
    fills = handler.check_pending_orders(bar)

    assert len(fills) == 1
    assert fills[0].side == OrderSide.BUY


@pytest.mark.unit
def test_limit_sell_triggers(handler, bar):
    """Limit sell triggers when high >= limit_price."""
    order = Order(
        side=OrderSide.SELL, order_type=OrderType.LIMIT,
        quantity=5.0, limit_price=104.0,
    )
    handler.submit_pending(order)
    fills = handler.check_pending_orders(bar)

    assert len(fills) == 1
    assert fills[0].side == OrderSide.SELL


@pytest.mark.unit
def test_pending_order_not_triggered(handler, bar):
    """No trigger if price doesn't reach level."""
    order = Order(
        side=OrderSide.BUY, order_type=OrderType.STOP,
        quantity=5.0, stop_price=110.0,
    )
    handler.submit_pending(order)
    fills = handler.check_pending_orders(bar)

    assert len(fills) == 0
    assert len(handler.pending_orders) == 1


@pytest.mark.unit
def test_triggered_order_removed(handler, bar):
    """Triggered order is removed from pending list."""
    order = Order(
        side=OrderSide.BUY, order_type=OrderType.STOP,
        quantity=5.0, stop_price=104.0,
    )
    handler.submit_pending(order)
    handler.check_pending_orders(bar)

    assert len(handler.pending_orders) == 0
