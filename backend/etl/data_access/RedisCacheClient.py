import pickle
from typing import Any, Optional

import redis

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.BaseCacheClient import BaseCacheClient


class RedisCacheClient(BaseCacheClient):
    """
    A cache client that uses a Redis server as the backend.

    This client serializes data using pickle and leverages Redis's built-in
    support for time-to-live (TTL) key expiration.
    """

    def __init__(self, redis_url: str, logger: Optional[VortexLogger] = None):
        """
        Initializes the RedisCacheClient and establishes a connection using a URL.

        Args:
            redis_url: The connection URL for the Redis server (e.g., "redis://localhost:6379/0").
            logger: Optional logger instance.
        """
        super().__init__()
        self.logger = logger or VortexLogger(
            name=self.__class__.__name__, level="DEBUG"
        )
        try:
            # Use from_url to connect, which is more flexible
            self.client = redis.Redis.from_url(redis_url, socket_timeout=5)
            # Check the connection
            self.client.ping()
            self.logger.info("Successfully connected to Redis from URL.")
        except redis.ConnectionError as e:
            self.logger.error(f"Could not connect to Redis: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves and deserializes an item from the Redis cache.

        Args:
            key: The key of the item to retrieve.

        Returns:
            The cached item, or None if not found or if a connection error occurs.
        """
        if not self.client:
            return None

        try:
            cached_value = self.client.get(key)
            if cached_value:
                return pickle.loads(cached_value)
            return None
        except (redis.RedisError, pickle.UnpicklingError) as e:
            self.logger.error(f"Error getting key '{key}' from Redis: {e}")
            return None

    def set(self, key: str, value: Any, time_to_live: Optional[int] = None):
        """
        Serializes and saves an item to the Redis cache.

        Args:
            key: The key under which to store the item.
            value: The item to store.
            time_to_live: Optional time-to-live in seconds.
        """
        if not self.client:
            return

        try:
            serialized_value = pickle.dumps(value)
            self.client.set(key, serialized_value, ex=time_to_live)
        except (redis.RedisError, pickle.PicklingError) as e:
            self.logger.error(f"Error setting key '{key}' in Redis: {e}")

    def delete(self, key: str):
        """
        Deletes an item from the Redis cache.

        Args:
            key: The key of the item to delete.
        """
        if not self.client:
            return

        try:
            self.client.delete(key)
        except redis.RedisError as e:
            self.logger.error(f"Error deleting key '{key}' from Redis: {e}")

    def exists(self, key: str) -> bool:
        """
        Checks if an item exists in the Redis cache.

        Args:
            key: The key to check.

        Returns:
            True if the item exists, False otherwise.
        """
        if not self.client:
            return False

        try:
            return self.client.exists(key) > 0
        except redis.RedisError as e:
            self.logger.error(f"Error checking existence of key '{key}' in Redis: {e}")
            return False
