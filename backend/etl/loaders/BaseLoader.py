from abc import ABC
from typing import Any, List

from backend.etl.data_access.DataDestinationClient import DataDestinationClient


class BaseLoader(ABC):
    """
    Abstract base class for data loaders.
    Defines the interface for saving transformed data into various storages.
    """

    def __init__(self, destinations: List[DataDestinationClient]):
        self.destinations = destinations

    def save_to_destinations(self, data: Any):
        """
        Main method to orchestrate saving to one or more destinations.
        Args:
            data: The transformed data.
        """
        for destination in self.destinations:
            destination.save_data(data)
