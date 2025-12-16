from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List

from backend.core.Config import AppConfig
from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.BaseCacheClient import BaseCacheClient
from backend.etl.data_access.LocalCacheClient import LocalCacheClient
from backend.etl.data_access.RedisCacheClient import RedisCacheClient
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.BaseLoader import BaseLoader
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.BaseTransformer import BaseTransformer
from backend.etl.transformers.TransformerFactory import TransformerFactory


class BaseController(ABC):
    """
    Base class for ETL controllers.
    Orchestrates the extraction, transformation, and loading of data,
    with a built-in caching layer to avoid redundant processing.
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
        self.params = kwargs
        self.logger = VortexLogger(name=self.__class__.__name__, level="DEBUG")
        settings = AppConfig()

        if settings.cache_type.lower() == "redis":
            self.logger.info("Using Redis cache client.")
            self.cache_client: BaseCacheClient = RedisCacheClient(
                redis_url=settings.redis_url, logger=self.logger
            )
        else:
            self.logger.info("Using local file cache client.")
            self.cache_client: BaseCacheClient = LocalCacheClient(logger=self.logger)

        self.extractor_factory = extractor_factory
        self.extractors: List[BaseExtractor] = [
            self.extractor_factory.create_extractor(e, **self.params)
            for e in extractors
        ]

        self.transformer_factory = transformer_factory
        self.transformers: List[BaseTransformer] = [
            self.transformer_factory.create_transformer(t, **self.params)
            for t in transformers
        ]

        self.loader_factory = loader_factory
        self.loaders: List[BaseLoader] = [
            self.loader_factory.create_loader(l, **self.params) for l in loaders
        ]

    def get_data(self) -> Any:
        """
        Main orchestration method.
        Handles caching, and if no valid cache is found, runs the full
        ETL pipeline.
        """
        cache_key = self.cache_client.generate_cache_key(self.params)
        cached_data = self.cache_client.get(cache_key)

        if cached_data is not None:
            self.logger.info(f"Cache hit for key {cache_key[:10]}...")
            return cached_data

        self.logger.info(f"Cache miss for key {cache_key[:10]}...")
        extracted_data = self.run_extractions()
        transformed_data = self.run_transformations(extracted_data)
        self.run_loaders(transformed_data)

        # Time to live in seconds (e.g., 1 day)
        # TODO: Make TTL configurable and relative to the request interval
        time_to_live = self.params.get("time_to_live_seconds", 86400)
        self.cache_client.set(cache_key, transformed_data, time_to_live=time_to_live)
        self.logger.info(f"Saved to cache with key {cache_key[:10]}...")

        return transformed_data

    @abstractmethod
    def run_extractions(self) -> Any:
        """
        Runs the extraction process.
        Should return the raw, extracted data.
        """
        raise NotImplementedError

    @abstractmethod
    def run_transformations(self, extracted_data: Any) -> Any:
        """
        Runs the transformation process.
        Should accept raw data and return the final, transformed data.
        """
        raise NotImplementedError

    @abstractmethod
    def run_loaders(self, transformed_data: Any):
        """
        Runs the loading process.
        Accepts the final data to be loaded into destinations.
        """
        raise NotImplementedError
