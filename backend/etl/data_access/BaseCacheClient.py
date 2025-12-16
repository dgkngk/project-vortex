import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.etl.data_access.DataDestinationClient import DataDestinationClient


class BaseCacheClient(DataDestinationClient, ABC):
    """
    Abstract base class for cache clients.
    Provides shared logic for cache key generation and a common interface.
    """
    DEFAULT_CACHE_TTL_SECONDS = 86400

    def save_data(self, data: Dict[str, Any]):
        """
        Saves data to the cache. This method adapts the DataDestinationClient
        interface for caching. The 'data' dictionary must contain a 'key'
        and a 'value'. An optional 'time_to_live' can also be provided.

        Args:
            data: A dictionary with 'key', 'value', and optional 'time_to_live' (in seconds).
        """
        if "key" not in data or "value" not in data:
            raise ValueError("Data for caching must include a 'key' and a 'value'.")

        # Default TTL of 1 day (in seconds)
        time_to_live = data.get("time_to_live", self.DEFAULT_CACHE_TTL_SECONDS)
        self.set(data["key"], data["value"], time_to_live=time_to_live)

    @staticmethod
    def generate_cache_key(params: Dict[str, Any]) -> str:
        """
        Generates a consistent SHA-256 hash for a given dictionary of parameters.

        Args:
            params: A dictionary of parameters that define the request.

        Returns:
            A string representing the SHA-256 hash of the parameters.
        """

        def convert_keys(obj):
            if isinstance(obj, dict):
                new_dict = {}
                for k, v in obj.items():
                    key_str = (
                        k.name
                        if hasattr(k, "name")
                        else str(k)
                    )
                    new_dict[key_str] = convert_keys(v)
                return new_dict
            elif isinstance(obj, list):
                return [convert_keys(i) for i in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_keys(i) for i in obj)
            return obj

        def default_converter(o):
            if hasattr(o, "value"):  # Handle Enums
                return o.value
            if hasattr(o, "name"):
                return o.name
            return str(o)

        # Pre-process params to ensure keys are strings (for sorting)
        clean_params = convert_keys(params)

        # Create a canonical string representation by sorting the keys
        canonical_string = json.dumps(
            clean_params, sort_keys=True, default=default_converter
        )

        # Encode the string to bytes, as hash functions operate on bytes
        encoded_string = canonical_string.encode("utf-8")

        # Create the hash object and get the hexadecimal digest
        sha256_hash = hashlib.sha256(encoded_string)
        return sha256_hash.hexdigest()

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Retrieve an item from the cache by key.

        Args:
            key: The key of the item to retrieve.

        Returns:
            The cached item, or None if the item is not found.
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, time_to_live: int = None):
        """
        Add an item to the cache with an optional time-to-live.

        Args:
            key: The key under which to store the item.
            value: The item to store.
            time_to_live: Optional time-to-live in seconds.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str):
        """
        Delete an item from the cache by key.

        Args:
            key: The key of the item to delete.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if an item exists in the cache.

        Args:
            key: The key to check.

        Returns:
            True if the item exists, False otherwise.
        """
        raise NotImplementedError
