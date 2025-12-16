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
        raw_data: Dict[str, pd.DataFrame],
        strategies_config: Dict[StrategyConfigs, Dict[str, Any]],
        **kwargs,
    ):
        """
        Initializes the StrategyTransformer.

        Args:
            raw_data: A dictionary of pandas DataFrames (keyed by asset ID) containing TA data.
            strategies_config: A dictionary where keys are StrategyConfigs enums
                               and values are configuration dictionaries for each strategy.
        """
        super().__init__(raw_data)
        self.strategies: Dict[StrategyConfigs, BaseStrategy] = {}
        for strategy_name, config in strategies_config.items():
            self.strategies[strategy_name] = StrategyFactory.create_strategy(
                strategy_name, config
            )

    def transform(self) -> Dict[str, pd.DataFrame]:
        """
        Applies the configured trading strategies to the raw data to generate signals.

        Returns:
            A dictionary of pandas DataFrames (keyed by asset ID) with the original data
            and additional columns for each strategy's trading signal.
        """
        transformed_data = {}
        
        if not isinstance(self.raw_data, dict):
             # Fallback if somehow a single DF is passed (though not expected in this pipeline)
             return self.raw_data
             
        for asset_id, df in self.raw_data.items():
            if df.empty:
                transformed_data[asset_id] = df
                continue
                
            df_copy = df.copy()
            for strategy_name, strategy in self.strategies.items():
                try:
                    signal_df = strategy.generate_signal(df_copy)
                    # We assume signal_df contains the original index and a 'signal' column.
                    # Or strategy returns a DF with the signal column added.
                    # Based on StochRSIStrategy it returns df with 'signal' column.
                    
                    # If the strategy returns a full DF, we can just use that,
                    # but we need to merge if we run multiple strategies sequentially on the same DF copy.
                    
                    # More robust: take the 'signal' column from the result and add it to our df_copy
                    if "signal" in signal_df.columns:
                        df_copy[f"{strategy_name.name}_signal"] = signal_df["signal"]
                except Exception as e:
                    # Log error but continue
                    print(f"Error applying strategy {strategy_name} for asset {asset_id}: {e}")
                    continue
            
            transformed_data[asset_id] = df_copy
            
        return transformed_data
