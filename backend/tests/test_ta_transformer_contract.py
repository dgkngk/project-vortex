import os

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from backend.etl.extractors.BinanceExtractor import BinanceExtractor
from backend.etl.transformers.BinanceHDTransformer import BinanceHDTransformer
from backend.etl.transformers.TATransformer import TATransformer


@pytest.fixture(scope="module")
def ohlcv_data() -> dict:
    """
    Provides transformed OHLCV data for a sample of assets.
    This fixture simulates the output of BinanceHDTransformer by running the
    full extraction and transformation pipeline. The data is scoped to the
    module to avoid expensive API calls for each test.
    """
    # 1. Extract data from Binance
    extractor = BinanceExtractor()
    listed_assets = extractor.get_listed_assets()
    # Take a small sample of assets for the test
    asset_ids = [
        asset["id"] for asset in listed_assets if asset["id"].endswith("USDT")
    ][:5]

    # Fetch enough data points for TA indicators to be meaningful
    historical_data = extractor.get_historical_data_for_assets(asset_ids, limit=100)

    # 2. Transform raw data to OHLCV DataFrames
    hd_transformer = BinanceHDTransformer(raw_data=historical_data)
    ohlcv_dataframes = hd_transformer.transform()

    return ohlcv_dataframes


@pytest.mark.contract
def test_ta_transformer_contract(ohlcv_data):
    """
    Contract test for TATransformer.
    It uses pre-transformed OHLCV data from a fixture and verifies that
    technical indicators are calculated correctly.
    """
    # Ensure the fixture provided valid data to test with
    assert ohlcv_data, "Fixture should provide OHLCV data"
    assert isinstance(ohlcv_data, dict), "Fixture data should be a dictionary"

    # 1. Define indicators and initialize the TATransformer
    indicators_to_test = ["rsi", "macd", "bbands"]
    ta_transformer = TATransformer(raw_data=ohlcv_data, indicators=indicators_to_test)

    # 2. Transform the data (calculate indicators)
    indicator_data = ta_transformer.transform()

    # 3. Assert the results
    assert indicator_data, "Indicator calculation should return data"
    assert isinstance(indicator_data, dict), "Result should be a dictionary"
    assert len(indicator_data) == len(ohlcv_data), "Should have results for each asset"

    for asset_id, df in indicator_data.items():
        assert asset_id in ohlcv_data, "Result key should be a valid asset ID"
        assert isinstance(df, pd.DataFrame), "Result value should be a DataFrame"
        assert not df.empty, f"Indicator DataFrame for {asset_id} should not be empty"
        assert isinstance(df.index, pd.DatetimeIndex), "Index should be a DatetimeIndex"

        # Check that indicator columns were created.
        # We check for substrings because pandas-ta generates full names (e.g., 'RSI_14').
        column_names_str = "".join(df.columns)
        assert "RSI" in column_names_str, "RSI indicator should be present"
        assert "MACD" in column_names_str, "MACD indicator should be present"
        assert "BBL" in column_names_str, "Bollinger Bands (lower) should be present"
        assert "BBU" in column_names_str, "Bollinger Bands (upper) should be present"

        # Check that all calculated values are numeric
        for col in df.columns:
            assert pd.api.types.is_numeric_dtype(df[col]), (
                f"Column {col} should be numeric"
            )
    # 4. --- Plotting Results ---
    plot_dir = os.path.join("backend", "tests", "test_plots")
    os.makedirs(plot_dir, exist_ok=True)
    print(f"\nSaving grouped indicator plots to: {os.path.abspath(plot_dir)}")

    for asset_id, df in indicator_data.items():
        if df.empty:
            continue

        # Group indicators by common prefixes for better visualization
        indicator_groups = {
            "RSI": [c for c in df.columns if "RSI" in c],
            "MACD": [c for c in df.columns if "MACD" in c],
            "Bollinger Bands": [c for c in df.columns if c.startswith("BB")],
        }
        # Filter out any groups that didn't produce columns
        indicator_groups = {
            name: cols for name, cols in indicator_groups.items() if cols
        }

        if not indicator_groups:
            continue

        num_groups = len(indicator_groups)
        fig, axes = plt.subplots(
            nrows=num_groups, ncols=1, figsize=(12, 4 * num_groups), sharex=True
        )
        if num_groups == 1:
            axes = [axes]

        fig.suptitle(f"Technical Indicators for {asset_id}", fontsize=16)

        for i, (group_name, cols) in enumerate(indicator_groups.items()):
            # Plot all columns of the group on the same subplot
            df[cols].plot(ax=axes[i], title=group_name, grid=True, legend=True)
            axes[i].set_ylabel(group_name)

        plt.xlabel("Date")
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])

        # Save the plot with a more descriptive name
        plot_path = os.path.join(plot_dir, f"{asset_id}_grouped_indicators.png")
        plt.savefig(plot_path)
        plt.close(fig)  # Close the figure to free up memory
