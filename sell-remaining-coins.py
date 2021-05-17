import json
import os
from binance.client import Client


# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)

args = parse_args()
DEFAULT_CREDS_FILE = 'creds.yml'

creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)

access_key, secret_key = load_correct_creds(parsed_creds)

client = Client(access_key, secret_key)

with open('coins_bought.json', 'r') as f:
    coins = json.load(f)

    for coin in list(coins):
        client.create_order(
            symbol = coin,
            side = 'SELL',
            type = 'MARKET',
            quantity = coins[coin]['volume']
        )

os.remove('coins_bought.json')






