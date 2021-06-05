import sys
sys.path.append('..')

import json
import os
from binance.client import Client
from datetime import datetime

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)

from colorama import init
init()

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'


args = parse_args()

DEFAULT_CONFIG_FILE = '../config.yml'
DEFAULT_CREDS_FILE = '../creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
LOG_FILE_PATH = '../' + LOG_FILE

access_key, secret_key = load_correct_creds(parsed_creds)

client = Client(access_key, secret_key)

def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE_PATH,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')

with open('../coins_bought.json', 'r') as f:
    coins = json.load(f)
    total_profit = 0
    total_price_change = 0

    for coin in list(coins):
        sell_coin = client.create_order(
            symbol = coin,
            side = 'SELL',
            type = 'MARKET',
            quantity = coins[coin]['volume']
        )

        BuyPrice = float(coins[coin]['bought_at'])
        LastPrice = float(sell_coin['fills'][0]['price'])
        profit = (LastPrice - BuyPrice) * coins[coin]['volume']
        PriceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

        total_profit += profit
        total_price_change += PriceChange

        text_color = txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS
        console_log_text = f"{text_color}Sell: {coins[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%{txcolors.DEFAULT}"
        print(console_log_text)

        if LOG_TRADES:
            timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
            write_log(f"Sell: {coins[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%")
    
    text_color = txcolors.SELL_PROFIT if total_price_change >= 0. else txcolors.SELL_LOSS
    print(f"Total Profit: {text_color}{total_profit:.2f}{txcolors.DEFAULT}. Total Price Change: {text_color}{total_price_change:.2f}%{txcolors.DEFAULT}")

os.remove('../coins_bought.json')