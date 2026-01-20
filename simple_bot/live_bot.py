"""
Production Live Trading Bot with Telegram Integration and PostgreSQL
Designed for deployment on Railway/Docker
"""

import os
import sys
import time
import json
import signal
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd
import numpy as np

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    print("WARNING: python-binance not installed. Install with: pip install python-binance")

from .strategies import BaseStrategy, Signal
from .indicators import sma, ema, atr
from .telegram_notifier import (
    TelegramNotifier, TelegramLogHandler, LogLevel,
    get_notifier
)
from .database import (
    Database, DatabaseConfig, Trade, Position as DBPosition, Candle,
    get_database, close_database
)


# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_DIR = Path(os.getenv('LOG_DIR', '/app/logs'))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / 'trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Current trading position"""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    entry_time: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    highest_price: Optional[float] = None
    db_id: Optional[int] = None  # Database ID


@dataclass
class BotConfig:
    """Bot configuration from environment"""
    # Binance
    api_key: str
    api_secret: str

    # Trading
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    trade_amount_usdt: float = 100.0

    # Strategy - Optimized Trend Follow
    fast_period: int = 76
    slow_period: int = 209
    filter_period: int = 23

    # Risk Management
    trailing_stop_pct: float = 0.0389
    stop_loss_pct: float = 0.0476
    take_profit_pct: Optional[float] = None

    # Mode
    paper_trading: bool = True
    initial_capital: float = 10000.0

    # Database
    use_database: bool = True

    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Load config from environment variables"""
        return cls(
            api_key=os.getenv('BINANCE_API_KEY', ''),
            api_secret=os.getenv('BINANCE_API_SECRET', ''),
            symbol=os.getenv('TRADING_SYMBOL', 'BTCUSDT'),
            interval=os.getenv('TRADING_INTERVAL', '1h'),
            trade_amount_usdt=float(os.getenv('TRADE_AMOUNT_USDT', '100')),
            fast_period=int(os.getenv('FAST_PERIOD', '76')),
            slow_period=int(os.getenv('SLOW_PERIOD', '209')),
            filter_period=int(os.getenv('FILTER_PERIOD', '23')),
            trailing_stop_pct=float(os.getenv('TRAILING_STOP_PCT', '0.0389')),
            stop_loss_pct=float(os.getenv('STOP_LOSS_PCT', '0.0476')),
            take_profit_pct=float(os.getenv('TAKE_PROFIT_PCT', '0')) or None,
            paper_trading=os.getenv('PAPER_TRADING', 'true').lower() == 'true',
            initial_capital=float(os.getenv('INITIAL_CAPITAL', '10000')),
            use_database=os.getenv('USE_DATABASE', 'true').lower() == 'true'
        )


class OptimizedTrendStrategy(BaseStrategy):
    """
    Optimized Trend Following Strategy
    Best params from Optuna: Sharpe 1.03, Annual Return 31.7%
    """

    def __init__(self, fast: int = 76, slow: int = 209, filter_p: int = 23):
        super().__init__(name=f"TrendFollow_{fast}_{slow}_{filter_p}")
        self.fast = fast
        self.slow = slow
        self.filter_p = filter_p

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = df.copy()

        df['fast_ma'] = sma(df['close'], self.fast)
        df['slow_ma'] = sma(df['close'], self.slow)
        df['filter_ema'] = ema(df['close'], self.filter_p)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # BUY: Golden cross + price above fast MA + filter rising
        buy = (
            (df['fast_ma'] > df['slow_ma']) &
            (df['fast_ma'].shift(1) <= df['slow_ma'].shift(1)) &
            (df['close'] > df['fast_ma']) &
            (df['filter_ema'] > df['filter_ema'].shift(3))
        )
        signals[buy] = Signal.BUY

        # SELL: Death cross
        sell = (
            (df['fast_ma'] < df['slow_ma']) &
            (df['fast_ma'].shift(1) >= df['slow_ma'].shift(1))
        )
        signals[sell] = Signal.SELL

        return signals

    def get_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Get current indicator values for logging"""
        df = df.copy()
        df['fast_ma'] = sma(df['close'], self.fast)
        df['slow_ma'] = sma(df['close'], self.slow)
        df['filter_ema'] = ema(df['close'], self.filter_p)

        last = df.iloc[-1]
        return {
            f'SMA_{self.fast}': float(last['fast_ma']),
            f'SMA_{self.slow}': float(last['slow_ma']),
            f'EMA_{self.filter_p}': float(last['filter_ema']),
            'Price': float(last['close'])
        }


class LiveTradingBot:
    """
    Production-ready live trading bot with Telegram notifications and PostgreSQL
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.notifier = get_notifier()
        self.db: Optional[Database] = None

        # Initialize strategy
        self.strategy = OptimizedTrendStrategy(
            fast=config.fast_period,
            slow=config.slow_period,
            filter_p=config.filter_period
        )

        # State
        self.position: Optional[Position] = None
        self.paper_balance = config.initial_capital
        self.trade_history = []
        self.daily_pnl = 0.0
        self.total_trades_today = 0

        # Binance client
        self.client = None
        if BINANCE_AVAILABLE and config.api_key and config.api_secret:
            try:
                self.client = Client(config.api_key, config.api_secret)
                self.client.ping()
                logger.info("Binance client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Binance: {e}")
                self.client = None

        if not self.client and not config.paper_trading:
            logger.warning("No Binance connection, forcing paper trading mode")
            self.config.paper_trading = True

        # Running state
        self.running = False
        self._setup_signal_handlers()

        # State persistence (file fallback)
        self.state_file = Path(os.getenv('STATE_DIR', '/app/data')) / f'state_{config.symbol}.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Add Telegram handler for errors
        telegram_handler = TelegramLogHandler(self.notifier, min_level=logging.ERROR)
        logging.getLogger().addHandler(telegram_handler)

    async def init_database(self):
        """Initialize database connection"""
        if not self.config.use_database:
            logger.info("Database disabled, using file-based state")
            self._load_state_from_file()
            return

        try:
            self.db = await get_database()
            logger.info("Database connected successfully")
            await self._load_state_from_db()
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Using file-based state.")
            self.db = None
            self._load_state_from_file()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    async def _load_state_from_db(self):
        """Load state from database"""
        if not self.db:
            return

        try:
            # Load paper balance
            balance = await self.db.get_state('paper_balance')
            if balance is not None:
                self.paper_balance = float(balance)

            # Load open position
            db_pos = await self.db.get_open_position(self.config.symbol)
            if db_pos:
                self.position = Position(
                    symbol=db_pos.symbol,
                    side=db_pos.side,
                    entry_price=float(db_pos.entry_price),
                    quantity=float(db_pos.quantity),
                    entry_time=db_pos.entry_time.isoformat() if db_pos.entry_time else "",
                    stop_loss=float(db_pos.stop_loss) if db_pos.stop_loss else None,
                    take_profit=float(db_pos.take_profit) if db_pos.take_profit else None,
                    trailing_stop_price=float(db_pos.trailing_stop) if db_pos.trailing_stop else None,
                    highest_price=float(db_pos.highest_price) if db_pos.highest_price else None,
                    db_id=db_pos.id
                )
                logger.info(f"Loaded open position from database: {self.position.side} {self.position.quantity}")

            logger.info("State loaded from database")
        except Exception as e:
            logger.error(f"Failed to load state from database: {e}")

    def _load_state_from_file(self):
        """Load state from file (fallback)"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.paper_balance = state.get('paper_balance', self.paper_balance)
                self.trade_history = state.get('trade_history', [])
                if state.get('position'):
                    pos = state['position']
                    self.position = Position(**pos)
                logger.info(f"Loaded state from {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    async def _save_state(self):
        """Save state to database and file"""
        # Save to database
        if self.db:
            try:
                await self.db.save_state('paper_balance', self.paper_balance)

                if self.position and self.position.db_id:
                    # Update existing position
                    db_pos = DBPosition(
                        id=self.position.db_id,
                        symbol=self.position.symbol,
                        side=self.position.side,
                        entry_price=self.position.entry_price,
                        quantity=self.position.quantity,
                        stop_loss=self.position.stop_loss,
                        take_profit=self.position.take_profit,
                        trailing_stop=self.position.trailing_stop_price,
                        highest_price=self.position.highest_price,
                        is_open=True
                    )
                    await self.db.save_position(db_pos)
            except Exception as e:
                logger.error(f"Failed to save state to database: {e}")

        # Save to file (fallback)
        try:
            state = {
                'paper_balance': self.paper_balance,
                'trade_history': self.trade_history[-100:],
                'position': asdict(self.position) if self.position else None,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state to file: {e}")

    def get_historical_data(self, limit: int = 300) -> pd.DataFrame:
        """Fetch historical klines from Binance"""
        if self.client:
            try:
                klines = self.client.get_klines(
                    symbol=self.config.symbol,
                    interval=self.config.interval,
                    limit=limit
                )

                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])

                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)

                df.set_index('timestamp', inplace=True)
                return df[['open', 'high', 'low', 'close', 'volume']]

            except BinanceAPIException as e:
                logger.error(f"Binance API error: {e}")
                raise
        else:
            from .data_loader import generate_sample_data
            return generate_sample_data(days=limit // 24 + 10).tail(limit)

    def get_current_price(self) -> float:
        """Get current price"""
        if self.client:
            ticker = self.client.get_symbol_ticker(symbol=self.config.symbol)
            return float(ticker['price'])
        else:
            df = self.get_historical_data(limit=1)
            return float(df.iloc[-1]['close'])

    def get_balance(self) -> float:
        """Get available USDT balance"""
        if self.config.paper_trading:
            return self.paper_balance

        if self.client:
            try:
                account = self.client.get_account()
                for asset in account['balances']:
                    if asset['asset'] == 'USDT':
                        return float(asset['free'])
            except Exception as e:
                logger.error(f"Failed to get balance: {e}")
        return 0.0

    async def open_position(self, price: float) -> bool:
        """Open a new long position"""
        if self.position:
            logger.warning("Position already open")
            return False

        balance = self.get_balance()
        trade_amount = min(self.config.trade_amount_usdt, balance * 0.95)

        if trade_amount < 10:
            logger.warning(f"Insufficient balance: ${balance:.2f}")
            return False

        quantity = trade_amount / price
        entry_time = datetime.now()

        # Execute order
        if self.config.paper_trading:
            self.paper_balance -= trade_amount
            logger.info(f"Paper BUY: {quantity:.6f} @ ${price:.2f}")
        else:
            try:
                order = self.client.create_order(
                    symbol=self.config.symbol,
                    side='BUY',
                    type='MARKET',
                    quoteOrderQty=trade_amount
                )
                quantity = float(order['executedQty'])
                price = float(order['cummulativeQuoteQty']) / quantity
                logger.info(f"Live BUY: {quantity:.6f} @ ${price:.2f}")
            except BinanceAPIException as e:
                logger.error(f"Order failed: {e}")
                await self.notifier.send_error(str(e), "Opening position")
                return False

        # Set position
        stop_loss = price * (1 - self.config.stop_loss_pct)
        take_profit = price * (1 + self.config.take_profit_pct) if self.config.take_profit_pct else None
        trailing_stop = price * (1 - self.config.trailing_stop_pct)

        self.position = Position(
            symbol=self.config.symbol,
            side='LONG',
            entry_price=price,
            quantity=quantity,
            entry_time=entry_time.isoformat(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_price=trailing_stop,
            highest_price=price
        )

        # Save to database
        if self.db:
            try:
                db_pos = DBPosition(
                    symbol=self.config.symbol,
                    side='LONG',
                    entry_price=price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    highest_price=price,
                    entry_time=entry_time,
                    is_open=True
                )
                self.position.db_id = await self.db.save_position(db_pos)

                # Log signal
                indicators = self.strategy.get_indicators(self.get_historical_data(300))
                await self.db.log_signal(
                    self.config.symbol, 'BUY', price, indicators, self.strategy.name
                )
            except Exception as e:
                logger.error(f"Failed to save position to database: {e}")

        await self._save_state()

        # Notify
        await self.notifier.send_trade(
            action="BUY",
            symbol=self.config.symbol,
            price=price,
            quantity=quantity
        )

        logger.info(f"Position opened: {quantity:.6f} {self.config.symbol} @ ${price:.2f}")
        logger.info(f"Stop Loss: ${stop_loss:.2f}, Trailing Stop: ${trailing_stop:.2f}")

        return True

    async def close_position(self, price: float, reason: str = "signal") -> bool:
        """Close current position"""
        if not self.position:
            return False

        quantity = self.position.quantity
        exit_time = datetime.now()

        # Execute order
        if self.config.paper_trading:
            revenue = quantity * price
            self.paper_balance += revenue
            logger.info(f"Paper SELL: {quantity:.6f} @ ${price:.2f}")
        else:
            try:
                order = self.client.create_order(
                    symbol=self.config.symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=quantity
                )
                price = float(order['cummulativeQuoteQty']) / float(order['executedQty'])
                logger.info(f"Live SELL: {quantity:.6f} @ ${price:.2f}")
            except BinanceAPIException as e:
                logger.error(f"Sell order failed: {e}")
                await self.notifier.send_error(str(e), "Closing position")
                return False

        # Calculate PnL
        pnl = (price - self.position.entry_price) * quantity
        pnl_pct = (price / self.position.entry_price - 1) * 100

        # Save trade to database
        if self.db:
            try:
                trade = Trade(
                    symbol=self.config.symbol,
                    side='LONG',
                    entry_price=self.position.entry_price,
                    exit_price=price,
                    quantity=quantity,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    reason=reason,
                    strategy=self.strategy.name,
                    entry_time=datetime.fromisoformat(self.position.entry_time),
                    exit_time=exit_time
                )
                await self.db.save_trade(trade)

                # Close position in database
                if self.position.db_id:
                    await self.db.close_position(self.position.db_id)

                # Log signal
                indicators = self.strategy.get_indicators(self.get_historical_data(300))
                await self.db.log_signal(
                    self.config.symbol, 'SELL', price, indicators, self.strategy.name
                )
            except Exception as e:
                logger.error(f"Failed to save trade to database: {e}")

        # Record trade (in memory)
        trade_record = {
            'symbol': self.config.symbol,
            'entry_price': self.position.entry_price,
            'exit_price': price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'entry_time': self.position.entry_time,
            'exit_time': exit_time.isoformat()
        }
        self.trade_history.append(trade_record)
        self.daily_pnl += pnl
        self.total_trades_today += 1

        # Notify
        await self.notifier.send_trade(
            action="SELL",
            symbol=self.config.symbol,
            price=price,
            quantity=quantity,
            pnl=pnl,
            pnl_percent=pnl_pct
        )

        logger.info(f"Position closed: PnL ${pnl:.2f} ({pnl_pct:.2f}%) - Reason: {reason}")

        self.position = None
        await self._save_state()

        return True

    def update_trailing_stop(self, current_price: float):
        """Update trailing stop if price moved higher"""
        if not self.position:
            return

        if current_price > self.position.highest_price:
            self.position.highest_price = current_price
            new_trailing = current_price * (1 - self.config.trailing_stop_pct)

            if new_trailing > self.position.trailing_stop_price:
                self.position.trailing_stop_price = new_trailing
                logger.debug(f"Trailing stop updated to ${new_trailing:.2f}")

    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Check if any exit condition is triggered"""
        if not self.position:
            return None

        self.update_trailing_stop(current_price)

        if current_price <= self.position.stop_loss:
            return "stop_loss"

        if current_price <= self.position.trailing_stop_price:
            return "trailing_stop"

        if self.position.take_profit and current_price >= self.position.take_profit:
            return "take_profit"

        return None

    async def run_iteration(self):
        """Run single trading iteration"""
        try:
            df = self.get_historical_data(limit=300)
            current_price = float(df.iloc[-1]['close'])

            signals = self.strategy.generate_signals(df)
            current_signal = signals.iloc[-1]

            logger.info(f"Price: ${current_price:.2f} | Signal: {current_signal.name}")

            # Check exit conditions first
            if self.position:
                exit_reason = self.check_exit_conditions(current_price)
                if exit_reason:
                    await self.close_position(current_price, exit_reason)
                    return

            # Process signals
            if current_signal == Signal.BUY and not self.position:
                indicators = self.strategy.get_indicators(df)
                await self.notifier.send_signal("BUY", self.config.symbol, current_price, indicators)
                await self.open_position(current_price)

            elif current_signal == Signal.SELL and self.position:
                indicators = self.strategy.get_indicators(df)
                await self.notifier.send_signal("SELL", self.config.symbol, current_price, indicators)
                await self.close_position(current_price, "signal")

            # Log status
            if self.position:
                unrealized_pnl = (current_price - self.position.entry_price) * self.position.quantity
                logger.info(f"Position: LONG {self.position.quantity:.6f} @ ${self.position.entry_price:.2f}")
                logger.info(f"Unrealized PnL: ${unrealized_pnl:.2f}")
            else:
                balance = self.get_balance()
                logger.info(f"No position | Balance: ${balance:.2f}")

        except Exception as e:
            logger.error(f"Error in trading iteration: {e}", exc_info=True)
            await self.notifier.send_error(str(e), "Trading iteration")

    async def send_periodic_status(self):
        """Send periodic status update to Telegram"""
        balance = self.get_balance()

        position_data = None
        if self.position:
            current_price = self.get_current_price()
            unrealized = (current_price - self.position.entry_price) * self.position.quantity
            position_data = {
                'side': self.position.side,
                'entry_price': self.position.entry_price,
                'quantity': self.position.quantity,
                'unrealized_pnl': unrealized
            }

        await self.notifier.send_status(
            balance=balance,
            position=position_data,
            daily_pnl=self.daily_pnl,
            total_trades=self.total_trades_today
        )

        # Send database stats
        if self.db:
            try:
                stats = await self.db.get_trade_stats(self.config.symbol, days=30)
                if stats['total_trades'] > 0:
                    await self.notifier.send_message(f"""
📊 <b>30-Day Stats</b>

Trades: {stats['total_trades']}
Win Rate: {stats['win_rate']:.1f}%
Total PnL: ${stats['total_pnl']:.2f}
Profit Factor: {stats['profit_factor']:.2f}
""")
            except Exception as e:
                logger.error(f"Failed to get trade stats: {e}")

    async def run(self):
        """Main trading loop"""
        # Initialize database
        await self.init_database()

        logger.info("=" * 60)
        logger.info("Starting Live Trading Bot")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.config.symbol}")
        logger.info(f"Interval: {self.config.interval}")
        logger.info(f"Strategy: {self.strategy.name}")
        logger.info(f"Mode: {'Paper' if self.config.paper_trading else 'Live'}")
        logger.info(f"Trade Amount: ${self.config.trade_amount_usdt}")
        logger.info(f"Trailing Stop: {self.config.trailing_stop_pct*100:.2f}%")
        logger.info(f"Stop Loss: {self.config.stop_loss_pct*100:.2f}%")
        logger.info(f"Database: {'Connected' if self.db else 'Disabled'}")
        logger.info("=" * 60)

        # Startup notification
        await self.notifier.send_startup({
            'Symbol': self.config.symbol,
            'Interval': self.config.interval,
            'Strategy': self.strategy.name,
            'Mode': 'Paper' if self.config.paper_trading else 'Live',
            'Trade Amount': f"${self.config.trade_amount_usdt}",
            'Trailing Stop': f"{self.config.trailing_stop_pct*100:.2f}%",
            'Database': 'Connected' if self.db else 'Disabled'
        })

        self.running = True

        interval_seconds = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900,
            '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400, '1d': 86400
        }
        sleep_time = interval_seconds.get(self.config.interval, 3600)

        iteration = 0
        last_status_hour = -1

        while self.running:
            try:
                await self.run_iteration()

                # Send status every 4 hours
                current_hour = datetime.now().hour
                if current_hour % 4 == 0 and current_hour != last_status_hour:
                    await self.send_periodic_status()
                    last_status_hour = current_hour

                # Reset daily stats at midnight
                if datetime.now().hour == 0 and iteration > 0:
                    self.daily_pnl = 0.0
                    self.total_trades_today = 0

                iteration += 1
                logger.info(f"Sleeping for {sleep_time}s until next candle...")
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Bot cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(60)

        await self.shutdown()

    def stop(self):
        """Signal the bot to stop"""
        logger.info("Stop signal received")
        self.running = False

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        await self._save_state()

        if self.db:
            await close_database()

        await self.notifier.send_shutdown("Graceful shutdown")
        await self.notifier.close()
        logger.info("Shutdown complete")


def main():
    """Entry point for the bot"""
    config = BotConfig.from_env()
    bot = LiveTradingBot(config)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
