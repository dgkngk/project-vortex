from enum import Enum


class AssetType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"


class DataType(Enum):
    OHLC = "ohlc"
    OHLCV = "ohlcv"
    TICK = "tick"


class DataSource(Enum):
    ALPHAVANTAGE = "alphavantage"
    BINANCE = "binance"
    COINBASE = "coinbase"
    COINGECKO = "coingecko"
    CRYPTO_COMPARE = "crypto_compare"
    FINNHUB = "finnhub"
    IEX = "iex"
    KRAKEN = "kraken"
    POLONIEX = "poloniex"
    QUANDL = "quandl"
    YAHOO = "yahoo"


class DataIntervals(Enum):
    SECONDS = "1s"
    ONE_MINUTE = "1m"
    FIVE_MINUTE = "5m"
    TEN_MINUTE = "10m"
    FIFTEEN_MINUTE = "15m"
    THIRTY_MINUTE = "30m"
    ONE_HOUR = "1h"
    TWO_HOUR = "2h"
    FOUR_HOUR = "4h"
    SIX_HOUR = "6h"
    EIGHT_HOUR = "8h"
    TWELVE_HOUR = "12h"
    ONE_DAY = "1d"
    THREE_DAY = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"
