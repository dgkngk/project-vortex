import json
import time
from typing import Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from backend.etl.data_access.RedisCacheClient import RedisCacheClient


class MockRedis:
    """
    A simple in-memory mock of the Redis client to support contract tests
    without requiring a running Redis instance or `fakeredis` dependency.
    """

    def __init__(self):
        self._store = {}

    def set(self, key: str, value: Union[str, bytes], ex: Optional[int] = None):
        expiry = time.time() + ex if ex is not None else None
        # Redis stores data as bytes usually, but strict=False allows strings.
        # RedisCacheClient sends JSON strings.
        self._store[key] = (value, expiry)
        return True

    def get(self, key: str) -> Optional[Union[str, bytes]]:
        if key not in self._store:
            return None
        
        value, expiry = self._store[key]
        if expiry and time.time() > expiry:
            del self._store[key]
            return None
        
        return value

    def exists(self, key: str) -> int:
        # Trigger cleanup if expired
        if self.get(key) is None:
            return 0
        return 1

    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    def ping(self):
        return True


@pytest.fixture
def mock_redis_client():
    return MockRedis()


@pytest.fixture
def cache_client(mock_redis_client):
    """
    Pytest fixture to create a RedisCacheClient instance with a mocked Redis backend.
    """
    with patch("redis.Redis.from_url", return_value=mock_redis_client):
        # The URL doesn't matter since we are mocking the connection
        client = RedisCacheClient(redis_url="redis://mock:6379/0")
        return client


class TestRedisCacheClientContract:
    """
    Contract tests for RedisCacheClient using a MockRedis implementation.
    Mirrors TestLocalCacheClientContract.
    """

    def test_set_and_get_simple_value(self, cache_client: RedisCacheClient):
        """Verify that a simple value can be set and retrieved correctly."""
        key = "test_key_1"
        value = {"data": "my-test-value", "number": 123}

        cache_client.set(key, value)
        retrieved_value = cache_client.get(key)

        assert retrieved_value is not None
        assert retrieved_value == value

    def test_get_nonexistent_key_returns_none(self, cache_client: RedisCacheClient):
        """Verify that getting a key that does not exist returns None."""
        retrieved_value = cache_client.get("nonexistent-key")
        assert retrieved_value is None

    def test_exists_method(self, cache_client: RedisCacheClient):
        """Verify that exists() returns True for an existing key and False otherwise."""
        key = "test_key_2"
        value = "i exist"

        # Check that it doesn't exist initially
        assert not cache_client.exists(key)

        # Set the key and check that it exists
        cache_client.set(key, value)
        assert cache_client.exists(key)

    def test_delete_method(self, cache_client: RedisCacheClient):
        """Verify that a key is removed from the cache after being deleted."""
        key = "test_key_3"
        value = "to-be-deleted"

        cache_client.set(key, value)
        assert cache_client.exists(key)

        cache_client.delete(key)
        assert not cache_client.exists(key)
        assert cache_client.get(key) is None

    def test_overwrite_existing_key(self, cache_client: RedisCacheClient):
        """Verify that setting an existing key overwrites its value."""
        key = "test_key_4"
        initial_value = "initial"
        new_value = "overwritten"

        cache_client.set(key, initial_value)
        assert cache_client.get(key) == initial_value

        cache_client.set(key, new_value)
        assert cache_client.get(key) == new_value

    def test_ttl_expiration(self, cache_client: RedisCacheClient):
        """Verify that a cached item expires and is removed after its TTL."""
        key = "test_key_ttl"
        value = "i will expire"
        ttl_seconds = 1

        cache_client.set(key, value, time_to_live=ttl_seconds)

        # Should exist immediately after setting
        assert cache_client.exists(key)

        # Wait for the TTL to expire
        time.sleep(ttl_seconds + 0.1)

        # Should not exist anymore (get should return None and trigger deletion)
        assert not cache_client.exists(key)
        assert cache_client.get(key) is None

    def test_value_with_no_ttl_persists(self, cache_client: RedisCacheClient):
        """Verify that an item with no TTL does not expire."""
        key = "test_key_no_ttl"
        value = "i will not expire"
        ttl_seconds = 1

        cache_client.set(key, value, time_to_live=None)
        time.sleep(ttl_seconds + 0.1)

        assert cache_client.exists(key)
        assert cache_client.get(key) == value

    def test_dataframe_serialization(self, cache_client: RedisCacheClient):
        """
        Specific test for RedisCacheClient to verify DataFrame serialization/deserialization.
        This confirms the JSON logic handles pandas objects correctly.
        """
        import pandas as pd
        
        key = "test_dataframe"
        df = pd.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
        
        cache_client.set(key, df)
        retrieved_df = cache_client.get(key)
        
        assert retrieved_df is not None
        assert isinstance(retrieved_df, pd.DataFrame)
        pd.testing.assert_frame_equal(df, retrieved_df)
