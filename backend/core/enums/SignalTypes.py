from enum import Enum


class SignalTypes(Enum):
    UNDERPRICED = 3
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2
    OVERPRICED = -3
