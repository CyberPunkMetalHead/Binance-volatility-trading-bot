"""
Strategy Optimizer Module
Grid search and optimization for finding profitable strategy parameters
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Callable
from dataclasses import dataclass
from itertools import product
import multiprocessing as mp
from functools import partial

from .strategies import (
    BaseStrategy, Signal, SMAStrategy, EMAStrategy, RSIStrategy,
    MACDStrategy, BollingerBandsStrategy, TripleMAStrategy
)
from .backtester import Backtester, BacktestResult
from .indicators import sma, ema, rsi, macd, bollinger_bands, atr, supertrend


@dataclass
class OptimizationResult:
    """Results of parameter optimization"""
    strategy_name: str
    best_params: Dict[str, Any]
    best_return: float
    best_sharpe: float
    all_results: List[Tuple[Dict, BacktestResult]]


class StrategyOptimizer:
    """
    Optimizer for finding best strategy parameters
    """

    def __init__(self, df: pd.DataFrame,
                 initial_capital: float = 10000,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize optimizer

        Args:
            df: Historical OHLCV data
            initial_capital: Starting capital
            commission: Trading commission
            slippage: Slippage
        """
        self.df = df
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def optimize_sma(self, short_range: range = range(5, 30, 5),
                     long_range: range = range(20, 100, 10)) -> OptimizationResult:
        """Optimize SMA crossover parameters"""
        results = []

        for short, long in product(short_range, long_range):
            if short >= long:
                continue

            strategy = SMAStrategy(short, long)
            backtester = Backtester(
                self.initial_capital, self.commission, self.slippage
            )
            result = backtester.run(self.df, strategy)
            results.append(({'short': short, 'long': long}, result))

        best = max(results, key=lambda x: x[1].total_return_percent)

        return OptimizationResult(
            strategy_name='SMA',
            best_params=best[0],
            best_return=best[1].total_return_percent,
            best_sharpe=best[1].sharpe_ratio,
            all_results=results
        )

    def optimize_rsi(self, period_range: range = range(7, 21, 2),
                     oversold_range: range = range(20, 40, 5),
                     overbought_range: range = range(60, 85, 5)) -> OptimizationResult:
        """Optimize RSI parameters"""
        results = []

        for period, oversold, overbought in product(period_range, oversold_range, overbought_range):
            if oversold >= overbought:
                continue

            strategy = RSIStrategy(period, oversold, overbought)
            backtester = Backtester(
                self.initial_capital, self.commission, self.slippage
            )
            result = backtester.run(self.df, strategy)
            results.append(({'period': period, 'oversold': oversold, 'overbought': overbought}, result))

        best = max(results, key=lambda x: x[1].total_return_percent)

        return OptimizationResult(
            strategy_name='RSI',
            best_params=best[0],
            best_return=best[1].total_return_percent,
            best_sharpe=best[1].sharpe_ratio,
            all_results=results
        )

    def optimize_with_sl_tp(self, strategy: BaseStrategy,
                            sl_range: List[float] = [0.02, 0.03, 0.05, 0.07, 0.10],
                            tp_range: List[float] = [0.03, 0.05, 0.07, 0.10, 0.15, 0.20]) -> OptimizationResult:
        """Optimize stop loss and take profit for a strategy"""
        results = []

        for sl, tp in product(sl_range, tp_range):
            backtester = Backtester(
                self.initial_capital, self.commission, self.slippage,
                stop_loss=sl, take_profit=tp
            )
            result = backtester.run(self.df, strategy)
            results.append(({'stop_loss': sl, 'take_profit': tp}, result))

        best = max(results, key=lambda x: x[1].total_return_percent)

        return OptimizationResult(
            strategy_name=f'{strategy.name}_SL_TP',
            best_params=best[0],
            best_return=best[1].total_return_percent,
            best_sharpe=best[1].sharpe_ratio,
            all_results=results
        )


# ============== IMPROVED STRATEGIES ==============

class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following with Multiple Confirmations

    Buy when:
    - Price above SMA 200 (long-term uptrend)
    - SMA 20 > SMA 50 (medium-term uptrend)
    - RSI > 50 but < 70 (momentum but not overbought)

    Sell when:
    - Price below SMA 200 OR
    - SMA 20 < SMA 50
    """

    def __init__(self):
        super().__init__(name="TrendFollowing")

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['sma_20'] = sma(df['close'], 20)
        df['sma_50'] = sma(df['close'], 50)
        df['sma_200'] = sma(df['close'], 200)
        df['rsi'] = rsi(df['close'], 14)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy conditions
        uptrend = (
            (df['close'] > df['sma_200']) &
            (df['sma_20'] > df['sma_50']) &
            (df['rsi'] > 45) &
            (df['rsi'] < 70)
        )

        # Entry on crossover
        entry = uptrend & ~uptrend.shift(1).fillna(False)
        signals[entry] = Signal.BUY

        # Sell conditions
        downtrend = (
            (df['close'] < df['sma_200']) |
            (df['sma_20'] < df['sma_50']) |
            (df['rsi'] > 75)
        )

        exit_signal = downtrend & ~downtrend.shift(1).fillna(False)
        signals[exit_signal] = Signal.SELL

        return signals


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy with Bollinger Bands

    Buy when:
    - Price touches lower BB
    - RSI < 30 (oversold)
    - Price starts recovering (close > open)

    Sell when:
    - Price touches upper BB OR
    - RSI > 70 OR
    - Price at middle BB with profit
    """

    def __init__(self, bb_period: int = 20, bb_std: float = 2.0,
                 rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70):
        super().__init__(name=f"MeanReversion_{bb_period}_{rsi_period}")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['bb_upper'], df['bb_middle'], df['bb_lower'] = bollinger_bands(
            df['close'], self.bb_period, self.bb_std
        )
        df['rsi'] = rsi(df['close'], self.rsi_period)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy: Price near lower BB + RSI oversold + bullish candle
        buy_cond = (
            (df['close'] <= df['bb_lower'] * 1.01) &
            (df['rsi'] < self.rsi_oversold + 10) &
            (df['close'] > df['open'])  # Bullish candle
        )
        signals[buy_cond] = Signal.BUY

        # Sell: Price near upper BB OR RSI overbought
        sell_cond = (
            (df['close'] >= df['bb_upper'] * 0.99) |
            (df['rsi'] > self.rsi_overbought)
        )
        signals[sell_cond] = Signal.SELL

        return signals


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy with Volume Confirmation

    Buy when:
    - Price breaks above 20-period high
    - Volume > 1.5x average volume
    - ATR indicates volatility expansion

    Sell when:
    - Price breaks below 10-period low OR
    - Trailing stop hit
    """

    def __init__(self, breakout_period: int = 20, exit_period: int = 10,
                 volume_mult: float = 1.5):
        super().__init__(name=f"Breakout_{breakout_period}_{exit_period}")
        self.breakout_period = breakout_period
        self.exit_period = exit_period
        self.volume_mult = volume_mult

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['highest'] = df['high'].rolling(self.breakout_period).max()
        df['lowest'] = df['low'].rolling(self.exit_period).min()
        df['avg_volume'] = df['volume'].rolling(20).mean()
        df['atr'] = atr(df['high'], df['low'], df['close'], 14)
        df['atr_ma'] = df['atr'].rolling(20).mean()

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy on breakout with volume
        buy_cond = (
            (df['close'] > df['highest'].shift(1)) &
            (df['volume'] > df['avg_volume'] * self.volume_mult) &
            (df['atr'] > df['atr_ma'])  # Volatility expansion
        )
        signals[buy_cond] = Signal.BUY

        # Sell on breakdown
        sell_cond = df['close'] < df['lowest'].shift(1)
        signals[sell_cond] = Signal.SELL

        return signals


class MomentumRSIStrategy(BaseStrategy):
    """
    Momentum Strategy with RSI Divergence

    Buy when:
    - RSI crosses above 50 from below
    - Price making higher lows
    - EMA 9 > EMA 21

    Sell when:
    - RSI crosses below 50 from above OR
    - RSI > 75
    """

    def __init__(self):
        super().__init__(name="MomentumRSI")

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['rsi'] = rsi(df['close'], 14)
        df['ema_9'] = ema(df['close'], 9)
        df['ema_21'] = ema(df['close'], 21)

        # Higher lows detection
        df['low_5'] = df['low'].rolling(5).min()
        df['higher_lows'] = df['low_5'] > df['low_5'].shift(5)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy: RSI crosses 50 + EMA alignment + higher lows
        rsi_cross_up = (df['rsi'] > 50) & (df['rsi'].shift(1) <= 50)
        ema_bullish = df['ema_9'] > df['ema_21']

        buy_cond = rsi_cross_up & ema_bullish & df['higher_lows']
        signals[buy_cond] = Signal.BUY

        # Sell: RSI crosses below 50 or overbought
        rsi_cross_down = (df['rsi'] < 50) & (df['rsi'].shift(1) >= 50)
        overbought = df['rsi'] > 75

        sell_cond = rsi_cross_down | overbought
        signals[sell_cond] = Signal.SELL

        return signals


class AdaptiveStrategy(BaseStrategy):
    """
    Adaptive Strategy that switches between trend and mean reversion

    In trending market (ADX > 25): Use trend following
    In ranging market (ADX < 20): Use mean reversion
    """

    def __init__(self):
        super().__init__(name="Adaptive")

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX indicator"""
        high, low, close = df['high'], df['low'], df['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = atr(high, low, close, 1)  # True Range

        plus_di = 100 * (plus_dm.ewm(span=period).mean() / tr.ewm(span=period).mean())
        minus_di = 100 * (minus_dm.ewm(span=period).mean() / tr.ewm(span=period).mean())

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period).mean()

        return adx

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        # Calculate indicators
        df['adx'] = self._calculate_adx(df)
        df['sma_20'] = sma(df['close'], 20)
        df['sma_50'] = sma(df['close'], 50)
        df['rsi'] = rsi(df['close'], 14)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = bollinger_bands(df['close'])

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Trending market: Trend following
        trending = df['adx'] > 25

        trend_buy = (
            trending &
            (df['sma_20'] > df['sma_50']) &
            (df['sma_20'].shift(1) <= df['sma_50'].shift(1)) &
            (df['rsi'] < 70)
        )

        trend_sell = (
            trending &
            (df['sma_20'] < df['sma_50']) &
            (df['sma_20'].shift(1) >= df['sma_50'].shift(1))
        )

        # Ranging market: Mean reversion
        ranging = df['adx'] < 20

        range_buy = (
            ranging &
            (df['close'] < df['bb_lower']) &
            (df['rsi'] < 35) &
            (df['close'] > df['open'])
        )

        range_sell = (
            ranging &
            ((df['close'] > df['bb_upper']) | (df['rsi'] > 65))
        )

        signals[trend_buy | range_buy] = Signal.BUY
        signals[trend_sell | range_sell] = Signal.SELL

        return signals


class SwingTradingStrategy(BaseStrategy):
    """
    Swing Trading Strategy for multi-day holds

    Buy when:
    - Weekly trend is up (price > SMA 50)
    - Daily pullback to support (near SMA 20)
    - RSI between 40-60 (not extreme)
    - Bullish engulfing or hammer pattern

    Sell when:
    - Target reached (2x ATR) OR
    - Stop loss hit (1.5x ATR) OR
    - Trend reversal
    """

    def __init__(self):
        super().__init__(name="SwingTrading")

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['sma_20'] = sma(df['close'], 20)
        df['sma_50'] = sma(df['close'], 50)
        df['rsi'] = rsi(df['close'], 14)
        df['atr'] = atr(df['high'], df['low'], df['close'], 14)

        # Detect bullish patterns
        df['body'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
        df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']

        # Bullish engulfing
        bullish_engulfing = (
            (df['close'] > df['open']) &
            (df['close'].shift(1) < df['open'].shift(1)) &
            (df['close'] > df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1))
        )

        # Hammer
        hammer = (
            (df['lower_wick'] > df['body'] * 2) &
            (df['upper_wick'] < df['body'] * 0.5) &
            (df['close'] > df['open'])
        )

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy conditions
        uptrend = df['close'] > df['sma_50']
        pullback = (df['close'] < df['sma_20'] * 1.02) & (df['close'] > df['sma_20'] * 0.98)
        rsi_ok = (df['rsi'] > 35) & (df['rsi'] < 65)
        pattern = bullish_engulfing | hammer

        buy_cond = uptrend & pullback & rsi_ok & pattern
        signals[buy_cond] = Signal.BUY

        # Sell conditions
        downtrend = df['close'] < df['sma_50']
        overbought = df['rsi'] > 70

        sell_cond = downtrend | overbought
        signals[sell_cond] = Signal.SELL

        return signals


def get_improved_strategies() -> Dict[str, BaseStrategy]:
    """Get all improved strategies"""
    return {
        'trend_following': TrendFollowingStrategy(),
        'mean_reversion': MeanReversionStrategy(),
        'breakout': BreakoutStrategy(),
        'momentum_rsi': MomentumRSIStrategy(),
        'adaptive': AdaptiveStrategy(),
        'swing_trading': SwingTradingStrategy(),
        # Optimized simple strategies
        'mean_reversion_tight': MeanReversionStrategy(20, 2.5, 14, 25, 75),
        'breakout_fast': BreakoutStrategy(15, 7, 1.3),
    }


def run_optimization(df: pd.DataFrame, verbose: bool = True) -> Dict[str, OptimizationResult]:
    """
    Run full optimization on all strategies

    Args:
        df: Historical data
        verbose: Print progress

    Returns:
        Dict of optimization results
    """
    optimizer = StrategyOptimizer(df)
    results = {}

    if verbose:
        print("\nOptimizing SMA parameters...")
    results['sma'] = optimizer.optimize_sma(
        short_range=range(5, 25, 3),
        long_range=range(20, 80, 5)
    )
    if verbose:
        print(f"  Best SMA: short={results['sma'].best_params['short']}, "
              f"long={results['sma'].best_params['long']} -> {results['sma'].best_return:.2f}%")

    if verbose:
        print("\nOptimizing RSI parameters...")
    results['rsi'] = optimizer.optimize_rsi(
        period_range=range(7, 18, 2),
        oversold_range=range(20, 40, 5),
        overbought_range=range(60, 80, 5)
    )
    if verbose:
        print(f"  Best RSI: period={results['rsi'].best_params['period']}, "
              f"oversold={results['rsi'].best_params['oversold']}, "
              f"overbought={results['rsi'].best_params['overbought']} -> {results['rsi'].best_return:.2f}%")

    # Test improved strategies with SL/TP optimization
    improved = get_improved_strategies()

    for name, strategy in improved.items():
        if verbose:
            print(f"\nOptimizing {name} with SL/TP...")
        results[name] = optimizer.optimize_with_sl_tp(
            strategy,
            sl_range=[0.02, 0.03, 0.04, 0.05, 0.07],
            tp_range=[0.04, 0.06, 0.08, 0.10, 0.15]
        )
        if verbose:
            print(f"  Best {name}: SL={results[name].best_params['stop_loss']:.1%}, "
                  f"TP={results[name].best_params['take_profit']:.1%} -> {results[name].best_return:.2f}%")

    return results


if __name__ == "__main__":
    from .data_loader import generate_sample_data

    print("Generating 4 years of sample data...")
    df = generate_sample_data(days=365 * 4)

    print(f"Data: {len(df)} candles, {df.index.min()} to {df.index.max()}")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    results = run_optimization(df)

    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)

    sorted_results = sorted(results.items(), key=lambda x: x[1].best_return, reverse=True)

    for name, result in sorted_results:
        print(f"\n{result.strategy_name}:")
        print(f"  Return: {result.best_return:.2f}%")
        print(f"  Sharpe: {result.best_sharpe:.2f}")
        print(f"  Params: {result.best_params}")
