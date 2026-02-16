from typing import Any, Dict, List, Optional

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.DataDestinationClient import DataDestinationClient


class StorageRouter(DataDestinationClient):
    """
    Routes data writes to the appropriate storage tier(s).

    Tier mapping:
        - 🔴 Hot:  Sub-ms reads (e.g., RedisCacheClient for real-time state)
        - 🟡 Warm: Recent history (placeholder for future InfluxDB integration)
        - 🔵 Cold: Full historical data (ParquetWriter for backtesting & ML)

    Each tier is an optional DataDestinationClient. When `save_data` is called,
    data is routed based on the 'tier' key in the data dict, or broadcast to
    all active tiers if no specific tier is requested.
    """

    TIER_HOT = "hot"
    TIER_WARM = "warm"
    TIER_COLD = "cold"

    def __init__(
        self,
        hot: Optional[DataDestinationClient] = None,
        warm: Optional[DataDestinationClient] = None,
        cold: Optional[DataDestinationClient] = None,
    ):
        super().__init__()
        self.tiers: Dict[str, DataDestinationClient] = {}
        self.logger = VortexLogger(name="StorageRouter")

        if hot:
            self.tiers[self.TIER_HOT] = hot
        if warm:
            self.tiers[self.TIER_WARM] = warm
        if cold:
            self.tiers[self.TIER_COLD] = cold

        if not self.tiers:
            self.logger.warning("StorageRouter initialised with no active tiers.")

    def save_data(self, data: Any):
        """
        Route data to the appropriate storage tier(s).

        If the data dict contains a 'tier' key, only that tier receives the
        write. Otherwise the write is broadcast to every active tier.

        Each tier write is wrapped in its own try/except so that a failure in
        one tier does not prevent the others from receiving the data.

        Args:
            data: The payload to persist.  For tier-specific routing, include
                  a 'tier' key with value 'hot', 'warm', or 'cold'.
        """
        target_tiers = self.route(data)

        for tier_name in target_tiers:
            destination = self.tiers.get(tier_name)
            if destination is None:
                self.logger.warning(
                    f"Tier '{tier_name}' requested but not configured. Skipping."
                )
                continue
            try:
                destination.save_data(data)
            except Exception as e:
                self.logger.error(
                    f"Failed to write to '{tier_name}' tier: {e}"
                )

    def route(self, data: Any) -> List[str]:
        """
        Determine which tiers should receive the data.

        Args:
            data: The payload. If it is a dict with a 'tier' key, only that
                  tier is returned. Otherwise all active tier names are returned.

        Returns:
            A list of tier name strings (e.g., ['hot', 'cold']).
        """
        if isinstance(data, dict) and "tier" in data:
            return [data["tier"]]
        return list(self.tiers.keys())
