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

        if LOG_TRADES:
            timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
            write_log(f"Sell: {coins[coin]['volume']} {coin} - {BuyPrice} - {LastPrice} Profit: {profit:.2f} {PriceChange:.2f}%")

os.remove('../coins_bought.json')