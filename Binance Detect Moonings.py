# use for environment variables
import os

# needed for the binance API and websockets
from binance.client import Client

# used for dates
from datetime import datetime, timedelta
import time

# used to repeatedly execute the code
from itertools import count

# used to store trades and sell assets
import json


# Switch between testnet and mainnet
# Setting this to False will use REAL funds, use at your own risk
# Define your API keys below in order for the toggle to work
TESTNET = True


# Get binance key and secret for TEST and MAINNET
# The keys below are pulled from environment variables using os.getenv
# Simply remove this and use the following format instead: api_key_test = 'YOUR_API_KEY'
api_key_test = os.getenv('binance_api_stalkbot_testnet')
api_secret_test = os.getenv('binance_secret_stalkbot_testnet')

api_key_live = os.getenv('binance_api_stalkbot_live')
api_secret_live = os.getenv('binance_secret_stalkbot_live')


# Authenticate with the client
if TESTNET:
    client = Client(api_key_test, api_secret_test)

    # The API URL needs to be manually changed in the library to work on the TESTNET
    client.API_URL = 'https://testnet.binance.vision/api'

else:
    client = Client(api_key_live, api_secret_live)



####################################################
#                   USER INPUTS                    #
# You may edit to adjust the parameters of the bot #
####################################################

# select what to pair the coins to and pull all coins paied with PAIR_WITH
PAIR_WITH = 'USDT'

# Define the size of each trade, by default in USDT
QUANTITY = 100

# List of pairs to exlcude
# by default we're excluding the most popular fiat pairs
# and some margin keywords, as we're only working on the SPOT account
FIATS = ['EURUSDT', 'GBPUSDT', 'JPYUSDT', 'USDUSDT', 'DOWN', 'UP']

# the amount of time in MINUTES to calculate the differnce from the current price
TIME_DIFFERENCE = 5

# the difference in % between the first and second checks for the price, by default set at 10 minutes apart.
CHANGE_IN_PRICE = 3

# define in % when to sell a coin that's not making a profit
STOP_LOSS = 3

# define in % when to take profit on a profitable coin
TAKE_PROFIT = 6

####################################################
#                END OF USER INPUTS                #
#                  Edit with care                  #
####################################################




# try to load all the coins bought by the bot if the file exists and is not empty
coins_bought = {}

# path to the saved coins_bought file
coins_bought_file_path = 'coins_bought.json'

# use separate files for testnet and live
if TESTNET:
    coins_bought_file_path = 'testnet_' + coins_bought_file_path

# if saved coins_bought json file exists and it's not empty then load it
if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
    with open(coins_bought_file_path) as file:
            coins_bought = json.load(file)


def get_price():
    '''Return the current price for all coins on binance'''

    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:

        # only Return USDT pairs and exlcude margin symbols like BTCDOWNUSDT
        if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
            initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}

    return initial_price


def wait_for_price():
    '''calls the initial price and ensures the correct amount of time has passed
    before reading the current price again'''

    volatile_coins = {}
    initial_price = get_price()

    while initial_price['BNBUSDT']['time'] > datetime.now() - timedelta(minutes=TIME_DIFFERENCE):
        print(f'not enough time has passed yet...')

        # let's wait here until the time passess...
        time.sleep(60*TIME_DIFFERENCE)

    else:
        last_price = get_price()

        # calculate the difference between the first and last price reads
        for coin in initial_price:
            threshold_check = (float(last_price[coin]['price']) - float(initial_price[coin]['price'])) / float(last_price[coin]['price']) * 100

            # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict
            if threshold_check > CHANGE_IN_PRICE:
                volatile_coins[coin] = threshold_check
                volatile_coins[coin] = round(volatile_coins[coin], 3)

                print(f'{coin} has gained {volatile_coins[coin]}% in the last {TIME_DIFFERENCE} minutes, calculating volume in {PAIR_WITH}')

        if len(volatile_coins) < 1:
                print(f'No coins moved more than {CHANGE_IN_PRICE}% in the last {TIME_DIFFERENCE} minute(s)')

        return volatile_coins, len(volatile_coins), last_price


def convert_volume():
    '''Converts the volume given in QUANTITY from USDT to the each coin's volume'''

    volatile_coins, number_of_coins, last_price = wait_for_price()
    lot_size = {}
    volume = {}

    for coin in volatile_coins:

        # Find the correct step size for each coin
        # max accuracy for BTC for example is 6 decimal points
        # while XRP is only 1
        try:
            info = client.get_symbol_info(coin)
            step_size = info['filters'][2]['stepSize']
            lot_size[coin] = step_size.index('1') - 1

            if lot_size[coin] < 0:
                lot_size[coin] = 0

        except:
            pass

        # calculate the volume in coin from QUANTITY in USDT (default)
        volume[coin] = float(QUANTITY / float(last_price[coin]['price']))

        # define the volume with the correct step size
        if coin not in lot_size:
            volume[coin] = float('{:.1f}'.format(volume[coin]))

        else:
            volume[coin] = float('{:.{}f}'.format(volume[coin], lot_size[coin]))

    return volume, last_price


def buy():
    '''Place Buy market orders for each volatile coin found'''

    volume, last_price = convert_volume()
    orders = {}

    for coin in volume:

        # only buy if the there are no active trades on the coin
        if coin not in coins_bought or coins_bought[coin] == None:
            print(f' preparing to buy {volume[coin]} {coin}')

            if TESTNET :
                # create test order before pushing an actual order
                test_order = client.create_test_order(symbol=coin, side='BUY', type='MARKET', quantity=volume[coin])

            # try to create a real order if the test orders did not raise an exception
            try:
                buy_limit = client.create_order(
                    symbol=coin,
                    side='BUY',
                    type='MARKET',
                    quantity=volume[coin]
                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(e)

            # run the else block if the position has been placed and return order info
            else:
                orders[coin] = client.get_all_orders(symbol=coin, limit=1)
        else:
            print(f'Signal detected, but there is already an active trade on {coin}')

    return orders, last_price, volume


def sell_coins():
    '''sell coins that have reached the STOP LOSS or TAKE PROFIT thershold'''

    last_price = get_price()
    #global coins_bought
    coins_sold = {}

    for coin in list(coins_bought):
        # define stop loss and take profit
        TP = float(coins_bought[coin]['bought_at']) + (float(coins_bought[coin]['bought_at']) * TAKE_PROFIT) / 100
        SL = float(coins_bought[coin]['bought_at']) - (float(coins_bought[coin]['bought_at']) * STOP_LOSS) / 100

        # check that the price is above the take profit or below the stop loss
        if float(last_price[coin]['price']) > TP or float(last_price[coin]['price']) < SL:
            print(f"TP or SL reached, selling {coins_bought[coin]['volume']} {coin}...")

            if TESTNET :
                # create test order before pushing an actual order
                test_order = client.create_test_order(symbol=coin, side='SELL', type='MARKET', quantity=coins_bought[coin]['volume'])

            # try to create a real order if the test orders did not raise an exception
            try:
                sell_coins_limit = client.create_order(
                    symbol=coin,
                    side='SELL',
                    type='MARKET',
                    quantity=coins_bought[coin]['volume']
                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(e)

            # run the else block if coin has been sold and create a dict for each coin sold
            else:
                coins_sold[coin] = coins_bought[coin]
        else:
            print(f'TP or SL not yet reached, not selling {coin} for now...')

    return coins_sold


def update_porfolio(orders, last_price, volume):
    '''add every coin bought to our portfolio for tracking/selling later'''

    for coin in orders:
        coins_bought[coin] = {
            'symbol': orders[coin][0]['symbol'],
            'orderid': orders[coin][0]['orderId'],
            'timestamp': orders[coin][0]['time'],
            'bought_at': last_price[coin]['price'],
            'volume': volume[coin]
            }

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)


def remove_from_portfolio(coins_sold):
    '''Remove coins sold due to SL or TP from portofio'''
    for coin in coins_sold:
        coins_bought.pop(coin)

    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=4)




if __name__ == '__main__':
    print('Press Ctrl-Q to stop the script')

    if not TESTNET:
        print('WARNING: You are using the Mainnet and live funds. As a safety measure, the script will start executing in 30 seconds.')
        time.sleep(30)

    for i in count():
        orders, last_price, volume = buy()
        update_porfolio(orders, last_price, volume)
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
