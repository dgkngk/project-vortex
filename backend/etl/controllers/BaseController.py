from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.BaseLoader import BaseLoader
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.BaseTransformer import BaseTransformer
from backend.etl.transformers.TransformerFactory import TransformerFactory


class BaseController(ABC):
    """
    Base class for ETL controllers.
    """

    def __init__(
        self,
        extractor_factory: ExtractorFactory,
        extractors: List[Enum],
        transformer_factory: TransformerFactory,
        transformers: List[Enum],
        loader_factory: LoaderFactory,
        loaders: List[Enum],
        **kwargs,
    ):
        self.extractor_factory = extractor_factory
        self.extractors: List[BaseExtractor] = [
            self.extractor_factory.create_extractor(extractor, **kwargs)
            for extractor in extractors
        ]

        self.transformer_factory = transformer_factory
        self.transformers: List[BaseTransformer] = [
            self.transformer_factory.create_transformer(transformer, **kwargs)
            for transformer in transformers
        ]

        self.loader_factory = loader_factory
        self.loaders: List[BaseLoader] = [
            self.loader_factory.create_loader(loader, **kwargs) for loader in loaders
        ]

    @abstractmethod
    def run_extractions(self):
        """
        Runs the extraction process.
        """
        raise NotImplementedError

    @abstractmethod
    def run_transformations(self):
        """
        Runs the transformation process.
        """
        raise NotImplementedError

    @abstractmethod
    def run_loaders(self):
        """
        Runs the loading process.
        """
        raise NotImplementedError
