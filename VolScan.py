# VolScan is a Binance Volatility Bot(BVT Bot)
# compatible module that generates crypto buying signals based upon negative price change & volatility.
# It does this in two different ways,
# the main one being by calculating the aggregate price change within a user defined period,
# the second way being by use of the Coefficient Of Variation(CV),
# which is a statistical measure of the dispersion of data points in a data series around the mean,
# and is used in certain markets to ascertain the volatility of products:
# https://www.investopedia.com/terms/c/coefficientofvariation.asp.
#
# VolScan provides the option to use either signals generating method individually,
# or combined within user defined settings.
# Volscan will provide all the buying signals required for your bot,
# so other external signal generating modules should be disabled.
#
# The way that VolScan works is that it collects all the cryto coin/token data for all USDT coin
# pairings that appear on Binance into user defined "scanning periods" which are varying numbers of minutes in length,
# each period then being split into the number of individual scans that make up the period.
# Example. you decide you want your scanning period to be 3 minutes in duration,
# and within that period you want all coins scanned every 30 seconds,
# so in total VolScan will carry out 2 scans per minute for 3 minutes in total = 6 price check scans,
# it then checks the variables between the current price & the previous price all the way back through the total number
# of scans, coming up with an aggregate change in price % for the whole scanning period.
# It then removes all coins that have positive changes in price %,
# and creates a list of all the coins that had a negative change in price, the list is in sequential order,
# the highest negative price change at the top, the lowest negative price change at the bottom.
#
# The Coefficient of Variation method works along similar lines,
# but concentrates purely on standard deviation in price ranges,
# the mean or average price which then is calculated into the final CV score for the scanning period....
# the higher the CV score, the higher the volatility of the coins/tokens.
# The CV rated coins are then created into a tickers list in exactly
# the same way as the previously described negative change in price coins.
#
# Whichever way you choose to have your tickers lists created,
# they will then be dynamically updated at the end of every scanning period with a completely new lists
# of the latest high volatilty coin results.
#
# The VolScan module is easy to format with most processes done automatically for you,
# below are the user defined settings you will need to create to get started using the module:


import os
import numpy as np
from time import sleep
from datetime import datetime

from binance.client import Client

from helpers.parameters import parse_args, load_config
# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

# Load trading vars
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
EX_PAIRS = parsed_config['trading_options']['EX_PAIRS']

# Load creds for correct environment
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)


# SCANNING_PERIOD - by default, we check the price difference for each coin on Binance for the last 3 minutes,
# you can change this value for different results.
# This also determines how often each iteration of the code is executed.
SCANNING_PERIOD = 3  # minutes

# TIME_SLEEP - how many seconds do you want between each price scan.
# By default, every 12 seconds the price change will be recorded during SCANNING_PERIOD (3min)
# After which the calculation is performed. The price change is also calculated every 12 seconds.
TIME_SLEEP = 30  # seconds

# If True, an updated list of coins will be generated from the site - http://edgesforledges.com/watchlists/binance.
# If False, then the list you create in TICKERS_LIST = 'tickers.txt' will be used.
CREATE_TICKER_LIST = True

# NUMBER_COINS_IN_LIST - Limit the number of coins that can be added to the dynamic list of volatile coins. For example,
# if NUMBER_COINS_IN_LIST = 20,
# then each period only 20 sorted coins will be added to the list (Above the lowest values with a minus sign).
NUMBER_COINS_IN_LIST = 20

# CV_INDEX - Coefficient of Variation. Only those coins with a COV greater than the specified value will be displayed.
CoV_INDEX = 0.0

# CREATE_LIST_BY_COV_AND_PRICE_CHANGE is a filter for creating dynamic lists of the most volatile coins.
# If COV_FILTER = True, lists of volatile coins will take into account the CoV parameter.
# For example,
# if CoV_INDEX = 0.5, then only coins with CoV above 0.5 and price change less than 0 will be added to list.
# If False will be used only Price Change.
CREATE_LIST_BY_COV_AND_PRICE_CHANGE = False

# CREATE_LIST_BY_ONLY_COV - If True - A dynamic list of volatile coins will be created only based on the CoV parameter.
# For example: If CoV_INDEX = 0.3 then the list will include coins with CoV_INDEX greater than 0.3 and the list will be
# sorted
# (At the top there will be coins with the highest CoV)
# If False The list will be created only based on the Price Change.
CREATE_LIST_BY_ONLY_COV = False

# When creating a ticker list from the source site:
# http://edgesforledges.com you can use the parameter (all or innovation-zone).
# ticker_type = 'innovation-zone'
ticker_type = 'all'
if CREATE_TICKER_LIST:
    TICKERS_LIST = 'tickers_all_USDT.txt'
else:
    TICKERS_LIST = 'tickers.txt'

# BTC_FILTER - This feature is still in development.
# Objective: Check the change in the price of bitcoin over the scanning period and,
# based upon the results, either halt the bot from buying, or allow it to continue.
# make further purchases of coins.
# For example, if Bitcoin price change = 1.0 and coin price change is negative (-0.8), we give a buy signal....
# BTC_FILTER = False


SIGNAL_BOT_NAME = 'VolScan'

class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'
    YELLOW = '\033[33m'
    TURQUOISE = '\033[36m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    ITALICS = '\033[3m'


# get_price() function, takes 1 parameter (Binance client).
# And it returns a dictionary of coins,
# with the given keys ('symbol'(str), 'price'(float), 'time', 'price_list'(list), 'change_price'(float), 'cov'(float)).
def get_price(client_api):
    initial_price = {}
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    prices = client_api.get_all_tickers()

    for coin in prices:
        for item in tickers:
            if item + PAIR_WITH == coin['symbol'] and all(item + PAIR_WITH not in coin['symbol'] for item in EX_PAIRS):
                initial_price[coin['symbol']] = {'symbol': coin['symbol'],
                                                 'price': coin['price'],
                                                 'time': datetime.now(),
                                                 'price_list': [],
                                                 'change_price': 0.0,
                                                 'cov': 0.0}
    return initial_price


# Function с_о_v(), takes 1 parameter (List of coin prices for the period 'price_list': []).
# And it returns the Coefficient of Variation (float) of the coin.
def c_o_v(price_list):
    if price_list:
        a = np.array(price_list, float)
        cov = round((a.std() / a.mean()) * 100, 2)
        return cov
    return 0.0


# Percentage_price_change() function, takes 1 parameter (List of coin prices for the period 'price_list': []).
# And it returns the percentage of price change.
def percentage_price_change(price_list):
    if price_list:
        return round(sum([100 * (b - a) / a for a, b in zip(price_list[::1], price_list[1::1])]), 4)


# sort_list_coins() function, takes 2 parameters (List of coins and sorting type).
# Based on the sorting type, sorts the coins in the list by their 'change_price' or 'cov'.
# And it returns a sorted list.
def sort_list_coins(list_coins, sort_type='change_price'):
    if sort_type == 'cov':
        sort_list = sorted(list_coins, key=lambda x: x[f'{sort_type}'], reverse=True)
    else:
        sort_list = sorted(list_coins, key=lambda x: x[f'{sort_type}'])
    return sort_list


# do_work () function, takes 1 parameter (Binance client). This is the main function of the module.
# Which, in an endless cycle, searches for coins with a negative indicator of price change,
# sorts them and gives buy signals.
def do_work():
    # Initializing coins for data storage.
    init_price = get_price(client)
    list_volatility = []
    count = 0

    while True:
        print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} launched with a period of {SCANNING_PERIOD} minutes.')
        print(f"{txcolors.YELLOW}Number of coins to scan - {len(init_price)}")
        # We reset the data every period.
        if count == (SCANNING_PERIOD * 60) / TIME_SLEEP:
            init_price = get_price(client)
            list_volatility = []
            count = 0

        # Start a cycle to collect prices for each coin within a period.
        while count < (SCANNING_PERIOD * 60) / TIME_SLEEP:
            count += 1
            print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME} Round {count} complete. Next scan in {TIME_SLEEP} seconds.')
            try:
                # Requesting the latest coin prices
                last_price = get_price(client)

                for coin in last_price:
                    # if len(init_price[coin]['price_list']) == (SCANNING_PERIOD * 60) / TIME_SLEEP:
                    #     del init_price[coin]['price_list'][0]
                    init_price[coin]['price_list'].append(float(last_price[coin]['price']))

                    if len(init_price[coin]['price_list']) == (SCANNING_PERIOD * 60) / TIME_SLEEP:
                        coin_price_list = init_price[coin]['price_list']
                        percent_change_price = percentage_price_change(coin_price_list)
                        cov = c_o_v(coin_price_list)

                        if CREATE_LIST_BY_COV_AND_PRICE_CHANGE:
                            condition = percent_change_price < 0 and cov >= CoV_INDEX

                        elif CREATE_LIST_BY_ONLY_COV:
                            condition = cov >= CoV_INDEX

                        else:
                            condition = percent_change_price < 0

                        if condition:
                            if init_price[coin] not in list_volatility:
                                init_price[coin]['time'] = datetime.now()
                                init_price[coin]['change_price'] = percent_change_price
                                init_price[coin]['cov'] = cov

                                list_volatility.append(init_price[coin])

                if not list_volatility:
                    print(f'{txcolors.YELLOW}Stand by for next update ...')
                else:
                    if os.path.exists('signals/vol_scan.exs'):
                        os.remove('signals/vol_scan.exs')

                    if CREATE_LIST_BY_ONLY_COV:
                        sort_t = 'cov'
                    else:
                        sort_t = 'change_price'
                    sort_list_vol_coin = sort_list_coins(list_volatility, sort_type=sort_t)

                    for item in sort_list_vol_coin[:NUMBER_COINS_IN_LIST]:
                        print(f'{txcolors.YELLOW}{SIGNAL_BOT_NAME}: detected a signal on{txcolors.END} '
                              f'{txcolors.YELLOW}{item["symbol"]}{txcolors.END}'
                              )
                        with open('signals/vol_scan.exs', 'a+') as f:
                            f.write(item["symbol"] + '\n')

                sleep(TIME_SLEEP)
            except Exception as e:
                print(e)
