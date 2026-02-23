import pytest
import pandas as pd

from backend.scitus.backtest.execution.Portfolio import Portfolio
from backend.scitus.backtest.execution.Fill import Fill
from backend.scitus.backtest.execution.Order import OrderSide


@pytest.fixture
def portfolio():
    return Portfolio(initial_capital=10_000.0)


def _make_fill(side, quantity, price, timestamp=None, commission=0.0, slippage=0.0):
    return Fill(
        order_id="test-order",
        symbol="DEFAULT",
        side=side,
        quantity=quantity,
        fill_price=price,
        timestamp=timestamp or pd.Timestamp("2023-01-01"),
        commission=commission,
        slippage_cost=slippage,
    )


@pytest.mark.unit
def test_initial_state(portfolio):
    """Cash = initial_capital, no positions."""
    assert portfolio.cash == 10_000.0
    assert len(portfolio.positions) == 0
    assert len(portfolio.trade_log) == 0


@pytest.mark.unit
def test_open_long_position(portfolio):
    """BUY fill opens long, deducts cash."""
    fill = _make_fill(OrderSide.BUY, quantity=10, price=100.0)
    portfolio.apply_fill(fill)

    assert "DEFAULT" in portfolio.positions
    pos = portfolio.positions["DEFAULT"]
    assert pos.side == OrderSide.BUY
    assert pos.quantity == 10
    assert pos.entry_price == 100.0
    assert portfolio.cash == pytest.approx(9_000.0)


@pytest.mark.unit
def test_open_short_position(portfolio):
    """SELL fill opens short, adds cash from short sale."""
    fill = _make_fill(OrderSide.SELL, quantity=10, price=100.0)
    portfolio.apply_fill(fill)

    pos = portfolio.positions["DEFAULT"]
    assert pos.side == OrderSide.SELL
    assert pos.quantity == 10
    assert portfolio.cash == pytest.approx(11_000.0)


@pytest.mark.unit
def test_close_long_position(portfolio):
    """Opposite fill closes position, creates TradeRecord."""
    buy_fill = _make_fill(OrderSide.BUY, quantity=10, price=100.0)
    portfolio.apply_fill(buy_fill)

    sell_fill = _make_fill(
        OrderSide.SELL, quantity=10, price=110.0,
        timestamp=pd.Timestamp("2023-01-02"),
    )
    portfolio.apply_fill(sell_fill)

    assert "DEFAULT" not in portfolio.positions
    assert len(portfolio.trade_log) == 1
    trade = portfolio.trade_log[0]
    assert trade.pnl == pytest.approx(100.0)  # (110 - 100) * 10


@pytest.mark.unit
def test_position_flip(portfolio):
    """BUY while short -> close short + open long remainder."""
    # Open short position of 5 units
    short_fill = _make_fill(OrderSide.SELL, quantity=5, price=100.0)
    portfolio.apply_fill(short_fill)

    # Buy 8 units -> close 5-unit short + open 3-unit long
    buy_fill = _make_fill(
        OrderSide.BUY, quantity=8, price=95.0,
        timestamp=pd.Timestamp("2023-01-02"),
    )
    portfolio.apply_fill(buy_fill)

    assert len(portfolio.trade_log) == 1
    trade = portfolio.trade_log[0]
    assert trade.pnl == pytest.approx(25.0)  # (100 - 95) * 5

    assert "DEFAULT" in portfolio.positions
    pos = portfolio.positions["DEFAULT"]
    assert pos.side == OrderSide.BUY
    assert pos.quantity == 3


@pytest.mark.unit
def test_mark_to_market(portfolio):
    """Unrealized PnL updates on price change."""
    fill = _make_fill(OrderSide.BUY, quantity=10, price=100.0)
    portfolio.apply_fill(fill)

    bar = pd.Series({"close": 110.0, "volume": 1000}, name=pd.Timestamp("2023-01-02"))
    portfolio.update_market_value(bar)

    pos = portfolio.positions["DEFAULT"]
    assert pos.unrealized_pnl == pytest.approx(100.0)  # (110 - 100) * 10


@pytest.mark.unit
def test_carry_costs_funding(portfolio):
    """Funding deducted from cash for all positions."""
    fill = _make_fill(OrderSide.BUY, quantity=10, price=100.0)
    portfolio.apply_fill(fill)

    bar = pd.Series({"close": 100.0, "volume": 1000}, name=pd.Timestamp("2023-01-01"))
    portfolio.update_market_value(bar)

    cash_before = portfolio.cash
    portfolio.apply_carry_costs(funding_rate_per_bar=0.001, borrow_rate_per_bar=0.0)

    # Funding = market_value * rate = 1000 * 0.001 = 1.0
    assert portfolio.cash == pytest.approx(cash_before - 1.0)


@pytest.mark.unit
def test_carry_costs_borrow(portfolio):
    """Borrow cost only on short positions."""
    fill = _make_fill(OrderSide.SELL, quantity=10, price=100.0)
    portfolio.apply_fill(fill)

    bar = pd.Series({"close": 100.0, "volume": 1000}, name=pd.Timestamp("2023-01-01"))
    portfolio.update_market_value(bar)

    cash_before = portfolio.cash
    portfolio.apply_carry_costs(funding_rate_per_bar=0.0, borrow_rate_per_bar=0.002)

    # Borrow = market_value * rate = 1000 * 0.002 = 2.0
    assert portfolio.cash == pytest.approx(cash_before - 2.0)


@pytest.mark.unit
def test_equity_history(portfolio):
    """Snapshots recorded correctly per bar."""
    portfolio.record_snapshot(pd.Timestamp("2023-01-01"))
    portfolio.record_snapshot(pd.Timestamp("2023-01-02"))

    eq = portfolio.equity_series
    assert len(eq) == 2
    assert eq.iloc[0] == 10_000.0
    assert eq.iloc[1] == 10_000.0
