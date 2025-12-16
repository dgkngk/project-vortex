import unittest
from unittest.mock import MagicMock

from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.ExtractionMode import ExtractionMode
from backend.etl.controllers.CryptoController import CryptoController
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.TransformerFactory import TransformerFactory


class TestCryptoController(unittest.TestCase):
    def setUp(self):
        self.mock_extractor_factory = MagicMock(spec=ExtractorFactory)
        self.mock_transformer_factory = MagicMock(spec=TransformerFactory)
        self.mock_loader_factory = MagicMock(spec=LoaderFactory)

        self.mock_extractor = MagicMock()
        self.mock_transformer = MagicMock()
        self.mock_loader = MagicMock()

        self.mock_extractor_factory.create_extractor.return_value = self.mock_extractor
        self.mock_transformer_factory.create_transformer.return_value = (
            self.mock_transformer
        )
        self.mock_loader_factory.create_loader.return_value = self.mock_loader

        self.asset_ids = ["BTC", "ETH"]
        self.extractors_enum = [MagicMock()]
        self.transformers_enum = [MagicMock()]
        self.loaders_enum = [MagicMock()]

    def test_initialization(self):
        controller = CryptoController(
            extractor_factory=self.mock_extractor_factory,
            extractors=self.extractors_enum,
            transformer_factory=self.mock_transformer_factory,
            transformers=self.transformers_enum,
            loader_factory=self.mock_loader_factory,
            loaders=self.loaders_enum,
            extraction_mode=ExtractionMode.DAILY,
            asset_ids=self.asset_ids,
        )

        self.assertEqual(controller.extraction_mode, ExtractionMode.DAILY)
        self.assertEqual(controller.asset_ids, self.asset_ids)
        # Check that transformers are empty in base, but stored in subclass
        self.assertEqual(controller.transformers, [])
        self.assertEqual(controller.transformer_enums, self.transformers_enum)

    def test_run_extractions(self):
        controller = CryptoController(
            extractor_factory=self.mock_extractor_factory,
            extractors=self.extractors_enum,
            transformer_factory=self.mock_transformer_factory,
            transformers=self.transformers_enum,
            loader_factory=self.mock_loader_factory,
            loaders=self.loaders_enum,
            extraction_mode=ExtractionMode.DAILY,
            asset_ids=self.asset_ids,
        )

        self.mock_extractor.get_historical_data_for_assets.return_value = {
            "BTC": "data"
        }

        result = controller.run_extractions()

        self.mock_extractor.get_historical_data_for_assets.assert_called_with(
            asset_ids=self.asset_ids,
            interval=DataIntervals.ONE_DAY,
            limit=100,
            days=1,
        )
        self.assertEqual(result, {"BTC": "data"})

    def test_run_transformations(self):
        controller = CryptoController(
            extractor_factory=self.mock_extractor_factory,
            extractors=self.extractors_enum,
            transformer_factory=self.mock_transformer_factory,
            transformers=self.transformers_enum,
            loader_factory=self.mock_loader_factory,
            loaders=self.loaders_enum,
            extraction_mode=ExtractionMode.DAILY,
            asset_ids=self.asset_ids,
        )

        self.mock_transformer.transform.return_value = "transformed_data"

        raw_data = {"BTC": "raw"}
        result = controller.run_transformations(raw_data)

        # Check if create_transformer was called with raw_data and asset_ids (part of params)
        # Note: we need to check if kwargs contains asset_ids.
        # MagicMock calls arguments are complex to unpack if mixed with kwargs.
        args, kwargs = self.mock_transformer_factory.create_transformer.call_args
        self.assertEqual(args[0], self.transformers_enum[0])
        self.assertEqual(kwargs["raw_data"], raw_data)
        self.assertEqual(kwargs["asset_ids"], self.asset_ids)

        self.assertEqual(result, "transformed_data")

    def test_run_loaders(self):
        controller = CryptoController(
            extractor_factory=self.mock_extractor_factory,
            extractors=self.extractors_enum,
            transformer_factory=self.mock_transformer_factory,
            transformers=self.transformers_enum,
            loader_factory=self.mock_loader_factory,
            loaders=self.loaders_enum,
            extraction_mode=ExtractionMode.DAILY,
            asset_ids=self.asset_ids,
        )

        controller.run_loaders("final_data")
        self.mock_loader.save_to_destinations.assert_called_with("final_data")


if __name__ == "__main__":
    unittest.main()
