# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException

from helpers.get_config import config
from helpers.handle_creds import test_api_key
from helpers.colors import txcolors


def auth():
    # Authenticate with the client, Ensure API key is good before continuing
    data, key = config()

    AMERICAN_USER = data["AMERICAN_USER"]
    TESTNET = data["TESTNET"]

    if AMERICAN_USER:
        client = Client(key["access_key"], key["secret_key"], tld="us")
    else:
        # Authenticate with the client
        if TESTNET:
            client = Client(key["access_key"], key["secret_key"])
            # The API URL needs to be manually changed in the library to work on the TESTNET
            client.API_URL = "https://testnet.binance.vision/api"
            print("Connected to TESTNET")
        else:
            client = Client(key["access_key"], key["secret_key"])
            print("Connected to MAINNET")

    # If the users has a bad / incorrect API key.
    # this will stop the script from starting, and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f"{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}")

    return client
