# Tech Stack

The Project Vortex stack is built for high-performance data processing, flexible research, and robust execution.

## Core Language
- **Python 3.13+**: Primary language for backend, ETL, and research.

## Web & API
- **FastAPI**: High-performance REST API for the shared backend.
- **Pydantic Settings**: Environment-driven configuration management.
- **MCP (Model Context Protocol)**: Server for AI Agent interaction.
- **React**: (Planned) Frontend for human operators.

## Data Storage & Analysis
- **Redis**: Hot Tier — Real-time state, latest quotes, and session caching.
- **InfluxDB**: Warm Tier — Recent historical data (last 30 days) for live charts.
- **Parquet + DuckDB**: Cold Tier — Full historical data storage for backtesting and ML.
- **Pandas**: Core data manipulation library.
- **PyArrow**: High-efficiency Parquet read/write.

## Quantitative & Machine Learning
- **Pandas-TA**: Technical analysis indicator calculations.
- **NumPy**: Numerical computing foundation.
- **Scikit-Learn / XGBoost**: (In Progress) Supervised learning models.
- **PyTorch / TensorFlow**: (Planned) Sequence and Graph models.

## Data Sources & Extraction
- **CCXT**: Unified access to crypto exchanges (Binance, etc.).
- **Polygon.io**: High-quality data for Stocks, Crypto, and Forex.
- **CoinGecko**: Market capitalization and alternative crypto data.
- **aiohttp**: Asynchronous HTTP extraction for high throughput.

## Infrastructure & Dev Tools
- **Poetry**: Dependency and virtual environment management.
- **Docker**: Containerization for consistent deployment.
- **JupyterLab**: Interactive research and exploratory data analysis.
- **Pytest**: Testing framework with parallel execution (`pytest-xdist`).
- **PostgreSQL**: Relational storage for metadata and persistent state.
