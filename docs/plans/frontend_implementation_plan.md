# Frontend Implementation Plan

## 1. Overview

The **Vortex Dashboard** is the human operator interface for Project Vortex. It provides real-time market monitoring, backtesting visualization, portfolio management, and trade approval.

### Design Principle

> The frontend is for **monitoring, tuning, and approving**. Strategy research happens in Jupyter notebooks. The dashboard visualizes results discovered there and provides operational control.

### Tech Stack

| Layer | Technology | Rationale |
|:---|:---|:---|
| Framework | **Vite + React + TypeScript** | Fast HMR, lightweight, great DX |
| Financial Charts | **TradingView Lightweight Charts** | Free, professional, GPU-accelerated |
| Analytics Charts | **Recharts** | React-native, composable, beautiful |
| Styling | **Vanilla CSS** + CSS Variables | Full control, dark mode via variables |
| Real-Time | **WebSocket** via FastAPI | Native support, push price updates |
| State Management | **TanStack Query** (server state) + **Zustand** (UI state) | Lightweight, great for async data |
| Data Tables | **TanStack Table** | Headless, virtualized for large datasets |
| HTTP Client | **Axios** or **fetch** wrapper | API calls to FastAPI backend |
| Icons | **Lucide React** | Clean, consistent icon set |
| Routing | **React Router v7** | Standard React routing |

---

## 2. Design System

### Color Palette (Dark Theme — Primary)

```css
:root {
    /* Backgrounds */
    --bg-primary: #0a0e17;        /* Deep navy — main background */
    --bg-secondary: #111827;      /* Card backgrounds */
    --bg-tertiary: #1a2332;       /* Elevated surfaces */
    --bg-hover: #1f2b3d;          /* Hover states */

    /* Accents */
    --accent-primary: #3b82f6;    /* Blue — primary actions */
    --accent-success: #10b981;    /* Green — profit, buy, positive */
    --accent-danger: #ef4444;     /* Red — loss, sell, negative */
    --accent-warning: #f59e0b;    /* Amber — caution, pending */
    --accent-info: #8b5cf6;       /* Purple — information, neutral */

    /* Text */
    --text-primary: #f1f5f9;      /* Bright white — headings */
    --text-secondary: #94a3b8;    /* Muted — body text */
    --text-tertiary: #64748b;     /* Dim — labels, timestamps */

    /* Borders */
    --border-default: #1e293b;
    --border-focus: #3b82f6;

    /* Gradients */
    --gradient-profit: linear-gradient(135deg, #10b981, #059669);
    --gradient-loss: linear-gradient(135deg, #ef4444, #dc2626);
    --gradient-header: linear-gradient(90deg, #1e293b, #0f172a);

    /* Glassmorphism */
    --glass-bg: rgba(17, 24, 39, 0.8);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-blur: blur(16px);

    /* Typography */
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    /* Spacing */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;

    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-normal: 250ms ease;
}
```

### Typography Scale

```css
.text-xs   { font-size: 0.75rem; line-height: 1rem; }
.text-sm   { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg   { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl   { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl  { font-size: 1.5rem; line-height: 2rem; }
.text-3xl  { font-size: 1.875rem; line-height: 2.25rem; }
```

### Component Patterns

- **Cards:** Glassmorphism with `var(--glass-bg)`, subtle border, `var(--glass-blur)` backdrop
- **Metric Cards:** Large number display with sparkline or delta indicator (▲ green / ▼ red)
- **Tables:** Alternating row opacity, sticky headers, hover highlight
- **Charts:** Dark background, grid lines at 0.1 opacity, green/red for profit/loss
- **Buttons:** Rounded (`var(--radius-md)`), primary/secondary/ghost variants
- **Animations:** Subtle fade-in on mount, number counters on metric changes, pulse on live data updates

---

## 3. Pages & Components

### 3.1 Sidebar Navigation

Persistent left sidebar with icon + label navigation:

| Icon | Label | Route | Phase |
|:---|:---|:---|:---|
| 📊 | Dashboard | `/` | Phase 0 |
| 📈 | Data Explorer | `/data` | Phase 0 |
| 🔬 | Strategy Lab | `/strategies` | Phase 1 |
| ⚠️ | Risk | `/risk` | Phase 2 |
| 🤖 | Models | `/models` | Phase 2 |
| 💰 | Live Trading | `/live` | Phase 3 |
| ⚙️ | Settings | `/settings` | Phase 0 |

### 3.2 Phase 0 — Dashboard Home (`/`)

**Purpose:** At-a-glance overview of system health and market state.

**Layout:**
```
┌──────────────────────────────────────────────────────────┐
│ Header: "Vortex Dashboard"                  [User] [⚙️]  │
├──────────┬───────────────────────────────────────────────┤
│          │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│          │ │ NAV  │ │Today │ │Sharpe│ │ Max  │          │
│  Side    │ │$124K │ │+2.3% │ │ 1.82 │ │DD -8%│          │
│  bar     │ └──────┘ └──────┘ └──────┘ └──────┘          │
│          │ ┌────────────────────────────────────┐        │
│          │ │         Portfolio Equity Curve      │        │
│          │ │     (TradingView Lightweight)       │        │
│          │ └────────────────────────────────────┘        │
│          │ ┌──────────────────┐ ┌──────────────────┐    │
│          │ │  ETL Health      │ │  Active Strategies │    │
│          │ │  Binance: ✅     │ │  MACD/BTC: Buy     │    │
│          │ │  Polygon: ✅     │ │  BB/ETH: Hold      │    │
│          │ │  CoinGecko: ⚠️  │ │  VWAP/AAPL: Sell   │    │
│          │ └──────────────────┘ └──────────────────┘    │
└──────────┴───────────────────────────────────────────────┘
```

**Components:**
- `MetricCard` — Large number + delta + sparkline (reusable)
- `EquityCurveChart` — TradingView area chart with portfolio value over time
- `ETLHealthPanel` — Per-extractor status badges (✅ / ⚠️ / ❌)
- `ActiveStrategiesTable` — Strategy name, asset, current signal, last update

**API Endpoints Required:**
- `GET /api/portfolio/summary` → NAV, daily P&L, Sharpe, MaxDD
- `GET /api/etl/health` → Per-extractor status
- `GET /api/strategies/active` → Running strategies + signals

### 3.3 Phase 0 — Data Explorer (`/data`)

**Purpose:** Browse, visualize, and verify historical data quality.

**Components:**
- `AssetSearchBar` — Search/filter assets by name, class, exchange
- `AssetList` — Filterable table with sparkline, last price, 24h change
- `CandlestickChart` — TradingView candlestick with indicator overlays (RSI, MACD, BB toggles)
- `IndicatorPanel` — Dropdown to select/deselect indicators, rendered as sub-charts
- `DataQualityBadge` — Shows data gaps, last update time, adjustment status
- `TimeframeSelector` — 1m / 5m / 15m / 1h / 4h / 1d / 1w

**API Endpoints Required:**
- `GET /api/market/search?q={query}&class={class}` → Asset search
- `GET /api/market/{asset}/ohlcv?timeframe={tf}&start={start}&end={end}` → OHLCV data
- `GET /api/market/{asset}/indicators?indicators={list}&timeframe={tf}` → Indicator values
- `GET /api/market/{asset}/quality` → Data gaps, adjustments, freshness

### 3.4 Phase 1 — Strategy Lab (`/strategies`)

**Purpose:** Run backtests, compare strategies, tune parameters. NOT for strategy creation (that's Jupyter).

**Components:**
- `BacktestConfigurator` — Form: strategy dropdown, asset, timeframe, date range, parameters
- `BacktestRunner` — Submit button → loading state → results
- `EquityCurveComparison` — Overlay 2+ equity curves on same chart
- `MetricsTable` — Sharpe, Sortino, MaxDD, WinRate, ProfitFactor, Calmar, TotalCosts
- `CostBreakdownChart` — Stacked bar: transaction, slippage, funding, borrow
- `TradeLogTable` — Sortable/filterable table: entry, exit, P&L, duration, side
- `MonthlyHeatmap` — Returns by Month × Year grid
- `DrawdownChart` — Underwater drawdown plot
- `ParameterHeatmap` — Grid search results as color-coded heatmap

**API Endpoints Required:**
- `GET /api/strategies` → List available strategies + param schemas
- `POST /api/backtest/run` → `{strategy, asset, timeframe, params}` → BacktestResult
- `POST /api/backtest/compare` → `{strategies[], asset, timeframe}` → ComparisonResult
- `POST /api/backtest/optimize` → `{strategy, asset, param_grid}` → OptimizationResult

### 3.5 Phase 2 — Risk Dashboard (`/risk`)

**Components:**
- `ExposureDonut` — Portfolio allocation by asset class (pie/donut chart)
- `CorrelationHeatmap` — Matrix view of cross-asset correlations
- `DrawdownGauge` — Current drawdown vs max tolerance (gauge chart)
- `VaRDisplay` — 95% VaR, Expected Shortfall, historical VaR chart
- `PositionTable` — Open positions with entry, current, P&L, stop-loss, risk contribution
- `StressTestPanel` — Select scenario → see estimated impact

### 3.6 Phase 2 — Model Dashboard (`/models`)

**Components:**
- `ModelRegistryTable` — Model name, version, asset, last trained, status
- `PerformanceChart` — Live vs backtest Sharpe over time
- `FeatureImportanceBar` — Horizontal bar chart of SHAP values
- `RegimeTimeline` — HMM state overlay on price chart (color bands: green=Bull, red=Bear, yellow=Chop)
- `DriftAlertList` — Feature distribution shifts with severity badges
- `DataQualityPanel` — Split/dividend adjustment status, data gaps, ticker mapping log

### 3.7 Phase 3 — Live Trading (`/live`)

**Components:**
- `LivePortfolioHeader` — Real-time NAV (WebSocket), today's P&L ticker
- `OrderBook` — Live bid/ask display for selected asset
- `SignalFeed` — Real-time strategy signals with confidence (WebSocket push)
- `PendingTradesPanel` — AI-proposed trades awaiting human approval (Approve / Reject buttons)
- `ExecutionLog` — Table of executed trades with fill price, slippage, status
- `AlertTicker` — Horizontal scrolling alerts (price, drawdown, signal)

**WebSocket Endpoints Required:**
- `WS /ws/portfolio` → Real-time NAV, P&L updates
- `WS /ws/signals` → Strategy signal push notifications
- `WS /ws/prices/{asset}` → Live price stream

---

## 4. Reusable Component Library

| Component | Props | Description |
|:---|:---|:---|
| `MetricCard` | `label, value, delta, sparklineData, color` | KPI display card |
| `PriceChart` | `asset, timeframe, indicators[], height` | TradingView wrapper |
| `DataTable` | `columns, data, sortable, filterable, paginated` | TanStack Table wrapper |
| `StatusBadge` | `status: "healthy" \| "warning" \| "error"` | Color-coded status pill |
| `Dropdown` | `options[], value, onChange, multi` | Styled select component |
| `DateRangePicker` | `start, end, onChange, presets` | Date range with quick presets |
| `LoadingSpinner` | `size, text` | Skeleton/spinner states |
| `TooltipChart` | `type: "bar" \| "line" \| "area", data` | Recharts wrapper |
| `GlassCard` | `children, title, headerAction` | Glassmorphism container |
| `EmptyState` | `icon, title, description, action` | Zero-data placeholder |

---

## 5. API Client Layer

```typescript
// frontend/src/services/api.ts

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ApiClient {
    // Market Data
    searchAssets(query: string, assetClass?: string): Promise<Asset[]>;
    getOHLCV(asset: string, timeframe: string, start: string, end: string): Promise<OHLCV[]>;
    getIndicators(asset: string, indicators: string[], timeframe: string): Promise<IndicatorData>;
    getDataQuality(asset: string): Promise<DataQuality>;

    // Portfolio
    getPortfolioSummary(): Promise<PortfolioSummary>;
    getPositions(): Promise<Position[]>;

    // Strategies
    listStrategies(): Promise<Strategy[]>;
    getActiveSignals(): Promise<Signal[]>;

    // Backtesting
    runBacktest(config: BacktestConfig): Promise<BacktestResult>;
    compareStrategies(config: CompareConfig): Promise<ComparisonResult>;
    optimizeParameters(config: OptimizeConfig): Promise<OptimizationResult>;

    // Risk
    getRiskMetrics(): Promise<RiskMetrics>;
    getCorrelationMatrix(assets: string[], window: number): Promise<CorrelationMatrix>;
    runStressTest(scenario: string): Promise<StressTestResult>;

    // ETL
    getETLHealth(): Promise<ETLHealth>;

    // Execution
    proposeTrade(trade: TradeProposal): Promise<PendingTrade>;
    getPendingTrades(): Promise<PendingTrade[]>;
    approveTrade(tradeId: string): Promise<void>;
    rejectTrade(tradeId: string): Promise<void>;
}
```

---

## 6. WebSocket Manager

```typescript
// frontend/src/services/websocket.ts

class VortexWebSocket {
    private ws: WebSocket;
    private subscribers: Map<string, Set<(data: any) => void>>;

    connect(url: string): void;
    subscribe(channel: string, callback: (data: any) => void): () => void;
    disconnect(): void;
}

// Usage:
// const ws = new VortexWebSocket();
// ws.connect('ws://localhost:8000/ws');
// const unsub = ws.subscribe('portfolio', (data) => updateNAV(data));
```

---

## 7. Directory Structure

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                     # Entry point
│   ├── App.tsx                      # Router + Layout
│   ├── index.css                    # Design system (CSS variables, globals)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Sidebar.css
│   │   │   ├── Header.tsx
│   │   │   └── Header.css
│   │   ├── charts/
│   │   │   ├── PriceChart.tsx       # TradingView wrapper
│   │   │   ├── EquityCurve.tsx
│   │   │   ├── DrawdownChart.tsx
│   │   │   ├── CorrelationHeatmap.tsx
│   │   │   └── MonthlyHeatmap.tsx
│   │   ├── ui/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── MetricCard.css
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── GlassCard.tsx
│   │   │   ├── GlassCard.css
│   │   │   ├── DataTable.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── EmptyState.tsx
│   │   └── domain/
│   │       ├── ETLHealthPanel.tsx
│   │       ├── ActiveStrategiesTable.tsx
│   │       ├── BacktestConfigurator.tsx
│   │       ├── TradeLogTable.tsx
│   │       ├── PendingTradesPanel.tsx
│   │       └── SignalFeed.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Dashboard.css
│   │   ├── DataExplorer.tsx
│   │   ├── DataExplorer.css
│   │   ├── StrategyLab.tsx
│   │   ├── StrategyLab.css
│   │   ├── RiskDashboard.tsx
│   │   ├── RiskDashboard.css
│   │   ├── ModelDashboard.tsx
│   │   ├── ModelDashboard.css
│   │   ├── LiveTrading.tsx
│   │   ├── LiveTrading.css
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── usePortfolio.ts          # TanStack Query hook for portfolio data
│   │   ├── useMarketData.ts         # Hook for OHLCV + indicators
│   │   ├── useBacktest.ts           # Mutation hook for running backtests
│   │   ├── useWebSocket.ts          # WebSocket subscription hook
│   │   └── useStrategies.ts         # Strategy listing + signals
│   ├── services/
│   │   ├── api.ts                   # REST API client
│   │   ├── websocket.ts             # WebSocket manager
│   │   └── types.ts                 # TypeScript interfaces for API responses
│   └── stores/
│       ├── uiStore.ts               # Zustand: sidebar state, theme, filters
│       └── chartStore.ts            # Zustand: selected asset, timeframe, indicators
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 8. Development Roadmap

### Phase 0 — Foundation + Data Explorer

| Step | Task | Description |
|:---|:---|:---|
| 1 | **Scaffold Vite + React** | `npx -y create-vite@latest ./ --template react-ts` |
| 2 | **Design System** | Create `index.css` with all CSS variables, typography, glassmorphism |
| 3 | **Layout Shell** | `Sidebar` + `Header` + content area with React Router |
| 4 | **Reusable Components** | `MetricCard`, `GlassCard`, `StatusBadge`, `DataTable`, `LoadingSpinner` |
| 5 | **API Client** | `services/api.ts` with Axios/fetch, TanStack Query provider |
| 6 | **Dashboard Page** | Metric cards (mocked), ETL health panel, active strategies table |
| 7 | **Data Explorer: Asset Search** | `AssetSearchBar` + `AssetList` with sparklines |
| 8 | **Data Explorer: Chart** | TradingView `PriceChart` component with candlesticks |
| 9 | **Data Explorer: Indicators** | Indicator overlay panel (RSI, MACD, BB toggles) |
| 10 | **Data Explorer: Quality** | Data quality badges, gap visualization |

### Phase 1 — Strategy Lab

| Step | Task | Description |
|:---|:---|:---|
| 11 | **Backtest Configurator** | Strategy/asset/timeframe/params form |
| 12 | **Backtest Runner** | Submit → loading → results flow |
| 13 | **Equity Curve + Drawdown** | Interactive charts with TradingView/Recharts |
| 14 | **Metrics Display** | Cards for Sharpe, MaxDD, WinRate, ProfitFactor, costs |
| 15 | **Trade Log** | Sortable/filterable TanStack Table of trades |
| 16 | **Strategy Comparison** | Multi-strategy overlay and side-by-side metrics table |
| 17 | **Cost Breakdown** | Stacked bar chart: transaction, slippage, funding, borrow |
| 18 | **Monthly Heatmap** | Returns by Month × Year grid |

### Phase 2 — Risk & Models

| Step | Task | Description |
|:---|:---|:---|
| 19 | **Risk Dashboard** | Exposure donut, drawdown gauge, VaR, position table |
| 20 | **Correlation Heatmap** | Interactive matrix with color scale |
| 21 | **Stress Test Panel** | Scenario selector → impact results |
| 22 | **Model Registry** | Table of models with performance metrics |
| 23 | **Regime Visualizer** | HMM state overlay on price chart |
| 24 | **Drift Alerts** | Feature distribution shift list |

### Phase 3 — Live Trading

| Step | Task | Description |
|:---|:---|:---|
| 25 | **WebSocket Manager** | Connection, reconnection, channel subscriptions |
| 26 | **Live Portfolio** | Real-time NAV header, P&L ticker |
| 27 | **Signal Feed** | Real-time strategy signals via WebSocket |
| 28 | **Pending Trades Panel** | AI proposals with Approve/Reject buttons |
| 29 | **Execution Log** | Historical trade list with fill details |
| 30 | **Alerts** | Price/drawdown/signal alert system |
