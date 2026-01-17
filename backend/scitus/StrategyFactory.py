from enum import Enum
from typing import Any, Dict, Type

from backend.core.enums.StrategyConfigs import StrategyConfigs
from backend.scitus.BaseStrategy import BaseStrategy
from backend.scitus.strategies.BollingerBandsStrategy import BollingerBandsStrategy
from backend.scitus.strategies.HMARSIStrategy import HMARSIStrategy
from backend.scitus.strategies.MACDStrategy import MACDStrategy
from backend.scitus.strategies.StochRSIStrategy import StochRSIStrategy
from backend.scitus.strategies.VWAPStrategy import VWAPStrategy


class StrategyFactory:
    """
    Factory class to create trading strategies.
    """

    _strategies: Dict[Enum, Type[BaseStrategy]] = {
        StrategyConfigs.BOLLINGER_BANDS: BollingerBandsStrategy,
        StrategyConfigs.STOCHRSI: StochRSIStrategy,
        StrategyConfigs.MACD: MACDStrategy,
        StrategyConfigs.VWAP: VWAPStrategy,
        StrategyConfigs.HMA_RSI: HMARSIStrategy,
    }

    @staticmethod
    def create_strategy(
        strategy_name: StrategyConfigs, config_dict: Dict[str, Any]
    ) -> BaseStrategy:
        """
        Creates a strategy for the given name.
        """
        strategy_class = StrategyFactory._strategies.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unsupported strategy: {strategy_name}")
        return strategy_class(config=config_dict)
