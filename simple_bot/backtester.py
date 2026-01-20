"""
Backtesting Engine Module
Simulates trading strategies on historical data
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .strategies import BaseStrategy, Signal


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    size: float = 1.0
    side: str = "long"  # "long" or "short"
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "open"  # "open" or "closed"


@dataclass
class BacktestResult:
    """Results of a backtest"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_percent: float
    annual_return: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    avg_trade_duration: float  # in hours
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: List[Trade] = field(default_factory=list)
    buy_hold_return: float = 0.0


class Backtester:
    """
    Backtesting engine for trading strategies
    """

    def __init__(self, initial_capital: float = 10000.0,
                 commission: float = 0.001,  # 0.1% per trade
                 slippage: float = 0.0005,  # 0.05% slippage
                 position_size: float = 1.0,  # Full position
                 stop_loss: Optional[float] = None,  # e.g., 0.05 for 5%
                 take_profit: Optional[float] = None,  # e.g., 0.10 for 10%
                 trailing_stop: Optional[float] = None,  # e.g., 0.03 for 3%
                 use_atr_stops: bool = False,  # Use ATR-based stops
                 atr_multiplier: float = 2.0):  # ATR multiplier for stops
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital
            commission: Trading commission (0.001 = 0.1%)
            slippage: Price slippage (0.0005 = 0.05%)
            position_size: Position size as fraction of capital (1.0 = 100%)
            stop_loss: Stop loss percentage (optional)
            take_profit: Take profit percentage (optional)
            trailing_stop: Trailing stop percentage (optional)
            use_atr_stops: Use ATR-based dynamic stops
            atr_multiplier: Multiplier for ATR stops
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size = position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        self.use_atr_stops = use_atr_stops
        self.atr_multiplier = atr_multiplier

    def run(self, df: pd.DataFrame, strategy: BaseStrategy,
            symbol: str = "UNKNOWN") -> BacktestResult:
        """
        Run backtest

        Args:
            df: DataFrame with OHLCV data
            strategy: Trading strategy to test
            symbol: Symbol name for reporting

        Returns:
            BacktestResult with performance metrics
        """
        # Generate signals
        signals = strategy.generate_signals(df)

        # Initialize tracking variables
        capital = self.initial_capital
        position = 0.0
        entry_price = 0.0
        entry_time = None
        highest_price = 0.0  # For trailing stop
        trailing_stop_price = 0.0

        trades: List[Trade] = []
        equity_curve = []

        # Track equity at each timestep
        for i, (timestamp, row) in enumerate(df.iterrows()):
            signal = signals.iloc[i] if i < len(signals) else Signal.HOLD
            current_price = row['close']

            # Calculate current equity
            if position > 0:
                unrealized_pnl = position * (current_price - entry_price) - \
                                 (position * current_price * self.commission)
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital

            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'price': current_price
            })

            # Check stop loss, trailing stop, and take profit if in position
            if position > 0 and entry_price > 0:
                price_change = (current_price - entry_price) / entry_price

                # Update trailing stop
                if self.trailing_stop:
                    if current_price > highest_price:
                        highest_price = current_price
                        trailing_stop_price = highest_price * (1 - self.trailing_stop)

                    # Trailing stop hit
                    if current_price <= trailing_stop_price and trailing_stop_price > 0:
                        exit_price = trailing_stop_price * (1 - self.slippage)
                        pnl = position * (exit_price - entry_price) - \
                              (position * exit_price * self.commission)
                        capital += pnl + (position * entry_price)

                        trades[-1].exit_time = timestamp
                        trades[-1].exit_price = exit_price
                        trades[-1].pnl = pnl
                        trades[-1].pnl_percent = (exit_price - entry_price) / entry_price * 100
                        trades[-1].status = "closed"

                        position = 0.0
                        entry_price = 0.0
                        entry_time = None
                        highest_price = 0.0
                        trailing_stop_price = 0.0
                        continue

                # Fixed stop loss hit
                if self.stop_loss and price_change <= -self.stop_loss:
                    exit_price = entry_price * (1 - self.stop_loss) * (1 - self.slippage)
                    pnl = position * (exit_price - entry_price) - \
                          (position * exit_price * self.commission)
                    capital += pnl + (position * entry_price)

                    trades[-1].exit_time = timestamp
                    trades[-1].exit_price = exit_price
                    trades[-1].pnl = pnl
                    trades[-1].pnl_percent = (exit_price - entry_price) / entry_price * 100
                    trades[-1].status = "closed"

                    position = 0.0
                    entry_price = 0.0
                    entry_time = None
                    highest_price = 0.0
                    trailing_stop_price = 0.0
                    continue

                # Take profit hit
                if self.take_profit and price_change >= self.take_profit:
                    exit_price = entry_price * (1 + self.take_profit) * (1 - self.slippage)
                    pnl = position * (exit_price - entry_price) - \
                          (position * exit_price * self.commission)
                    capital += pnl + (position * entry_price)

                    trades[-1].exit_time = timestamp
                    trades[-1].exit_price = exit_price
                    trades[-1].pnl = pnl
                    trades[-1].pnl_percent = (exit_price - entry_price) / entry_price * 100
                    trades[-1].status = "closed"

                    position = 0.0
                    entry_price = 0.0
                    entry_time = None
                    highest_price = 0.0
                    trailing_stop_price = 0.0
                    continue

            # Process signals
            if signal == Signal.BUY and position == 0:
                # Open long position
                available_capital = capital * self.position_size
                entry_price = current_price * (1 + self.slippage)
                position = (available_capital / entry_price) * (1 - self.commission)
                capital -= available_capital
                entry_time = timestamp
                highest_price = entry_price  # Initialize for trailing stop
                trailing_stop_price = entry_price * (1 - (self.trailing_stop or 1.0))

                trades.append(Trade(
                    entry_time=timestamp,
                    entry_price=entry_price,
                    size=position,
                    side="long"
                ))

            elif signal == Signal.SELL and position > 0:
                # Close long position
                exit_price = current_price * (1 - self.slippage)
                pnl = position * (exit_price - entry_price) - \
                      (position * exit_price * self.commission)
                capital += pnl + (position * entry_price)

                trades[-1].exit_time = timestamp
                trades[-1].exit_price = exit_price
                trades[-1].pnl = pnl
                trades[-1].pnl_percent = (exit_price - entry_price) / entry_price * 100
                trades[-1].status = "closed"

                position = 0.0
                entry_price = 0.0
                entry_time = None

        # Close any remaining position at the end
        if position > 0:
            exit_price = df.iloc[-1]['close'] * (1 - self.slippage)
            pnl = position * (exit_price - entry_price) - \
                  (position * exit_price * self.commission)
            capital += pnl + (position * entry_price)

            trades[-1].exit_time = df.index[-1]
            trades[-1].exit_price = exit_price
            trades[-1].pnl = pnl
            trades[-1].pnl_percent = (exit_price - entry_price) / entry_price * 100
            trades[-1].status = "closed"

        # Build equity curve DataFrame
        equity_df = pd.DataFrame(equity_curve)
        equity_df.set_index('timestamp', inplace=True)

        # Calculate metrics
        result = self._calculate_metrics(
            strategy_name=strategy.name,
            symbol=symbol,
            df=df,
            equity_df=equity_df,
            trades=trades,
            final_capital=capital
        )

        return result

    def _calculate_metrics(self, strategy_name: str, symbol: str,
                           df: pd.DataFrame, equity_df: pd.DataFrame,
                           trades: List[Trade], final_capital: float) -> BacktestResult:
        """
        Calculate performance metrics

        Args:
            strategy_name: Name of strategy
            symbol: Symbol traded
            df: Original OHLCV data
            equity_df: Equity curve DataFrame
            trades: List of trades
            final_capital: Final capital

        Returns:
            BacktestResult with all metrics
        """
        # Basic metrics
        total_return = final_capital - self.initial_capital
        total_return_percent = (total_return / self.initial_capital) * 100

        # Time period
        start_date = df.index[0]
        end_date = df.index[-1]
        years = (end_date - start_date).days / 365.25

        # Annualized return
        if years > 0:
            annual_return = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100
        else:
            annual_return = 0.0

        # Drawdown calculation
        equity = equity_df['equity']
        running_max = equity.expanding().max()
        drawdown = equity - running_max
        drawdown_percent = (drawdown / running_max) * 100
        max_drawdown = drawdown.min()
        max_drawdown_percent = drawdown_percent.min()

        # Returns for Sharpe/Sortino
        returns = equity.pct_change().dropna()

        # Sharpe Ratio (assuming risk-free rate of 2% annually)
        risk_free_rate = 0.02
        excess_returns = returns - (risk_free_rate / 365 / 24)  # Hourly data assumed
        if returns.std() > 0:
            sharpe_ratio = np.sqrt(365 * 24) * excess_returns.mean() / returns.std()
        else:
            sharpe_ratio = 0.0

        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = np.sqrt(365 * 24) * excess_returns.mean() / downside_returns.std()
        else:
            sortino_ratio = 0.0

        # Trade statistics
        closed_trades = [t for t in trades if t.status == "closed"]
        total_trades = len(closed_trades)

        if total_trades > 0:
            winning_trades = [t for t in closed_trades if t.pnl > 0]
            losing_trades = [t for t in closed_trades if t.pnl <= 0]

            win_rate = len(winning_trades) / total_trades * 100

            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0

            total_wins = sum([t.pnl for t in winning_trades])
            total_losses = abs(sum([t.pnl for t in losing_trades]))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

            # Average trade duration
            durations = []
            for t in closed_trades:
                if t.exit_time and t.entry_time:
                    duration = (t.exit_time - t.entry_time).total_seconds() / 3600
                    durations.append(duration)
            avg_trade_duration = np.mean(durations) if durations else 0.0

        else:
            win_rate = 0.0
            winning_trades = []
            losing_trades = []
            avg_win = 0.0
            avg_loss = 0.0
            profit_factor = 0.0
            avg_trade_duration = 0.0

        # Buy and hold comparison
        buy_hold_return = ((df.iloc[-1]['close'] / df.iloc[0]['close']) - 1) * 100

        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_percent=total_return_percent,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_trade_duration=avg_trade_duration,
            equity_curve=equity,
            trades=trades,
            buy_hold_return=buy_hold_return
        )


def print_results(result: BacktestResult):
    """
    Print backtest results in a formatted way

    Args:
        result: BacktestResult to print
    """
    print("\n" + "=" * 60)
    print(f"BACKTEST RESULTS: {result.strategy_name}")
    print("=" * 60)

    print(f"\nSymbol: {result.symbol}")
    print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")

    print("\n--- RETURNS ---")
    print(f"Initial Capital:     ${result.initial_capital:,.2f}")
    print(f"Final Capital:       ${result.final_capital:,.2f}")
    print(f"Total Return:        ${result.total_return:,.2f} ({result.total_return_percent:.2f}%)")
    print(f"Annual Return:       {result.annual_return:.2f}%")
    print(f"Buy & Hold Return:   {result.buy_hold_return:.2f}%")

    print("\n--- RISK METRICS ---")
    print(f"Max Drawdown:        ${result.max_drawdown:,.2f} ({result.max_drawdown_percent:.2f}%)")
    print(f"Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:       {result.sortino_ratio:.2f}")

    print("\n--- TRADE STATISTICS ---")
    print(f"Total Trades:        {result.total_trades}")
    print(f"Winning Trades:      {result.winning_trades}")
    print(f"Losing Trades:       {result.losing_trades}")
    print(f"Win Rate:            {result.win_rate:.2f}%")
    print(f"Avg Winning Trade:   ${result.avg_win:,.2f}")
    print(f"Avg Losing Trade:    ${result.avg_loss:,.2f}")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print(f"Avg Trade Duration:  {result.avg_trade_duration:.1f} hours")

    print("=" * 60)


def compare_strategies(results: List[BacktestResult]) -> pd.DataFrame:
    """
    Compare multiple strategy results

    Args:
        results: List of BacktestResult objects

    Returns:
        DataFrame with comparison
    """
    data = []
    for r in results:
        data.append({
            'Strategy': r.strategy_name,
            'Total Return %': round(r.total_return_percent, 2),
            'Annual Return %': round(r.annual_return, 2),
            'Max Drawdown %': round(r.max_drawdown_percent, 2),
            'Sharpe': round(r.sharpe_ratio, 2),
            'Sortino': round(r.sortino_ratio, 2),
            'Win Rate %': round(r.win_rate, 2),
            'Trades': r.total_trades,
            'Profit Factor': round(r.profit_factor, 2),
            'Buy&Hold %': round(r.buy_hold_return, 2)
        })

    df = pd.DataFrame(data)
    df = df.sort_values('Total Return %', ascending=False)

    return df


if __name__ == "__main__":
    # Test backtester with sample data
    from .strategies import SMAStrategy, RSIStrategy, MACDStrategy
    from .data_loader import generate_sample_data

    # Generate 4 years of sample data
    print("Generating 4 years of sample data...")
    df = generate_sample_data(days=365 * 4)

    # Initialize backtester
    backtester = Backtester(
        initial_capital=10000,
        commission=0.001,
        slippage=0.0005,
        stop_loss=0.05,
        take_profit=0.10
    )

    # Test strategies
    strategies = [
        SMAStrategy(20, 50),
        RSIStrategy(14, 30, 70),
        MACDStrategy()
    ]

    results = []
    for strategy in strategies:
        print(f"\nRunning backtest for {strategy.name}...")
        result = backtester.run(df, strategy, symbol="TEST")
        results.append(result)
        print_results(result)

    # Compare strategies
    print("\n\nSTRATEGY COMPARISON:")
    comparison = compare_strategies(results)
    print(comparison.to_string(index=False))
