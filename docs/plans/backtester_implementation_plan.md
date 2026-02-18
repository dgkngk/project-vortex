# Backtester Implementation Plan

## 1. Overview

The **Backtesting Engine** is the critical validation layer for all strategies (Heuristic, ML, GNN, RL). It simulates historical performance to estimate future viability.

**Types:**
1. **Vectorized Backtester (Phase 1):** Optimized for speed. Uses pandas matrix operations. Best for proof-of-concept, feature filtering, and parameter optimization.
2. **Event-Driven Backtester (Phase 2):** Optimized for realism. Loops bar-by-bar. Supports complex order types, stop-losses, partial fills. Best for RL agents and final validation.
3. **Portfolio Backtester (Phase 3):** Multi-asset, multi-strategy portfolio simulation with rebalancing and portfolio-level risk constraints.

**Shared Principles:**
- All backtester types read from **Parquet cold store** via `HistoricalDataStore` (DuckDB).
- All return `pd.DataFrame` results — usable in both Jupyter notebooks and the Frontend Strategy Lab.
- All include cost-of-carry modeling (funding rates, borrow costs) as first-class parameters.

---

## 2. Vectorized Backtester (Phase 1)

### Specification

- **Class:** `VectorizedBacktester`
- **Path:** `backend/scitus/backtest/VectorizedBacktester.py`
- **Inherits:** `BaseBacktester`

### Inputs

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `data` | `pd.DataFrame` | Required | OHLCV data from `HistoricalDataStore` |
| `signals` | `pd.Series` | Required | 1 = Buy, -1 = Sell, 0 = Hold |
| `initial_capital` | `float` | 10,000 | Starting capital |
| `transaction_cost` | `float` | 0.001 | Per-trade cost (0.1%) |
| `slippage_model` | `SlippageModel` | `VolumeWeightedSlippage` | Slippage calculator |
| `funding_rate` | `float \| pd.Series` | 0.0 | Per-period funding rate (for crypto perps) |
| `borrow_rate` | `float \| pd.Series` | 0.0 | Annualized borrow cost (for short positions) |

### Core Logic Steps

```python
class VectorizedBacktester(BaseBacktester):
    def run(self, data, signals, **kwargs) -> BacktestResult:
        # Step 1: Signal Alignment
        # Shift signals by 1 bar to prevent lookahead bias
        aligned_signals = signals.shift(1).fillna(0)

        # Step 2: Position Calculation
        # Convert signals to positions (1 = long, -1 = short, 0 = flat)
        positions = aligned_signals.replace(0, method="ffill")

        # Step 3: Market Returns
        market_returns = data["close"].pct_change()

        # Step 4: Strategy Returns (before costs)
        strategy_returns = positions * market_returns

        # Step 5: Transaction Cost Deduction
        # Apply cost every time position changes
        trades = positions.diff().abs()
        cost_per_bar = trades * self.transaction_cost

        # Step 6: Slippage Deduction
        slippage_per_bar = self.slippage_model.calculate(
            trades, data["volume"], data["close"]
        )

        # Step 7: Funding Rate Deduction (Crypto Perps)
        # Funding is paid on the notional value of the position
        funding_cost = positions.abs() * self.funding_rate

        # Step 8: Borrow Cost Deduction (Short Positions)
        # Only applies to short positions, prorated per bar
        borrow_cost = (positions < 0).astype(float) * (self.borrow_rate / bars_per_year)

        # Step 9: Net Returns
        net_returns = strategy_returns - cost_per_bar - slippage_per_bar - funding_cost - borrow_cost

        # Step 10: Equity Curve
        equity_curve = (1 + net_returns).cumprod() * self.initial_capital

        return BacktestResult(
            equity_curve=equity_curve,
            returns=net_returns,
            positions=positions,
            trades=trades,
            costs={"transaction": cost_per_bar, "slippage": slippage_per_bar,
                   "funding": funding_cost, "borrow": borrow_cost}
        )
```

### Slippage Models

| Model | Class | Logic |
|:---|:---|:---|
| Fixed | `FixedSlippage` | Constant penalty per trade (e.g., 0.05%) |
| Volume-Weighted | `VolumeWeightedSlippage` | `slippage = base_slippage * (order_size / avg_volume)^0.5` |
| Volatility-Adjusted | `VolatilitySlippage` | `slippage = ATR(14) * multiplier` |

**Path:** `backend/scitus/backtest/slippage/`

### Metrics Output

Calculated by the `MetricsCalculator` class:

| Metric | Formula | Notes |
|:---|:---|:---|
| Total Return | `(Final / Initial) - 1` | Net of all costs |
| CAGR | `(Final / Initial)^(1/years) - 1` | Annualized |
| Sharpe Ratio | `Mean(Returns) / Std(Returns) * sqrt(periods_per_year)` | Use 252 for stocks, 365 for crypto |
| Sortino Ratio | `Mean(Returns) / Downside_Std * sqrt(periods_per_year)` | Only penalizes downside vol |
| Max Drawdown | `Min(Equity / Rolling_Max_Equity - 1)` | Worst peak-to-trough |
| Win Rate | `Count(Positive Trades) / Total Trades` | Per-trade basis |
| Profit Factor | `Sum(Winning Trades) / Abs(Sum(Losing Trades))` | > 1.5 is good |
| Calmar Ratio | `CAGR / Abs(Max Drawdown)` | Risk-adjusted return |
| Total Costs | `Sum(Transaction + Slippage + Funding + Borrow)` | Cost transparency |
| Avg Trade Duration | `Mean(exit_time - entry_time)` | Time in position |

**Path:** `backend/scitus/backtest/MetricsCalculator.py`

---

## 3. Event-Driven Backtester (Phase 2)

### Specification

- **Class:** `EventBacktester`
- **Path:** `backend/scitus/backtest/EventBacktester.py`
- **Inherits:** `BaseBacktester`

### Components

| Component | Class | Responsibility |
|:---|:---|:---|
| Data Feed | `DataQueue` | Generator yielding one bar at a time |
| Portfolio | `Portfolio` | Tracks `cash`, `holdings`, position sizing |
| Execution | `ExecutionHandler` | Simulates fills, slippage, partial fills |
| Risk | `RiskManager` | Pre-trade checks, stop-loss monitoring |
| Strategy | `BaseStrategy` | Generates signals from visible history only |

### Event Loop

```python
class EventBacktester(BaseBacktester):
    def run(self, data, strategy, risk_manager, **kwargs) -> BacktestResult:
        portfolio = Portfolio(initial_capital=self.initial_capital)
        execution = ExecutionHandler(
            slippage_model=self.slippage_model,
            funding_rate=self.funding_rate,
            borrow_rate=self.borrow_rate,
        )

        for bar in DataQueue(data):
            # 1. Mark-to-market: update portfolio with current prices
            portfolio.update_market_value(bar)

            # 2. Apply funding/borrow costs for current positions
            portfolio.apply_carry_costs(bar, execution)

            # 3. Check pending orders (stop-loss, take-profit triggers)
            triggered_orders = execution.check_pending_orders(bar, portfolio)
            for order in triggered_orders:
                portfolio.execute(order, bar)

            # 4. Risk check: circuit breaker, drawdown limits
            if risk_manager.should_halt(portfolio):
                continue  # Skip signal generation, hold position

            # 5. Strategy generates signal from visible history only
            history = data.loc[:bar.name]  # No future data
            signal = strategy.generate_signal(history)

            # 6. Position sizing via risk manager
            sized_order = risk_manager.size_order(signal, portfolio, bar)

            # 7. Execution handler processes order
            if sized_order:
                fill = execution.execute(sized_order, bar)
                portfolio.apply_fill(fill)

        return BacktestResult(
            equity_curve=portfolio.equity_history,
            trades=portfolio.trade_log,
            ...
        )
```

### Execution Handler Features

- **Volume-Weighted Slippage:** Slippage proportional to `order_size / bar_volume`.
- **Partial Fills:** If order size > available volume at price level, simulate partial execution.
- **Limit Orders:** Only fill if `bar.low <= limit_price` (buy) or `bar.high >= limit_price` (sell).
- **Funding Settlement:** Deduct funding every 8 hours (crypto perps) from portfolio cash.
- **Borrow Cost Settlement:** Deduct daily borrow cost for short positions.

---

## 4. Walk-Forward Validation

### Specification

- **Class:** `WalkForwardValidator`
- **Path:** `backend/scitus/validation/WalkForwardValidator.py`

### Methods

```python
class WalkForwardValidator:
    def generate_splits(
        self,
        data: pd.DataFrame,
        train_window: int,   # e.g., 252 bars (1 year)
        test_window: int,    # e.g., 63 bars (1 quarter)
        step: int            # e.g., 63 bars (slide by 1 quarter)
    ) -> list[TrainTestSplit]:
        """Generate walk-forward train/test splits.

        Example with 3 years of data, 1yr train, 3mo test:
          Split 1: Train [0:252],   Test [252:315]
          Split 2: Train [63:315],  Test [315:378]
          Split 3: Train [126:378], Test [378:441]
          ...
        """

    def validate(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        backtester: BaseBacktester,
    ) -> WalkForwardResult:
        """Run walk-forward validation and aggregate OOS metrics."""

    def monte_carlo(
        self,
        trades: pd.DataFrame,
        n_simulations: int = 1000,
    ) -> MonteCarloResult:
        """Shuffle trade order to test robustness.
        Returns confidence intervals for Sharpe, MaxDD, Total Return.
        """
```

### OOS Reserve Rule

- Hold out the most recent **20%** of available data.
- This data is **never** used during walk-forward optimization.
- Only used once for final "go/no-go" validation before paper trading.

---

## 5. Visualization Module

### Specification

- **Class:** `BacktestPlotter`
- **Path:** `backend/scitus/backtest/BacktestPlotter.py`
- **Library:** Plotly (interactive, preferred for notebooks and frontend embedding).

### Plots

| Plot | Description | Use Case |
|:---|:---|:---|
| Equity Curve | Strategy vs Benchmark (Buy & Hold) | Primary performance view |
| Drawdown Underwater | Risk depth over time | Risk assessment |
| Trade Markers | Buy/Sell arrows on price chart | Trade quality review |
| Monthly Heatmap | Returns by Month × Year | Seasonality analysis |
| Cost Breakdown | Stacked bar: Transaction, Slippage, Funding, Borrow | Cost transparency |
| Walk-Forward OOS | OOS equity segments stitched together | Validation visualization |

### Output Formats

- `plot_results() -> plotly.Figure` — Interactive chart for Jupyter / Frontend.
- `to_dataframe() -> pd.DataFrame` — Raw results for further analysis.
- `to_json() -> dict` — Serialized for FastAPI / MCP responses.

---

## 6. Base Classes & Data Models

### BaseBacktester

```python
# backend/scitus/backtest/BaseBacktester.py
from abc import ABC, abstractmethod

class BaseBacktester(ABC):
    def __init__(
        self,
        initial_capital: float = 10_000,
        transaction_cost: float = 0.001,
        slippage_model: SlippageModel = None,
        funding_rate: float | pd.Series = 0.0,
        borrow_rate: float | pd.Series = 0.0,
    ): ...

    @abstractmethod
    def run(self, data, signals_or_strategy, **kwargs) -> BacktestResult: ...
```

### BacktestResult

```python
# backend/scitus/backtest/BacktestResult.py
@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame          # Entry/exit/PnL/duration per trade
    metrics: dict[str, float]      # Sharpe, MaxDD, WinRate, etc.
    costs: dict[str, pd.Series]    # Breakdown: transaction, slippage, funding, borrow
    metadata: dict                 # Strategy name, params, data range

    def to_dataframe(self) -> pd.DataFrame: ...
    def to_json(self) -> dict: ...
    def plot(self) -> plotly.Figure: ...
```

---

## 7. Directory Structure

```
backend/scitus/backtest/
├── __init__.py
├── BaseBacktester.py
├── VectorizedBacktester.py
├── EventBacktester.py
├── PortfolioBacktester.py
├── BacktestResult.py
├── MetricsCalculator.py
├── BacktestPlotter.py
├── slippage/
│   ├── __init__.py
│   ├── BaseSlippage.py
│   ├── FixedSlippage.py
│   ├── VolumeWeightedSlippage.py
│   └── VolatilitySlippage.py
└── execution/
    ├── __init__.py
    ├── ExecutionHandler.py
    ├── DataQueue.py
    └── Portfolio.py

backend/scitus/validation/
├── __init__.py
├── WalkForwardValidator.py
└── MonteCarloSimulator.py
```

---

## 8. Development Roadmap

| Step | Task | Description | Depends On |
|:---|:---|:---|:---|
| 1 | `BaseBacktester` + `BacktestResult` | Abstract base class and result dataclass | — |
| 2 | `SlippageModel` hierarchy | Fixed, Volume-Weighted, Volatility slippage | — |
| 3 | `MetricsCalculator` | Sharpe, Sortino, MaxDD, Calmar, costs | — |
| 4 | `VectorizedBacktester` | Fast pandas engine with full cost modeling | Steps 1-3 |
| 5 | Unit Tests | Verify calculations against known scenarios | Step 4 |
| 6 | `HistoricalDataStore` integration | Load Parquet data via DuckDB | Level -1 |
| 7 | Integration Tests | `StrategyTransformer` → `VectorizedBacktester` | Steps 4, 6 |
| 8 | `WalkForwardValidator` | Train/test splitting and OOS validation | Step 4 |
| 9 | `BacktestPlotter` | Plotly-based visualization | Step 4 |
| 10 | `EventBacktester` components | `DataQueue`, `Portfolio`, `ExecutionHandler` | Steps 1-3 |
| 11 | `EventBacktester` | Full event-driven loop with funding/borrow | Step 10 |
| 12 | `PortfolioBacktester` | Multi-asset with rebalancing | Steps 4, 11 |
