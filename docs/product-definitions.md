# Product Definitions

## Project Vortex: Quantitative Trading Stack
Project Vortex is a production-grade quantitative trading system designed for alpha generation through multi-asset class analysis and autonomous execution.

## Core Mission
Transition from traditional heuristic rule-based trading to probabilistic, network-aware, and autonomous AI systems.

## Scope
- **Asset Classes:** Crypto, Stocks, Commodities.
- **Data Fidelity:** Clean, survivorship-bias-free historical data.
- **Strategy Range:** From simple technical indicators to Deep Reinforcement Learning.

## Product Hierarchy (Evolutionary Levels)

### Level -1: Data Foundation
- **Tiered Storage:** Hot (Redis), Warm (InfluxDB), Cold (Parquet/DuckDB).
- **Maintenance:** Split/dividend adjustment, ticker mapping, and universe building.

### Level 0: Foundation & Validation
- **Backtesters:** Fast vectorized (Pandas) and realistic event-driven engines.
- **Risk Management:** Kelly criterion, ATR-based stops, and portfolio constraints.
- **Walk-Forward Validation:** Rigorous out-of-sample testing to prevent overfitting.

### Level 1: Heuristic Strategies
- **Consensus Voting:** Combining multiple signals (Trend, Volatility, Momentum).
- **Composite Logic:** Indicator-based rules serving as feature generators for ML.

### Level 2: Predictive Modeling
- **Supervised Learning:** XGBoost/LightGBM for short-term price movement prediction.
- **Sequence Models:** LSTM/Transformers for path-dependent market behavior.

### Level 3: Market Regimes & Optimization
- **Unsupervised Learning:** Hidden Markov Models (HMM) for regime classification (Bull/Bear/Chop).
- **Portfolio Optimization:** Mean-Variance, Risk Parity, and Hierarchical Risk Parity (HRP).

### Level 4: Network Effects
- **Graph Neural Networks (GNN):** Modeling inter-asset dependencies and correlations as a graph.

### Level 5: Autonomous Action
- **Reinforcement Learning:** PPO/DQN agents managing position sizing and execution autonomously.

## Key Interfaces
- **React Frontend:** Modern dashboard for human operators to monitor performance.
- **MCP Server:** Interface for AI agents to interact with the trading stack.
- **FastAPI Backend:** Unified REST API for data access and execution control.
