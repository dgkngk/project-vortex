import pytest

from backend.scitus.backtest.execution.Order import Order, OrderSide, OrderType


@pytest.mark.unit
def test_market_order_creation():
    """Valid market order with side and quantity."""
    order = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=10.0)
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.MARKET
    assert order.quantity == 10.0
    assert order.symbol == "DEFAULT"


@pytest.mark.unit
def test_stop_order_requires_stop_price():
    """STOP orders must have stop_price; missing it raises ValueError."""
    with pytest.raises(ValueError, match="stop_price"):
        Order(side=OrderSide.SELL, order_type=OrderType.STOP, quantity=5.0)


@pytest.mark.unit
def test_limit_order_requires_limit_price():
    """LIMIT orders must have limit_price; missing it raises ValueError."""
    with pytest.raises(ValueError, match="limit_price"):
        Order(side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=5.0)


@pytest.mark.unit
def test_order_has_unique_id():
    """Each order gets a unique UUID."""
    order_a = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1.0)
    order_b = Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1.0)
    assert order_a.id != order_b.id


@pytest.mark.unit
def test_order_rejects_zero_quantity():
    """Order quantity must be positive."""
    with pytest.raises(ValueError, match="positive"):
        Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0)
