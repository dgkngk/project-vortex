import pandas as pd
import pytest

from backend.etl.extractors.BinanceExtractor import BinanceExtractor
from backend.etl.transformers.BinanceHDTransformer import BinanceHDTransformer


@pytest.fixture(scope="module")
def binance_extractor():
    """
    Fixture for the BinanceExtractor.
    Using module scope to avoid re-instantiating for every test function.
    """
    return BinanceExtractor()


@pytest.mark.contract
def test_binance_hd_transformer_contract(binance_extractor):
    """
    Contract test for BinanceHDTransformer.
    It simulates the process from fetching asset lists to transforming historical data.
    """
    # 1. Get listed assets
    listed_assets = binance_extractor.get_listed_assets()
    assert listed_assets, "Should retrieve a list of assets"
    assert isinstance(listed_assets, list), "Asset list should be a list"

    # 2. Get a small sample of asset IDs to test
    asset_ids = [
        asset["id"] for asset in listed_assets if asset["id"].endswith("USDT")
    ][:30]
    assert asset_ids, "Should be able to find some USDT pairs"

    # 3. Fetch historical data for the sample assets
    historical_data = binance_extractor.get_historical_data_for_assets(
        asset_ids, limit=10
    )
    assert historical_data, "Should retrieve historical data"
    assert isinstance(historical_data, dict), "Historical data should be a dictionary"
    assert len(historical_data) > 0, "Should contain data for at least one asset"

    # 4. Transform the data
    transformer = BinanceHDTransformer(raw_data=historical_data)
    transformed_data = transformer.transform()

    # 5. Assert the transformation result
    assert transformed_data, "Transformed data should not be empty"
    assert isinstance(transformed_data, dict), "Transformed data should be a dictionary"
    assert len(transformed_data) > 0, (
        "Should contain transformed data for at least one asset"
    )

    for asset_id, df in transformed_data.items():
        assert asset_id in asset_ids, (
            f"Asset ID {asset_id} should be in the requested list"
        )
        assert isinstance(df, pd.DataFrame), (
            "Transformed object should be a pandas DataFrame"
        )
        assert not df.empty, f"DataFrame for {asset_id} should not be empty"

        expected_columns = ["open", "high", "low", "close", "volume"]
        assert all(col in df.columns for col in expected_columns), (
            "DataFrame should have the correct columns"
        )
        assert df.index.name == "timestamp", (
            "DataFrame index should be named 'timestamp'"
        )
        assert isinstance(df.index, pd.DatetimeIndex), "Index should be a DatetimeIndex"

        # Check dtypes
        for col in expected_columns:
            assert pd.api.types.is_numeric_dtype(df[col]), (
                f"Column {col} should be numeric"
            )
