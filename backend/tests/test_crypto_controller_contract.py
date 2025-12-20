import shutil
import unittest
from pathlib import Path

import pandas as pd

from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.ExchangeEnums import Exchange
from backend.core.enums.ExtractionMode import ExtractionMode
from backend.core.enums.StrategyConfigs import StrategyConfigs
from backend.core.enums.TAStudies import TAStudies
from backend.core.enums.TransformTypes import TransformTypes
from backend.etl.controllers.CryptoController import CryptoController
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.TransformerFactory import TransformerFactory


class TestCryptoControllerContract(unittest.TestCase):
    def setUp(self):
        # Ensure we are using a clean cache directory if possible,
        # but BaseController hardcodes LocalCacheClient init.
        # We can clean up .cache/data before/after test.
        self.cache_dir = Path(".cache/data")
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

        self.asset_ids = ["BTCUSDT"]
        self.extraction_mode = ExtractionMode.DAILY
        self.extractors = [Exchange.BINANCE]
        self.transformers = [
            TransformTypes.BINANCEHD_TO_OHLCV,
            TransformTypes.OHLCV_TO_TA,
            TransformTypes.TA_TO_SIGNAL,
        ]
        # We pass an empty list of loaders for this test as we only want to test extraction -> cache
        self.loaders = []

        # Configuration for Transformers
        self.studies = [TAStudies.STOCHRSI, TAStudies.HMA, TAStudies.RSI]
        self.strategies_config = {
            StrategyConfigs.STOCHRSI: StrategyConfigs.STOCHRSI.value,
            StrategyConfigs.HMA_RSI: StrategyConfigs.HMA_RSI.value,
        }

    def tearDown(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)

    def test_run_full_pipeline_contract(self):
        """
        Contract test:
        1. Fetches DAILY data for BTCUSDT from Binance.
        2. Transforms: BinanceHD -> OHLCV -> TA (StochRSI, HMA, RSI) -> Signal (StochRSI, HMA_RSI).
        3. Saves to Local Cache.
        """
        controller = CryptoController(
            extractor_factory=ExtractorFactory(),
            extractors=self.extractors,
            transformer_factory=TransformerFactory(),
            transformers=self.transformers,
            loader_factory=LoaderFactory(),
            loaders=self.loaders,
            extraction_mode=self.extraction_mode,
            asset_ids=self.asset_ids,
            # Extra params for transformers
            studies=self.studies,
            strategies_config=self.strategies_config,
            # Force cache type to local (though Config defaults to local, being explicit helps)
            cache_type="local",
        )

        # Run the pipeline
        final_data = controller.get_data()

        # Assertions
        self.assertIsInstance(final_data, dict)
        self.assertIn("BTCUSDT", final_data)
        self.assertIsInstance(final_data["BTCUSDT"], pd.DataFrame)
        
        df = final_data["BTCUSDT"]
        self.assertFalse(df.empty)

        # Check for close column (TATransformer ensures close is kept)
        self.assertIn("close", df.columns)

        # Check for TA columns (names depend on pandas_ta defaults)
        # StochRSI usually adds STOCHRSIk_..., STOCHRSId_...
        # HMA adds HMA_...
        # RSI adds RSI_...
        # We can check loosely or strictly if we know exact names.
        # StrategyConfigs tells us expected names:
        # STOCHRSI: "STOCHRSIk_14_14_3_3", "STOCHRSId_14_14_3_3"
        # HMA_RSI: "HMA_10", "RSI_14"

        self.assertTrue(any("STOCHRSIk" in col for col in df.columns), "Missing StochRSI K column")
        self.assertTrue(any("STOCHRSId" in col for col in df.columns), "Missing StochRSI D column")
        self.assertTrue(any("HMA" in col for col in df.columns), "Missing HMA column")
        self.assertTrue(any("RSI" in col for col in df.columns), "Missing RSI column")

        # Check for Strategy Signal columns
        self.assertIn("STOCHRSI_signal", df.columns)
        self.assertIn("HMA_RSI_signal", df.columns)

        # Verify Caching
        # The controller should have generated a cache key and saved the data.
        # Since we don't have easy access to the exact key generated inside get_data without
        # mocking, we can check if the cache directory is not empty.
        self.assertTrue(any(self.cache_dir.iterdir()), "Cache directory should not be empty")

        # Run again to test cache hit (optional, but good for verification)
        # We can mock the extractor or check logs, but here we just ensure it doesn't crash
        # and returns same data.
        cached_data = controller.get_data()
        self.assertIsInstance(cached_data, dict)
        self.assertIn("BTCUSDT", cached_data)
        pd.testing.assert_frame_equal(df, cached_data["BTCUSDT"])

if __name__ == "__main__":
    unittest.main()
