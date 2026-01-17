from enum import Enum


class ExtractionMode(Enum):
    WEEKLY = "WEEKLY"
    DAILY = "DAILY"
    HOURLY = "HOURLY"
    MINUTELY = "MINUTELY"
