# Backtester Implementation Plan

## 1. Overview
The **Backtesting Engine** is the critical validation layer for all strategies (Heuristic, ML, GNN). Its purpose is to simulate historical performance to estimate future viability.

**Types:**
1.  **Vectorized Backtester (Phase 1):** Optimized for speed. Uses pandas matrix operations. Best for "Proof of Concept" and initial filtering of ML features.
2.  **Event-Driven Backtester (Phase 2):** Optimized for realism. Loops bar-by-bar. Supports complex order types, stop-losses, and realistic fill simulation. Best for RL Agents and Final Validation.

---

## 2. Vectorized Backtester (Phase 1)

### Architecture
*   **Class:** `VectorizedBacktester`
*   **Path:** `backend/scitus/backtest/VectorizedBacktester.py`

### Inputs
*   `data`: `pd.DataFrame` (OHLCV)
*   `signals`: `pd.Series` (1 = Buy, -1 = Sell, 0 = Hold)
*   `initial_capital`: `float` (Default: 10,000)
*   `transaction_cost`: `float` (Default: 0.001 -> 0.1%)

### Core Logic Steps
1.  **Signal Alignment:** Ensure signals align with price data (shift signals by 1 to avoid lookahead bias).
2.  **Position Calculation:** Convert Signals (1, -1) into Positions (Holding 1 unit, Holding 0 units).
3.  **Returns Calculation:** 
    *   `Strategy Returns = Position * Market Returns`
4.  **Cost Adjustment:** Subtract `transaction_cost` every time the position changes (`diff(Position) != 0`).
5.  **Equity Curve:** Cumulative sum of adjusted returns.

### Metrics Output
*   **Total Return:** `(Final / Initial) - 1`
*   **Sharpe Ratio:** `Mean(Returns) / Std(Returns) * sqrt(252 or 365)`
*   **Max Drawdown:** `Min(Equity / Max_Rolling_Equity - 1)`
*   **Win Rate:** `Count(Positive Trades) / Total Trades`

---

## 3. Event-Driven Backtester (Phase 2)

### Architecture
*   **Class:** `EventBacktester`
*   **Path:** `backend/scitus/backtest/EventBacktester.py`

### Components
*   **DataQueue:** A generator yielding one bar at a time.
*   **Portfolio:** Tracks `Cash` and `Holdings`. Handles sizing (e.g., "Use 50% of cash").
*   **ExecutionHandler:** Simulates fills.
    *   *Slippage Model:* Randomized penalty based on volatility?
    *   *Limit Orders:* Only fill if `Low < Limit Price`.

### Loop Logic
```python
for bar in data:
    1. Update Portfolio (Mark-to-Market)
    2. Check Pending Orders (Stop Loss / Take Profit triggers)
    3. Strategy.generate_signal(history + bar) -> Signal
    4. ExecutionHandler.process(Signal) -> Trade
    5. Portfolio.update(Trade)
```

---

## 4. Visualization Module

### Class
*   **Class:** `BacktestPlotter`
*   **Library:** Plotly (Interactive) or Matplotlib (Static).

### Plots
1.  **Equity Curve:** Strategy vs Benchmark (Buy & Hold).
2.  **Drawdown Underwater Plot:** Visualizing risk depth.
3.  **Trade Markers:** Overlay Buy/Sell arrows on the price chart.
4.  **Monthly Heatmap:** Returns by Month/Year.

---

## 5. Development Roadmap

| Step | Task | Description |
| :--- | :--- | :--- |
| **1** | **Base Class** | Create `BaseBacktester` interface. |
| **2** | **Vectorized Engine** | Implement fast pandas-based logic. |
| **3** | **Metrics Lib** | Implement Sharpe, Sortino, MaxDD functions. |
| **4** | **Unit Tests** | Verify calculations against known scenarios. |
| **5** | **Integration** | Connect `StrategyTransformer` -> `VectorizedBacktester`. |
| **6** | **Visualization** | Generate basic performance plots. |
