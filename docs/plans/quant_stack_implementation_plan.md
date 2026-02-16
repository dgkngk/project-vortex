# Quantitative Trading Stack — Master Implementation Plan

## Overview
- **Goal:** Production-grade quantitative trading system generating >50% alpha over buy-and-hold.
- **Scope:** Multi-Asset Class (Crypto, Stocks, Commodities).
- **Philosophy:** Transition from heuristic rule-based systems → probabilistic, network-aware, autonomous AI systems.
- **Interfaces:** React Frontend (Human Operator) + MCP Server (AI Agent) + FastAPI REST (Shared Backend).

---

## Level -1: Data Foundation (Before Everything Else)

> Without clean data and fast storage, every backtest result is a lie.

### 1. Tiered Storage Architecture

| Tier | Technology | Purpose | Access Pattern |
|:---|:---|:---|:---|
| 🔴 Hot | Redis | Real-time state, latest quotes, session cache | Sub-ms reads |
| 🟡 Warm | InfluxDB | Recent history for live charts/monitoring (last 30 days) | Seconds |
| 🔵 Cold | Parquet + DuckDB | Full historical data for backtesting & ML training | Batch reads |

**Implementation Steps:**
1. **Create `backend/etl/storage/` module** with a `StorageRouter` class that directs writes to appropriate tiers based on data age.
2. **Parquet Partitioning:** Partition files by `asset_class/asset_symbol/year/month/` for efficient range scans.
3. **DuckDB Query Layer:** Create a `HistoricalDataStore` class wrapping DuckDB that exposes `query(asset, start, end, timeframe) -> pd.DataFrame`.
4. **Migration Script:** Backfill existing InfluxDB/Postgres data into Parquet cold store.
5. **Write Path:** ETL Loaders write to Hot (Redis) + Warm (InfluxDB) in real-time; a nightly job archives Warm → Cold (Parquet).

**Directory Structure:**
```
backend/etl/data_access/storage/
├── __init__.py
├── StorageRouter.py         # Routes data to appropriate tier
├── HistoricalDataStore.py   # DuckDB wrapper for cold store queries
├── ParquetWriter.py         # Writes DataFrames to partitioned Parquet files
└── MigrationScripts.py      # Backfill and archival jobs
```

### 2. Data Maintenance Module

Handles corporate actions, survivorship bias, and ticker lifecycle — the silent killers of backtest accuracy.

**Implementation Steps:**
1. **Create `backend/etl/maintenance/` module.**
2. **`AdjustmentEngine`** — Fetches and applies split/dividend adjustment factors to historical OHLCV data before it enters the Feature Store.
   - Input: Raw OHLCV + corporate actions calendar (from Polygon API).
   - Output: Adjusted OHLCV with `adjustment_factor` column.
   - Method: `adjust(raw_data: pd.DataFrame, actions: list[CorporateAction]) -> pd.DataFrame`
3. **`TickerMapper`** — Maintains a mapping table for renamed/migrated tickers (LEND→AAVE, MATIC→POL) and stitches their price histories into continuous series.
   - Storage: `ticker_mappings.json` or Postgres table.
   - Method: `resolve(ticker: str, date: datetime) -> str` returns the canonical ticker at that point in time.
4. **`UniverseBuilder`** — Constructs the full historical asset universe including delisted/dead tickers to prevent survivorship bias.
   - Method: `get_universe(date: datetime, asset_class: str) -> list[str]` returns all tickers that were tradeable on that date.
   - Source: Exchange API historical listings or third-party data (e.g., Polygon reference data).

**Directory Structure:**
```
backend/etl/maintenance/
├── __init__.py
├── AdjustmentEngine.py     # Split/dividend adjustment
├── TickerMapper.py          # Ticker rename/migration mapping
└── UniverseBuilder.py       # Survivorship-bias-free universe
```

### 3. Feature Store

Consistent feature calculation with point-in-time correctness.

**Implementation Steps:**
1. **Create `backend/scitus/features/` module.**
2. **`FeatureStore`** class — Central registry and calculator for all features.
   - Method: `compute(asset, features: list[str], as_of: datetime) -> pd.DataFrame`
   - Enforces point-in-time: only uses data available at `as_of` timestamp.
3. **`FeatureRegistry`** — YAML/JSON config file documenting every feature: name, calculation logic, data source, staleness tolerance, version.
4. **Storage:** Features stored as Parquet files alongside raw data, partitioned by `asset/feature_version/`.
5. **Versioning:** V1 RSI (14-period) and V2 RSI (adaptive) both reproducible via version tag.

### 4. Jupyter Research Environment

**Implementation Steps:**
1. Add `jupyterlab` to `pyproject.toml` dev dependencies.
2. Create `notebooks/` directory with example notebooks:
   - `01_data_exploration.ipynb` — Load from HistoricalDataStore, plot candles.
   - `02_backtest_example.ipynb` — Import BacktestEngine, run strategy, display results as DataFrame.
3. Ensure all engine classes (`BacktestEngine`, `FeatureStore`, `StrategyFactory`) return `pd.DataFrame` results, not just JSON.

---

## Level 0: Foundation & Validation

### 1. Vectorized Backtester
> See: [`backtester_implementation_plan.md`](./backtester_implementation_plan.md) for full specification.

- Fast pandas-based backtesting for proof-of-concept and initial feature filtering.
- **Must include:** Transaction costs, slippage, **funding rates**, **borrow costs**.
- **Data source:** Parquet cold store via `HistoricalDataStore`.

### 2. Event-Driven Backtester
> See: [`backtester_implementation_plan.md`](./backtester_implementation_plan.md) for full specification.

- Bar-by-bar simulation with order book interaction, stop-loss/take-profit, partial fills.
- Prevents lookahead bias. Required for RL agent training.

### 3. Risk Management Engine

**Class:** `RiskManager`
**Path:** `backend/scitus/risk/RiskManager.py`

**Components:**
1. **`PositionSizer`** — Calculates position size using:
   - Fixed Fractional (risk X% of capital per trade)
   - Kelly Criterion (optimal sizing based on win rate and payoff ratio)
   - Volatility-targeted sizing (ATR-based: size inversely proportional to volatility)
   - Method: `calculate_size(capital, risk_pct, stop_distance, method) -> float`
2. **`StopLossEngine`** — Generates stop-loss levels:
   - Fixed percentage, ATR-based, trailing, time-based exit
   - Method: `get_stop(entry_price, method, params) -> StopOrder`
3. **`PortfolioConstraints`** — Enforces portfolio-level risk limits:
   - Max drawdown circuit breaker (halt trading if DD > threshold)
   - Max exposure per asset class (e.g., max 30% in crypto)
   - Sector concentration limits
   - Correlation-aware diversification check
   - Method: `validate_trade(proposed_trade, portfolio) -> (bool, str)`

**Directory Structure:**
```
backend/scitus/risk/
├── __init__.py
├── RiskManager.py
├── PositionSizer.py
├── StopLossEngine.py
└── PortfolioConstraints.py
```

### 4. Walk-Forward Validation Framework

**Class:** `WalkForwardValidator`
**Path:** `backend/scitus/validation/WalkForwardValidator.py`

**Implementation Steps:**
1. **Walk-Forward Split:** Train on N bars, test on M bars, slide forward by M, repeat.
   - Method: `generate_splits(data, train_window, test_window, step) -> list[TrainTestSplit]`
2. **OOS Reserve:** Hold out most recent 20% of data — never touched until final validation.
3. **Monte Carlo Shuffle:** Randomize trade order to test if returns are sequence-dependent.
   - Method: `monte_carlo(trades, n_simulations) -> ConfidenceInterval`
4. **Combinatorial Purged CV:** For ML models — prevents data leakage between folds.

### 5. Multi-Asset Portfolio Backtester

**Class:** `PortfolioBacktester`
**Path:** `backend/scitus/backtest/PortfolioBacktester.py`

- Runs N strategies on N assets simultaneously with portfolio-level constraints.
- Handles rebalancing (daily/weekly) with turnover constraints.
- Cross-asset signals (e.g., NVDA signal → BTC position).
- Method: `run(strategies: dict[str, Strategy], data: dict[str, pd.DataFrame], rebalance_freq) -> PortfolioResult`

### 6. Execution Handler

- **`ExchangeClient`** — Wrapper around CCXT (Crypto), IBKR/Alpaca (Stocks).
- **`OrderManager`** — Tracks order states: `PENDING`, `OPEN`, `FILLED`, `CANCELLED`, `REJECTED`.
- Method: `submit_order(order: Order) -> OrderResult`
- Paper trading mode: Same interface, simulated fills.

---

## Level 1: Heuristic Strategies

Refining rule-based logic to serve as Feature Generators for ML levels.

- **Composite Strategies:** Combine Trend + Volatility indicators.
- **Voting Strategies:** Ensemble consensus from multiple technical indicators.
- **Role:** These generate **features** for Level 2+ (e.g., "RSI says Overbought" → binary feature).
- **Monitoring:** Each strategy has performance decay detection — alert if live Sharpe drops below historical Sharpe by > 1 SD.

---

## Level 2: Predictive Modeling (Supervised Learning)

### 1. Tabular Models (XGBoost / LightGBM)
- **Data:** OHLCV + Technical Indicators + Macro Data (Interest Rates, DXY) + Alternative Data (sentiment, on-chain, options flow).
- **Target:** `Target_5m` (Binary: Will price rise > 0.5% in next 5 mins?).
- **Feature Engineering:**
  - Stationarity checks (log-returns, fractional differentiation).
  - Time-features (hour of day, day of week, pre/post market).
  - All features via `FeatureStore` with point-in-time correctness.
- **Implementation:** `MLStrategy` class loading `.json` booster models.
- **Validation:** Walk-Forward with purged CV. No standard train/test split.

### 2. Sequence Models (LSTM / Temporal Fusion Transformers)
- **Data:** Sliding window of raw normalized returns.
- **Edge:** Capturing path-dependency (e.g., rapid crash vs slow bleed).

### 3. Model Lifecycle
- **Model Registry:** MLFlow for versioning (`XGBoost_v4_BTC` vs `GNN_v1_Global`).
- **Concept Drift Detection:** Monitor PSI / KL-divergence on feature distributions.
- **Performance Decay Alerts:** If live Sharpe < backtest Sharpe - 1 SD → alert.
- **Shadow Mode:** Run new models in parallel without execution. Compare for N days.
- **A/B Testing:** Route 10% capital to Model B, 90% to Model A.
- **Auto-Retrain:** Scheduled retrain on new data with automatic validation gate.

---

## Level 3: Market Regimes (Unsupervised Learning)

### Hidden Markov Models (HMM)
- **Objective:** Classify market state → `Bull`, `Bear`, `HighVol_Chop`, `LowVol_Chop`.
- **Inputs:** Volatility (ATR), Returns, Volume.
- **Meta-Strategy:** Switch Level 2 models based on regime.
  - If `HighVol_Chop` → Disable trend models, enable mean reversion.
  - If `Bull` → Increase position sizes via risk manager.
- **Regime-Aware Risk:** Tighten stops in `HighVol` regimes, widen in `LowVol_Chop`.

---

## Level 3.5: Portfolio Optimization

- **Mean-Variance Optimization** — Classic Markowitz.
- **Risk Parity** — Equal risk contribution across assets.
- **Hierarchical Risk Parity (HRP)** — Clustering-based, no matrix inversion.
- **Kelly-Optimal Allocation** — Optimal capital split across strategies.
- **Implementation:** `PortfolioOptimizer` class in `backend/scitus/portfolio/`.

---

## Level 4: Network Effects (Graph Neural Networks)

### Before Building GNN:
1. **Baseline first:** Build a simple correlation-based portfolio rotation strategy. If alpha isn't in plain correlations, a GNN won't find it.
2. **Practical considerations:**
   - Graph update frequency: Weekly rolling correlations.
   - Training data: Daily bars, 600 nodes × 252 bars/year is small — consider augmentation.

### Architecture
- **Nodes:** Assets (AAPL, BTC, GOLD, NVDA).
- **Edges:** Static (Sector, Supply Chain) + Dynamic (Rolling Correlation > 0.8, Granger Causality).
- **Node Features:** LSTM-encoded time-series embeddings at time $t$.
- **GNN Layer:** GAT (Graph Attention Network) to aggregate neighbor signals.
- **Output:** Regressor predicting next-day return for all nodes simultaneously.

---

## Level 5: Autonomous Action (Reinforcement Learning)

### Deep Q-Network / PPO Agent
- **State:** Market Regime (L3), GNN Predictions (L4), Portfolio Balance, Current Drawdown.
- **Action Space:** Continuous (% of capital) preferred over discrete buckets.
- **Reward:** Differential Sharpe Ratio (online, per-step) - Transaction Costs - Max DD Penalty.
- **Promotion Pipeline:**
  ```
  Backtest → Walk-Forward → Paper Trading (30 days, Sharpe > 1.5, DD < 10%) → Small Allocation (1%) → Full Allocation
  ```

---

## Data & Infrastructure Roadmap

1. **Data Lake:** Parquet cold store partitioned by `asset_class/symbol/year/month/`.
2. **Feature Store:** Point-in-time feature computation with versioning.
3. **Model Registry (MLFlow):** Version control, A/B testing, drift monitoring.
4. **MCP Server:** AI agent interface — see [`mcp_server_implementation_plan.md`](./mcp_server_implementation_plan.md).
5. **Frontend Dashboard:** React + TradingView — see [`frontend_implementation_plan.md`](./frontend_implementation_plan.md).
6. **Jupyter Research Environment:** Notebook-first research workflow.