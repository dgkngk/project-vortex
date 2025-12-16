import gzip
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.BaseCacheClient import BaseCacheClient


class LocalCacheClient(BaseCacheClient):
    """
    A file-system-based cache client.

    This client stores cached items as compressed, pickled files in a local directory.
    It handles time-to-live (TTL) by storing expiration metadata alongside the data.
    """

    def __init__(
        self, cache_dir: str = ".cache/data", logger: Optional[VortexLogger] = None
    ):
        """
        Initializes the LocalCacheClient.

        Args:
            cache_dir: The directory where cache files will be stored.
                       Defaults to '.cache/data' in the project root.
            logger: Optional logger instance.
        """
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or VortexLogger(
            name=self.__class__.__name__, level="DEBUG"
        )

    def _get_file_path(self, key: str) -> Path:
        """Constructs the full path for a given cache key."""
        return self.cache_dir / key

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves, decompresses, and deserializes an item from the file cache.

        If the item is expired, it is deleted from the cache and None is returned.

        Args:
            key: The key of the item to retrieve.

        Returns:
            The cached item, or None if the item is not found or is expired.
        """
        file_path = self._get_file_path(key)
        if not file_path.is_file():
            return None

        try:
            with gzip.open(file_path, "rb") as f:
                payload = pickle.load(f)

            expires_at_str = payload.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at:
                    # Cache has expired, delete the file and return None
                    self.logger.debug(f"Cache key '{key}' has expired. Deleting.")
                    self.delete(key)
                    return None

            return payload.get("value")

        except (
            pickle.UnpicklingError,
            FileNotFoundError,
            EOFError,
            gzip.BadGzipFile,
        ) as e:
            # Handle corrupted or missing files gracefully
            self.logger.error(
                f"Could not read or decode cache file for key '{key}': {e}"
            )
            if file_path.exists():
                self.delete(key)
            return None

    def set(self, key: str, value: Any, time_to_live: Optional[int] = None):
        """
        Serializes, compresses, and saves an item to the file cache.

        Args:
            key: The key under which to store the item.
            value: The item to store.
            time_to_live: Optional time-to-live in seconds.
        """
        file_path = self._get_file_path(key)
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(seconds=time_to_live))
            if time_to_live
            else None
        )

        payload = {
            "value": value,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

        try:
            with gzip.open(file_path, "wb") as f:
                pickle.dump(payload, f)
        except (pickle.PicklingError, OSError):
            # Handle potential errors during file writing
            pass

    def delete(self, key: str):
        """
        Deletes an item from the file cache.

        Args:
            key: The key of the item to delete.
        """
        file_path = self._get_file_path(key)
        try:
            file_path.unlink()
        except FileNotFoundError:
            # File is already gone, which is the desired state.
            pass

    def exists(self, key: str) -> bool:
        """
        Checks if a non-expired item exists in the cache.

        Note: This is functionally equivalent to `get(key) is not None`,
        as it also triggers an expiration check.

        Args:
            key: The key to check.

        Returns:
            True if a valid, non-expired item exists, False otherwise.
        """
        return self.get(key) is not None
