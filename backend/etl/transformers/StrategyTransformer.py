from typing import Any, Dict

import pandas as pd

from backend.core.enums.StrategyConfigs import StrategyConfigs
from backend.etl.transformers.BaseTransformer import BaseTransformer
from backend.scitus.BaseStrategy import BaseStrategy
from backend.scitus.StrategyFactory import StrategyFactory


class StrategyTransformer(BaseTransformer):
    """
    Transforms technical analysis (TA) data by applying a set of trading strategies
    to generate trading signals.
    """

    def __init__(
        self,
        raw_data: pd.DataFrame,
        strategies_config: Dict[StrategyConfigs, Dict[str, Any]],
    ):
        """
        Initializes the StrategyTransformer.

        Args:
            raw_data: A pandas DataFrame containing TA data.
            strategies_config: A dictionary where keys are StrategyConfigs enums
                               and values are configuration dictionaries for each strategy.
        """
        super().__init__(raw_data)
        self.strategies: Dict[StrategyConfigs, BaseStrategy] = {}
        for strategy_name, config in strategies_config.items():
            self.strategies[strategy_name] = StrategyFactory.create_strategy(
                strategy_name, config
            )

    def transform(self) -> pd.DataFrame:
        """
        Applies the configured trading strategies to the raw data to generate signals.

        Each strategy's generated signal is added as a new column to the DataFrame.
        The column name is derived from the strategy's enum name.

        Returns:
            A pandas DataFrame with the original data and additional columns for
            each strategy's trading signal.
        """
        transformed_data = self.raw_data.copy()
        for strategy_name, strategy in self.strategies.items():
            signal_df = strategy.generate_signal(self.raw_data)
            transformed_data[f"{strategy_name.name}_signal"] = signal_df["signal"]
        return transformed_data
