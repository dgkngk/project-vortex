from enum import Enum
from typing import List

from backend.core.enums.ExtractionMode import ExtractionMode
from backend.etl.controllers.BaseController import BaseController
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.TransformerFactory import TransformerFactory


class CronableController(BaseController):
    """
    A controller that is configurable by passing the extraction mode.
    Suitable for running in cron jobs.
    """

    def __init__(
        self,
        extractor_factory: ExtractorFactory,
        extractors: List[Enum],
        transformer_factory: TransformerFactory,
        transformers: List[Enum],
        loader_factory: LoaderFactory,
        loaders: List[Enum],
        extraction_mode: ExtractionMode,
        **kwargs,
    ):
        super().__init__(
            extractor_factory=extractor_factory,
            extractors=extractors,
            transformer_factory=transformer_factory,
            transformers=transformers,
            loader_factory=loader_factory,
            loaders=loaders,
            **kwargs,
        )
        self.extraction_mode = extraction_mode
