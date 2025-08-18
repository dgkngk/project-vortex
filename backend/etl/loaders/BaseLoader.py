from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseLoader(ABC):
    """
    Abstract base class for data loaders.
    Defines the interface for saving transformed data into various storages.
    """

    def __init__(self):
        # Placeholders for DB clients
        self.redis_client: Optional[Any] = None
        self.influx_client: Optional[Any] = None
        self.pg_conn: Optional[Any] = None

    @abstractmethod
    def save_to_influx(self, data: Any):
        """
        Save data into InfluxDB.
        Args:
            data: The transformed data to store.
        """
        pass

    @abstractmethod
    def save_to_redis(self, data: Any):
        """
        Save data into Redis.
        Args:
            data: The transformed data to store.
        """
        pass

    @abstractmethod
    def save_to_pg(self, data: Any):
        """
        Save data into PostgreSQL.
        Args:
            data: The transformed data to store.
        """
        pass

    @abstractmethod
    def run_save(self, data: Any, destinations: list[str]):
        """
        Main method to orchestrate saving to one or more destinations.
        Args:
            data: The transformed data.
            destinations: List of destination identifiers ["redis", "influx", "pg"]
        """
        pass
