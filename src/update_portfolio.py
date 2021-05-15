"""
This module adds every coin bought to our json portfolio file.
"""

import json

from config import DEBUG, coins_bought_file_path, coins_bought, STOP_LOSS, TAKE_PROFIT


def update_portfolio(orders, last_price, volume):
    """Add every coin bought to our portfolio for tracking/selling later."""

    if DEBUG:
        print(orders)

    for coin in orders:
        coins_bought[coin] = {
            'symbol': orders[coin][0]['symbol'],
            'orderid': orders[coin][0]['orderId'],
            'timestamp': orders[coin][0]['time'],
            'bought_at': last_price[coin]['price'],
            'volume': volume[coin],
            'stop_loss': -STOP_LOSS,
            'take_profit': TAKE_PROFIT,
        }

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)

        print(f'Order with id {orders[coin][0]["orderId"]} placed and saved to file')
