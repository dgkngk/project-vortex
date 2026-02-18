import pandas as pd
from typing import List, Dict, Any
from backend.scitus.BaseStrategy import BaseStrategy
from backend.core.enums.SignalTypes import SignalTypes
from backend.core.enums.StrategyConfigs import StrategyConfigs
from backend.core.VortexLogger import VortexLogger

class VotingStrategy(BaseStrategy):
    """
    A strategy that aggregates signals from multiple sub-strategies via voting.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the VotingStrategy.
        
        Config structure expected:
        {
            "strategies": [
                {"type": "MACD", "config": {...}},
                {"type": "RSI", "config": {...}}
            ],
            "min_votes": 2
        }
        """
        super().__init__(config)
        self.logger = VortexLogger(name="VotingStrategy")
        self.strategies: List[BaseStrategy] = []
        self.min_votes = self.config.get("min_votes", 1)
        self._initialize_strategies()

    def _initialize_strategies(self):
        # Local import to avoid circular dependency
        from backend.scitus.StrategyFactory import StrategyFactory
        
        strategy_configs = self.config.get("strategies", [])
        for entry in strategy_configs:
            strat_type_str = entry.get("type")
            strat_conf = entry.get("config", {})
            
            # Resolve string to Enum
            try:
                # Assuming strat_type_str matches the Enum member name exactly (e.g. "MACD")
                strat_enum = StrategyConfigs[strat_type_str]
                strategy = StrategyFactory.create_strategy(strat_enum, strat_conf)
                self.strategies.append(strategy)
            except KeyError:
                self.logger.warning(f"Unknown strategy type '{strat_type_str}' in VotingStrategy config.")
            except Exception as e:
                self.logger.error(f"Error initializing sub-strategy {strat_type_str}: {e}")

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        
        if not self.strategies:
            # If no sub-strategies are configured, default to HOLD for all rows
            df["signal"] = SignalTypes.HOLD.value
            return df
            
        # Initialize vote counters
        buy_votes = pd.Series(0, index=df.index)
        sell_votes = pd.Series(0, index=df.index)
        
        for strategy in self.strategies:
            # We assume generate_signal returns a DF with a 'signal' column
            # or the same DF with 'signal' appended.
            try:
                sig_df = strategy.generate_signal(df.copy())
                if "signal" in sig_df.columns:
                    # Tally votes
                    s = sig_df["signal"]
                    # Treat any positive value as BUY-directional
                    buy_votes += (s > 0).astype(int)
                    # Some strategies might use UNDERPRICED as BUY equivalent, check logic?
                    # For now, strict mapping to SignalTypes
                    
                    # Treat any negative value as SELL-directional
                    sell_votes += (s < 0).astype(int)
            except Exception as e:
                self.logger.error(f"Error in sub-strategy execution: {e}")
                
        # Determine final signal
        final_signal = pd.Series(SignalTypes.HOLD.value, index=df.index)
        
        # Buy Condition
        final_signal[buy_votes >= self.min_votes] = SignalTypes.BUY.value
        
        # Sell Condition (Prioritize Sell if both meet threshold? Or net vote? 
        # Usually Sell signals are distinct. Let's say if Sell votes >= threshold -> Sell)
        # If both conflict, Hold (or prioritize one). Here we let Sell overwrite Buy for safety.
        final_signal[sell_votes >= self.min_votes] = SignalTypes.SELL.value
        
        df["signal"] = final_signal
        return df
