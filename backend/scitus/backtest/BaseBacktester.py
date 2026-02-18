from abc import ABC, abstractmethod
from typing import Union

import pandas as pd

from backend.scitus.backtest.BacktestResult import BacktestResult
from backend.scitus.backtest.slippage.BaseSlippage import BaseSlippage
from backend.scitus.backtest.slippage.FixedSlippage import FixedSlippage


class BaseBacktester(ABC):
    """
    Abstract base class for all backtesting engines.
    """

    def __init__(
        self,
        initial_capital: float = 10_000.0,
        transaction_cost: float = 0.001,
        slippage_model: Union[BaseSlippage, None] = None,
        funding_rate: Union[float, pd.Series] = 0.0,
        borrow_rate: Union[float, pd.Series] = 0.0,
        bars_per_year: int = 365,
    ):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.slippage_model = slippage_model or FixedSlippage(slippage_pct=0.0)
        self.funding_rate = funding_rate
        self.borrow_rate = borrow_rate
        self.bars_per_year = bars_per_year

    @abstractmethod
    def run(self, data: pd.DataFrame, signals: pd.Series, **kwargs) -> BacktestResult:
        """
        Run the backtest.
        
        Args:
            data: OHLCV DataFrame.
            signals: Series of trading signals (1, -1, 0).
            
        Returns:
            BacktestResult object containing all metrics and curves.
        """
        pass
