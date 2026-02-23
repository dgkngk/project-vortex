from dataclasses import dataclass

import pandas as pd

from backend.scitus.backtest.execution.Order import OrderSide


@dataclass
class TradeRecord:
    """
    A closed round-trip trade record with full entry/exit details.
    """
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    pnl: float
    commission: float
    slippage: float
    holding_bars: int
