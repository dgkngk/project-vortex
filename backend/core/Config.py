from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    # Binance
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None

    # CoinGecko
    coingecko_key_mode: Optional[str] = None
    coingecko_api_key: Optional[str] = None

    # Database / Infra
    postgres_dsn: Optional[str] = None
    redis_url: Optional[str] = None
    influx_url: Optional[str] = None
    cache_type: str = "local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
