import pytest
from unittest.mock import patch, MagicMock
from backend.core.enums.AssetEnums import DataIntervals
from backend.etl.extractors.BinanceExtractor import BinanceExtractor


@pytest.fixture
def extractor():
    return BinanceExtractor()


@patch("requests.get")
@pytest.mark.unit
def test_get_listed_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "symbols": [
            {"symbol": "BTCUSDT"},
            {"symbol": "ETHUSDT"},
        ]
    }
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    assets = extractor.get_listed_assets()
    assert isinstance(assets, list)
    assert assets[0]["symbol"] == "BTCUSDT"
    assert assets[1]["symbol"] == "ETHUSDT"
    assert mock_get.called


@patch("requests.get")
@pytest.mark.unit
def test_get_latest_data_for_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"symbol": "BTCUSDT", "price": "50000.00"},
        {"symbol": "ETHUSDT", "price": "4000.00"},
    ]
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    data = extractor.get_latest_data_for_assets(["BTCUSDT", "ETHUSDT"])
    assert "BTCUSDT" in data
    assert float(data["BTCUSDT"]["price"]) == 50000.00
    assert "ETHUSDT" in data
    assert mock_get.called


@patch("requests.get")
@pytest.mark.unit
def test_run_extraction(mock_get, extractor):
    # Mock assets list
    mock_assets_response = MagicMock()
    mock_assets_response.json.return_value = {
        "symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]
    }
    mock_assets_response.raise_for_status = lambda: None

    # Mock ticker data
    mock_ticker_response = MagicMock()
    mock_ticker_response.json.return_value = [
        {"symbol": "BTCUSDT", "price": "50000.00"},
        {"symbol": "ETHUSDT", "price": "4000.00"},
    ]
    mock_ticker_response.raise_for_status = lambda: None

    # Side effect: first call = assets, second call = ticker
    mock_get.side_effect = [mock_assets_response, mock_ticker_response]

    results = extractor.run_extraction()
    assert isinstance(results, dict)
    assert "BTCUSDT" in results
    assert float(results["BTCUSDT"]["price"]) == 50000.00
    assert "ETHUSDT" in results
    assert mock_get.call_count == 2

@pytest.mark.contract
def test_binance_extractor_contract():
    extractor = BinanceExtractor()

    # 🔹 1. Test asset listing
    assets = extractor.get_listed_assets()
    assert isinstance(assets, list)
    assert len(assets) > 0

    # Pick first 2 assets for contract testing
    sample_assets = [a for a in assets[:2]]

    # 🔹 2. Test latest ticker data
    latest_data = extractor.get_latest_data_for_assets([n["id"] for n in sample_assets])
    assert isinstance(latest_data, dict)

    market_data = extractor.get_market_data_for_assets([n["id"] for n in sample_assets], DataIntervals.ONE_DAY)
    assert isinstance(market_data, dict)

    # 🔹 Test run_extraction() integration
    results = extractor.run_extraction()
    assert isinstance(results, dict)
