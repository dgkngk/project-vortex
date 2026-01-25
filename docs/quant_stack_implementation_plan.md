# Quantitative Trading Stack Implementation Plan

## Overview
**Goal:** Develop a production-grade quantitative trading system capable of generating >50% alpha over buy-and-hold strategies.
**Scope:** Multi-Asset Class (Crypto, Stocks, Commodities).
**Core Philosophy:** Transition from heuristic rule-based systems to probabilistic, network-aware, and autonomous AI systems.

---

## Level 0: Foundation & Validation (Immediate Priority)
Before any ML model can be trained or deployed, the system needs the ability to simulate history and execute trades.

### 1. Vectorized Backtester
*   **Objective:** Fast, batch-processing of strategies to prove statistical edge.
*   **Implementation:** 
    *   Input: `StrategyTransformer` output (Signals).
    *   Logic: Vectorized Pandas operations to calculate PnL, Drawdown, Sharpe, Sortino.
    *   Features: Commission modeling, Slippage estimation.
*   **Deliverable:** `BacktestEngine` class in `backend/scitus/backtest/`.
    *   **Phase 1:** Core Logic. `run(data, signal_col) -> equity_curve`.
    *   **Phase 2:** Metrics. `calculate_metrics(equity_curve) -> {Sharpe, MaxDD, WinRate}`.
    *   **Phase 3:** Visualization. `plot_results()` using Matplotlib/Plotly.

### 2. Event-Driven Backtester
*   **Objective:** Realistic simulation of order execution and latency for ML/RL models.
*   **Implementation:**
    *   Step-by-step iteration (bar by bar).
    *   Simulates Order Book interaction.
    *   Prevents "Lookahead Bias" inherent in vectorized approaches.

### 3. Execution Handler
*   **Objective:** Interface with Exchanges/Brokers.
*   **Implementation:** 
    *   `ExchangeClient` (Wrapper around CCXT for Crypto, IBKR/Alpaca for Stocks).
    *   `OrderManager` to track `OPEN`, `FILLED`, `CANCELLED` states.

---

## Level 1: Heuristic Strategies (Current)
Refining rule-based logic to serve as "Feature Generators" for later levels.

*   **Composite Strategies:** Combine Trend + Volatility indicators.
*   **Voting Strategies:** Ensemble consensus from multiple technical indicators.
*   **Role in Stack:** These will serve as **Inputs/Features** for Level 2 & 5 models (e.g., "RSI says Overbought" is a feature, not just a rule).

---

## Level 2: Predictive Modeling (Supervised Learning)
Moving from "Rules" to "Probabilities".

### 1. Tabular Models (XGBoost / LightGBM)
*   **Data:** OHLCV, Technical Indicators, Macro Data (Interest Rates, DXY).
*   **Target:** `Target_5m` (Binary: Will price rise > 0.5% in next 5 mins?).
*   **Feature Engineering:**
    *   Stationarity checks (Log-returns, Fractional Differentiation).
    *   Time-features (Hour of day, Day of week).
*   **Implementation:** `MLStrategy` class loading `.json` booster models.

### 2. Sequence Models (LSTM / Temporal Fusion Transformers)
*   **Data:** Sliding window of raw normalized returns.
*   **Edge:** Capturing path-dependency (e.g., rapid crash vs slow bleed).

---

## Level 3: Market Regimes (Unsupervised Learning)
Context-awareness. Strategies behave differently in different environments.

### Hidden Markov Models (HMM)
*   **Objective:** Classify market state into `Bull`, `Bear`, `HighVol_Chop`, `LowVol_Chop`.
*   **Inputs:** Volatility (ATR), Returns, Volume.
*   **Implementation:** 
    *   Train Gaussian HMM.
    *   **Meta-Strategy:** Switch Level 2 models based on Regime. 
        *   *Example:* If `HighVol_Chop` -> Disable Trend Models, Enable Mean Reversion Models.

---

## Level 4: Network Effects (Graph Neural Networks - GNN)
**Special Focus:** Leveraging cross-asset correlations in a multi-asset universe.

### Concept
Markets are not isolated time-series; they are a graph of interconnected entities. A shock in Oil affects Airlines (Stocks) and Energy-intensive protocols (Crypto).

### Architecture
*   **Nodes ($V$):** Assets (e.g., AAPL, BTC, GOLD, NVDA).
*   **Edges ($E$):** Relationships.
    *   **Static Edges:** Sector (Tech), Supply Chain (Chip Maker -> Cloud Provider), Consensus (PoW Coins).
    *   **Dynamic Edges:** Rolling Correlation (> 0.8), Granger Causality.
*   **Node Features ($X_t$):** The time-series embedding of the asset (output of an LSTM or raw indicators) at time $t$.

### Graph Convolution (GCN/GAT)
*   **Mechanism:** Aggregates information from neighbors.
    *   $h_v^{(l+1)} = \sigma( \sum_{u \in \mathcal{N}(v)} \frac{1}{c_{vu}} W^{(l)} h_u^{(l)} )$
*   **The Alpha:** "NVDA is pumping. BTC has high correlation to Tech. NVDA is a neighbor of BTC in the graph. Therefore, predict BTC Up."
*   **Implementation Steps:**
    1.  **Graph Construction:** Build the Adjacency Matrix $A$ based on 1-year rolling correlations of the S&P500 + Top 100 Crypto + Gold/Oil.
    2.  **Feature Encoder:** A small LSTM to encode the last 30 days of price action for *each* node into a vector.
    3.  **GNN Layer:** Pass vectors through GAT (Graph Attention Network) layers to mix signals.
    4.  **Output Head:** Regressor predicting next-day return for *all* nodes simultaneously.

---

## Level 5: Autonomous Action (Reinforcement Learning)
The "Trader" Agent that optimizes execution and risk.

### Deep Q-Network / PPO Agent
*   **State:** Market Regime (Level 3), GNN Predictions (Level 4), Current Portfolio Balance, Current Drawdown.
*   **Action Space:** `[Buy 10%, Buy 50%, Hold, Sell 10%, Sell 50%, Close All]`.
*   **Reward Function:** Risk-Adjusted Returns (Sharpe) - Transaction Costs.
*   **Goal:** Learn to "Sit out" during uncertainty and "Size up" during high-probability GNN setups.

---

## Data & Infrastructure Roadmap

1.  **Data Lake:** Store raw historical data (Parquet/HDF5).
2.  **Feature Store:**
    *   Consistent calculation of indicators for Training and Inference.
    *   "Time-Travel" capability (what was the RSI known *at that exact moment*?).
3.  **Model Registry (MLFlow):** Version control for models (e.g., `XGBoost_v4_BTC` vs `GNN_v1_Global`).