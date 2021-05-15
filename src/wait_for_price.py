# This handles price differences and calls the sell_coins function once a threshold
# has been reached

from datetime import datetime, timedelta
import time

# import local dependencies
from get_price import get_price
from sell import sell_coins
from remove_coins import remove_from_portfolio
from config import PAIR_WITH, TIME_DIFFERENCE, RECHECK_INTERVAL, CHANGE_IN_PRICE, coins_bought, MAX_COINS

def wait_for_price():
    '''calls the initial price and ensures the correct amount of time has passed
    before reading the current price again'''

    volatile_coins = {}
    initial_price = get_price()

    while initial_price['BNB' + PAIR_WITH]['time'] > datetime.now() - timedelta(seconds=TIME_DIFFERENCE):
        i=0
        while i < RECHECK_INTERVAL:
            print(f'checking TP/SL...')
            coins_sold = sell_coins()
            remove_from_portfolio(coins_sold)
            time.sleep((TIME_DIFFERENCE/RECHECK_INTERVAL))
            i += 1
            # let's wait here until the time passess...

        print(f'not enough time has passed yet...')

    else:
        last_price = get_price()
        infoChange = -100.00
        infoCoin = 'none'
        infoStart = 0.00
        infoStop = 0.00

        # calculate the difference between the first and last price reads
        for coin in initial_price:
            threshold_check = (float(last_price[coin]['price']) - float(initial_price[coin]['price'])) / float(initial_price[coin]['price']) * 100

            if threshold_check > infoChange:
                infoChange = threshold_check
                infoCoin = coin
                infoStart = initial_price[coin]['price']
                infoStop = last_price[coin]['price']

            # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict if less than MAX_COINS is not reached.
            if threshold_check > CHANGE_IN_PRICE:
                if len(coins_bought) < MAX_COINS:
                    volatile_coins[coin] = threshold_check
                    volatile_coins[coin] = round(volatile_coins[coin], 3)
                    print(f'{coin} has gained {volatile_coins[coin]}% in the last {TIME_DIFFERENCE} seconds, calculating volume in {PAIR_WITH}')

                else:
                    print(f'{txcolors.WARNING}{coin} has gained {threshold_check}% in the last {TIME_DIFFERENCE} seconds, but you are holding max number of coins{txcolors.DEFAULT}')

        # Print more info if there are no volatile coins this iteration
        if infoChange < CHANGE_IN_PRICE:
                print(f'No coins moved more than {CHANGE_IN_PRICE}% in the last {TIME_DIFFERENCE} second(s)')

        print(f'Max movement {float(infoChange):.2f}% by {infoCoin} from {float(infoStart):.4f} to {float(infoStop):.4f}')

        return volatile_coins, len(volatile_coins), last_price
