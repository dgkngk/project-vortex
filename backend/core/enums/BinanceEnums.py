from enum import Enum


class SymbolStatus(Enum):
    """
    ENUM for Symbol status.
    """
    TRADING = "TRADING"
    END_OF_DAY = "END_OF_DAY"
    HALT = "HALT"
    BREAK = "BREAK"


class AccountPermissions(Enum):
    """
    ENUM for Account and Symbol Permissions.
    """
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    LEVERAGED = "LEVERAGED"
    TRD_GRP_002 = "TRD_GRP_002"
    TRD_GRP_003 = "TRD_GRP_003"
    TRD_GRP_004 = "TRD_GRP_004"
    TRD_GRP_005 = "TRD_GRP_005"
    TRD_GRP_006 = "TRD_GRP_006"
    TRD_GRP_007 = "TRD_GRP_007"
    TRD_GRP_008 = "TRD_GRP_008"
    TRD_GRP_009 = "TRD_GRP_009"
    TRD_GRP_010 = "TRD_GRP_010"
    TRD_GRP_011 = "TRD_GRP_011"
    TRD_GRP_012 = "TRD_GRP_012"
    TRD_GRP_013 = "TRD_GRP_013"
    TRD_GRP_014 = "TRD_GRP_014"
    TRD_GRP_015 = "TRD_GRP_015"
    TRD_GRP_016 = "TRD_GRP_016"
    TRD_GRP_017 = "TRD_GRP_017"
    TRD_GRP_018 = "TRD_GRP_018"
    TRD_GRP_019 = "TRD_GRP_019"
    TRD_GRP_020 = "TRD_GRP_020"
    TRD_GRP_021 = "TRD_GRP_021"
    TRD_GRP_022 = "TRD_GRP_022"
    TRD_GRP_023 = "TRD_GRP_023"
    TRD_GRP_024 = "TRD_GRP_024"
    TRD_GRP_025 = "TRD_GRP_025"


class OrderStatus(Enum):
    """
    ENUM for Order status.
    """
    NEW = "NEW"
    PENDING_NEW = "PENDING_NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXPIRED_IN_MATCH = "EXPIRED_IN_MATCH"


class OrderListStatus(Enum):
    """
    ENUM for Order List Status.
    """
    RESPONSE = "RESPONSE"
    EXEC_STARTED = "EXEC_STARTED"
    UPDATED = "UPDATED"
    ALL_DONE = "ALL_DONE"


class OrderListOrderStatus(Enum):
    """
    ENUM for Order List Order Status.
    """
    EXECUTING = "EXECUTING"
    ALL_DONE = "ALL_DONE"
    REJECT = "REJECT"


class ContingencyType(Enum):
    """
    ENUM for ContingencyType.
    """
    OCO = "OCO"
    OTO = "OTO"


class AllocationType(Enum):
    """
    ENUM for AllocationType.
    """
    SOR = "SOR"


class OrderType(Enum):
    """
    ENUM for Order types.
    """
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"


class OrderResponseType(Enum):
    """
    ENUM for Order Response Type.
    """
    ACK = "ACK"
    RESULT = "RESULT"
    FULL = "FULL"


class WorkingFloor(Enum):
    """
    ENUM for Working Floor.
    """
    EXCHANGE = "EXCHANGE"
    SOR = "SOR"


class OrderSide(Enum):
    """
    ENUM for Order side.
    """
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    """
    ENUM for Time in force.
    """
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class RateLimitType(Enum):
    """
    ENUM for Rate limiters.
    """
    REQUEST_WEIGHT = "REQUEST_WEIGHT"
    ORDERS = "ORDERS"
    RAW_REQUESTS = "RAW_REQUESTS"


class RateLimitInterval(Enum):
    """
    ENUM for Rate limit intervals.
    """
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    DAY = "DAY"


class STPMode(Enum):
    """
    ENUM for STP Modes.
    """
    NONE = "NONE"
    EXPIRE_MAKER = "EXPIRE_MAKER"
    EXPIRE_TAKER = "EXPIRE_TAKER"
    EXPIRE_BOTH = "EXPIRE_BOTH"
    DECREMENT = "DECREMENT"
