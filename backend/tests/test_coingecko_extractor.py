import time
from unittest.mock import MagicMock, patch

import pytest

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
    assert list(assets[0].keys())[0] == "bitcoin"
    assert assets[1]["ethereum"]["symbol"] == "eth"
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


@pytest.mark.contract
def test_coingecko_extractor_contract(extractor):
    """
    Contract test for CoinGeckoExtractor.
    This test makes live calls to the CoinGecko API.
    """
    # 1. Test asset listing
    assets = extractor.get_listed_assets()
    assert isinstance(assets, list)
    assert len(assets) > 0, "Should retrieve a list of assets"

    # Use a few well-known assets for the rest of the tests
    sample_asset_ids = ["bitcoin", "ethereum"]

    # 2. Test getting asset details
    asset_details = extractor.get_asset_details(sample_asset_ids[0])
    assert isinstance(asset_details, dict)
    assert asset_details["id"] == sample_asset_ids[0], (
        "Details should be for the requested asset"
    )

    # 3. Test latest data retrieval
    latest_data = extractor.get_latest_data_for_assets(sample_asset_ids)
    assert isinstance(latest_data, dict)
    for asset_id in sample_asset_ids:
        assert asset_id in latest_data, f"Latest data should contain {asset_id}"

    # 4. Test market data retrieval
    market_data = extractor.get_market_data_for_assets(sample_asset_ids)
    assert isinstance(market_data, dict)
    for asset_id in sample_asset_ids:
        assert asset_id in market_data, f"Market data should contain {asset_id}"

    # 5. Test historical data retrieval
    historical_data = extractor.get_historical_data_for_assets(sample_asset_ids, days=7)
    assert isinstance(historical_data, dict)
    for asset_id in sample_asset_ids:
        assert asset_id in historical_data, f"Historical data should contain {asset_id}"
        assert "prices" in historical_data[asset_id]

    # 6. Test historical chart data in a range
    to_timestamp = int(time.time())
    from_timestamp = to_timestamp - (7 * 24 * 60 * 60)  # 7 days ago
    chart_data = extractor.get_historical_chart_data_range(
        sample_asset_ids, from_timestamp, to_timestamp
    )
    assert isinstance(chart_data, dict)
    for asset_id in sample_asset_ids:
        assert asset_id in chart_data, f"Chart data should contain {asset_id}"
        assert "prices" in chart_data[asset_id]
        assert len(chart_data[asset_id]["prices"]) > 0

    # 7. Test OHLC data retrieval
    ohlc_data = extractor.get_ohlc_data_for_assets(sample_asset_ids, days=7)
    assert isinstance(ohlc_data, dict)
    for asset_id in sample_asset_ids:
        assert asset_id in ohlc_data, f"OHLC data should contain {asset_id}"
        assert isinstance(ohlc_data[asset_id], list)
        assert len(ohlc_data[asset_id]) > 0
        # OHLC data format is [timestamp, open, high, low, close]
        assert len(ohlc_data[asset_id][0]) == 5
