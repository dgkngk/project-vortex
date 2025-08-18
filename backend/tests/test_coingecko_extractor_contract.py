import pytest
from backend.etl.extractors.CoinGeckoExtractor import CoinGeckoExtractor

@pytest.fixture(scope="module")
def extractor():
    return CoinGeckoExtractor()


@pytest.mark.contract
def test_contract_get_listed_assets(extractor):
    assets = extractor.get_listed_assets()
    assert isinstance(assets, list)
    assert any(asset["id"] == "bitcoin" for asset in assets)
    assert any("symbol" in asset for asset in assets)


@pytest.mark.contract
def test_contract_get_latest_data_for_assets(extractor):
    data = extractor.get_latest_data_for_assets(["bitcoin", "ethereum", "litecoin"])
    assert "bitcoin" in data
    assert "usd" in data["bitcoin"]
    assert isinstance(data["bitcoin"]["usd"], (int, float))


@pytest.mark.contract
def test_contract_get_historical_data_for_assets(extractor):
    data = extractor.get_historical_data_for_assets(["bitcoin"], days=1)
    assert "bitcoin" in data
    assert "prices" in data["bitcoin"]
    assert len(data["bitcoin"]["prices"]) > 0
    assert isinstance(data["bitcoin"]["prices"][0][1], (int, float))


@pytest.mark.contract
def test_contract_get_market_data_for_assets(extractor):
    data = extractor.get_market_data_for_assets(["bitcoin", "ethereum"])
    assert "bitcoin" in data
    assert "ethereum" in data
    assert "current_price" in data["bitcoin"]
    assert isinstance(data["bitcoin"]["current_price"], (int, float))
