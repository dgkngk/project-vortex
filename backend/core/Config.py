from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class AppConfig(BaseSettings):
    # Binance
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None

    # Other providers can be added here in the future
    # kraken_api_key: Optional[str] = None
    # kraken_base_url: str = "https://api.kraken.com"

    # Database / Infra
    postgres_dsn: Optional[str] = None
    redis_url: Optional[str] = None
    influx_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
