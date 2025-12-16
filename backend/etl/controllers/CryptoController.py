from enum import Enum
from typing import Any, List

from backend.core.enums.AssetEnums import DataIntervals
from backend.core.enums.ExtractionMode import ExtractionMode
from backend.etl.controllers.CronableController import CronableController
from backend.etl.extractors.ExtractorFactory import ExtractorFactory
from backend.etl.loaders.LoaderFactory import LoaderFactory
from backend.etl.transformers.TransformerFactory import TransformerFactory


class CryptoController(CronableController):
    """
    Controller specifically for Crypto data ETL.
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
        asset_ids: List[str],
        **kwargs,
    ):
        # We pass empty list for transformers to BaseController because
        # BaseTransformer requires raw_data which is not available yet.
        # We will instantiate transformers in run_transformations.
        super().__init__(
            extractor_factory=extractor_factory,
            extractors=extractors,
            transformer_factory=transformer_factory,
            transformers=[],  # Pass empty list here
            loader_factory=loader_factory,
            loaders=loaders,
            extraction_mode=extraction_mode,
            asset_ids=asset_ids,  # Store asset_ids in params
            **kwargs,
        )
        self.transformer_enums = transformers
        self.asset_ids = asset_ids

    def _get_interval_from_mode(self) -> DataIntervals:
        if self.extraction_mode == ExtractionMode.DAILY:
            return DataIntervals.ONE_DAY
        elif self.extraction_mode == ExtractionMode.HOURLY:
            return DataIntervals.ONE_HOUR
        elif self.extraction_mode == ExtractionMode.MINUTELY:
            return DataIntervals.ONE_MINUTE
        # Default or fallback
        return DataIntervals.ONE_DAY

    def run_extractions(self) -> Any:
        self.logger.info(
            f"Running extractions for {len(self.asset_ids)} assets in {self.extraction_mode.value} mode."
        )
        interval = self._get_interval_from_mode()

        extracted_data = {}
        for extractor in self.extractors:
            try:
                # Attempt to extract historical data with the interval
                data = extractor.get_historical_data_for_assets(
                    asset_ids=self.asset_ids,
                    interval=interval,
                    limit=100,  # Reasonable default
                    days=1,  # Reasonable default for CoinGecko
                )
                if data:
                    extracted_data.update(data)
            except Exception as e:
                self.logger.error(
                    f"Error in extraction with {extractor.__class__.__name__}: {e}"
                )

        return extracted_data

    def run_transformations(self, extracted_data: Any) -> Any:
        self.logger.info("Running transformations...")
        transformed_data = extracted_data

        # Instantiate and run transformers sequentially
        for transformer_enum in self.transformer_enums:
            transformer = self.transformer_factory.create_transformer(
                transformer_enum, raw_data=transformed_data, **self.params
            )
            transformed_data = transformer.transform()

        return transformed_data

    def run_loaders(self, transformed_data: Any):
        self.logger.info("Running loaders...")
        for loader in self.loaders:
            loader.save_to_destinations(transformed_data)
