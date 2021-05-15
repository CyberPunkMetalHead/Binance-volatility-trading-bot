# This module handles the sell logic of our bot

# Import dependencies
from get_price import get_price
from config import coins_bought, client, TRAILING_TAKE_PROFIT, TRAILING_STOP_LOSS, USE_TRAILING_STOP_LOSS, LOG_TRADES, TESTNET
from colors import txcolors
from save_trade import write_log


def sell_coins():
    '''sell coins that have reached the STOP LOSS or TAKE PROFIT threshold'''

    last_price = get_price()
    coins_sold = {}

    for coin in list(coins_bought):
        # define stop loss and take profit
        TP = float(coins_bought[coin]['bought_at']) + (float(coins_bought[coin]['bought_at']) * coins_bought[coin]['take_profit']) / 100
        SL = float(coins_bought[coin]['bought_at']) + (float(coins_bought[coin]['bought_at']) * coins_bought[coin]['stop_loss']) / 100


        LastPrice = float(last_price[coin]['price'])
        BuyPrice = float(coins_bought[coin]['bought_at'])
        PriceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        if float(last_price[coin]['price']) > TP and USE_TRAILING_STOP_LOSS:
            print("TP reached, adjusting TP and SL accordingly to lock-in profit")

            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
            coins_bought[coin]['take_profit'] += TRAILING_TAKE_PROFIT
            coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS

            continue

        # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
        if float(last_price[coin]['price']) < SL or (float(last_price[coin]['price']) > TP and not USE_TRAILING_STOP_LOSS):
            print(f"{txcolors.SELL}TP or SL reached, selling {coins_bought[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} : {PriceChange:.2f}%{txcolors.DEFAULT}")

            if TESTNET :
                # create test order before pushing an actual order
                test_order = client.create_test_order(symbol=coin, side='SELL', type='MARKET', quantity=coins_bought[coin]['volume'])

            # try to create a real order if the test orders did not raise an exception
            try:

                sell_coins_limit = client.create_order(
                    symbol = coin,
                    side = 'SELL',
                    type = 'MARKET',
                    quantity = coins_bought[coin]['volume']

                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(e)

            # run the else block if coin has been sold and create a dict for each coin sold
            else:
                coins_sold[coin] = coins_bought[coin]
                # Log trade

                if LOG_TRADES:
                    profit = (LastPrice - BuyPrice) * coins_sold[coin]['volume']
                    write_log(f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%")
            continue

        # no action
        print(f'TP or SL not yet reached, not selling {coin} for now {BuyPrice} - {LastPrice} : {PriceChange:.2f}% ')

    return coins_sold
