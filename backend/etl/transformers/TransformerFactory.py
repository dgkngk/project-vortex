from enum import Enum
from typing import Dict, Type

from backend.core.enums.TransformTypes import TransformTypes
from backend.etl.transformers.BaseTransformer import BaseTransformer
from backend.etl.transformers.BinanceHDTransformer import BinanceHDTransformer
from backend.etl.transformers.StrategyTransformer import StrategyTransformer
from backend.etl.transformers.TATransformer import TATransformer


class TransformerFactory:
    """
    Factory class to create crypto data transformers.
    """

    _transformers: Dict[Enum, Type[BaseTransformer]] = {
        TransformTypes.BINANCEHD_TO_OHLCV: BinanceHDTransformer,
        TransformTypes.OHLCV_TO_TA: TATransformer,
        TransformTypes.TA_TO_SIGNAL: StrategyTransformer,
    }

    @staticmethod
    def create_transformer(transformer_type: Enum, **kwargs) -> BaseTransformer:
        """
        Creates a transformer for the given type.
        """
        transformer_class = TransformerFactory._transformers.get(transformer_type)
        if not transformer_class:
            raise ValueError(f"Unsupported type: {transformer_type}")
        return transformer_class(**kwargs)
