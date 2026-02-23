from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

import pandas as pd


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


@dataclass
class Order:
    """
    Represents a trading order.

    quantity is always positive; side determines direction.
    LIMIT orders require limit_price, STOP orders require stop_price.
    """
    side: OrderSide
    order_type: OrderType
    quantity: float
    symbol: str = "DEFAULT"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    created_at: Optional[pd.Timestamp] = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(f"Order quantity must be positive, got {self.quantity}")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("LIMIT orders require limit_price")
        if self.order_type == OrderType.STOP and self.stop_price is None:
            raise ValueError("STOP orders require stop_price")
