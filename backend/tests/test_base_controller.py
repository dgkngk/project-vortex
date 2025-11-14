import unittest
from unittest.mock import MagicMock

from backend.etl.controllers.BaseController import BaseController
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.TransformerFactory import TransformerFactory


class TestBaseController(unittest.TestCase):
    def test_base_controller_initialization(self):
        # Arrange
        mock_extractor_factory = MagicMock(spec=ExtractorFactory)
        mock_transformer_factory = MagicMock(spec=TransformerFactory)
        mock_loader_factory = MagicMock(spec=LoaderFactory)

        mock_extractor_factory.create_extractor.return_value = MagicMock()
        mock_transformer_factory.create_transformer.return_value = MagicMock()
        mock_loader_factory.create_loader.return_value = MagicMock()

        extractors_enum = [MagicMock(), MagicMock()]
        transformers_enum = [MagicMock()]
        loaders_enum = [MagicMock(), MagicMock(), MagicMock()]

        # Act
        class ConcreteController(BaseController):
            def run_extractions(self):
                pass

            def run_transformations(self):
                pass

            def run_loaders(self):
                pass

        controller = ConcreteController(
            extractor_factory=mock_extractor_factory,
            extractors=extractors_enum,
            transformer_factory=mock_transformer_factory,
            transformers=transformers_enum,
            loader_factory=mock_loader_factory,
            loaders=loaders_enum,
        )

        # Assert
        self.assertEqual(len(controller.extractors), len(extractors_enum))
        self.assertEqual(len(controller.transformers), len(transformers_enum))
        self.assertEqual(len(controller.loaders), len(loaders_enum))

        mock_extractor_factory.create_extractor.assert_called()
        mock_transformer_factory.create_transformer.assert_called()
        mock_loader_factory.create_loader.assert_called()


if __name__ == "__main__":
    unittest.main()
