from enum import Enum
from typing import Dict, Type

from backend.etl.loaders.BaseLoader import BaseLoader


class LoaderFactory:
    """
    Factory class to create crypto data loaders.
    """

    _loaders: Dict[Enum, Type[BaseLoader]] = {}

    @staticmethod
    def create_loader(loader_type: Enum, **kwargs) -> BaseLoader:
        """
        Creates a loader for the given type.
        """
        loader_class = LoaderFactory._loaders.get(loader_type)
        if not loader_class:
            raise ValueError(f"Unsupported type: {loader_type}")
        return loader_class(**kwargs)
