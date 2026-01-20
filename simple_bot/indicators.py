"""
Technical Indicators Module
Simple indicators for cryptocurrency trading
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple


def sma(data: pd.Series, period: int) -> pd.Series:
    """
    Simple Moving Average (SMA)

    Args:
        data: Price series (usually close prices)
        period: Number of periods for the moving average

    Returns:
        Series with SMA values
    """
    return data.rolling(window=period).mean()


def ema(data: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average (EMA)

    Args:
        data: Price series
        period: Number of periods

    Returns:
        Series with EMA values
    """
    return data.ewm(span=period, adjust=False).mean()


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI)

    Args:
        data: Price series (usually close prices)
        period: RSI period (default: 14)

    Returns:
        Series with RSI values (0-100)
    """
    delta = data.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence (MACD)

    Args:
        data: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands

    Args:
        data: Price series
        period: SMA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)

    Returns:
        Tuple of (Upper band, Middle band (SMA), Lower band)
    """
    middle = sma(data, period)
    std = data.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR)

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 14)

    Returns:
        Series with ATR values
    """
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_values = true_range.ewm(span=period, adjust=False).mean()

    return atr_values


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)

    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_period).mean()

    return k, d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Williams %R

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Period (default: 14)

    Returns:
        Series with Williams %R values (-100 to 0)
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()

    wr = -100 * ((highest_high - close) / (highest_high - lowest_low))

    return wr


def momentum(data: pd.Series, period: int = 10) -> pd.Series:
    """
    Momentum Indicator

    Args:
        data: Price series
        period: Period (default: 10)

    Returns:
        Series with momentum values
    """
    return data - data.shift(period)


def roc(data: pd.Series, period: int = 10) -> pd.Series:
    """
    Rate of Change (ROC)

    Args:
        data: Price series
        period: Period (default: 10)

    Returns:
        Series with ROC values (percentage)
    """
    return ((data - data.shift(period)) / data.shift(period)) * 100


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume (OBV)

    Args:
        close: Close prices
        volume: Volume data

    Returns:
        Series with OBV values
    """
    direction = np.where(close > close.shift(1), 1,
                         np.where(close < close.shift(1), -1, 0))

    obv_values = (volume * direction).cumsum()

    return pd.Series(obv_values, index=close.index)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP)

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume data

    Returns:
        Series with VWAP values
    """
    typical_price = (high + low + close) / 3
    vwap_values = (typical_price * volume).cumsum() / volume.cumsum()

    return vwap_values


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend Indicator

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 10)
        multiplier: ATR multiplier (default: 3.0)

    Returns:
        Tuple of (Supertrend values, Direction: 1 for uptrend, -1 for downtrend)
    """
    atr_val = atr(high, low, close, period)

    hl2 = (high + low) / 2

    upper_band = hl2 + (multiplier * atr_val)
    lower_band = hl2 - (multiplier * atr_val)

    supertrend_vals = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    supertrend_vals.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

            if direction.iloc[i] == 1 and lower_band.iloc[i] < lower_band.iloc[i - 1]:
                lower_band.iloc[i] = lower_band.iloc[i - 1]
            if direction.iloc[i] == -1 and upper_band.iloc[i] > upper_band.iloc[i - 1]:
                upper_band.iloc[i] = upper_band.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend_vals.iloc[i] = lower_band.iloc[i]
        else:
            supertrend_vals.iloc[i] = upper_band.iloc[i]

    return supertrend_vals, direction


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all indicators and add them to the dataframe

    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)

    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()

    # Moving averages
    df['sma_10'] = sma(df['close'], 10)
    df['sma_20'] = sma(df['close'], 20)
    df['sma_50'] = sma(df['close'], 50)
    df['sma_200'] = sma(df['close'], 200)

    df['ema_9'] = ema(df['close'], 9)
    df['ema_21'] = ema(df['close'], 21)
    df['ema_50'] = ema(df['close'], 50)

    # RSI
    df['rsi'] = rsi(df['close'], 14)

    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = macd(df['close'])

    # Bollinger Bands
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = bollinger_bands(df['close'])

    # ATR
    df['atr'] = atr(df['high'], df['low'], df['close'])

    # Stochastic
    df['stoch_k'], df['stoch_d'] = stochastic(df['high'], df['low'], df['close'])

    # Momentum
    df['momentum'] = momentum(df['close'])
    df['roc'] = roc(df['close'])

    # Volume indicators
    if 'volume' in df.columns:
        df['obv'] = obv(df['close'], df['volume'])
        df['vwap'] = vwap(df['high'], df['low'], df['close'], df['volume'])

    return df
