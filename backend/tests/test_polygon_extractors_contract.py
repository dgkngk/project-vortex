import os

import pytest

from backend.core.enums.AssetEnums import DataIntervals
from backend.etl.extractors.PolygonCryptoExtractor import PolygonCryptoExtractor
from backend.etl.extractors.PolygonForexExtractor import PolygonForexExtractor
from backend.etl.extractors.PolygonStockExtractor import PolygonStockExtractor

skip_if_no_key = pytest.mark.skipif(
    not (os.getenv("POLYGON_API_KEY") or os.getenv("MASSIVE_API_KEY")),
    reason="Polygon API key not found in environment"
)


@skip_if_no_key
@pytest.mark.contract
def test_polygon_stock_extractor_contract():
    extractor = PolygonStockExtractor()

    # 1. Test asset listing
    assets = extractor.get_listed_assets(limit=10)
    assert isinstance(assets, list)
    assert len(assets) > 0

    # Pick first 2 assets
    sample_assets = [a for a in assets[:2]]
    asset_ids = [n["id"] for n in sample_assets]

    # 2. Test latest data
    latest_data = extractor.get_latest_data_for_assets(asset_ids)
    assert isinstance(latest_data, dict)
    # Note: Depending on market hours, snapshot might be empty or partial,
    # but the method should return a dict.

    # 3. Test market data (previous close)
    market_data = extractor.get_market_data_for_assets(asset_ids)
    assert isinstance(market_data, dict)

    # 4. Test historical data
    historical_data = extractor.get_historical_data_for_assets(
        asset_ids, DataIntervals.ONE_DAY, limit=5
    )
    assert isinstance(historical_data, dict)
    for aid in asset_ids:
        if aid in historical_data:
            assert isinstance(historical_data[aid], list)


@skip_if_no_key
@pytest.mark.contract
def test_polygon_crypto_extractor_contract():
    extractor = PolygonCryptoExtractor()

    # 1. Test asset listing
    assets = extractor.get_listed_assets(limit=5)
    assert isinstance(assets, list)
    assert len(assets) > 0

    sample_assets = [a for a in assets[:2]]
    asset_ids = [n["id"] for n in sample_assets]

    # 2. Test latest data
    latest_data = extractor.get_latest_data_for_assets(asset_ids)
    assert isinstance(latest_data, dict)

    # 3. Test market data
    market_data = extractor.get_market_data_for_assets(asset_ids)
    assert isinstance(market_data, dict)

    # 4. Test historical data
    historical_data = extractor.get_historical_data_for_assets(
        asset_ids, DataIntervals.ONE_DAY, limit=5
    )
    assert isinstance(historical_data, dict)


@skip_if_no_key
@pytest.mark.contract
def test_polygon_forex_extractor_contract():
    extractor = PolygonForexExtractor()

    # 1. Test asset listing
    assets = extractor.get_listed_assets(limit=5)
    assert isinstance(assets, list)
    assert len(assets) > 0

    sample_assets = [a for a in assets[:2]]
    asset_ids = [n["id"] for n in sample_assets]

    # 2. Test latest data
    latest_data = extractor.get_latest_data_for_assets(asset_ids)
    assert isinstance(latest_data, dict)

    # 3. Test market data
    market_data = extractor.get_market_data_for_assets(asset_ids)
    assert isinstance(market_data, dict)

    # 4. Test historical data
    historical_data = extractor.get_historical_data_for_assets(
        asset_ids, DataIntervals.ONE_DAY, limit=5
    )
    assert isinstance(historical_data, dict)
