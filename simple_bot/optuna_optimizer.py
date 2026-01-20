"""
Optuna Optimizer for Sharpe Ratio Maximization
"""

import warnings
warnings.filterwarnings('ignore')

import optuna
from optuna.samplers import TPESampler
import pandas as pd
import numpy as np
from typing import Dict, Any, Callable
from dataclasses import dataclass

from .data_loader import generate_sample_data
from .strategies import (
    BaseStrategy, Signal, SMAStrategy, EMAStrategy, RSIStrategy,
    MACDStrategy, GoldenDeathCrossStrategy, HourlyTrendStrategy
)
from .indicators import sma, ema, rsi, macd, bollinger_bands, atr
from .backtester import Backtester, BacktestResult


# Global data cache
_data_cache = None


def get_data(days: int = 365 * 4) -> pd.DataFrame:
    """Get cached data"""
    global _data_cache
    if _data_cache is None:
        _data_cache = generate_sample_data(days=days, interval_hours=1)
    return _data_cache


class DynamicStrategy(BaseStrategy):
    """Dynamic strategy with configurable parameters"""

    def __init__(self, params: Dict[str, Any]):
        self.params = params
        name = f"Dynamic_{params.get('strategy_type', 'unknown')}"
        super().__init__(name=name)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()
        strategy_type = self.params.get('strategy_type', 'ma_cross')

        if strategy_type == 'ma_cross':
            return self._ma_cross_signals(df)
        elif strategy_type == 'rsi_ma':
            return self._rsi_ma_signals(df)
        elif strategy_type == 'trend_follow':
            return self._trend_follow_signals(df)
        elif strategy_type == 'mean_reversion':
            return self._mean_reversion_signals(df)
        else:
            return pd.Series(Signal.HOLD, index=df.index)

    def _ma_cross_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params.get('fast_period', 20)
        slow = self.params.get('slow_period', 50)
        ma_type = self.params.get('ma_type', 'sma')

        if ma_type == 'sma':
            df['fast'] = sma(df['close'], fast)
            df['slow'] = sma(df['close'], slow)
        else:
            df['fast'] = ema(df['close'], fast)
            df['slow'] = ema(df['close'], slow)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Golden cross
        buy = (df['fast'] > df['slow']) & (df['fast'].shift(1) <= df['slow'].shift(1))
        signals[buy] = Signal.BUY

        # Death cross
        sell = (df['fast'] < df['slow']) & (df['fast'].shift(1) >= df['slow'].shift(1))
        signals[sell] = Signal.SELL

        return signals

    def _rsi_ma_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi_period = self.params.get('rsi_period', 14)
        rsi_low = self.params.get('rsi_low', 30)
        rsi_high = self.params.get('rsi_high', 70)
        ma_period = self.params.get('trend_ma', 200)

        df['rsi'] = rsi(df['close'], rsi_period)
        df['trend_ma'] = sma(df['close'], ma_period)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy: RSI oversold + above trend
        buy = (
            (df['rsi'] < rsi_low) &
            (df['rsi'].shift(1) >= rsi_low) &
            (df['close'] > df['trend_ma'])
        )
        signals[buy] = Signal.BUY

        # Sell: RSI overbought or below trend
        sell = (df['rsi'] > rsi_high) | (df['close'] < df['trend_ma'] * 0.98)
        signals[sell] = Signal.SELL

        return signals

    def _trend_follow_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params.get('fast_period', 50)
        slow = self.params.get('slow_period', 200)
        filter_period = self.params.get('filter_period', 20)

        df['fast'] = sma(df['close'], fast)
        df['slow'] = sma(df['close'], slow)
        df['filter'] = ema(df['close'], filter_period)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy: Golden cross + price above fast MA + filter rising
        buy = (
            (df['fast'] > df['slow']) &
            (df['fast'].shift(1) <= df['slow'].shift(1)) &
            (df['close'] > df['fast']) &
            (df['filter'] > df['filter'].shift(3))
        )
        signals[buy] = Signal.BUY

        # Sell: Death cross
        sell = (df['fast'] < df['slow']) & (df['fast'].shift(1) >= df['slow'].shift(1))
        signals[sell] = Signal.SELL

        return signals

    def _mean_reversion_signals(self, df: pd.DataFrame) -> pd.Series:
        bb_period = self.params.get('bb_period', 20)
        bb_std = self.params.get('bb_std', 2.0)
        rsi_period = self.params.get('rsi_period', 14)

        df['bb_upper'], df['bb_mid'], df['bb_lower'] = bollinger_bands(
            df['close'], bb_period, bb_std
        )
        df['rsi'] = rsi(df['close'], rsi_period)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Buy: Price near lower BB + RSI oversold
        buy = (
            (df['close'] < df['bb_lower'] * 1.01) &
            (df['rsi'] < 35) &
            (df['close'] > df['open'])
        )
        signals[buy] = Signal.BUY

        # Sell: Price near upper BB or RSI overbought
        sell = (df['close'] > df['bb_upper'] * 0.99) | (df['rsi'] > 70)
        signals[sell] = Signal.SELL

        return signals


def objective(trial: optuna.Trial) -> float:
    """Optuna objective function to maximize Sharpe Ratio"""

    df = get_data()

    # Select strategy type
    strategy_type = trial.suggest_categorical(
        'strategy_type',
        ['ma_cross', 'rsi_ma', 'trend_follow']
    )

    params = {'strategy_type': strategy_type}

    if strategy_type == 'ma_cross':
        params['ma_type'] = trial.suggest_categorical('ma_type', ['sma', 'ema'])
        params['fast_period'] = trial.suggest_int('fast_period', 10, 100)
        params['slow_period'] = trial.suggest_int('slow_period', 50, 300)

        if params['fast_period'] >= params['slow_period']:
            return -100  # Invalid params

    elif strategy_type == 'rsi_ma':
        params['rsi_period'] = trial.suggest_int('rsi_period', 7, 21)
        params['rsi_low'] = trial.suggest_int('rsi_low', 20, 40)
        params['rsi_high'] = trial.suggest_int('rsi_high', 60, 80)
        params['trend_ma'] = trial.suggest_int('trend_ma', 100, 300)

    elif strategy_type == 'trend_follow':
        params['fast_period'] = trial.suggest_int('fast_period', 20, 80)
        params['slow_period'] = trial.suggest_int('slow_period', 100, 300)
        params['filter_period'] = trial.suggest_int('filter_period', 10, 50)

        if params['fast_period'] >= params['slow_period']:
            return -100

    # Risk management params
    trailing_stop = trial.suggest_float('trailing_stop', 0.02, 0.08)
    use_sl = trial.suggest_categorical('use_stop_loss', [True, False])
    use_tp = trial.suggest_categorical('use_take_profit', [True, False])

    stop_loss = trial.suggest_float('stop_loss', 0.02, 0.06) if use_sl else None
    take_profit = trial.suggest_float('take_profit', 0.05, 0.20) if use_tp else None

    # Create strategy and backtest
    strategy = DynamicStrategy(params)

    bt = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        trailing_stop=trailing_stop,
        stop_loss=stop_loss,
        take_profit=take_profit
    )

    result = bt.run(df, strategy, 'BTCUSDT')

    # Penalize too few trades
    if result.total_trades < 20:
        return -100

    # Penalize losses
    if result.total_return_percent < 0:
        return result.sharpe_ratio - 10

    # Maximize Sharpe, but also consider return
    score = result.sharpe_ratio + (result.total_return_percent / 500)

    # Store additional info
    trial.set_user_attr('return', result.total_return_percent)
    trial.set_user_attr('annual_return', result.annual_return)
    trial.set_user_attr('max_drawdown', result.max_drawdown_percent)
    trial.set_user_attr('win_rate', result.win_rate)
    trial.set_user_attr('trades', result.total_trades)
    trial.set_user_attr('profit_factor', result.profit_factor)

    return score


def run_optimization(n_trials: int = 200, show_progress: bool = True) -> optuna.Study:
    """
    Run Optuna optimization

    Args:
        n_trials: Number of optimization trials
        show_progress: Show progress bar

    Returns:
        Optuna study object
    """
    sampler = TPESampler(seed=42)

    study = optuna.create_study(
        direction='maximize',
        sampler=sampler,
        study_name='sharpe_optimization'
    )

    # Suppress optuna logging if not showing progress
    if not show_progress:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    study.optimize(
        objective,
        n_trials=n_trials,
        show_progress_bar=show_progress,
        n_jobs=1  # Single thread for reproducibility
    )

    return study


def print_results(study: optuna.Study):
    """Print optimization results"""
    print("\n" + "=" * 70)
    print("OPTUNA OPTIMIZATION RESULTS - SHARPE RATIO")
    print("=" * 70)

    best = study.best_trial

    print(f"\nBest Score: {best.value:.4f}")
    print(f"\n--- BEST PARAMETERS ---")

    for key, value in best.params.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    print(f"\n--- PERFORMANCE ---")
    print(f"  Total Return:   {best.user_attrs['return']:.2f}%")
    print(f"  Annual Return:  {best.user_attrs['annual_return']:.2f}%")
    print(f"  Sharpe Ratio:   {best.value:.2f}")
    print(f"  Max Drawdown:   {best.user_attrs['max_drawdown']:.2f}%")
    print(f"  Win Rate:       {best.user_attrs['win_rate']:.1f}%")
    print(f"  Profit Factor:  {best.user_attrs['profit_factor']:.2f}")
    print(f"  Total Trades:   {best.user_attrs['trades']}")

    # Calculate monthly return
    total_return = best.user_attrs['return']
    monthly = ((1 + total_return/100) ** (1/48) - 1) * 100
    print(f"  Monthly Return: {monthly:.2f}%")

    # Top 5 trials
    print(f"\n--- TOP 5 TRIALS ---")
    trials = sorted(study.trials, key=lambda t: t.value if t.value else -999, reverse=True)

    for i, trial in enumerate(trials[:5]):
        if trial.value and trial.value > -50:
            strat = trial.params.get('strategy_type', 'unknown')
            ret = trial.user_attrs.get('return', 0)
            sharpe = trial.value
            print(f"  {i+1}. {strat}: Sharpe={sharpe:.2f}, Return={ret:.1f}%")

    return best


def create_best_strategy(study: optuna.Study) -> tuple:
    """Create strategy from best trial params"""
    best = study.best_trial

    params = {k: v for k, v in best.params.items()
              if k not in ['trailing_stop', 'stop_loss', 'take_profit',
                          'use_stop_loss', 'use_take_profit']}

    strategy = DynamicStrategy(params)

    risk_params = {
        'trailing_stop': best.params.get('trailing_stop'),
        'stop_loss': best.params.get('stop_loss') if best.params.get('use_stop_loss') else None,
        'take_profit': best.params.get('take_profit') if best.params.get('use_take_profit') else None,
    }

    return strategy, risk_params


if __name__ == "__main__":
    import sys

    n_trials = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    print(f"Running Optuna optimization with {n_trials} trials...")
    print("Optimizing for maximum Sharpe Ratio on 1H timeframe")
    print()

    study = run_optimization(n_trials=n_trials, show_progress=True)
    best = print_results(study)

    # Verify best result
    print("\n--- VERIFICATION ---")
    strategy, risk_params = create_best_strategy(study)

    df = get_data()
    bt = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        **risk_params
    )
    result = bt.run(df, strategy, 'BTCUSDT')

    print(f"Verified Return: {result.total_return_percent:.2f}%")
    print(f"Verified Sharpe: {result.sharpe_ratio:.2f}")
