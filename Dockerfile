# Binance Trading Bot - Production Dockerfile
# Optimized for Railway deployment

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY simple_bot/ ./simple_bot/

# Create directories for logs and data persistence
RUN mkdir -p /app/logs /app/data

# Set volume mount points
VOLUME ["/app/logs", "/app/data"]

# Environment variables (to be set at runtime)
ENV BINANCE_API_KEY="" \
    BINANCE_API_SECRET="" \
    TELEGRAM_BOT_TOKEN="" \
    TELEGRAM_CHAT_ID="" \
    TELEGRAM_ENABLED="true" \
    TRADING_SYMBOL="BTCUSDT" \
    TRADING_INTERVAL="1h" \
    TRADE_AMOUNT_USDT="100" \
    FAST_PERIOD="76" \
    SLOW_PERIOD="209" \
    FILTER_PERIOD="23" \
    TRAILING_STOP_PCT="0.0389" \
    STOP_LOSS_PCT="0.0476" \
    TAKE_PROFIT_PCT="0" \
    PAPER_TRADING="true" \
    INITIAL_CAPITAL="10000" \
    LOG_LEVEL="INFO" \
    LOG_DIR="/app/logs" \
    STATE_DIR="/app/data"

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "-m", "simple_bot.live_bot"]
