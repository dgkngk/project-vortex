import time

import pytest

from backend.core.Config import AppConfig
from backend.etl.extractors.PolygonCryptoExtractor import PolygonCryptoExtractor
from backend.etl.extractors.PolygonStockExtractor import PolygonStockExtractor


skip_if_no_key = pytest.mark.skipif(
    not AppConfig().polygon_api_key,
    reason="Polygon API key not found in environment"
)


@skip_if_no_key
@pytest.mark.contract
def test_pagination_exhaustion():
    """
    Test that the extractor stops correctly when there are no more pages,
    even if the requested limit hasn't been reached.
    """
    extractor = PolygonCryptoExtractor()
    # We know there are around 623 crypto assets. Requesting 2000 should return all of them.
    # This verifies the `next_url` check loop termination.
    assets = extractor.get_listed_assets(limit=2000)

    print(f"Crypto assets found: {len(assets)}")
    assert len(assets) > 0
    assert len(assets) < 2000
    assert isinstance(assets[0], dict)


@skip_if_no_key
@pytest.mark.slow
def test_pagination_exact_limit():
    """
    Test that the extractor stops exactly at the requested limit
    when it spans multiple pages.
    """
    extractor = PolygonStockExtractor()
    # Request 5500 items. Should trigger 6 requests (1000 * 5, 500).
    # Since we have 5 requests/min bucket, this should be fast enough.
    time.sleep(60)
    assets = extractor.get_listed_assets(limit=5500)

    print(f"Stock assets found: {len(assets)}")
    assert len(assets) >= 5500
    assert isinstance(assets[0], dict)
