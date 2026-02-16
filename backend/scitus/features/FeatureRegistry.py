from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

import pandas as pd
import pandas_ta as ta


@dataclass
class FeatureDef:
    """Defines a single feature: its name, calculation function, and parameters."""

    name: str
    description: str
    function: Callable[[pd.DataFrame], pd.Series]
    params: Dict = field(default_factory=dict)
    window: int = 0


class FeatureRegistry:
    """
    Central registry for feature definitions.

    Features are registered as (name -> FeatureDef) mappings.
    A set of default technical indicators are pre-registered on construction.
    """

    def __init__(self):
        self._features: Dict[str, FeatureDef] = {}
        self._register_defaults()

    def register(self, feature_def: FeatureDef) -> None:
        """Register a feature definition."""
        self._features[feature_def.name] = feature_def

    def get(self, name: str) -> FeatureDef:
        """
        Retrieve a feature definition by name.

        Raises:
            KeyError: If feature name is not registered.
        """
        if name not in self._features:
            raise KeyError(
                f"Feature '{name}' is not registered. "
                f"Available: {list(self._features.keys())}"
            )
        return self._features[name]

    def list_features(self) -> list[str]:
        """Return all registered feature names."""
        return list(self._features.keys())

    def _register_defaults(self) -> None:
        """Pre-register standard technical indicators."""
        self.register(FeatureDef(
            name="rsi_14",
            description="Relative Strength Index (14-period)",
            function=lambda df: ta.rsi(df["close"], length=14),
            window=14,
        ))
        self.register(FeatureDef(
            name="sma_20",
            description="Simple Moving Average (20-period)",
            function=lambda df: ta.sma(df["close"], length=20),
            window=20,
        ))
        self.register(FeatureDef(
            name="sma_50",
            description="Simple Moving Average (50-period)",
            function=lambda df: ta.sma(df["close"], length=50),
            window=50,
        ))
        self.register(FeatureDef(
            name="ema_12",
            description="Exponential Moving Average (12-period)",
            function=lambda df: ta.ema(df["close"], length=12),
            window=12,
        ))
        self.register(FeatureDef(
            name="ema_26",
            description="Exponential Moving Average (26-period)",
            function=lambda df: ta.ema(df["close"], length=26),
            window=26,
        ))
