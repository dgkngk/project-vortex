from dataclasses import dataclass, field
from typing import Dict, Any, Union

import pandas as pd


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
    costs: Dict[str, Union[pd.Series, float]]
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
        # Safely handle cases where trades may be empty or None
        if isinstance(self.trades, pd.DataFrame) and not self.trades.empty:
            # Preserve numeric types in trades; only stringify datetime-like columns
            trades_df = self.trades.copy()
            datetime_cols = trades_df.select_dtypes(include=["datetime", "datetimetz"]).columns
            if len(datetime_cols) > 0:
                trades_df[datetime_cols] = trades_df[datetime_cols].astype(str)
            trades_data = trades_df.to_dict(orient="records")
        else:
            trades_data = []

        return {
            "metrics": self.metrics,
            "metadata": self.metadata,
            "trades": trades_data,
            # Use None for NaNs to be JSON compliant (null)
            "equity_curve": self.equity_curve.where(pd.notna(self.equity_curve), None).to_dict(),
        }
