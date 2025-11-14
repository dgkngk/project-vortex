from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.etl.extractors.ExtractorFactory import ExtractorFactory


class BaseController(ABC):
    """
    Base class for ETL controllers.
    """

    def __init__(
        self, extractor_factory: ExtractorFactory, extractors: List[Enum], **kwargs
    ):
        self.extractor_factory = extractor_factory
        self.extractors: List[BaseExtractor] = [
            self.extractor_factory.create_extractor(extractor, **kwargs)
            for extractor in extractors
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
