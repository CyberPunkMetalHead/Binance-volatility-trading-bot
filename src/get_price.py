from datetime import datetime

from .config import client, CUSTOM_LIST, PAIR_WITH, FIATS, tickers


def get_price():
    """Return the current price for all coins on binance."""

    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:

        if CUSTOM_LIST:
            coin_is_in_ticker = any(item + PAIR_WITH in coin['symbol'] for item in tickers)
        else:
            coin_is_in_ticker = PAIR_WITH in coin['symbol']

        coin_is_not_in_blocklist = all(item not in coin['symbol'] for item in FIATS)

        if coin_is_in_ticker and coin_is_not_in_blocklist:
            initial_price[coin['symbol']] = {
                'price': coin['price'],
                'time': datetime.now(),
            }

    return initial_price
