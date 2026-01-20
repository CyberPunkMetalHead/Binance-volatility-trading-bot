"""
Live/Paper Trading Bot Module
Main trading bot that can run in live or paper trading mode
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading

import pandas as pd
import numpy as np

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

from .strategies import BaseStrategy, Signal, get_all_strategies
from .indicators import calculate_all_indicators


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    side: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Order:
    """Represents an order"""
    symbol: str
    side: str  # "BUY" or "SELL"
    order_type: str  # "MARKET" or "LIMIT"
    quantity: float
    price: Optional[float] = None
    timestamp: datetime = None
    order_id: Optional[str] = None
    status: str = "PENDING"


class TradingBot:
    """
    Trading bot supporting live and paper trading modes
    """

    def __init__(self, config: dict):
        """
        Initialize trading bot

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.mode = config.get('mode', 'paper')  # 'live' or 'paper'

        # Trading parameters
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.interval = config.get('interval', '1h')
        self.quantity_usdt = config.get('quantity_usdt', 100)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.05)
        self.take_profit_pct = config.get('take_profit_pct', 0.10)

        # Initialize strategy
        strategy_name = config.get('strategy', 'sma_20_50')
        strategies = get_all_strategies()
        self.strategy = strategies.get(strategy_name)
        if not self.strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        logger.info(f"Using strategy: {self.strategy.name}")

        # State
        self.position: Optional[Position] = None
        self.orders: List[Order] = []
        self.trade_history: List[dict] = []

        # Paper trading state
        self.paper_balance = config.get('initial_capital', 10000)
        self.paper_positions: Dict[str, Position] = {}

        # Initialize Binance client for live mode
        self.client = None
        if self.mode == 'live' and BINANCE_AVAILABLE:
            api_key = config.get('api_key')
            api_secret = config.get('api_secret')
            if api_key and api_secret:
                self.client = Client(api_key, api_secret)
                logger.info("Binance client initialized for live trading")
            else:
                logger.warning("API credentials not provided, switching to paper mode")
                self.mode = 'paper'

        # Running flag
        self.running = False

        # Load state if exists
        self._load_state()

    def _load_state(self):
        """Load bot state from file"""
        state_file = f"bot_state_{self.symbol}.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.paper_balance = state.get('paper_balance', self.paper_balance)
                    self.trade_history = state.get('trade_history', [])
                    if state.get('position'):
                        pos = state['position']
                        self.position = Position(
                            symbol=pos['symbol'],
                            side=pos['side'],
                            entry_price=pos['entry_price'],
                            quantity=pos['quantity'],
                            entry_time=datetime.fromisoformat(pos['entry_time']),
                            stop_loss=pos.get('stop_loss'),
                            take_profit=pos.get('take_profit')
                        )
                    logger.info(f"Loaded state from {state_file}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Save bot state to file"""
        state_file = f"bot_state_{self.symbol}.json"
        try:
            state = {
                'paper_balance': self.paper_balance,
                'trade_history': self.trade_history,
                'position': None
            }
            if self.position:
                state['position'] = {
                    'symbol': self.position.symbol,
                    'side': self.position.side,
                    'entry_price': self.position.entry_price,
                    'quantity': self.position.quantity,
                    'entry_time': self.position.entry_time.isoformat(),
                    'stop_loss': self.position.stop_loss,
                    'take_profit': self.position.take_profit
                }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def get_historical_data(self, limit: int = 200) -> pd.DataFrame:
        """
        Get historical klines data

        Args:
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        if self.mode == 'live' and self.client:
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=self.interval,
                limit=limit
            )

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df
        else:
            # Generate simulated data for paper trading
            from .data_loader import generate_sample_data
            return generate_sample_data(days=limit // 24 + 10).tail(limit)

    def get_current_price(self) -> float:
        """Get current price for symbol"""
        if self.mode == 'live' and self.client:
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        else:
            # For paper trading, use last price from historical data
            df = self.get_historical_data(limit=1)
            return df.iloc[-1]['close']

    def calculate_quantity(self, price: float) -> float:
        """
        Calculate order quantity based on available balance

        Args:
            price: Current price

        Returns:
            Quantity to trade
        """
        if self.mode == 'live' and self.client:
            # Get account balance
            account = self.client.get_account()
            usdt_balance = 0
            for asset in account['balances']:
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['free'])
                    break

            available = min(self.quantity_usdt, usdt_balance)
        else:
            available = min(self.quantity_usdt, self.paper_balance)

        quantity = available / price

        # Round to appropriate precision (8 decimal places for most crypto)
        return round(quantity, 6)

    def place_order(self, side: str, quantity: float, price: Optional[float] = None) -> Optional[Order]:
        """
        Place an order

        Args:
            side: "BUY" or "SELL"
            quantity: Order quantity
            price: Limit price (None for market order)

        Returns:
            Order object or None if failed
        """
        order = Order(
            symbol=self.symbol,
            side=side,
            order_type="MARKET" if price is None else "LIMIT",
            quantity=quantity,
            price=price,
            timestamp=datetime.now()
        )

        if self.mode == 'live' and self.client:
            try:
                if price is None:
                    result = self.client.create_order(
                        symbol=self.symbol,
                        side=side,
                        type='MARKET',
                        quantity=quantity
                    )
                else:
                    result = self.client.create_order(
                        symbol=self.symbol,
                        side=side,
                        type='LIMIT',
                        timeInForce='GTC',
                        quantity=quantity,
                        price=str(price)
                    )

                order.order_id = str(result['orderId'])
                order.status = result['status']
                logger.info(f"Order placed: {side} {quantity} {self.symbol} - ID: {order.order_id}")

            except BinanceAPIException as e:
                logger.error(f"Binance API error: {e}")
                return None
            except Exception as e:
                logger.error(f"Error placing order: {e}")
                return None
        else:
            # Paper trading
            current_price = self.get_current_price()
            execution_price = price if price else current_price

            order.order_id = f"PAPER_{int(time.time())}"
            order.status = "FILLED"

            if side == "BUY":
                cost = quantity * execution_price
                if cost > self.paper_balance:
                    logger.warning(f"Insufficient balance. Required: {cost}, Available: {self.paper_balance}")
                    return None
                self.paper_balance -= cost
            else:
                revenue = quantity * execution_price
                self.paper_balance += revenue

            logger.info(f"Paper order: {side} {quantity} {self.symbol} @ {execution_price}")
            logger.info(f"Paper balance: ${self.paper_balance:.2f}")

        self.orders.append(order)
        self._save_state()
        return order

    def open_position(self, side: str = "long") -> bool:
        """
        Open a new position

        Args:
            side: "long" or "short"

        Returns:
            True if position opened successfully
        """
        if self.position:
            logger.warning("Position already open")
            return False

        current_price = self.get_current_price()
        quantity = self.calculate_quantity(current_price)

        if quantity <= 0:
            logger.warning("Insufficient balance to open position")
            return False

        order = self.place_order("BUY" if side == "long" else "SELL", quantity)

        if order and order.status == "FILLED":
            # Calculate stop loss and take profit
            if side == "long":
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
            else:
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)

            self.position = Position(
                symbol=self.symbol,
                side=side,
                entry_price=current_price,
                quantity=quantity,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            logger.info(f"Opened {side} position: {quantity} {self.symbol} @ {current_price}")
            logger.info(f"Stop Loss: {stop_loss:.2f}, Take Profit: {take_profit:.2f}")

            self._save_state()
            return True

        return False

    def close_position(self, reason: str = "signal") -> bool:
        """
        Close current position

        Args:
            reason: Reason for closing (signal, stop_loss, take_profit)

        Returns:
            True if position closed successfully
        """
        if not self.position:
            logger.warning("No position to close")
            return False

        current_price = self.get_current_price()

        order = self.place_order(
            "SELL" if self.position.side == "long" else "BUY",
            self.position.quantity
        )

        if order and order.status == "FILLED":
            # Calculate PnL
            if self.position.side == "long":
                pnl = (current_price - self.position.entry_price) * self.position.quantity
                pnl_pct = (current_price / self.position.entry_price - 1) * 100
            else:
                pnl = (self.position.entry_price - current_price) * self.position.quantity
                pnl_pct = (self.position.entry_price / current_price - 1) * 100

            # Record trade
            trade = {
                'symbol': self.symbol,
                'side': self.position.side,
                'entry_price': self.position.entry_price,
                'exit_price': current_price,
                'quantity': self.position.quantity,
                'entry_time': self.position.entry_time.isoformat(),
                'exit_time': datetime.now().isoformat(),
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'reason': reason
            }
            self.trade_history.append(trade)

            logger.info(f"Closed position: {self.position.quantity} {self.symbol} @ {current_price}")
            logger.info(f"PnL: ${pnl:.2f} ({pnl_pct:.2f}%) - Reason: {reason}")

            self.position = None
            self._save_state()
            return True

        return False

    def check_stop_loss_take_profit(self) -> Optional[str]:
        """
        Check if stop loss or take profit is triggered

        Returns:
            "stop_loss", "take_profit", or None
        """
        if not self.position:
            return None

        current_price = self.get_current_price()

        if self.position.side == "long":
            if self.position.stop_loss and current_price <= self.position.stop_loss:
                return "stop_loss"
            if self.position.take_profit and current_price >= self.position.take_profit:
                return "take_profit"
        else:  # short
            if self.position.stop_loss and current_price >= self.position.stop_loss:
                return "stop_loss"
            if self.position.take_profit and current_price <= self.position.take_profit:
                return "take_profit"

        return None

    def run_iteration(self):
        """Run single trading iteration"""
        try:
            # Get historical data for signal generation
            df = self.get_historical_data(limit=200)

            # Generate signals
            signals = self.strategy.generate_signals(df)
            current_signal = signals.iloc[-1]

            current_price = df.iloc[-1]['close']
            logger.info(f"Price: {current_price:.2f}, Signal: {current_signal}")

            # Check stop loss / take profit first
            sl_tp_trigger = self.check_stop_loss_take_profit()
            if sl_tp_trigger:
                self.close_position(reason=sl_tp_trigger)
                return

            # Process signals
            if current_signal == Signal.BUY and not self.position:
                logger.info("BUY signal detected, opening long position")
                self.open_position("long")

            elif current_signal == Signal.SELL and self.position and self.position.side == "long":
                logger.info("SELL signal detected, closing long position")
                self.close_position(reason="signal")

        except Exception as e:
            logger.error(f"Error in trading iteration: {e}")

    def run(self):
        """
        Main trading loop
        """
        logger.info(f"Starting trading bot in {self.mode} mode")
        logger.info(f"Symbol: {self.symbol}, Interval: {self.interval}")
        logger.info(f"Strategy: {self.strategy.name}")

        if self.mode == 'paper':
            logger.info(f"Paper trading balance: ${self.paper_balance:.2f}")

        self.running = True

        # Calculate sleep time based on interval
        interval_map = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900,
            '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400,
            '1d': 86400
        }
        sleep_time = interval_map.get(self.interval, 3600)

        while self.running:
            try:
                self.run_iteration()

                # Print current status
                if self.position:
                    current_price = self.get_current_price()
                    if self.position.side == "long":
                        unrealized_pnl = (current_price - self.position.entry_price) * self.position.quantity
                    else:
                        unrealized_pnl = (self.position.entry_price - current_price) * self.position.quantity
                    logger.info(f"Position: {self.position.side} {self.position.quantity} @ {self.position.entry_price:.2f}")
                    logger.info(f"Unrealized PnL: ${unrealized_pnl:.2f}")
                else:
                    logger.info("No open position")

                logger.info(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.running = False
        self._save_state()

    def get_performance_summary(self) -> dict:
        """
        Get performance summary

        Returns:
            Dictionary with performance metrics
        """
        if not self.trade_history:
            return {'message': 'No trades recorded'}

        total_pnl = sum(t['pnl'] for t in self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] <= 0]

        return {
            'total_trades': len(self.trade_history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trade_history) * 100 if self.trade_history else 0,
            'total_pnl': total_pnl,
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
            'paper_balance': self.paper_balance if self.mode == 'paper' else None
        }


def create_bot_from_config(config_path: str) -> TradingBot:
    """
    Create bot from YAML config file

    Args:
        config_path: Path to config file

    Returns:
        TradingBot instance
    """
    import yaml

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return TradingBot(config)


if __name__ == "__main__":
    # Example usage
    config = {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'interval': '1h',
        'quantity_usdt': 100,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.10,
        'strategy': 'sma_20_50',
        'initial_capital': 10000
    }

    bot = TradingBot(config)

    # Run a single iteration for testing
    bot.run_iteration()

    # Print performance
    print("\nPerformance Summary:")
    print(bot.get_performance_summary())
