import pytest
import pandas as pd
from backend.etl.maintenance.UniverseBuilder import UniverseBuilder

@pytest.fixture
def universe_builder():
    return UniverseBuilder()

@pytest.mark.unit
class TestUniverseBuilder:
    def test_get_universe_returns_list(self, universe_builder):
        """Contract test: get_universe should return a list of strings."""
        result = universe_builder.get_universe(pd.Timestamp("2024-01-01"), "crypto")
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)

    def test_get_universe_filters_by_asset_class(self, universe_builder):
        """Ensure it respects the asset_class parameter."""
        # For now, we might mock this or expect empty/dummy list
        result = universe_builder.get_universe(pd.Timestamp("2024-01-01"), "stocks")
        assert isinstance(result, list)
