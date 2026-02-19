from dataclasses import dataclass

import pandas as pd

from backend.scitus.backtest.execution.Order import OrderSide


@dataclass
class Fill:
    """
    Represents a completed order execution.
    """
    order_id: str
    side: OrderSide
    quantity: float
    fill_price: float
    timestamp: pd.Timestamp
    commission: float = 0.0
    slippage_cost: float = 0.0
