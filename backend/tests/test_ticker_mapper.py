import pytest
import pandas as pd
from backend.etl.maintenance.TickerMapper import TickerMapper

@pytest.fixture
def ticker_mapper():
    # Setup a mapper with some known mappings
    mapper = TickerMapper()
    # Manually inject mappings for testing purposes
    # Logic: "OLD": [("NEW", "2023-01-01")] means OLD became NEW on 2023-01-01
    mapper.mappings = {
        "LEND": {"new_ticker": "AAVE", "date": pd.Timestamp("2020-10-02")},
        "MATIC": {"new_ticker": "POL", "date": pd.Timestamp("2024-09-01")}
    }
    return mapper

@pytest.mark.unit
class TestTickerMapper:
    def test_resolve_renamed_ticker_before_rename(self, ticker_mapper):
        """Before the rename date, it should return the old ticker."""
        assert ticker_mapper.resolve("LEND", pd.Timestamp("2020-01-01")) == "LEND"

    def test_resolve_renamed_ticker_after_rename(self, ticker_mapper):
        """After the rename date, it should return the new ticker."""
        assert ticker_mapper.resolve("LEND", pd.Timestamp("2020-10-03")) == "AAVE"
        
    def test_resolve_stable_ticker(self, ticker_mapper):
        """Tickers with no mappings should return themselves."""
        assert ticker_mapper.resolve("BTC", pd.Timestamp("2020-01-01")) == "BTC"

    def test_resolve_chained_rename(self, ticker_mapper):
        """Future-proofing: Test handling if A -> B -> C (not implemented yet, but good to think about).
        For now, just ensure direct mapping works."""
        pytest.xfail("Chained renames (A -> B -> C) are not implemented yet in TickerMapper.")
