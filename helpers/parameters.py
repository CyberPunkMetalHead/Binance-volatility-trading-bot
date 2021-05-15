import yaml
import argparse


def get_creds_for_env(creds, TESTNET):
    if TESTNET:
        return creds['test']['access_key'], creds['prod']['secret_key']
    else:
        return creds['prod']['access_key'], creds['prod']['secret_key']


def load_creds(file):
    with open(file) as file:
        content = yaml.load(file, Loader=yaml.FullLoader)
    return content

def load_config(file):
    with open(file) as file:
        content = yaml.load(file, Loader=yaml.FullLoader)


    # Load system vars
    TESTNET = content['script_options']['TESTNET']
    PROD_WAIT_TIME = content['script_options']['PROD_WAIT_TIME']
    LOG_TRADES = content['script_options'].get('LOG_TRADES')
    LOG_FILE = content['script_options'].get('LOG_FILE')
    DEBUG_SETTING = content['script_options'].get('DEBUG')

    # Load trading vars
    PAIR_WITH = content['trading_options']['PAIR_WITH']
    QUANTITY = content['trading_options']['QUANTITY']
    MAX_COINS = content['trading_options']['MAX_COINS']
    FIATS = content['trading_options']['FIATS']
    TIME_DIFFERENCE = content['trading_options']['TIME_DIFFERENCE']
    RECHECK_INTERVAL = content['trading_options']['RECHECK_INTERVAL']
    CHANGE_IN_PRICE = content['trading_options']['CHANGE_IN_PRICE']
    STOP_LOSS = content['trading_options']['STOP_LOSS']
    TAKE_PROFIT = content['trading_options']['TAKE_PROFIT']
    CUSTOM_LIST = content['trading_options']['CUSTOM_LIST']
    USE_TRAILING_STOP_LOSS = content['trading_options']['USE_TRAILING_STOP_LOSS']
    TRAILING_STOP_LOSS = content['trading_options']['TRAILING_STOP_LOSS']
    TRAILING_TAKE_PROFIT = content['trading_options']['TRAILING_TAKE_PROFIT']

    return (
        PROD_WAIT_TIME, TESTNET, LOG_TRADES, LOG_FILE, DEBUG_SETTING, 
        
        PAIR_WITH, QUANTITY, MAX_COINS, FIATS, TIME_DIFFERENCE,
        RECHECK_INTERVAL, CHANGE_IN_PRICE, STOP_LOSS, TAKE_PROFIT,
        CUSTOM_LIST, USE_TRAILING_STOP_LOSS, TRAILING_STOP_LOSS, TRAILING_TAKE_PROFIT
    )


def parse_args():
    x = argparse.ArgumentParser()
    x.add_argument('--debug', '-d', help="extra logging", action='store_true')
    x.add_argument('--config', '-c', help="Path to config.yml")
    x.add_argument('--creds', '-u', help="Path to creds file")
    return x.parse_args()