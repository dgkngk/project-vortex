from abc import ABC, abstractmethod
from typing import Any

class BaseTransformer(ABC):
    """
    Abstract base class for data transformers.
    Handles conversion of raw extractor output into normalized data structures.
    """

    def __init__(self, raw_data: Any):
        self.raw_data = raw_data

    @abstractmethod
    def transform(self) -> Any:
        """
        Transform raw_data into a cleaned, structured format.
        Returns:
            Transformed data (e.g., DataFrame, list of dicts, etc.)
        """
        pass
