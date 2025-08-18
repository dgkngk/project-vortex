import pytest
from unittest.mock import patch, MagicMock
from backend.etl.extractors.CoinGeckoExtractor import CoinGeckoExtractor


@pytest.fixture
def extractor():
    return CoinGeckoExtractor()


@patch("requests.get")
@pytest.mark.unit
def test_get_listed_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
    ]
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    assets = extractor.get_listed_assets()
    assert isinstance(assets, list)
    assert assets[0]["id"] == "bitcoin"
    assert assets[1]["symbol"] == "eth"
    assert mock_get.called


@patch("requests.get")
@pytest.mark.unit
def test_get_latest_data_for_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "bitcoin": {
            "usd": 50000,
            "usd_market_cap": 1000000000,
            "usd_24h_vol": 20000000,
            "usd_24h_change": -1.5,
            "last_updated_at": 1618910000,
        }
    }
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    data = extractor.get_latest_data_for_assets(["bitcoin"])
    assert "bitcoin" in data
    assert "usd" in data["bitcoin"]
    assert data["bitcoin"]["usd"] == 50000
    assert mock_get.called


@patch("requests.get")
@pytest.mark.unit
def test_get_historical_data_for_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "prices": [[1618910000, 50000], [1618913600, 50500]],
        "market_caps": [[1618910000, 1000000000]],
        "total_volumes": [[1618910000, 20000000]],
    }
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    data = extractor.get_historical_data_for_assets(["bitcoin"], days=1)
    assert "bitcoin" in data
    assert "prices" in data["bitcoin"]
    assert isinstance(data["bitcoin"]["prices"], list)
    assert mock_get.called


@patch("requests.get")
@pytest.mark.unit
def test_get_market_data_for_assets(mock_get, extractor):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "bitcoin", "symbol": "btc", "current_price": 50000}
    ]
    mock_response.raise_for_status = lambda: None
    mock_get.return_value = mock_response

    data = extractor.get_market_data_for_assets(["bitcoin"])
    assert "bitcoin" in data
    assert data["bitcoin"]["current_price"] == 50000
    assert mock_get.called
