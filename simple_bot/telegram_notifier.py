"""
Telegram Notifier for Trading Bot
Sends trade signals, alerts, and status updates to Telegram
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    DEBUG = "🔍"
    INFO = "ℹ️"
    TRADE = "💰"
    WARNING = "⚠️"
    ERROR = "❌"
    PROFIT = "💚"
    LOSS = "🔴"
    SIGNAL = "📊"


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    enabled: bool = True
    parse_mode: str = "HTML"


class TelegramNotifier:
    """
    Async Telegram notifier for trading bot

    Usage:
        notifier = TelegramNotifier.from_env()
        await notifier.send_trade("BUY", "BTCUSDT", 50000, 0.1)
    """

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None

    @classmethod
    def from_env(cls) -> 'TelegramNotifier':
        """Create notifier from environment variables"""
        token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        enabled = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'

        config = TelegramConfig(
            bot_token=token,
            chat_id=chat_id,
            enabled=enabled and bool(token) and bool(chat_id)
        )
        return cls(config)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_message(self, text: str, silent: bool = False) -> bool:
        """Send message to Telegram"""
        if not self.config.enabled:
            logger.debug(f"Telegram disabled, message: {text}")
            return False

        try:
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"

            payload = {
                "chat_id": self.config.chat_id,
                "text": text,
                "parse_mode": self.config.parse_mode,
                "disable_notification": silent
            }

            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"Telegram API error: {resp.status} - {error}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_sync(self, text: str, silent: bool = False) -> bool:
        """Synchronous wrapper for send_message"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.send_message(text, silent))
                    )
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(self.send_message(text, silent))
        except Exception as e:
            logger.error(f"Sync send failed: {e}")
            return False

    # ==================== Trade Notifications ====================

    async def send_trade(
        self,
        action: str,
        symbol: str,
        price: float,
        quantity: float,
        pnl: Optional[float] = None,
        pnl_percent: Optional[float] = None
    ):
        """Send trade execution notification"""
        emoji = "🟢" if action.upper() == "BUY" else "🔴"

        text = f"""
{emoji} <b>{action.upper()}</b> {symbol}

💵 Price: <code>${price:,.2f}</code>
📦 Quantity: <code>{quantity:.6f}</code>
💰 Value: <code>${price * quantity:,.2f}</code>
"""
        if pnl is not None:
            pnl_emoji = "💚" if pnl >= 0 else "❤️"
            text += f"""
{pnl_emoji} PnL: <code>${pnl:+,.2f}</code> ({pnl_percent:+.2f}%)
"""

        text += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_message(text)

    async def send_signal(
        self,
        signal: str,
        symbol: str,
        price: float,
        indicators: Dict[str, Any]
    ):
        """Send trading signal notification"""
        emoji = "📈" if signal.upper() == "BUY" else "📉" if signal.upper() == "SELL" else "⏸"

        text = f"""
{emoji} <b>SIGNAL: {signal.upper()}</b>

🪙 Symbol: {symbol}
💵 Price: <code>${price:,.2f}</code>

📊 <b>Indicators:</b>
"""
        for name, value in indicators.items():
            if isinstance(value, float):
                text += f"  • {name}: <code>{value:.4f}</code>\n"
            else:
                text += f"  • {name}: <code>{value}</code>\n"

        text += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_message(text)

    async def send_status(
        self,
        balance: float,
        position: Optional[Dict[str, Any]] = None,
        daily_pnl: float = 0,
        total_trades: int = 0
    ):
        """Send bot status update"""
        text = f"""
📊 <b>BOT STATUS</b>

💰 Balance: <code>${balance:,.2f}</code>
📈 Daily PnL: <code>${daily_pnl:+,.2f}</code>
🔢 Trades Today: {total_trades}
"""

        if position:
            side = position.get('side', 'NONE')
            entry = position.get('entry_price', 0)
            qty = position.get('quantity', 0)
            unrealized = position.get('unrealized_pnl', 0)

            pos_emoji = "🟢" if side == "LONG" else "🔴" if side == "SHORT" else "⚪"
            text += f"""
{pos_emoji} <b>Position:</b> {side}
  Entry: <code>${entry:,.2f}</code>
  Size: <code>{qty:.6f}</code>
  Unrealized: <code>${unrealized:+,.2f}</code>
"""
        else:
            text += "\n⚪ Position: NONE"

        text += f"\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_message(text)

    async def send_alert(self, level: LogLevel, title: str, message: str):
        """Send alert notification"""
        text = f"""
{level.value} <b>{title}</b>

{message}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        silent = level in [LogLevel.DEBUG, LogLevel.INFO]
        await self.send_message(text, silent=silent)

    async def send_error(self, error: str, context: str = ""):
        """Send error notification"""
        text = f"""
❌ <b>ERROR</b>

{error}
"""
        if context:
            text += f"\n📝 Context: {context}"

        text += f"\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_message(text)

    async def send_startup(self, config: Dict[str, Any]):
        """Send bot startup notification"""
        text = f"""
🚀 <b>BOT STARTED</b>

⚙️ <b>Configuration:</b>
"""
        for key, value in config.items():
            # Hide sensitive data
            if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower():
                value = '***hidden***'
            text += f"  • {key}: <code>{value}</code>\n"

        text += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_message(text)

    async def send_shutdown(self, reason: str = "Manual stop"):
        """Send bot shutdown notification"""
        text = f"""
🛑 <b>BOT STOPPED</b>

📝 Reason: {reason}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(text)

    async def send_daily_report(
        self,
        date: str,
        starting_balance: float,
        ending_balance: float,
        trades: int,
        wins: int,
        losses: int,
        total_pnl: float
    ):
        """Send daily performance report"""
        win_rate = (wins / trades * 100) if trades > 0 else 0
        pnl_percent = ((ending_balance - starting_balance) / starting_balance * 100) if starting_balance > 0 else 0

        emoji = "💚" if total_pnl >= 0 else "❤️"

        text = f"""
📅 <b>DAILY REPORT - {date}</b>

💰 Starting: <code>${starting_balance:,.2f}</code>
💰 Ending: <code>${ending_balance:,.2f}</code>
{emoji} PnL: <code>${total_pnl:+,.2f}</code> ({pnl_percent:+.2f}%)

📊 <b>Statistics:</b>
  • Trades: {trades}
  • Wins: {wins} ✅
  • Losses: {losses} ❌
  • Win Rate: {win_rate:.1f}%

🕐 Generated at {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text)


class TelegramLogHandler(logging.Handler):
    """
    Python logging handler that sends logs to Telegram

    Usage:
        notifier = TelegramNotifier.from_env()
        handler = TelegramLogHandler(notifier, min_level=logging.WARNING)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, notifier: TelegramNotifier, min_level: int = logging.WARNING):
        super().__init__()
        self.notifier = notifier
        self.setLevel(min_level)

    def emit(self, record: logging.LogRecord):
        try:
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.ERROR,
            }
            level = level_map.get(record.levelno, LogLevel.INFO)

            message = self.format(record)

            # Use sync version to avoid async issues in logging
            self.notifier.send_sync(
                f"{level.value} <b>{record.levelname}</b>\n\n<code>{message}</code>",
                silent=(record.levelno < logging.WARNING)
            )
        except Exception:
            self.handleError(record)


# Singleton instance
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """Get or create global notifier instance"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier.from_env()
    return _notifier


# Convenience functions
def notify_trade(action: str, symbol: str, price: float, quantity: float, **kwargs):
    """Send trade notification (sync)"""
    notifier = get_notifier()
    asyncio.run(notifier.send_trade(action, symbol, price, quantity, **kwargs))


def notify_signal(signal: str, symbol: str, price: float, indicators: dict):
    """Send signal notification (sync)"""
    notifier = get_notifier()
    asyncio.run(notifier.send_signal(signal, symbol, price, indicators))


def notify_error(error: str, context: str = ""):
    """Send error notification (sync)"""
    notifier = get_notifier()
    asyncio.run(notifier.send_error(error, context))


def notify_status(balance: float, **kwargs):
    """Send status notification (sync)"""
    notifier = get_notifier()
    asyncio.run(notifier.send_status(balance, **kwargs))
