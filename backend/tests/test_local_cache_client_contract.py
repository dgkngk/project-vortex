import time
from pathlib import Path

import pytest

from backend.etl.data_access.LocalCacheClient import LocalCacheClient


@pytest.fixture
def cache_client(tmp_path: Path) -> LocalCacheClient:
    """
    Pytest fixture to create a LocalCacheClient instance in a temporary
    directory for test isolation.
    """
    cache_dir = tmp_path / "test_cache"
    client = LocalCacheClient(cache_dir=str(cache_dir))
    return client


class TestLocalCacheClientContract:
    """
    Contract tests for any client implementing BaseCacheClient,
    using LocalCacheClient as the concrete implementation.
    """

    def test_set_and_get_simple_value(self, cache_client: LocalCacheClient):
        """Verify that a simple value can be set and retrieved correctly."""
        key = "test_key_1"
        value = {"data": "my-test-value", "number": 123}

        cache_client.set(key, value)
        retrieved_value = cache_client.get(key)

        assert retrieved_value is not None
        assert retrieved_value == value

    def test_get_nonexistent_key_returns_none(self, cache_client: LocalCacheClient):
        """Verify that getting a key that does not exist returns None."""
        retrieved_value = cache_client.get("nonexistent-key")
        assert retrieved_value is None

    def test_exists_method(self, cache_client: LocalCacheClient):
        """Verify that exists() returns True for an existing key and False otherwise."""
        key = "test_key_2"
        value = "i exist"

        # Check that it doesn't exist initially
        assert not cache_client.exists(key)

        # Set the key and check that it exists
        cache_client.set(key, value)
        assert cache_client.exists(key)

    def test_delete_method(self, cache_client: LocalCacheClient):
        """Verify that a key is removed from the cache after being deleted."""
        key = "test_key_3"
        value = "to-be-deleted"

        cache_client.set(key, value)
        assert cache_client.exists(key)

        cache_client.delete(key)
        assert not cache_client.exists(key)
        assert cache_client.get(key) is None

    def test_overwrite_existing_key(self, cache_client: LocalCacheClient):
        """Verify that setting an existing key overwrites its value."""
        key = "test_key_4"
        initial_value = "initial"
        new_value = "overwritten"

        cache_client.set(key, initial_value)
        assert cache_client.get(key) == initial_value

        cache_client.set(key, new_value)
        assert cache_client.get(key) == new_value

    def test_ttl_expiration(self, cache_client: LocalCacheClient):
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

        # Verify the underlying file is also gone
        cache_file = cache_client._get_file_path(key)
        assert not cache_file.exists()

    def test_value_with_no_ttl_persists(self, cache_client: LocalCacheClient):
        """Verify that an item with no TTL does not expire."""
        key = "test_key_no_ttl"
        value = "i will not expire"
        ttl_seconds = 1

        cache_client.set(key, value, time_to_live=None)
        time.sleep(ttl_seconds + 0.1)

        assert cache_client.exists(key)
        assert cache_client.get(key) == value


class TestCacheKeyGeneration:
    """Tests the static key generation method."""

    def test_generate_cache_key_consistency(self):
        """
        Verify that the same parameters produce the same key, regardless of order.
        """
        params1 = {"asset": "BTC", "interval": "4h", "limit": 100}
        params2 = {"interval": "4h", "limit": 100, "asset": "BTC"}

        key1 = LocalCacheClient.generate_cache_key(params1)
        key2 = LocalCacheClient.generate_cache_key(params2)

        assert key1 == key2

    def test_generate_cache_key_uniqueness(self):
        """Verify that different parameters produce different keys."""
        params1 = {"asset": "BTC", "interval": "4h"}
        params2 = {"asset": "ETH", "interval": "4h"}

        key1 = LocalCacheClient.generate_cache_key(params1)
        key2 = LocalCacheClient.generate_cache_key(params2)

        assert key1 != key2
