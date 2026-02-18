import pandas as pd
from backend.scitus.backtest.slippage.BaseSlippage import BaseSlippage

class RollingStdDevSlippage(BaseSlippage):
    """
    Slippage estimates based on recent volatility (Rolling Standard Deviation).
    Model: slippage_price = StdDev(period) * multiplier
    Cost = trades * slippage_price
    """

    def __init__(self, atr_period: int = 14, multiplier: float = 0.1):
        self.atr_period = atr_period
        self.multiplier = multiplier

    def calculate(self, trades: pd.Series, volume: pd.Series, close: pd.Series) -> pd.Series:
        # Handle case where we don't have enough data for ATR
        if len(close) < self.atr_period:
            return pd.Series(0.0, index=close.index)

        # Create basic OHLC frame for pandas_ta (using close as proxy for H/L/C)
        # This is an estimation since we only have 'close' passed in here usually.
        # Ideally, we'd pass full OHLC. For now, we use close to estimate.
        # But wait, BaseBacktester usually has full data? 
        # The interface only asks for (trades, volume, close).
        
        # Strategy: Use rolling volatility (std dev) if OHLC not available, 
        # or just rely on passed 'close' to compute a proxy volatility.
        # Better: Standard ATR requires High/Low. 
        # Let's use rolling std dev of returns as a proxy for volatility if High/Low missing,
        # OR just assume High=Low=Close which yields ATR ~ rolling change.
        
        # Since pandas_ta.atr needs high/low/close, and we only defined (trades, volume, close),
        # we strictly need High/Low for true ATR. 
        # Let's try to assume 'close' acts as the price series and calculate volatility from it.
        # Rolling Std Dev of Close is a common proxy when High/Low unavailable.
        
        # HOWEVER, let's look at the contract. If we want true ATR, we need to pass a DataFrame.
        # But for 'vectorized' strictness, let's use rolling std of percent change * price.
        
        # Alternative: We change the signature? No, let's keep it simple.
        # Proxy: Volatility = Rolling Std(Close) * multiplier? 
        # Or: Slippage = Percentage Volatility * Trade Value
        
        # Let's use: Slippage % = Rolling Std Dev of Returns (Over period) * Multiplier
        
        returns = close.pct_change()
        volatility = returns.rolling(window=self.atr_period).std()
        
        # Fill NaN at start
        volatility = volatility.fillna(0)
        
        slippage_rate = volatility * self.multiplier
        return (trades * close) * slippage_rate
