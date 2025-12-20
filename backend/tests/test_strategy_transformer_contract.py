import os

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from backend.core.enums.StrategyConfigs import StrategyConfigs
from backend.core.enums.TAStudies import TAStudies
from backend.etl.extractors.BinanceExtractor import BinanceExtractor
from backend.etl.transformers.BinanceHDTransformer import BinanceHDTransformer
from backend.etl.transformers.StrategyTransformer import StrategyTransformer
from backend.etl.transformers.TATransformer import TATransformer


@pytest.fixture(scope="module")
def ta_data() -> dict:
    """
    Provides TA data for a sample of assets.
    This fixture runs a full extraction and transformation pipeline to generate
    the necessary TA indicators for strategy testing.
    """
    # 1. Extract data from Binance
    extractor = BinanceExtractor()
    listed_assets = extractor.get_listed_assets()
    asset_ids = [
        asset["id"] for asset in listed_assets if asset["id"].endswith("USDT")
    ][:5]
    historical_data = extractor.get_historical_data_for_assets(asset_ids, limit=200)

    # 2. Transform raw data to OHLCV DataFrames
    hd_transformer = BinanceHDTransformer(raw_data=historical_data)
    ohlcv_dataframes = hd_transformer.transform()

    # 3. Calculate TA indicators using TAStudies
    studies = [
        TAStudies.RSI,
        TAStudies.MACD,
        TAStudies.BBANDS,
        TAStudies.STOCHRSI,
        TAStudies.VWAP,
        TAStudies.HMA,
    ]
    ta_transformer = TATransformer(raw_data=ohlcv_dataframes, studies=studies)
    indicator_data = ta_transformer.transform()

    return indicator_data


@pytest.mark.contract
def test_strategy_transformer_contract(ta_data):
    """
    Contract test for StrategyTransformer.
    It uses pre-calculated TA data and verifies that trading signals are generated correctly.
    """
    assert ta_data, "Fixture should provide TA data"
    assert isinstance(ta_data, dict), "Fixture data should be a dictionary"

    # 1. Define strategies to test
    strategies_config = {
        StrategyConfigs.BOLLINGER_BANDS: StrategyConfigs.BOLLINGER_BANDS.value,
        StrategyConfigs.STOCHRSI: StrategyConfigs.STOCHRSI.value,
        StrategyConfigs.MACD: StrategyConfigs.MACD.value,
        StrategyConfigs.VWAP: StrategyConfigs.VWAP.value,
        StrategyConfigs.HMA_RSI: StrategyConfigs.HMA_RSI.value,
    }

    # 2. Apply StrategyTransformer to each asset's data
    signal_data = {}
    for asset_id, df in ta_data.items():
        if df.empty:
            print(f"Skipping {asset_id} due to empty data from TATransformer.")
            continue
        strategy_transformer = StrategyTransformer(
            raw_data={asset_id: df}, strategies_config=strategies_config
        )
        signal_data[asset_id] = strategy_transformer.transform()[asset_id]

    # 3. Assert the results
    assert signal_data, "Signal generation should return data"

    for asset_id, df in signal_data.items():
        assert isinstance(df, pd.DataFrame), "Result value should be a DataFrame"
        assert not df.empty, f"Signal DataFrame for {asset_id} should not be empty"

        # Check for signal columns
        for strategy_name in strategies_config:
            signal_col = f"{strategy_name.name}_signal"
            assert signal_col in df.columns, f"{signal_col} should be in DataFrame"
            assert pd.api.types.is_integer_dtype(df[signal_col]), (
                f"{signal_col} should be of integer type"
            )
            # Assert that signal values are within the range of SignalTypes enum
            assert df[signal_col].between(-3, 3).all(), (
                f"{signal_col} values should be between -3 and 3"
            )

    # 4. --- Plotting Results ---
    plot_dir = os.path.join("backend", "tests", "test_plots")
    os.makedirs(plot_dir, exist_ok=True)
    print(f"\nSaving strategy signal plots to: {os.path.abspath(plot_dir)}")

    for asset_id, df in signal_data.items():
        if df.empty:
            continue

        fig, ax = plt.subplots(figsize=(15, 8))
        ax.plot(df.index, df["close"], label="Close Price", color="blue", alpha=0.5)

        signal_legend_elements = []
        for strategy_name in strategies_config:
            signal_col = f"{strategy_name.name}_signal"

            # Using a consistent color/marker for each strategy's signals
            strategy_markers = {"BUY": ("^", "green"), "SELL": ("v", "red")}

            for signal_type, (marker, color) in strategy_markers.items():
                signal_value = 1 if signal_type == "BUY" else -1
                signals = df[df[signal_col] == signal_value]
                if not signals.empty:
                    ax.scatter(
                        signals.index,
                        signals["close"],
                        label=f"{strategy_name.name} {signal_type}",
                        marker=marker,
                        color=color,
                        s=100,
                        alpha=0.8,
                    )

        ax.set_title(f"Trading Signals for {asset_id}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()
        ax.grid(True)
        plt.tight_layout()

        plot_path = os.path.join(plot_dir, f"{asset_id}_strategy_signals.png")
        plt.savefig(plot_path)
        plt.close(fig)
