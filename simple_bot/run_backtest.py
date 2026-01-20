#!/usr/bin/env python3
"""
Main Backtest Script
Run comprehensive backtests on 4 years of historical data
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_bot.data_loader import DataLoader, generate_sample_data
from simple_bot.strategies import get_all_strategies
from simple_bot.backtester import Backtester, print_results, compare_strategies
from simple_bot.visualization import (
    plot_equity_curve, plot_trades_on_price, plot_indicators,
    plot_strategy_comparison, plot_monthly_returns, generate_html_report,
    print_trade_log
)


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file"""
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def run_backtest(symbol: str = 'BTCUSDT',
                 interval: str = '1h',
                 years: int = 4,
                 strategies_to_test: list = None,
                 initial_capital: float = 10000,
                 commission: float = 0.001,
                 slippage: float = 0.0005,
                 stop_loss: float = None,
                 take_profit: float = None,
                 use_sample_data: bool = False,
                 show_plots: bool = True,
                 save_report: bool = True):
    """
    Run comprehensive backtest

    Args:
        symbol: Trading pair symbol
        interval: Candle interval
        years: Number of years of data
        strategies_to_test: List of strategy names to test
        initial_capital: Starting capital
        commission: Trading commission
        slippage: Slippage percentage
        stop_loss: Stop loss percentage (optional)
        take_profit: Take profit percentage (optional)
        use_sample_data: Use generated sample data instead of API
        show_plots: Show matplotlib plots
        save_report: Save HTML report
    """
    print("=" * 70)
    print("CRYPTOCURRENCY TRADING BOT - BACKTEST")
    print("=" * 70)
    print(f"\nSymbol: {symbol}")
    print(f"Interval: {interval}")
    print(f"Period: {years} years")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Commission: {commission * 100:.2f}%")
    print(f"Slippage: {slippage * 100:.3f}%")

    if stop_loss:
        print(f"Stop Loss: {stop_loss * 100:.1f}%")
    if take_profit:
        print(f"Take Profit: {take_profit * 100:.1f}%")

    # Load data
    print("\n" + "-" * 70)
    print("Loading historical data...")
    print("-" * 70)

    if use_sample_data:
        print("Using generated sample data...")
        df = generate_sample_data(days=years * 365, interval_hours=1 if interval == '1h' else 4)
    else:
        loader = DataLoader(data_dir="data")
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')

        try:
            df = loader.get_data(
                symbol=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                use_cache=True
            )
        except Exception as e:
            print(f"Error fetching data from Binance: {e}")
            print("Falling back to sample data...")
            df = generate_sample_data(days=years * 365, interval_hours=1 if interval == '1h' else 4)

    print(f"\nData loaded: {len(df)} candles")
    print(f"Date range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
    print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    # Initialize backtester
    backtester = Backtester(
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
        stop_loss=stop_loss,
        take_profit=take_profit
    )

    # Get strategies to test
    all_strategies = get_all_strategies()

    if strategies_to_test:
        strategies = {name: all_strategies[name] for name in strategies_to_test
                      if name in all_strategies}
    else:
        strategies = all_strategies

    print(f"\nTesting {len(strategies)} strategies...")

    # Run backtests
    results = []
    print("\n" + "-" * 70)
    print("Running backtests...")
    print("-" * 70)

    for name, strategy in strategies.items():
        print(f"\n  Testing {strategy.name}...", end=" ")
        try:
            result = backtester.run(df, strategy, symbol=symbol)
            results.append(result)
            print(f"Done! Return: {result.total_return_percent:.2f}%")
        except Exception as e:
            print(f"Error: {e}")

    # Print results
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)

    for result in results:
        print_results(result)

    # Print comparison table
    print("\n" + "=" * 70)
    print("STRATEGY COMPARISON")
    print("=" * 70)
    comparison_df = compare_strategies(results)
    print(comparison_df.to_string(index=False))

    # Find best strategy
    best_result = max(results, key=lambda x: x.total_return_percent)
    print(f"\n*** Best Strategy: {best_result.strategy_name} with {best_result.total_return_percent:.2f}% return ***")

    # Generate visualizations
    if show_plots:
        try:
            print("\nGenerating plots...")

            # Plot indicators for the data
            plot_indicators(df.tail(500), save_path=f"plots/{symbol}_indicators.png")

            # Plot equity curves for top 3 strategies
            for result in sorted(results, key=lambda x: x.total_return_percent, reverse=True)[:3]:
                plot_equity_curve(result, save_path=f"plots/{result.strategy_name}_equity.png")

            # Plot strategy comparison
            plot_strategy_comparison(results, save_path=f"plots/{symbol}_comparison.png")

            # Plot monthly returns for best strategy
            plot_monthly_returns(best_result, save_path=f"plots/{best_result.strategy_name}_monthly.png")

            # Plot trades for best strategy
            plot_trades_on_price(
                df.tail(1000),
                [t for t in best_result.trades if t.entry_time >= df.index[-1000]],
                title=f"{best_result.strategy_name} - Trades (last 1000 candles)",
                save_path=f"plots/{best_result.strategy_name}_trades.png"
            )

        except Exception as e:
            print(f"Could not generate plots: {e}")
            print("Install matplotlib with: pip install matplotlib")

    # Generate HTML report
    if save_report:
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        generate_html_report(results, output_path=report_path)

    # Print trade log for best strategy
    print_trade_log(best_result.trades, limit=20)

    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run cryptocurrency trading backtest')

    parser.add_argument('--symbol', type=str, default='BTCUSDT',
                        help='Trading pair symbol (default: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h',
                        help='Candle interval (default: 1h)')
    parser.add_argument('--years', type=int, default=4,
                        help='Number of years of historical data (default: 4)')
    parser.add_argument('--capital', type=float, default=10000,
                        help='Initial capital (default: 10000)')
    parser.add_argument('--commission', type=float, default=0.001,
                        help='Commission per trade (default: 0.001 = 0.1%%)')
    parser.add_argument('--slippage', type=float, default=0.0005,
                        help='Slippage (default: 0.0005 = 0.05%%)')
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='Stop loss percentage (e.g., 0.05 for 5%%)')
    parser.add_argument('--take-profit', type=float, default=None,
                        help='Take profit percentage (e.g., 0.10 for 10%%)')
    parser.add_argument('--strategies', type=str, nargs='+', default=None,
                        help='Strategies to test (default: all)')
    parser.add_argument('--sample-data', action='store_true',
                        help='Use generated sample data instead of Binance API')
    parser.add_argument('--no-plots', action='store_true',
                        help='Disable plot generation')
    parser.add_argument('--no-report', action='store_true',
                        help='Disable HTML report generation')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config YAML file')

    args = parser.parse_args()

    # Load config if provided
    config = load_config(args.config)

    # Override with command line args
    symbol = args.symbol or config.get('backtest', {}).get('symbols', ['BTCUSDT'])[0]
    interval = args.interval or config.get('interval', '1h')
    years = args.years or config.get('backtest', {}).get('years', 4)
    capital = args.capital or config.get('initial_capital', 10000)
    commission = args.commission or config.get('backtest', {}).get('commission', 0.001)
    slippage = args.slippage or config.get('backtest', {}).get('slippage', 0.0005)
    strategies = args.strategies or config.get('backtest', {}).get('strategies', None)

    # Create output directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    # Run backtest
    run_backtest(
        symbol=symbol,
        interval=interval,
        years=years,
        strategies_to_test=strategies,
        initial_capital=capital,
        commission=commission,
        slippage=slippage,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        use_sample_data=args.sample_data,
        show_plots=not args.no_plots,
        save_report=not args.no_report
    )


if __name__ == "__main__":
    main()
