"""
Visualization Module
Charts and reports for trading analysis
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from datetime import datetime
import os

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .backtester import BacktestResult, Trade
from .indicators import sma, ema, rsi, macd, bollinger_bands


def check_matplotlib():
    """Check if matplotlib is available"""
    if not MATPLOTLIB_AVAILABLE:
        print("Warning: matplotlib not available. Install with: pip install matplotlib")
        return False
    return True


def plot_equity_curve(result: BacktestResult, save_path: Optional[str] = None):
    """
    Plot equity curve from backtest result

    Args:
        result: BacktestResult object
        save_path: Optional path to save figure
    """
    if not check_matplotlib():
        return

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Equity curve
    ax1 = axes[0]
    ax1.plot(result.equity_curve.index, result.equity_curve.values, 'b-', linewidth=1.5, label='Strategy Equity')

    # Add horizontal line for initial capital
    ax1.axhline(y=result.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')

    # Highlight drawdown periods
    equity = result.equity_curve
    running_max = equity.expanding().max()
    in_drawdown = equity < running_max

    # Find drawdown periods
    drawdown_starts = []
    drawdown_ends = []
    in_dd = False

    for i, (timestamp, is_dd) in enumerate(zip(equity.index, in_drawdown)):
        if is_dd and not in_dd:
            drawdown_starts.append(timestamp)
            in_dd = True
        elif not is_dd and in_dd:
            drawdown_ends.append(timestamp)
            in_dd = False

    if in_dd and drawdown_starts:
        drawdown_ends.append(equity.index[-1])

    for start, end in zip(drawdown_starts, drawdown_ends):
        ax1.axvspan(start, end, alpha=0.2, color='red')

    ax1.set_title(f'{result.strategy_name} - Equity Curve\n'
                  f'Total Return: {result.total_return_percent:.2f}% | '
                  f'Max Drawdown: {result.max_drawdown_percent:.2f}% | '
                  f'Sharpe: {result.sharpe_ratio:.2f}',
                  fontsize=12)
    ax1.set_ylabel('Equity ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # Drawdown plot
    ax2 = axes[1]
    drawdown = (equity - running_max) / running_max * 100
    ax2.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
    ax2.plot(drawdown.index, drawdown.values, 'r-', linewidth=1)

    ax2.set_ylabel('Drawdown (%)')
    ax2.set_xlabel('Date')
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved equity curve to {save_path}")

    plt.show()


def plot_trades_on_price(df: pd.DataFrame, trades: List[Trade],
                         title: str = "Price with Trades",
                         save_path: Optional[str] = None):
    """
    Plot price chart with trade markers

    Args:
        df: OHLCV DataFrame
        trades: List of Trade objects
        title: Chart title
        save_path: Optional path to save figure
    """
    if not check_matplotlib():
        return

    fig, ax = plt.subplots(figsize=(16, 8))

    # Plot price
    ax.plot(df.index, df['close'], 'b-', linewidth=1, alpha=0.7, label='Close Price')

    # Add moving averages
    df['sma_20'] = sma(df['close'], 20)
    df['sma_50'] = sma(df['close'], 50)

    ax.plot(df.index, df['sma_20'], 'orange', linewidth=1, alpha=0.7, label='SMA 20')
    ax.plot(df.index, df['sma_50'], 'purple', linewidth=1, alpha=0.7, label='SMA 50')

    # Plot trades
    for trade in trades:
        if trade.entry_time and trade.entry_price:
            # Entry point
            ax.scatter(trade.entry_time, trade.entry_price, marker='^', color='green',
                       s=100, zorder=5, label='_nolegend_')

        if trade.exit_time and trade.exit_price:
            # Exit point
            color = 'lime' if trade.pnl > 0 else 'red'
            ax.scatter(trade.exit_time, trade.exit_price, marker='v', color=color,
                       s=100, zorder=5, label='_nolegend_')

            # Connect entry and exit
            ax.plot([trade.entry_time, trade.exit_time],
                    [trade.entry_price, trade.exit_price],
                    color=color, linestyle='--', alpha=0.5, linewidth=1)

    ax.set_title(title, fontsize=14)
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved trades chart to {save_path}")

    plt.show()


def plot_indicators(df: pd.DataFrame, save_path: Optional[str] = None):
    """
    Plot price with common indicators

    Args:
        df: OHLCV DataFrame
        save_path: Optional path to save figure
    """
    if not check_matplotlib():
        return

    fig, axes = plt.subplots(4, 1, figsize=(16, 14), gridspec_kw={'height_ratios': [3, 1, 1, 1]})

    # Prepare data
    df = df.copy()
    df['sma_20'] = sma(df['close'], 20)
    df['sma_50'] = sma(df['close'], 50)
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = bollinger_bands(df['close'])
    df['rsi'] = rsi(df['close'])
    df['macd'], df['signal'], df['hist'] = macd(df['close'])

    # Price chart with Bollinger Bands
    ax1 = axes[0]
    ax1.plot(df.index, df['close'], 'b-', linewidth=1, label='Close')
    ax1.plot(df.index, df['sma_20'], 'orange', linewidth=1, alpha=0.7, label='SMA 20')
    ax1.plot(df.index, df['sma_50'], 'purple', linewidth=1, alpha=0.7, label='SMA 50')
    ax1.fill_between(df.index, df['bb_upper'], df['bb_lower'], alpha=0.2, color='gray', label='BB')
    ax1.set_title('Price with Bollinger Bands & Moving Averages', fontsize=12)
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2 = axes[1]
    ax2.plot(df.index, df['rsi'], 'purple', linewidth=1)
    ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
    ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
    ax2.fill_between(df.index, 70, df['rsi'], where=(df['rsi'] >= 70), alpha=0.3, color='red')
    ax2.fill_between(df.index, 30, df['rsi'], where=(df['rsi'] <= 30), alpha=0.3, color='green')
    ax2.set_title('RSI (14)', fontsize=12)
    ax2.set_ylabel('RSI')
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)

    # MACD
    ax3 = axes[2]
    ax3.plot(df.index, df['macd'], 'b-', linewidth=1, label='MACD')
    ax3.plot(df.index, df['signal'], 'r-', linewidth=1, label='Signal')
    colors = ['green' if x >= 0 else 'red' for x in df['hist']]
    ax3.bar(df.index, df['hist'], color=colors, alpha=0.5, width=0.8)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_title('MACD', fontsize=12)
    ax3.set_ylabel('MACD')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)

    # Volume
    ax4 = axes[3]
    colors = ['green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
              for i in range(len(df))]
    ax4.bar(df.index, df['volume'], color=colors, alpha=0.5)
    ax4.set_title('Volume', fontsize=12)
    ax4.set_ylabel('Volume')
    ax4.set_xlabel('Date')
    ax4.grid(True, alpha=0.3)

    # Format x-axes
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved indicators chart to {save_path}")

    plt.show()


def plot_strategy_comparison(results: List[BacktestResult], save_path: Optional[str] = None):
    """
    Plot comparison of multiple strategies

    Args:
        results: List of BacktestResult objects
        save_path: Optional path to save figure
    """
    if not check_matplotlib():
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Equity curves comparison
    ax1 = axes[0, 0]
    for result in results:
        normalized = result.equity_curve / result.initial_capital * 100
        ax1.plot(result.equity_curve.index, normalized.values, linewidth=1.5, label=result.strategy_name)

    ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title('Normalized Equity Curves (%)', fontsize=12)
    ax1.set_ylabel('Equity (%)')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Returns comparison (bar chart)
    ax2 = axes[0, 1]
    names = [r.strategy_name for r in results]
    returns = [r.total_return_percent for r in results]
    buy_hold = results[0].buy_hold_return if results else 0

    colors = ['green' if r > 0 else 'red' for r in returns]
    bars = ax2.bar(range(len(names)), returns, color=colors, alpha=0.7)
    ax2.axhline(y=buy_hold, color='blue', linestyle='--', linewidth=2, label=f'Buy & Hold: {buy_hold:.1f}%')

    ax2.set_title('Total Return by Strategy', fontsize=12)
    ax2.set_ylabel('Return (%)')
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Risk metrics comparison
    ax3 = axes[1, 0]
    x = np.arange(len(names))
    width = 0.35

    sharpe_ratios = [r.sharpe_ratio for r in results]
    sortino_ratios = [r.sortino_ratio for r in results]

    ax3.bar(x - width / 2, sharpe_ratios, width, label='Sharpe Ratio', alpha=0.7)
    ax3.bar(x + width / 2, sortino_ratios, width, label='Sortino Ratio', alpha=0.7)

    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_title('Risk-Adjusted Returns', fontsize=12)
    ax3.set_ylabel('Ratio')
    ax3.set_xticks(x)
    ax3.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # Win rate and trade count
    ax4 = axes[1, 1]

    win_rates = [r.win_rate for r in results]
    trade_counts = [r.total_trades for r in results]

    ax4_twin = ax4.twinx()

    bars1 = ax4.bar(x - width / 2, win_rates, width, label='Win Rate (%)', color='green', alpha=0.7)
    bars2 = ax4_twin.bar(x + width / 2, trade_counts, width, label='Total Trades', color='blue', alpha=0.7)

    ax4.set_title('Win Rate & Trade Count', fontsize=12)
    ax4.set_ylabel('Win Rate (%)', color='green')
    ax4_twin.set_ylabel('Total Trades', color='blue')
    ax4.set_xticks(x)
    ax4.set_xticklabels(names, rotation=45, ha='right', fontsize=8)

    ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax4.grid(True, alpha=0.3, axis='y')

    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved strategy comparison to {save_path}")

    plt.show()


def plot_monthly_returns(result: BacktestResult, save_path: Optional[str] = None):
    """
    Plot monthly returns heatmap

    Args:
        result: BacktestResult object
        save_path: Optional path to save figure
    """
    if not check_matplotlib():
        return

    # Calculate monthly returns
    equity = result.equity_curve
    monthly_returns = equity.resample('ME').last().pct_change() * 100
    monthly_returns = monthly_returns.dropna()

    # Create pivot table for heatmap
    monthly_returns_df = pd.DataFrame({
        'Year': monthly_returns.index.year,
        'Month': monthly_returns.index.month,
        'Return': monthly_returns.values
    })

    pivot = monthly_returns_df.pivot(index='Year', columns='Month', values='Return')

    fig, ax = plt.subplots(figsize=(14, 8))

    # Create heatmap
    im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=-20, vmax=20)

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Return (%)', rotation=-90, va="bottom")

    # Configure axes
    ax.set_xticks(np.arange(12))
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    # Add values to cells
    for i in range(len(pivot.index)):
        for j in range(12):
            if j + 1 in pivot.columns:
                value = pivot.iloc[i, pivot.columns.get_loc(j + 1)]
                if not np.isnan(value):
                    text = ax.text(j, i, f'{value:.1f}%',
                                   ha="center", va="center", color="black", fontsize=8)

    ax.set_title(f'{result.strategy_name} - Monthly Returns', fontsize=14)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved monthly returns to {save_path}")

    plt.show()


def generate_html_report(results: List[BacktestResult], output_path: str = "backtest_report.html"):
    """
    Generate HTML report for backtest results

    Args:
        results: List of BacktestResult objects
        output_path: Path to save HTML file
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Backtest Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            h1 { color: #333; text-align: center; }
            h2 { color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; background-color: white; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: right; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            .positive { color: green; font-weight: bold; }
            .negative { color: red; font-weight: bold; }
            .summary { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .metric { display: inline-block; margin: 10px 20px; }
            .metric-value { font-size: 24px; font-weight: bold; }
            .metric-label { color: #666; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>Cryptocurrency Trading Bot - Backtest Report</h1>
        <p style="text-align: center;">Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>

        <h2>Strategy Comparison</h2>
        <table>
            <tr>
                <th>Strategy</th>
                <th>Total Return</th>
                <th>Annual Return</th>
                <th>Max Drawdown</th>
                <th>Sharpe Ratio</th>
                <th>Sortino Ratio</th>
                <th>Win Rate</th>
                <th>Total Trades</th>
                <th>Profit Factor</th>
                <th>Buy & Hold</th>
            </tr>
    """

    for r in sorted(results, key=lambda x: x.total_return_percent, reverse=True):
        return_class = "positive" if r.total_return_percent > 0 else "negative"
        html += f"""
            <tr>
                <td style="text-align: left; font-weight: bold;">{r.strategy_name}</td>
                <td class="{return_class}">{r.total_return_percent:.2f}%</td>
                <td class="{return_class}">{r.annual_return:.2f}%</td>
                <td class="negative">{r.max_drawdown_percent:.2f}%</td>
                <td>{r.sharpe_ratio:.2f}</td>
                <td>{r.sortino_ratio:.2f}</td>
                <td>{r.win_rate:.1f}%</td>
                <td>{r.total_trades}</td>
                <td>{r.profit_factor:.2f}</td>
                <td>{r.buy_hold_return:.2f}%</td>
            </tr>
        """

    html += """
        </table>

        <h2>Individual Strategy Details</h2>
    """

    for r in results:
        return_class = "positive" if r.total_return_percent > 0 else "negative"
        html += f"""
        <div class="summary">
            <h3>{r.strategy_name}</h3>
            <p>Period: {r.start_date.strftime('%Y-%m-%d')} to {r.end_date.strftime('%Y-%m-%d')}</p>

            <div class="metric">
                <div class="metric-value {return_class}">${r.final_capital:,.2f}</div>
                <div class="metric-label">Final Capital</div>
            </div>
            <div class="metric">
                <div class="metric-value {return_class}">{r.total_return_percent:.2f}%</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric">
                <div class="metric-value">{r.sharpe_ratio:.2f}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric">
                <div class="metric-value negative">{r.max_drawdown_percent:.2f}%</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric">
                <div class="metric-value">{r.total_trades}</div>
                <div class="metric-label">Total Trades</div>
            </div>
            <div class="metric">
                <div class="metric-value">{r.win_rate:.1f}%</div>
                <div class="metric-label">Win Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{r.avg_trade_duration:.1f}h</div>
                <div class="metric-label">Avg Trade Duration</div>
            </div>
        </div>
        """

    html += """
    </body>
    </html>
    """

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Report saved to {output_path}")


def print_trade_log(trades: List[Trade], limit: int = 20):
    """
    Print formatted trade log

    Args:
        trades: List of Trade objects
        limit: Maximum number of trades to print
    """
    print("\n" + "=" * 100)
    print("TRADE LOG")
    print("=" * 100)
    print(f"{'#':<4} {'Entry Time':<20} {'Entry Price':<12} {'Exit Time':<20} {'Exit Price':<12} {'PnL':<12} {'PnL %':<10}")
    print("-" * 100)

    for i, trade in enumerate(trades[:limit]):
        entry_time = trade.entry_time.strftime('%Y-%m-%d %H:%M') if trade.entry_time else 'N/A'
        exit_time = trade.exit_time.strftime('%Y-%m-%d %H:%M') if trade.exit_time else 'N/A'
        entry_price = f"${trade.entry_price:.2f}" if trade.entry_price else 'N/A'
        exit_price = f"${trade.exit_price:.2f}" if trade.exit_price else 'N/A'
        pnl = f"${trade.pnl:.2f}"
        pnl_pct = f"{trade.pnl_percent:.2f}%"

        # Color coding
        if trade.pnl > 0:
            pnl = f"\033[92m{pnl}\033[0m"
            pnl_pct = f"\033[92m{pnl_pct}\033[0m"
        elif trade.pnl < 0:
            pnl = f"\033[91m{pnl}\033[0m"
            pnl_pct = f"\033[91m{pnl_pct}\033[0m"

        print(f"{i + 1:<4} {entry_time:<20} {entry_price:<12} {exit_time:<20} {exit_price:<12} {pnl:<12} {pnl_pct:<10}")

    if len(trades) > limit:
        print(f"\n... and {len(trades) - limit} more trades")

    print("=" * 100)
