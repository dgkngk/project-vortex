from enum import Enum


class StrategyConfigs(Enum):
    BOLLINGER_BANDS = {
        "close_col": "close",
        "bbh_col": "BBU_5_2.0_2.0",
        "bbm_col": "BBM_5_2.0_2.0",
        "bbl_col": "BBL_5_2.0_2.0",
        "proximity_factor": 0.05,
    }
    STOCHRSI = {
        "k_col": "STOCHRSIk_14_14_3_3",
        "d_col": "STOCHRSId_14_14_3_3",
        "overbought_threshold": 80,
        "oversold_threshold": 20,
    }
    MACD = {
        "macd_col": "MACD_12_26_9",
        "macd_signal_col": "MACDs_12_26_9",
        "overbought_threshold": 2,
        "oversold_threshold": -2,
    }
    VWAP = {"close_col": "close", "vwap_col": "VWAP_D", "proximity_factor": 0.01}
    HMA_RSI = {
        "close_col": "close",
        "hma_col": "HMA_10",
        "rsi_col": "RSI_14",
        "rsi_hma_period": 14,
        "rsi_buy_threshold": 40,
        "rsi_sell_threshold": 60,
    }
    VOTING = {
        "strategies": [],
        "min_votes": 1,
    }
    COMPOSITE = {
        "primary_strategy": {},
        "filter_strategies": [],
    }
