from datetime import timedelta
from typing import List, Optional

import pandas as pd

from backend.core.VortexLogger import VortexLogger
from backend.etl.data_access.storage.HistoricalDataStore import HistoricalDataStore
from backend.scitus.features.FeatureRegistry import FeatureRegistry


class FeatureStore:
    """
    Central engine for computing features with point-in-time correctness.

    Orchestrates data fetching from HistoricalDataStore and feature calculation
    via FeatureRegistry. Ensures enough lookback data is fetched to produce
    valid indicator values from the first requested date.
    """

    LOOKBACK_BUFFER_MULTIPLIER = 2

    def __init__(
        self,
        registry: Optional[FeatureRegistry] = None,
        data_store: Optional[HistoricalDataStore] = None,
    ):
        self.registry = registry or FeatureRegistry()
        self.data_store = data_store or HistoricalDataStore()
        self.logger = VortexLogger(name="FeatureStore")

    def compute(
        self,
        asset_id: str,
        feature_names: List[str],
        start: str,
        end: str,
        asset_class: str = "crypto",
    ) -> pd.DataFrame:
        """
        Compute requested features for an asset within a date range.

        Point-in-time correctness is enforced:
        - Enough lookback data is fetched so the first row at ``start``
          already has valid indicator values.
        - No data after ``end`` is ever included.

        Args:
            asset_id: Asset identifier (e.g., 'BTCUSDT').
            feature_names: List of registered feature names to compute.
            start: Start date (ISO format, inclusive).
            end: End date (ISO format, inclusive).
            asset_class: Top-level partition (default: 'crypto').

        Returns:
            DataFrame with a column per feature for rows between ``start`` and ``end``.
        """
        feature_defs = [self.registry.get(name) for name in feature_names]

        max_window = max((fd.window for fd in feature_defs), default=0)
        lookback_days = max_window * self.LOOKBACK_BUFFER_MULTIPLIER

        adjusted_start = (
            pd.Timestamp(start) - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")

        raw_data = self.data_store.query(
            asset_id=asset_id,
            start_date=adjusted_start,
            end_date=end,
            asset_class=asset_class,
        )

        if raw_data.empty:
            self.logger.warning(
                f"No raw data for {asset_id} between {adjusted_start} and {end}."
            )
            return pd.DataFrame(columns=feature_names)

        result = pd.DataFrame(index=raw_data.index)

        for feature_def in feature_defs:
            try:
                series = feature_def.function(raw_data)
                if series is not None:
                    result[feature_def.name] = series
                else:
                    self.logger.warning(
                        f"Feature '{feature_def.name}' returned None for {asset_id}."
                    )
                    result[feature_def.name] = pd.NA
            except Exception as exc:
                self.logger.error(
                    f"Error computing '{feature_def.name}' for {asset_id}: {exc}"
                )
                result[feature_def.name] = pd.NA

        # Trim to requested date range (point-in-time: discard lookback rows)
        if "timestamp" in raw_data.columns:
            # Ensure timestamp type for comparison
            raw_data["timestamp"] = pd.to_datetime(raw_data["timestamp"])
            mask = (raw_data["timestamp"] >= start) & (raw_data["timestamp"] <= end)
            result = result.loc[mask]
        elif isinstance(raw_data.index, pd.DatetimeIndex):
            mask = (raw_data.index >= start) & (raw_data.index <= end)
            result = result.loc[mask]
        else:
            self.logger.warning(
                "Could not trim feature data: no 'timestamp' col or DatetimeIndex. "
                "Returning empty to prevent leakage."
            )
            return pd.DataFrame(columns=feature_names)

        return result
