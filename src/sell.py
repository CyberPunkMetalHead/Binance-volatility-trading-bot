"""
This module handles the sell logic of our bot.
"""
from binance.helpers import round_step_size

from .colors import txcolors
from .config import coins_bought, client, TRAILING_TAKE_PROFIT, TRAILING_STOP_LOSS, USE_TRAILING_STOP_LOSS, LOG_TRADES, TESTNET
from .get_price import get_price
from .save_trade import write_log


def sell_coins():
    """Sell coins that have reached the STOP LOSS or TAKE PROFIT threshold."""

    current_prices = get_price()
    coins_sold = {}

    for coin in list(coins_bought):
        last_price = float(current_prices[coin]['price'])
        buy_price = float(coins_bought[coin]['bought_at'])
        price_change = float((last_price - buy_price) / buy_price * 100)

        TP = buy_price + (buy_price * coins_bought[coin].get('take_profit', 1)) / 100
        SL = buy_price + (buy_price * coins_bought[coin].get('stop_loss', 1)) / 100

        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        if last_price > TP and USE_TRAILING_STOP_LOSS:
            print("TP reached, adjusting TP and SL accordingly to lock-in profit")

            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
            coins_bought[coin]['take_profit'] += TRAILING_TAKE_PROFIT
            coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS

            continue

        # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
        if last_price < SL or last_price > TP:
            print(f"{txcolors.SELL}TP or SL reached, selling {coins_bought[coin]['volume']} {coin} - {buy_price} - {last_price} : {price_change:.2f}%{txcolors.DEFAULT}")

            if TESTNET:
                # create test order before pushing an actual order
                test_order = client.create_test_order(symbol=coin, side='SELL', type='MARKET', quantity=coins_bought[coin]['volume'])

            # try to create a real order if the test orders did not raise an exception
            try:
                try:
                    rounded_amount = round_step_size(coins_bought[coin]['volume'], coins_bought[coin]['step_size'])
                except:
                    tick_size = float(
                        next(
                            filter(
                                lambda f: f['filterType'] == 'LOT_SIZE',
                                client.get_symbol_info(coin)['filters']
                            )
                        )['stepSize']
                    )
                    rounded_amount = round_step_size(coins_bought[coin]['volume'], tick_size)

                client.create_order(
                    symbol=coin,
                    side='SELL',
                    type='MARKET',
                    quantity=rounded_amount,
                )

            except Exception as e:
                print(e)

            # run the else block if coin has been sold and create a dict for each coin sold
            else:
                coins_sold[coin] = coins_bought[coin]
                # Log trade

                if LOG_TRADES:
                    profit = (last_price - buy_price) * coins_sold[coin]['volume']
                    write_log(f"Sell: {coins_sold[coin]['volume']} {coin} - {buy_price} - {last_price} Profit: {profit:.2f} {price_change:.2f}%")

            continue

        # no action
        print(f'TP or SL not yet reached, not selling {coin} for now {buy_price} - {last_price} : {price_change:.2f}% ')

    return coins_sold
