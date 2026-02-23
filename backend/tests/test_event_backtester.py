import pytest
import numpy as np
import pandas as pd
from typing import Optional

from backend.scitus.backtest.EventBacktester import EventBacktester
from backend.scitus.backtest.EventStrategy import EventStrategy
from backend.scitus.backtest.execution.Order import Order, OrderSide, OrderType
from backend.scitus.backtest.execution.Portfolio import Portfolio


class BuyAndHoldStrategy(EventStrategy):
    """Always long on the first bar, then hold."""
    def __init__(self):
        super().__init__(config={})
        self._entered = False

    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        if not self._entered:
            self._entered = True
            capital = portfolio.cash
            price = bar["close"]
            qty = capital / price
            return Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=qty)
        return None


class NeverTradeStrategy(EventStrategy):
    """Does nothing every bar."""
    def __init__(self):
        super().__init__(config={})

    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        return None


class ShortOnlyStrategy(EventStrategy):
    """Short on the first bar, then hold."""
    def __init__(self):
        super().__init__(config={})
        self._entered = False

    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        if not self._entered:
            self._entered = True
            capital = portfolio.cash
            price = bar["close"]
            qty = capital / price
            return Order(side=OrderSide.SELL, order_type=OrderType.MARKET, quantity=qty)
        return None


class StopLossStrategy(EventStrategy):
    """Buy on bar 0, then submit a stop-loss sell."""
    def __init__(self, stop_price: float):
        super().__init__(config={})
        self._entered = False
        self._stop_submitted = False
        self._stop_price = stop_price

    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        if not self._entered:
            self._entered = True
            price = bar["close"]
            qty = portfolio.cash / price
            return Order(side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=qty)
        if not self._stop_submitted and portfolio.positions:
            self._stop_submitted = True
            pos = list(portfolio.positions.values())[0]
            return Order(
                symbol=pos.symbol,
                side=OrderSide.SELL, order_type=OrderType.STOP,
                quantity=pos.quantity, stop_price=self._stop_price,
            )
        return None


class LimitBuyStrategy(EventStrategy):
    """Submit a limit buy on bar 0."""
    def __init__(self, limit_price: float, quantity: float):
        super().__init__(config={})
        self._submitted = False
        self._limit_price = limit_price
        self._quantity = quantity

    def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
        if not self._submitted:
            self._submitted = True
            return Order(
                side=OrderSide.BUY, order_type=OrderType.LIMIT,
                quantity=self._quantity, limit_price=self._limit_price,
            )
        return None


@pytest.fixture
def rising_market():
    dates = pd.date_range("2023-01-01", periods=10)
    return pd.DataFrame({
        "close": np.linspace(100, 110, 10),
        "high": np.linspace(101, 111, 10),
        "low": np.linspace(99, 109, 10),
        "volume": [1000] * 10,
    }, index=dates)


@pytest.fixture
def dropping_market():
    dates = pd.date_range("2023-01-01", periods=10)
    return pd.DataFrame({
        "close": np.linspace(100, 80, 10),
        "high": np.linspace(101, 81, 10),
        "low": np.linspace(99, 79, 10),
        "volume": [1000] * 10,
    }, index=dates)


@pytest.mark.unit
def test_buy_and_hold_gains_in_uptrend(rising_market):
    """Event-driven buy-and-hold in a rising market should gain."""
    backtester = EventBacktester(
        initial_capital=10_000,
        transaction_cost=0.0,
    )
    result = backtester.run(rising_market, strategy=BuyAndHoldStrategy())

    assert result.equity_curve.iloc[-1] > 10_000
    assert result.metrics["total_return"] > 0


@pytest.mark.unit
def test_no_lookahead_bias(rising_market):
    """Strategy receives bars sequentially."""
    timestamps = []

    class RecorderStrategy(EventStrategy):
        def __init__(self):
            super().__init__(config={})

        def on_bar(self, bar: pd.Series, portfolio: Portfolio) -> Optional[Order]:
            timestamps.append(bar.name)
            return None

    backtester = EventBacktester(initial_capital=10_000)
    backtester.run(rising_market, strategy=RecorderStrategy())

    # Ensure we saw all dates in order
    assert len(timestamps) == 10
    assert timestamps == list(rising_market.index)


@pytest.mark.unit
def test_stop_loss_triggers(dropping_market):
    """Stop-loss exits position when price drops below threshold."""
    backtester = EventBacktester(
        initial_capital=10_000,
        transaction_cost=0.0,
    )
    # Stop at 90 -- market drops to 80 so it should trigger
    strategy = StopLossStrategy(stop_price=90.0)
    result = backtester.run(dropping_market, strategy=strategy)

    # Position should have been closed by stop-loss
    assert len(result.trades) > 0


@pytest.mark.unit
def test_limit_order_fills(rising_market):
    """Limit order fills when market low reaches limit price."""
    # Limit buy at 101: submitted on bar 0, bar 1 low (~100.1) <= 101 -> triggers
    backtester = EventBacktester(
        initial_capital=10_000,
        transaction_cost=0.0,
    )
    strategy = LimitBuyStrategy(limit_price=101.0, quantity=10.0)
    result = backtester.run(rising_market, strategy=strategy)

    # Limit fill at 101 with 10 units on a rising market -> gains
    assert result.equity_curve.iloc[-1] > 10_000


@pytest.mark.unit
def test_short_in_uptrend_loses(rising_market):
    """Short position loses in rising market."""
    backtester = EventBacktester(
        initial_capital=10_000,
        transaction_cost=0.0,
    )
    result = backtester.run(rising_market, strategy=ShortOnlyStrategy())

    assert result.equity_curve.iloc[-1] < 10_000


@pytest.mark.unit
def test_funding_costs_applied(rising_market):
    """Funding rate reduces equity compared to no-funding run."""
    # No funding
    bt_clean = EventBacktester(initial_capital=10_000, transaction_cost=0.0)
    res_clean = bt_clean.run(rising_market, strategy=BuyAndHoldStrategy())

    # With funding
    bt_funded = EventBacktester(
        initial_capital=10_000, transaction_cost=0.0,
        funding_rate=0.50, bars_per_year=10,
    )
    res_funded = bt_funded.run(rising_market, strategy=BuyAndHoldStrategy())

    assert res_funded.equity_curve.iloc[-1] < res_clean.equity_curve.iloc[-1]


@pytest.mark.unit
def test_borrow_costs_on_shorts(rising_market):
    """Borrow cost only applied to shorts, reducing equity further."""
    bt_no_borrow = EventBacktester(
        initial_capital=10_000, transaction_cost=0.0, borrow_rate=0.0,
    )
    bt_with_borrow = EventBacktester(
        initial_capital=10_000, transaction_cost=0.0,
        borrow_rate=0.50, bars_per_year=10,
    )

    res_no = bt_no_borrow.run(rising_market, strategy=ShortOnlyStrategy())
    res_yes = bt_with_borrow.run(rising_market, strategy=ShortOnlyStrategy())

    # Borrow costs make shorting even worse
    assert res_yes.equity_curve.iloc[-1] < res_no.equity_curve.iloc[-1]


@pytest.mark.unit
def test_empty_strategy(rising_market):
    """Strategy that never trades -> flat equity."""
    backtester = EventBacktester(initial_capital=10_000)
    result = backtester.run(rising_market, strategy=NeverTradeStrategy())

    assert result.equity_curve.iloc[-1] == pytest.approx(10_000.0)
    assert result.metrics["total_return"] == pytest.approx(0.0)
