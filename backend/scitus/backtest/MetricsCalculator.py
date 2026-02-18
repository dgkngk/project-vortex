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
        bars_per_year: int = 365
    ) -> Dict[str, float]:
        """
        Compute full suite of metrics.
        """
        metrics = {}
        
        # Basic Return Metrics
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1 if not equity.empty else 0.0
        
        years = len(equity) / bars_per_year if len(equity) > 0 else 0
        if years > 0 and equity.iloc[-1] > 0:
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
        
        # Trade Stats
        metrics["win_rate"] = MetricsCalculator._win_rate(returns)
        metrics["profit_factor"] = MetricsCalculator._profit_factor(returns)
        
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
        downside = returns[returns < 0]
        if downside.empty or downside.std() == 0:
            return 0.0
        
        # Sortino uses downside dev as denominator
        std_down = downside.std() 
        # Some defs use sqrt(mean(downside^2)). Let's use std of negative returns for simplicity + consistency
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
    def _win_rate(returns: pd.Series) -> float:
        # Vectorized "trades" are tricky to define just from returns.
        # This is a bar-by-bar win rate, explicitly noted.
        # For actual *Trade* win rate, we need the trades DataFrame.
        # Let's stick to positive bars / total bars for generic vector backtests?
        # OR: The plan implies trade-based. VectorizedBacktester creates a trades DF.
        # But this function only takes returns?
        
        # Let's use Bar Win Rate for now, or assume this is a placeholder 
        # until we pass the Trades DF into Calculate.
        
        # Update: Let's assume returns != 0 are active periods.
        active_returns = returns[returns != 0]
        if active_returns.empty:
            return 0.0
        return len(active_returns[active_returns > 0]) / len(active_returns)

    @staticmethod
    def _profit_factor(returns: pd.Series) -> float:
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
            
        return gross_profit / gross_loss
