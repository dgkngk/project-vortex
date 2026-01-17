from enum import Enum
from typing import Dict, Type

from backend.core.enums.ExchangeEnums import Exchange
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.etl.extractors.BinanceExtractor import BinanceExtractor
from backend.etl.extractors.CoinGeckoExtractor import CoinGeckoExtractor


class ExtractorFactory:
    """
    Factory class to create crypto data extractors.
    """

    _extractors: Dict[Enum, Type[BaseExtractor]] = {
        Exchange.BINANCE: BinanceExtractor,
        Exchange.COINGECKO: CoinGeckoExtractor,
    }

    @staticmethod
    def create_extractor(extractor_type: Enum, **kwargs) -> BaseExtractor:
        """
        Creates an extractor for the given type.
        """
        extractor_class = ExtractorFactory._extractors.get(extractor_type)
        if not extractor_class:
            raise ValueError(f"Unsupported type: {extractor_type}")
        return extractor_class(**kwargs)
