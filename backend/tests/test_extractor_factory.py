import pytest

from backend.core.enums.ExchangeEnums import Exchange
from backend.etl.extractors.BaseExtractor import BaseExtractor
from backend.etl.extractors.BinanceExtractor import BinanceExtractor
from backend.etl.extractors.CoinGeckoExtractor import CoinGeckoExtractor
from backend.etl.extractors.ExtractorFactory import ExtractorFactory


@pytest.mark.unit
def test_create_binance_extractor():
    extractor = ExtractorFactory.create_extractor(Exchange.BINANCE)
    assert isinstance(extractor, BinanceExtractor)
    assert isinstance(extractor, BaseExtractor)


@pytest.mark.unit
def test_create_coingecko_extractor():
    extractor = ExtractorFactory.create_extractor(Exchange.COINGECKO)
    assert isinstance(extractor, CoinGeckoExtractor)
    assert isinstance(extractor, BaseExtractor)


@pytest.mark.unit
def test_create_unsupported_extractor():
    with pytest.raises(ValueError):
        ExtractorFactory.create_extractor(Exchange.NYSE)
