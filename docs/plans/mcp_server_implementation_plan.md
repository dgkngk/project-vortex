# MCP Server Implementation Plan

## 1. Overview

The **Vortex MCP Server** exposes Project Vortex's quant engine to AI agents via the Model Context Protocol. It enables a **Human + AI co-operation model**: the AI agent analyzes data, runs backtests, and proposes trades — the human reviews and approves via the React frontend.

### Architecture Principle

> The MCP server **never** accesses databases or engine classes directly. It calls the same FastAPI REST endpoints that the frontend uses. One source of truth, one permission layer.

```
┌─────────────────┐     ┌──────────────────┐
│  React Frontend │     │   MCP Server     │
│  (Human)        │     │   (AI Agent)     │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
   ┌─────────────────────────────────────┐
   │         FastAPI Backend             │
   │  (REST + WebSocket Endpoints)       │
   └──────────────────┬──────────────────┘
                      │
   ┌──────────────────▼──────────────────┐
   │          Quant Engine               │
   │  ETL │ Backtest │ Risk │ ML │ Exec  │
   └──────────────────┬──────────────────┘
                      │
   ┌──────────────────▼──────────────────┐
   │           Data Layer                │
   │  Redis │ InfluxDB │ Parquet/DuckDB  │
   └─────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|:---|:---|
| MCP SDK | `mcp` Python SDK (`MCPServer` class) |
| Transport | `streamable-http` (production recommended) |
| Internal HTTP Client | `httpx` (async calls to FastAPI) |
| Serialization | JSON responses |

---

## 2. Summarizer Service

> **Critical:** MCP tools return summaries by default. Raw data is available via `raw=true` with pagination.

### Problem
30 days of 1-minute OHLCV = ~43,000 rows = context window overflow.

### Solution: `DataSummarizer`

**Path:** `backend/mcp_server/services/DataSummarizer.py`

```python
class DataSummarizer:
    """Compresses financial data into LLM-digestible summaries."""

    def summarize_ohlcv(self, data: pd.DataFrame) -> dict:
        """Summarize OHLCV data into key statistics.

        Returns:
            {
                "period": "2026-01-15 to 2026-02-15",
                "bars": 43200,
                "timeframe": "1m",
                "trend": {"direction": "up", "slope": 0.52, "r_squared": 0.78},
                "price": {"open": 64200, "high": 69800, "low": 62100, "close": 68500, "change_pct": 6.7},
                "volatility": {"atr_14": 1250, "daily_std": 2.3, "regime": "moderate"},
                "volume": {"avg_daily": 28.5e9, "trend": "increasing"},
                "key_levels": {"support": [65000, 62000], "resistance": [70000, 72500]},
            }
        """

    def summarize_indicators(self, indicators: dict[str, pd.Series]) -> dict:
        """Summarize technical indicator values.

        Returns:
            {
                "RSI_14": {"value": 48, "signal": "neutral", "divergence": "none"},
                "MACD": {"value": -120, "signal_line": -80, "histogram": -40, "crossover": "bearish"},
                "BB": {"position": "middle", "bandwidth": 4.2, "squeeze": false},
            }
        """

    def summarize_backtest(self, result: BacktestResult) -> dict:
        """Summarize backtest results.

        Returns all metrics + equity curve sampled to ~50 points for plotting context.
        """
```

### Response Format Contract

Every data-returning MCP tool follows this pattern:

```python
@mcp.tool()
async def get_market_data(
    asset: str,
    timeframe: str = "1d",
    days: int = 30,
    raw: bool = False,          # False = summary (default), True = raw data
    page: int = 1,              # Only used when raw=True
    page_size: int = 500,       # Rows per page when raw=True
) -> str:
    """Fetch historical market data for an asset.

    By default returns a summary (trend, volatility, key levels).
    Set raw=True to get full OHLCV rows with pagination.
    """
    data = await self.api_client.get(f"/api/market/{asset}", params={...})

    if raw:
        # Paginated raw data
        start = (page - 1) * page_size
        end = start + page_size
        page_data = data.iloc[start:end]
        return json.dumps({
            "data": page_data.to_dict(orient="records"),
            "pagination": {"page": page, "page_size": page_size,
                          "total_rows": len(data), "total_pages": ceil(len(data) / page_size)}
        })
    else:
        # Summary (default)
        return json.dumps(self.summarizer.summarize_ohlcv(data))
```

---

## 3. MCP Tools Specification

### 3.1 Data & Market Tools

#### `get_market_data`
- **Parameters:** `asset: str`, `timeframe: str = "1d"`, `days: int = 30`, `raw: bool = False`, `page: int = 1`, `page_size: int = 500`
- **Summary response:** Trend direction/slope, price range, volatility regime, volume trend, key support/resistance levels
- **Raw response:** Paginated OHLCV rows

#### `get_latest_price`
- **Parameters:** `asset: str`
- **Returns:** Current price, 24h change %, 24h volume, bid/ask spread

#### `get_technical_indicators`
- **Parameters:** `asset: str`, `indicators: str` (comma-separated, e.g. `"RSI,MACD,BB"`), `timeframe: str = "4h"`
- **Returns:** Summarized indicator values with signal interpretation (overbought/oversold/neutral/crossover)

#### `search_assets`
- **Parameters:** `query: str`, `asset_class: str = "all"` (crypto/stocks/commodities/all)
- **Returns:** Matching asset names, tickers, last price, 24h change

#### `get_correlation_matrix`
- **Parameters:** `assets: str` (comma-separated), `window: int = 90` (days)
- **Returns:** Pairwise correlation values, highest/lowest pairs, cluster groups

### 3.2 Strategy & Backtest Tools

#### `list_strategies`
- **Parameters:** None
- **Returns:** Strategy names, descriptions, parameter schemas, compatible asset classes

#### `get_strategy_signals`
- **Parameters:** `strategy: str`, `asset: str`, `timeframe: str = "4h"`
- **Returns:** Current signal (buy/sell/hold), confidence, last N signals with timestamps

#### `run_backtest`
- **Parameters:** `strategy: str`, `asset: str`, `timeframe: str = "1d"`, `days: int = 365`, `params: str = "{}"` (JSON strategy parameters), `include_costs: bool = True`
- **Returns:** Summary metrics (Sharpe, MaxDD, WinRate, ProfitFactor, TotalCosts), equity curve sampled to ~50 points, trade summary stats
- **Note:** Long-running — consider returning a job ID for large backtests

#### `compare_strategies`
- **Parameters:** `strategies: str` (comma-separated), `asset: str`, `timeframe: str = "1d"`, `days: int = 365`
- **Returns:** Side-by-side metrics table, relative ranking, winner per metric

#### `optimize_parameters`
- **Parameters:** `strategy: str`, `asset: str`, `param_grid: str` (JSON grid definition)
- **Returns:** Best parameters, top-3 parameter sets with metrics, sensitivity assessment

### 3.3 Risk & Portfolio Tools

#### `get_portfolio_status`
- **Parameters:** None
- **Returns:** Total NAV, cash balance, holdings breakdown, daily P&L, current drawdown

#### `calculate_position_size`
- **Parameters:** `asset: str`, `risk_pct: float = 1.0`, `stop_distance: float`, `method: str = "fixed_fractional"` (fixed_fractional/kelly/volatility)
- **Returns:** Calculated position size, dollar value, rationale explaining the calculation

#### `get_risk_metrics`
- **Parameters:** None
- **Returns:** Portfolio Sharpe, current drawdown, VaR (95%), max exposure by asset class, correlation to BTC/SPY

#### `stress_test`
- **Parameters:** `scenario: str` (e.g., "covid_crash", "2022_crypto_winter", "custom"), `custom_shock: float = None`
- **Returns:** Estimated portfolio impact, worst-hit positions, recovery time estimate

### 3.4 Execution Tools (Human Approval Required)

#### `propose_trade`
- **Parameters:** `asset: str`, `side: str` (buy/sell), `size_pct: float` (% of portfolio), `reason: str`
- **Returns:** Pending trade ID, estimated cost impact, risk impact summary
- **Behavior:** Creates a pending trade entry visible in the frontend. Does NOT execute.

#### `get_pending_trades`
- **Parameters:** None
- **Returns:** List of proposed trades with status (pending/approved/rejected), proposer (AI/human), reason

### 3.5 System Tools

#### `get_etl_health`
- **Parameters:** None
- **Returns:** Per-extractor status (last run, success/fail, data freshness), overall pipeline health

#### `get_data_quality`
- **Parameters:** `asset: str`
- **Returns:** Data gaps, last adjustment date, split/dividend history, ticker mapping status

---

## 4. MCP Resources

Read-only data feeds exposed as `vortex://` URIs:

| Resource URI | Returns |
|:---|:---|
| `vortex://portfolio/summary` | JSON portfolio overview (NAV, P&L, holdings) |
| `vortex://portfolio/positions` | Open positions with entry price, current price, unrealized P&L |
| `vortex://market/{asset}/snapshot` | Latest price, 24h stats, key indicators |
| `vortex://strategies/active` | Currently running strategies and their latest signals |
| `vortex://risk/dashboard` | Current risk metrics (drawdown, exposure, VaR) |
| `vortex://etl/health` | Pipeline health: per-extractor status, data freshness |
| `vortex://models/{model_id}/performance` | Model metrics: Sharpe, accuracy, drift status |

---

## 5. MCP Prompts

Pre-built analysis templates:

| Prompt | Parameters | Generates |
|:---|:---|:---|
| `analyze_asset` | `asset: str`, `depth: str = "standard"` | Instructions to analyze technicals, fundamentals, and regime for an asset |
| `review_portfolio` | `risk_tolerance: str = "moderate"` | Instructions to review portfolio health and suggest rebalancing |
| `debug_strategy` | `strategy: str`, `asset: str`, `period: str = "30d"` | Instructions to investigate why a strategy underperformed |
| `morning_briefing` | `watchlist: str` | Instructions to generate pre-market summary for listed assets |
| `trade_thesis` | `asset: str`, `direction: str` | Instructions to build a bull/bear case with data |

---

## 6. Directory Structure

```
backend/mcp_server/
├── __init__.py
├── VortexMCPServer.py         # MCPServer instance, registration, entry point
├── ApiClient.py                # Async httpx client pointing to FastAPI
├── tools/
│   ├── __init__.py
│   ├── MarketDataTools.py      # get_market_data, get_latest_price, search_assets, etc.
│   ├── StrategyTools.py        # list_strategies, run_backtest, compare_strategies, etc.
│   ├── RiskTools.py            # get_portfolio_status, calculate_position_size, stress_test
│   ├── ExecutionTools.py       # propose_trade, get_pending_trades
│   └── SystemTools.py          # get_etl_health, get_data_quality
├── resources/
│   ├── __init__.py
│   ├── PortfolioResources.py   # vortex://portfolio/*
│   ├── MarketResources.py      # vortex://market/*
│   └── SystemResources.py      # vortex://etl/*, vortex://strategies/*
├── prompts/
│   ├── __init__.py
│   └── AnalysisPrompts.py      # analyze_asset, morning_briefing, trade_thesis, etc.
└── services/
    ├── __init__.py
    └── DataSummarizer.py       # Compresses financial data for LLM consumption
```

---

## 7. Server Entry Point

```python
# backend/mcp_server/VortexMCPServer.py
from mcp.server.mcpserver import MCPServer
from backend.mcp_server.ApiClient import ApiClient
from backend.mcp_server.services.DataSummarizer import DataSummarizer

mcp = MCPServer(
    name="Project Vortex",
    instructions=(
        "Quantitative trading engine for market analysis, backtesting, and portfolio management. "
        "Data tools return summaries by default. Use raw=True for full data with pagination. "
        "Execution tools (propose_trade) create proposals for human review — they do NOT auto-execute."
    ),
    version="1.0.0",
)

api = ApiClient(base_url="http://localhost:8000")
summarizer = DataSummarizer()

# Tool registration happens via imports that use @mcp.tool()
from backend.mcp_server.tools import MarketDataTools, StrategyTools, RiskTools, ExecutionTools, SystemTools
from backend.mcp_server.resources import PortfolioResources, MarketResources, SystemResources
from backend.mcp_server.prompts import AnalysisPrompts

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001, json_response=True)
```

---

## 8. Development Roadmap

| Step | Task | Description | Depends On |
|:---|:---|:---|:---|
| 1 | `ApiClient` | Async httpx wrapper for FastAPI calls | FastAPI endpoints exist |
| 2 | `DataSummarizer` | OHLCV, indicator, and backtest summarization | — |
| 3 | `VortexMCPServer` scaffold | MCPServer instance with transport config | — |
| 4 | Market Data Tools | `get_market_data`, `get_latest_price`, `search_assets`, `get_technical_indicators`, `get_correlation_matrix` | Steps 1-3 |
| 5 | Market Resources | `vortex://market/{asset}/snapshot` | Steps 1, 3 |
| 6 | System Tools + Resources | `get_etl_health`, `get_data_quality`, `vortex://etl/health` | Steps 1, 3 |
| 7 | Strategy Tools | `list_strategies`, `get_strategy_signals`, `run_backtest`, `compare_strategies`, `optimize_parameters` | Steps 1-3, Backtester exists |
| 8 | Risk Tools | `get_portfolio_status`, `calculate_position_size`, `get_risk_metrics`, `stress_test` | Steps 1-3, Risk Manager exists |
| 9 | Portfolio Resources | `vortex://portfolio/*`, `vortex://risk/*`, `vortex://strategies/*` | Steps 1, 3 |
| 10 | Analysis Prompts | `analyze_asset`, `morning_briefing`, `trade_thesis`, etc. | — |
| 11 | Execution Tools | `propose_trade`, `get_pending_trades` | Steps 1, 3, Execution Handler exists |
| 12 | Integration Testing | End-to-end test: AI agent → MCP → FastAPI → Engine → Response | All above |

---

## 9. Configuration

```json
// .vscode/mcp.json or equivalent
{
  "servers": {
    "project-vortex": {
      "type": "http",
      "url": "http://localhost:8001/mcp",
      "command": "poetry run python -m backend.mcp_server.VortexMCPServer"
    }
  }
}
```
