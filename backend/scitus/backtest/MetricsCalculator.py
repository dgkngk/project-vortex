import numpy as np
import pandas as pd
from typing import Dict

class MetricsCalculator:
    """
    Static utility for calculating backtest performance metrics.
    """

    @staticmethod
    def calculate(
        returns: pd.Series, 
        equity: pd.Series, 
        positions: pd.Series,
        trades_df: pd.DataFrame = None,
        costs: Dict[str, pd.Series] = None,
        bars_per_year: int = 365
    ) -> Dict[str, float]:
        """
        Compute full suite of metrics.
        """
        metrics = {}
        
        # Basic Return Metrics
        total_return = (
            (equity.iloc[-1] / equity.iloc[0]) - 1
            if (len(equity) > 0 and equity.iloc[0] > 0)
            else 0.0
        )
        
        years = len(equity) / bars_per_year if len(equity) > 0 else 0
        if years > 0 and not equity.empty and equity.iloc[0] > 0 and equity.iloc[-1] > 0:
            cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
        else:
            cagr = 0.0

        metrics["total_return"] = total_return
        metrics["cagr"] = cagr
        
        # Risk Metrics
        metrics["sharpe_ratio"] = MetricsCalculator._sharpe(returns, bars_per_year)
        metrics["sortino_ratio"] = MetricsCalculator._sortino(returns, bars_per_year)
        metrics["max_drawdown"] = MetricsCalculator._max_drawdown(equity)
        metrics["calmar_ratio"] = MetricsCalculator._calmar(cagr, metrics["max_drawdown"])
        
        # Cost Metrics
        total_cost = 0.0
        if costs:
            for cost_type, cost_series in costs.items():
                total_cost += cost_series.sum()
        metrics["total_costs"] = total_cost

        # Trade Stats
        metrics["win_rate"] = MetricsCalculator._win_rate(returns, trades_df)
        metrics["profit_factor"] = MetricsCalculator._profit_factor(returns, trades_df)
        metrics["avg_trade_duration"] = MetricsCalculator._avg_trade_duration(trades_df)
        
        return metrics

    @staticmethod
    def _sharpe(returns: pd.Series, bars_per_year: int) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        return (returns.mean() / returns.std()) * np.sqrt(bars_per_year)

    @staticmethod
    def _sortino(returns: pd.Series, bars_per_year: int) -> float:
        if returns.empty:
            return 0.0
        # Sortino uses downside deviation (std of negative returns) as denominator
        downside = returns[returns < 0]
        if downside.empty:
            return 0.0
            
        # Strict definition: sqrt(mean(min(0, r)^2))
        downside_std = np.sqrt(np.mean(np.minimum(0, returns)**2))
        
        if downside_std == 0:
            return 0.0
            
        return (returns.mean() / downside_std) * np.sqrt(bars_per_year)

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        if equity.empty:
            return 0.0
        running_max = equity.cummax()
        drawdown = (equity / running_max) - 1
        return abs(drawdown.min())

    @staticmethod
    def _calmar(cagr: float, max_dd: float) -> float:
        if max_dd == 0:
            return 0.0
        return cagr / max_dd

    @staticmethod
    def _win_rate(returns: pd.Series, trades_df: pd.DataFrame = None) -> float:
        if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
            # Use actual trades if available and they have PnL calculated
            completed_trades = trades_df.dropna(subset=["pnl"])
            if completed_trades.empty:
                return 0.0
            wins = len(completed_trades[completed_trades["pnl"] > 0])
            return wins / len(completed_trades)
            
        # Fallback to bar-by-bar active periods
        active_returns = returns[returns != 0]
        if active_returns.empty:
            return 0.0
        return len(active_returns[active_returns > 0]) / len(active_returns)

    @staticmethod
    def _profit_factor(returns: pd.Series, trades_df: pd.DataFrame = None) -> float:
        if trades_df is not None and not trades_df.empty and "pnl" in trades_df.columns:
            # Use actual trades if available and they have PnL calculated
            completed_trades = trades_df.dropna(subset=["pnl"])
            gross_profit = completed_trades[completed_trades["pnl"] > 0]["pnl"].sum()
            gross_loss = abs(completed_trades[completed_trades["pnl"] < 0]["pnl"].sum())
        else:
            # Fallback to bar-by-bar
            gross_profit = returns[returns > 0].sum()
            gross_loss = abs(returns[returns < 0].sum())
        
        if gross_loss == 0:
             # Return a large finite number to avoid JSON serialization issues with Infinity
            return 100.0 if gross_profit > 0 else 0.0
            
        return gross_profit / gross_loss

    @staticmethod
    def _avg_trade_duration(trades_df: pd.DataFrame = None) -> float:
        if trades_df is None or trades_df.empty or "duration" not in trades_df.columns:
            return 0.0
            
        completed_trades = trades_df.dropna(subset=["duration"])
        if completed_trades.empty:
            return 0.0
            
        return float(completed_trades["duration"].mean())
