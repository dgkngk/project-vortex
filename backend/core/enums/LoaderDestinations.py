from enum import Enum


class LoaderDestinations(Enum):
    POSTGRES = "Postgres"
    REDIS = "Redis"
    MONGO = "MongoDB"
