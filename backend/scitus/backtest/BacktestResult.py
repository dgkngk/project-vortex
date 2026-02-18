from dataclasses import dataclass, field
from typing import Dict, Any

import pandas as pd
import plotly.graph_objects as go


@dataclass
class BacktestResult:
    """
    Container for backtest results.
    """
    equity_curve: pd.Series
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: Dict[str, float]
    costs: Dict[str, pd.Series]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Combine core time-series into a single DataFrame.
        """
        df = pd.DataFrame({
            "equity": self.equity_curve,
            "returns": self.returns,
            "positions": self.positions,
        })
        
        # Add cost columns
        for cost_name, cost_series in self.costs.items():
            df[f"cost_{cost_name}"] = cost_series
            
        return df

    def to_json(self) -> Dict[str, Any]:
        """
        Serialize results for API response.
        Handles NaN/Inf values for JSON compliance.
        """
        return {
            "metrics": self.metrics,
            "metadata": self.metadata,
            "trades": self.trades.astype(str).to_dict(orient="records"),
            # Equity curve sampled for lightweight frontend? Or full?
            # For now full, convert index to string
            "equity_curve": self.equity_curve.fillna(0).to_dict(),
        }
