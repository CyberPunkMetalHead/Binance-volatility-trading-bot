"""
PostgreSQL Database Module for Trading Bot
Stores trades, positions, candles, and bot state
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Trade record"""
    id: Optional[int] = None
    symbol: str = ""
    side: str = ""  # BUY/SELL
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    reason: str = ""
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    strategy: str = ""


@dataclass
class Position:
    """Position record"""
    id: Optional[int] = None
    symbol: str = ""
    side: str = ""  # LONG/SHORT
    entry_price: float = 0.0
    quantity: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    highest_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    is_open: bool = True


@dataclass
class Candle:
    """OHLCV candle"""
    symbol: str
    interval: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class DatabaseConfig:
    """Database configuration"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trading_bot",
        user: str = "postgres",
        password: str = "",
        min_connections: int = 2,
        max_connections: int = 10
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Load config from environment"""
        # Support DATABASE_URL format (used by Railway)
        database_url = os.getenv('DATABASE_URL', '')
        if database_url:
            # Parse postgresql://user:pass@host:port/dbname
            import urllib.parse
            parsed = urllib.parse.urlparse(database_url)
            return cls(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/') or 'trading_bot',
                user=parsed.username or 'postgres',
                password=parsed.password or ''
            )

        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'trading_bot'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class Database:
    """
    Async PostgreSQL database handler

    Usage:
        db = Database(config)
        await db.connect()
        await db.save_trade(trade)
        await db.close()
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def connect(self) -> bool:
        """Connect to database and create tables"""
        if not ASYNCPG_AVAILABLE:
            logger.error("asyncpg not installed. Install with: pip install asyncpg")
            return False

        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=60
            )

            await self._create_tables()
            self._initialized = True
            logger.info(f"Connected to PostgreSQL at {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        async with self.pool.acquire() as conn:
            yield conn

    async def _create_tables(self):
        """Create required tables"""
        async with self.acquire() as conn:
            # Trades table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    entry_price DECIMAL(20, 8) NOT NULL,
                    exit_price DECIMAL(20, 8),
                    quantity DECIMAL(20, 8) NOT NULL,
                    pnl DECIMAL(20, 8),
                    pnl_percent DECIMAL(10, 4),
                    reason VARCHAR(50),
                    strategy VARCHAR(100),
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Positions table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL,
                    entry_price DECIMAL(20, 8) NOT NULL,
                    quantity DECIMAL(20, 8) NOT NULL,
                    stop_loss DECIMAL(20, 8),
                    take_profit DECIMAL(20, 8),
                    trailing_stop DECIMAL(20, 8),
                    highest_price DECIMAL(20, 8),
                    entry_time TIMESTAMP NOT NULL,
                    is_open BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Candles table (for caching historical data)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS candles (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    interval VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open DECIMAL(20, 8) NOT NULL,
                    high DECIMAL(20, 8) NOT NULL,
                    low DECIMAL(20, 8) NOT NULL,
                    close DECIMAL(20, 8) NOT NULL,
                    volume DECIMAL(30, 8) NOT NULL,
                    UNIQUE(symbol, interval, timestamp)
                )
            ''')

            # Bot state table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_state (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Signals log table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    signal VARCHAR(10) NOT NULL,
                    price DECIMAL(20, 8) NOT NULL,
                    indicators JSONB,
                    strategy VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_positions_is_open ON positions(is_open)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval ON candles(symbol, interval)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON candles(timestamp)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')

            logger.info("Database tables created/verified")

    # ==================== TRADES ====================

    async def save_trade(self, trade: Trade) -> int:
        """Save trade to database"""
        async with self.acquire() as conn:
            row = await conn.fetchrow('''
                INSERT INTO trades (symbol, side, entry_price, exit_price, quantity,
                                   pnl, pnl_percent, reason, strategy, entry_time, exit_time)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            ''', trade.symbol, trade.side, trade.entry_price, trade.exit_price,
                trade.quantity, trade.pnl, trade.pnl_percent, trade.reason,
                trade.strategy, trade.entry_time, trade.exit_time)
            return row['id']

    async def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Trade]:
        """Get trades with optional filters"""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        param_idx = 1

        if symbol:
            query += f" AND symbol = ${param_idx}"
            params.append(symbol)
            param_idx += 1

        if start_date:
            query += f" AND entry_time >= ${param_idx}"
            params.append(start_date)
            param_idx += 1

        if end_date:
            query += f" AND entry_time <= ${param_idx}"
            params.append(end_date)
            param_idx += 1

        query += f" ORDER BY entry_time DESC LIMIT ${param_idx}"
        params.append(limit)

        async with self.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [Trade(**dict(row)) for row in rows]

    async def get_trade_stats(self, symbol: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get trading statistics"""
        start_date = datetime.now() - timedelta(days=days)

        query = '''
            SELECT
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
                COUNT(*) FILTER (WHERE pnl <= 0) as losing_trades,
                COALESCE(SUM(pnl), 0) as total_pnl,
                COALESCE(AVG(pnl) FILTER (WHERE pnl > 0), 0) as avg_win,
                COALESCE(AVG(pnl) FILTER (WHERE pnl <= 0), 0) as avg_loss,
                COALESCE(MAX(pnl), 0) as best_trade,
                COALESCE(MIN(pnl), 0) as worst_trade
            FROM trades
            WHERE entry_time >= $1
        '''
        params = [start_date]

        if symbol:
            query += " AND symbol = $2"
            params.append(symbol)

        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            total = row['total_trades']
            winning = row['winning_trades']

            return {
                'total_trades': total,
                'winning_trades': winning,
                'losing_trades': row['losing_trades'],
                'win_rate': (winning / total * 100) if total > 0 else 0,
                'total_pnl': float(row['total_pnl']),
                'avg_win': float(row['avg_win']),
                'avg_loss': float(row['avg_loss']),
                'best_trade': float(row['best_trade']),
                'worst_trade': float(row['worst_trade']),
                'profit_factor': abs(float(row['avg_win']) / float(row['avg_loss'])) if row['avg_loss'] else 0
            }

    # ==================== POSITIONS ====================

    async def save_position(self, position: Position) -> int:
        """Save or update position"""
        async with self.acquire() as conn:
            if position.id:
                # Update existing
                await conn.execute('''
                    UPDATE positions SET
                        stop_loss = $1, take_profit = $2, trailing_stop = $3,
                        highest_price = $4, is_open = $5, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $6
                ''', position.stop_loss, position.take_profit, position.trailing_stop,
                    position.highest_price, position.is_open, position.id)
                return position.id
            else:
                # Insert new
                row = await conn.fetchrow('''
                    INSERT INTO positions (symbol, side, entry_price, quantity,
                                          stop_loss, take_profit, trailing_stop,
                                          highest_price, entry_time, is_open)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                ''', position.symbol, position.side, position.entry_price, position.quantity,
                    position.stop_loss, position.take_profit, position.trailing_stop,
                    position.highest_price, position.entry_time, position.is_open)
                return row['id']

    async def get_open_position(self, symbol: str) -> Optional[Position]:
        """Get open position for symbol"""
        async with self.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM positions
                WHERE symbol = $1 AND is_open = TRUE
                ORDER BY entry_time DESC LIMIT 1
            ''', symbol)
            return Position(**dict(row)) if row else None

    async def close_position(self, position_id: int):
        """Mark position as closed"""
        async with self.acquire() as conn:
            await conn.execute('''
                UPDATE positions SET is_open = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', position_id)

    # ==================== CANDLES ====================

    async def save_candles(self, candles: List[Candle]):
        """Bulk save candles"""
        if not candles:
            return

        async with self.acquire() as conn:
            await conn.executemany('''
                INSERT INTO candles (symbol, interval, timestamp, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (symbol, interval, timestamp)
                DO UPDATE SET open = $4, high = $5, low = $6, close = $7, volume = $8
            ''', [(c.symbol, c.interval, c.timestamp, c.open, c.high, c.low, c.close, c.volume)
                  for c in candles])

    async def get_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get historical candles"""
        query = '''
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE symbol = $1 AND interval = $2
        '''
        params = [symbol, interval]

        if start_time:
            query += " AND timestamp >= $3"
            params.append(start_time)

        query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        async with self.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in reversed(rows)]

    # ==================== BOT STATE ====================

    async def save_state(self, key: str, value: Any):
        """Save bot state value"""
        import json
        async with self.acquire() as conn:
            await conn.execute('''
                INSERT INTO bot_state (key, value, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
            ''', key, json.dumps(value))

    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get bot state value"""
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT value FROM bot_state WHERE key = $1', key)
            return row['value'] if row else default

    # ==================== SIGNALS ====================

    async def log_signal(
        self,
        symbol: str,
        signal: str,
        price: float,
        indicators: Dict[str, Any],
        strategy: str = ""
    ):
        """Log trading signal"""
        import json
        async with self.acquire() as conn:
            await conn.execute('''
                INSERT INTO signals (symbol, signal, price, indicators, strategy)
                VALUES ($1, $2, $3, $4, $5)
            ''', symbol, signal, price, json.dumps(indicators), strategy)

    async def get_recent_signals(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get recent signals"""
        async with self.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM signals
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT $2
            ''', symbol, limit)
            return [dict(row) for row in rows]


# Singleton instance
_db: Optional[Database] = None


async def get_database() -> Database:
    """Get or create global database instance"""
    global _db
    if _db is None:
        config = DatabaseConfig.from_env()
        _db = Database(config)
        await _db.connect()
    return _db


async def close_database():
    """Close global database instance"""
    global _db
    if _db:
        await _db.close()
        _db = None
