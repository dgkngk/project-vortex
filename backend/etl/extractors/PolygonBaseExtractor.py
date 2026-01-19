import os
from typing import Any, Dict, List, Optional

from massive import RESTClient

from backend.core.Config import AppConfig
from backend.core.enums.AssetEnums import DataIntervals
from backend.core.VortexLogger import VortexLogger
from backend.etl.extractors.BaseExtractor import BaseExtractor


class PolygonBaseExtractor(BaseExtractor):
    """
    Base class for Polygon.io extractors using the Massive library.
    """

    INTERVAL_MAP = {
        DataIntervals.ONE_MINUTE: (1, "minute"),
        DataIntervals.FIVE_MINUTE: (5, "minute"),
        DataIntervals.TEN_MINUTE: (10, "minute"),
        DataIntervals.FIFTEEN_MINUTE: (15, "minute"),
        DataIntervals.THIRTY_MINUTE: (30, "minute"),
        DataIntervals.ONE_HOUR: (1, "hour"),
        DataIntervals.ONE_DAY: (1, "day"),
        DataIntervals.ONE_WEEK: (1, "week"),
        DataIntervals.ONE_MONTH: (1, "month"),
    }

    def __init__(self, **kwargs):
        self.config = AppConfig()
        api_key = self.config.polygon_api_key or os.getenv("MASSIVE_API_KEY")

        if not api_key:
            VortexLogger(name=self.__class__.__name__).warning(
                "Polygon API key not found in config or environment."
            )

        self.client = RESTClient(api_key=api_key)

        super().__init__(
            api_base_url="https://api.massive.com",
            # Default rate limit for free tier
            rate_limit_configs={"default": {"requests_per_minute": 5}},
            logger=VortexLogger(name=self.__class__.__name__, level="INFO"),
            **kwargs,
        )

    def _map_interval(self, interval: DataIntervals):
        return self.INTERVAL_MAP.get(interval, (1, "day"))
