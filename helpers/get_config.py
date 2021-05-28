# Load helper modules
from helpers.parameters import parse_args, load_config
from helpers.handle_creds import load_correct_creds

# used to store trades and sell assets
import json


def config():

    data = dict()
    # Load arguments then parse settings
    args = parse_args()

    DEFAULT_CONFIG_FILE = "config.yml"
    DEFAULT_CREDS_FILE = "creds.yml"

    data["config_file"] = args.config if args.config else DEFAULT_CONFIG_FILE
    data["creds_file"] = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(data["config_file"])
    parsed_creds = load_config(data["creds_file"])

    # Load system vars
    data["TEST_MODE"] = parsed_config["script_options"]["TEST_MODE"]
    data["LOG_TRADES"] = parsed_config["script_options"].get("LOG_TRADES")
    data["LOG_FILE"] = parsed_config["script_options"].get("LOG_FILE")
    data["DEBUG"] = parsed_config["script_options"].get("DEBUG")
    data["AMERICAN_USER"] = parsed_config["script_options"].get("AMERICAN_USER")
    data["TESTNET"] = parsed_config["script_options"].get("TESTNET")

    # Load trading vars
    data["PAIR_WITH"] = parsed_config["trading_options"]["PAIR_WITH"]
    data["QUANTITY"] = parsed_config["trading_options"]["QUANTITY"]
    data["MAX_ORDERS"] = parsed_config["trading_options"]["MAX_ORDERS"]
    data["MAX_COINS"] = parsed_config["trading_options"]["MAX_COINS"]
    data["FIATS"] = parsed_config["trading_options"]["FIATS"]
    data["TIME_DIFFERENCE"] = parsed_config["trading_options"]["TIME_DIFFERENCE"]
    data["RECHECK_INTERVAL"] = parsed_config["trading_options"]["RECHECK_INTERVAL"]
    data["CHANGE_IN_PRICE"] = parsed_config["trading_options"]["CHANGE_IN_PRICE"]
    data["STOP_LOSS"] = parsed_config["trading_options"]["STOP_LOSS"]
    data["TAKE_PROFIT"] = parsed_config["trading_options"]["TAKE_PROFIT"]
    data["CUSTOM_LIST"] = parsed_config["trading_options"]["CUSTOM_LIST"]
    data["TICKERS_LIST"] = parsed_config["trading_options"]["TICKERS_LIST"]
    data["USE_TRAILING_STOP_LOSS"] = parsed_config["trading_options"]["USE_TRAILING_STOP_LOSS"]
    data["TRAILING_STOP_LOSS"] = parsed_config["trading_options"]["TRAILING_STOP_LOSS"]
    data["TRAILING_TAKE_PROFIT"] = parsed_config["trading_options"]["TRAILING_TAKE_PROFIT"]
    data["TRADING_FEE"] = parsed_config["trading_options"]["TRADING_FEE"]
    data["SIGNALLING_MODULES"] = parsed_config["trading_options"]["SIGNALLING_MODULES"]

    # Load signalling vars
    data["EXCHANGE"] = parsed_config["signalling_options"]["EXCHANGE"]
    data["SCREENER"] = parsed_config["signalling_options"]["SCREENER"]
    data["TIME_TO_WAIT"] = parsed_config["signalling_options"]["TIME_TO_WAIT"]
    data["FULL_LOG"] = parsed_config["signalling_options"]["FULL_LOG"]

    # perform certain checks
    if data["DEBUG"] or args.debug:
        data["DEBUG"] = True
        print(f"loaded config below\n{json.dumps(parsed_config, indent=4)}")
        print(f"Your credentials have been loaded from {data['creds_file']}")

    if args.notimeout:
        data["NOTIMEOUT"] = True

    # Load creds for correct environment
    key = dict()

    if data["TESTNET"]:
        key["access_key"], key["secret_key"] = load_correct_creds(parsed_creds, "test")
    else:
        key["access_key"], key["secret_key"] = load_correct_creds(parsed_creds, "prod")

    return data, key
