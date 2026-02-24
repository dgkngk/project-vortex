import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, Union

from backend.scitus.backtest.BacktestResult import BacktestResult

class BacktestPlotter:
    """
    Visualization module for Backtest outcomes using Plotly.
    Interactive charts for Jupyter or frontend embedding.
    """
    def __init__(self, result: BacktestResult, market_data: Optional[pd.DataFrame] = None):
        """
        Args:
            result: The BacktestResult object to plot.
            market_data: Optional OHLCV dataframe. Used for plotting trade markers on price chart.
        """
        self.result = result
        self.market_data = market_data

    @staticmethod
    def _compute_drawdown(equity: pd.Series) -> pd.Series:
        """Compute underwater drawdown series from an equity curve."""
        rolling_max = equity.cummax()
        return (equity - rolling_max) / rolling_max

    @staticmethod
    def _is_plottable_series(value: Union[pd.Series, float, None]) -> bool:
        """Check if a cost value is a non-empty Series suitable for plotting."""
        return isinstance(value, pd.Series) and not value.empty

    def plot_equity_curve(self) -> go.Figure:
        """Plot standalone strategy equity curve."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.result.equity_curve.index,
            y=self.result.equity_curve.values,
            mode='lines',
            name='Strategy Equity',
            line=dict(color='blue')
        ))
        
        # Benchmark (Buy and Hold)
        if self.market_data is not None and "close" in self.market_data.columns:
            initial_cap = self.result.equity_curve.iloc[0] if not self.result.equity_curve.empty else 10000
            market_returns = self.market_data["close"].pct_change().fillna(0)
            benchmark_equity = (1 + market_returns).cumprod() * initial_cap
            
            fig.add_trace(go.Scatter(
                x=benchmark_equity.index,
                y=benchmark_equity.values,
                mode='lines',
                name='Benchmark (B&H)',
                line=dict(color='gray', dash='dash')
            ))

        fig.update_layout(
            title="Equity Curve vs Benchmark",
            xaxis_title="Date",
            yaxis_title="Equity (Capital)",
            template="plotly_white"
        )
        return fig

    def plot_drawdown(self) -> go.Figure:
        """Plot underwater drawdown curve."""
        equity = self.result.equity_curve
        if equity.empty:
            return go.Figure()

        drawdown = self._compute_drawdown(equity)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=drawdown.index,
            y=drawdown.values,
            mode='lines',
            fill='tozeroy',
            name='Drawdown',
            line=dict(color='red')
        ))
        fig.update_layout(
            title="Drawdown Underwater",
            xaxis_title="Date",
            yaxis_title="Drawdown %",
            yaxis_tickformat='.1%',
            template="plotly_white"
        )
        return fig

    def plot_cost_breakdown(self) -> go.Figure:
        """Plot stacked bar chart of cumulative costs."""
        fig = go.Figure()
        
        if not self.result.costs:
            return fig

        for cost_name, cost_series in self.result.costs.items():
            if self._is_plottable_series(cost_series):
                cumulative_cost = cost_series.cumsum()
                fig.add_trace(go.Scatter(
                    x=cumulative_cost.index,
                    y=cumulative_cost.values,
                    mode='lines',
                    stackgroup='one',
                    name=cost_name.capitalize()
                ))

        fig.update_layout(
            title="Cumulative Cost Breakdown",
            xaxis_title="Date",
            yaxis_title="Cumulative Cost",
            template="plotly_white"
        )
        return fig

    def plot_results(self) -> go.Figure:
        """
        Master plot combining multiple views:
        Row 1: Equity Curve
        Row 2: Drawdown
        Row 3: Costs
        """
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=("Equity Curve", "Drawdown", "Cumulative Costs")
        )

        ## 1. Equity Curve
        equity = self.result.equity_curve
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity.values, mode='lines', name='Equity', line=dict(color='blue')
        ), row=1, col=1)

        ## 2. Drawdown
        if not equity.empty:
            drawdown = self._compute_drawdown(equity)
            fig.add_trace(go.Scatter(
                x=drawdown.index, y=drawdown.values, mode='lines', fill='tozeroy', name='Drawdown', line=dict(color='red')
            ), row=2, col=1)

        ## 3. Costs (Stacked)
        if self.result.costs:
            for cost_name, cost_series in self.result.costs.items():
                if self._is_plottable_series(cost_series):
                    cumulative_cost = cost_series.cumsum()
                    fig.add_trace(go.Scatter(
                        x=cumulative_cost.index, y=cumulative_cost.values, mode='lines', stackgroup='costs', name=cost_name
                    ), row=3, col=1)

        fig.update_layout(
            height=800,
            title_text="Backtest Results Overview",
            template="plotly_white",
            showlegend=True
        )
        # Format the drawdown Y axis
        fig.update_yaxes(tickformat='.1%', row=2, col=1)

        return fig
