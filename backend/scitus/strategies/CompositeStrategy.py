import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from backend.scitus.BaseStrategy import BaseStrategy
from backend.core.enums.SignalTypes import SignalTypes
from backend.core.enums.StrategyConfigs import StrategyConfigs

class CompositeStrategy(BaseStrategy):
    """
    A strategy that uses a Primary strategy to generate candidates,
    and a set of Filter strategies to confirm them.
    
    Logic:
    - Primary says BUY -> Check Filters.
    - If ALL Filters agree (or don't say SELL), confirm BUY.
    - Else HOLD.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Config structure expected:
        {
            "primary_strategy": {"type": "MACD", "config": {...}},
            "filter_strategies": [
                {"type": "RSI", "config": {...}}
            ]
        }
        """
        super().__init__(config)
        self.primary_strategy: Optional[BaseStrategy] = None
        self.filter_strategies: list[BaseStrategy] = []
        self._initialize_strategies()

    def _initialize_strategies(self):
        from backend.scitus.StrategyFactory import StrategyFactory
        
        # Init Primary
        primary_conf = self.config.get("primary_strategy", {})
        if primary_conf:
            try:
                p_type = primary_conf.get("type")
                p_cfg = primary_conf.get("config", {})
                self.primary_strategy = StrategyFactory.create_strategy(
                    StrategyConfigs[p_type], p_cfg
                )
            except Exception as e:
                print(f"Error initializing primary strategy: {e}")

        # Init Filters
        filter_confs = self.config.get("filter_strategies", [])
        for entry in filter_confs:
            try:
                f_type = entry.get("type")
                f_cfg = entry.get("config", {})
                filt = StrategyFactory.create_strategy(
                    StrategyConfigs[f_type], f_cfg
                )
                self.filter_strategies.append(filt)
            except Exception as e:
                print(f"Error initializing filter strategy: {e}")

    def generate_signal(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        
        if not self.primary_strategy:
            return df
            
        # 1. Get Primary Signal
        primary_res = self.primary_strategy.generate_signal(df.copy())
        if "signal" not in primary_res.columns:
            return df
            
        primary_signals = primary_res["signal"]
        
        # 2. Apply Filters
        # We start with the primary signal, then invalidate it if filters disagree
        final_signal = primary_signals.copy()
        
        for filt in self.filter_strategies:
            filt_res = filt.generate_signal(df.copy())
            if "signal" in filt_res.columns:
                filt_s = filt_res["signal"]
                
                # Logic:
                # If Primary is BUY, Filter must NOT be SELL (or must be BUY? "Confirmation" vs "Filter")
                # Let's implement "Confirmation": Filter must also be BUY to allow a BUY.
                # If Filter is HOLD, it invalidates the BUY. (Strict Mode)
                # Flexible Mode: Filter must not be SELL.
                
                # Let's go with Strict Confirmation for "Composite" usually implies high confidence.
                # BUY requires Primary=BUY AND Filter=BUY
                
                mask_buy = (final_signal == SignalTypes.BUY.value)
                # If filter is not BUY, set to HOLD
                final_signal[mask_buy & (filt_s != SignalTypes.BUY.value)] = SignalTypes.HOLD.value
                
                # SELL requires Primary=SELL AND Filter=SELL
                mask_sell = (final_signal == SignalTypes.SELL.value)
                final_signal[mask_sell & (filt_s != SignalTypes.SELL.value)] = SignalTypes.HOLD.value

        df["signal"] = final_signal
        return df
