import pandas as pd
import pytest

from backend.scitus.features.FeatureRegistry import FeatureDef, FeatureRegistry


@pytest.fixture
def registry():
    return FeatureRegistry()


@pytest.mark.unit
class TestFeatureRegistry:
    def test_default_features_registered(self, registry):
        """Default features (rsi_14, sma_20, etc.) should be pre-registered."""
        defaults = registry.list_features()
        assert "rsi_14" in defaults
        assert "sma_20" in defaults
        assert "sma_50" in defaults
        assert "ema_12" in defaults
        assert "ema_26" in defaults

    def test_get_existing_feature(self, registry):
        """Getting a registered feature should return its FeatureDef."""
        feature_def = registry.get("rsi_14")
        assert feature_def.name == "rsi_14"
        assert feature_def.window == 14
        assert callable(feature_def.function)

    def test_get_missing_feature_raises(self, registry):
        """Getting an unregistered feature should raise KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            registry.get("nonexistent_feature")

    def test_register_custom_feature(self, registry):
        """Custom features can be added to the registry."""
        custom = FeatureDef(
            name="my_feature",
            description="A custom test feature",
            function=lambda df: df["close"] * 2,
            window=1,
        )
        registry.register(custom)

        retrieved = registry.get("my_feature")
        assert retrieved.name == "my_feature"
        assert retrieved.description == "A custom test feature"

    def test_list_features_includes_custom(self, registry):
        """list_features should include both default and custom features."""
        custom = FeatureDef(
            name="custom_sma",
            description="Custom SMA",
            function=lambda df: df["close"].rolling(5).mean(),
            window=5,
        )
        registry.register(custom)

        features = registry.list_features()
        assert "custom_sma" in features
        assert "rsi_14" in features
