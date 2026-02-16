from unittest.mock import MagicMock

import pytest

from backend.etl.data_access.DataDestinationClient import DataDestinationClient
from backend.etl.data_access.storage.StorageRouter import StorageRouter


def _make_mock_destination() -> MagicMock:
    """Create a mock DataDestinationClient with a save_data method."""
    mock = MagicMock(spec=DataDestinationClient)
    return mock


@pytest.mark.unit
class TestStorageRouter:
    """Unit tests for StorageRouter."""

    def test_is_data_destination_client(self):
        """StorageRouter must be a DataDestinationClient subclass."""
        router = StorageRouter()
        assert isinstance(router, DataDestinationClient)

    def test_save_data_routes_to_cold_tier(self):
        """When tier='cold' is specified, only the cold destination receives data."""
        cold_mock = _make_mock_destination()
        hot_mock = _make_mock_destination()
        router = StorageRouter(hot=hot_mock, cold=cold_mock)

        payload = {"tier": "cold", "df": "some_data", "asset_id": "BTC"}
        router.save_data(payload)

        cold_mock.save_data.assert_called_once_with(payload)
        hot_mock.save_data.assert_not_called()

    def test_save_data_routes_to_hot_tier(self):
        """When tier='hot' is specified, only the hot destination receives data."""
        cold_mock = _make_mock_destination()
        hot_mock = _make_mock_destination()
        router = StorageRouter(hot=hot_mock, cold=cold_mock)

        payload = {"tier": "hot", "key": "latest_btc", "value": 50000}
        router.save_data(payload)

        hot_mock.save_data.assert_called_once_with(payload)
        cold_mock.save_data.assert_not_called()

    def test_save_data_routes_to_all_tiers(self):
        """Without a 'tier' key, data is broadcast to all active tiers."""
        cold_mock = _make_mock_destination()
        hot_mock = _make_mock_destination()
        router = StorageRouter(hot=hot_mock, cold=cold_mock)

        payload = {"df": "some_data", "asset_id": "ETH"}
        router.save_data(payload)

        hot_mock.save_data.assert_called_once_with(payload)
        cold_mock.save_data.assert_called_once_with(payload)

    def test_tier_failure_does_not_block_others(self):
        """A failure in one tier should not prevent other tiers from writing."""
        cold_mock = _make_mock_destination()
        hot_mock = _make_mock_destination()
        hot_mock.save_data.side_effect = RuntimeError("Redis down")

        router = StorageRouter(hot=hot_mock, cold=cold_mock)

        payload = {"df": "some_data", "asset_id": "SOL"}
        # Should NOT raise, even though hot tier fails
        router.save_data(payload)

        hot_mock.save_data.assert_called_once()
        cold_mock.save_data.assert_called_once_with(payload)

    def test_route_returns_specific_tier(self):
        """route() with tier key returns only that tier name."""
        router = StorageRouter(cold=_make_mock_destination())
        result = router.route({"tier": "cold"})
        assert result == ["cold"]

    def test_route_returns_all_active_tiers(self):
        """route() without tier key returns all configured tier names."""
        router = StorageRouter(
            hot=_make_mock_destination(),
            cold=_make_mock_destination(),
        )
        result = router.route({"some": "data"})
        assert sorted(result) == ["cold", "hot"]

    def test_unconfigured_tier_is_skipped(self):
        """Requesting a tier that was not configured should log a warning and skip."""
        cold_mock = _make_mock_destination()
        router = StorageRouter(cold=cold_mock)

        payload = {"tier": "warm", "data": "something"}
        # Should not raise
        router.save_data(payload)

        cold_mock.save_data.assert_not_called()
