from abc import ABC, abstractmethod
from typing import Any, Optional


class DataDestinationClient(ABC):
    """
    Abstract base class for data destination clients.
    """

    def __init__(self):
        self.client: Optional[Any] = None

    @abstractmethod
    def save_data(self, data: Any):
        """
        Save data to the destination.
        Args:
            data: The transformed data to store.
        """
        raise NotImplementedError
