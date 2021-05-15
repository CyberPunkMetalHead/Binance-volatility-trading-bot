from datetime import datetime, timedelta
import os # file lookups
import time

# third party modules
from binance.client import Client
from colorama import init # pretty output


# Module for loading creds and config
from helpers.parameters import (
    load_creds, get_creds_for_env,
    parse_args, load_config
)

# Modules for reading and writing files
from helpers.file_operations import (
    write_log, update_coins_json, load_json_file,
)


# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL = '\033[91m'
    DEFAULT = '\033[39m'


def get_price():
    '''Return the current price for all coins on binance'''

    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:

        if CUSTOM_LIST:
            if any(item + PAIR_WITH == coin['symbol'] for item in tickers) and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}
        else:
            if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = { 'price': coin['price'], 'time': datetime.now()}

    return initial_price


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
            # if lot size has 0 decimal points, make the volume an integer
            if lot_size[coin] == 0:
                volume[coin] = int(volume[coin])
            else:
                volume[coin] = float('{:.{}f}'.format(volume[coin], lot_size[coin]))

    return volume, last_price


def buy():
    '''Place Buy market orders for each volatile coin found'''

    volume, last_price = convert_volume()
    orders = {}

    for coin in volume:

        # only buy if the there are no active trades on the coin
        if coin not in coins_bought:
            print(f"{txcolors.BUY}Preparing to buy {volume[coin]} {coin}{txcolors.DEFAULT}")

            if TESTNET:
                # create test order before pushing an actual order
                test_order = client.create_test_order(symbol=coin, side='BUY', type='MARKET', quantity=volume[coin])

            # try to create a real order if the test orders did not raise an exception
            try:
                buy_limit = client.create_order(
                    symbol = coin,
                    side = 'BUY',
                    type = 'MARKET',
                    quantity = volume[coin]
                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(e)

            # run the else block if the position has been placed and return order info
            else:
                orders[coin] = client.get_all_orders(symbol=coin, limit=1)

                # binance sometimes returns an empty list, the code will wait here until binance returns the order
                while orders[coin] == []:
                    print('Binance is being slow in returning the order, calling the API again...')

                    orders[coin] = client.get_all_orders(symbol=coin, limit=1)
                    time.sleep(1)

                else:
                    print('Order returned, saving order to file')

                    # Log trade
                    if LOG_TRADES:
                        write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}", LOG_FILE)


        else:
            print(f'Signal detected, but there is already an active trade on {coin}')

    return orders, last_price, volume


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
                    write_log(f"Sell: {coins_sold[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%", LOG_FILE)
            continue

        # no action
        print(f'TP or SL not yet reached, not selling {coin} for now {BuyPrice} - {LastPrice} : {PriceChange:.2f}% ')

    return coins_sold


def update_portfolio(orders, last_price, volume):
    '''add every coin bought to our portfolio for tracking/selling later'''
    if DEBUG: print(orders)
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
        update_coins_json(coins_bought_file_path, coins_bought, 'w')
        # with open(coins_bought_file_path, 'w') as file:
        #     json.dump(coins_bought, file, indent=4)

        print(f'Order with id {orders[coin][0]["orderId"]} placed and saved to file')


def remove_from_portfolio(coins_sold):
    '''Remove coins sold due to SL or TP from portfolio'''
    for coin in coins_sold:
        coins_bought.pop(coin)

    update_coins_json(coins_bought_file_path, coins_bought, 'w')
    # with open(coins_bought_file_path, 'w') as file:
    #     json.dump(coins_bought, file, indent=4)



if __name__ == '__main__':
    init() # colorama
    # Load arguments then parse settings
    args = parse_args()

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_creds(creds_file)

    # Default no debugging
    DEBUG = False

    (PROD_WAIT_TIME, TESTNET, LOG_TRADES, LOG_FILE, DEBUG_SETTING,
    PAIR_WITH, QUANTITY, MAX_COINS, FIATS,
    TIME_DIFFERENCE, RECHECK_INTERVAL, CHANGE_IN_PRICE,
    STOP_LOSS, TAKE_PROFIT,CUSTOM_LIST, USE_TRAILING_STOP_LOSS,
    TRAILING_STOP_LOSS, TRAILING_TAKE_PROFIT) = load_config(config_file)

    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers=[line.strip() for line in open('tickers.txt')]

    if DEBUG_SETTING or args.debug:
        DEBUG = True

    # Load creds for correct envionment
    # If testnet true in config.yml, load test keys
    access_key, secret_key = get_creds_for_env(parsed_creds, TESTNET)

    # Default file path
    coins_bought_file_path = 'coins_bought.json'

    # Authenticate with the client
    if TESTNET:
        coins_bought_file_path = 'testnet_' + coins_bought_file_path
        client = Client(access_key, secret_key)

        # API URL needs to be manually changed for TESTNET
        client.API_URL = 'https://testnet.binance.vision/api'

    else:
        print('WARNING: You are using the Mainnet and live funds.')
        print(f'Waiting {PROD_WAIT_TIME} seconds as a security measure\n\n')
        time.sleep(PROD_WAIT_TIME)
        client = Client(access_key, secret_key)


    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}
    # if saved coins_bought json file exists and it's not empty then load it
    if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size!= 0:
        coins_bought = load_json_file(coins_bought_file_path)
        # with open(coins_bought_file_path) as file:
        #         coins_bought = json.load(file)

    print('Press Ctrl-Q or Keyboard Interupt to stop the script')
    while True:
        orders, last_price, volume = buy()
        update_portfolio(orders, last_price, volume)
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)

