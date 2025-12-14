from enum import Enum


class TAStudies(Enum):
    """
    Configurations for pandas-ta studies.
    Each enum member is a dictionary that can be used in a pandas-ta Study.
    """

    RSI = {"kind": "rsi"}
    MACD = {"kind": "macd"}
    BBANDS = {"kind": "bbands"}
    STOCHRSI = {"kind": "stochrsi"}
    VWAP = {"kind": "vwap"}
    HMA = {"kind": "hma"}
