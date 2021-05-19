
import requests
# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)
# Load creds modules
from helpers.handle_creds import (
    load_telegram_creds
)

# Load arguments then parse settings
args = parse_args()
mymodule = {}
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)

TELEGRAM_LOGGING = parsed_config['script_options']['TELEGRAM_LOGGING']

# Telegram Bot
TELEGRAM_CHANNEL_ID, TELEGRAM_TOKEN = load_telegram_creds(parsed_creds)

def log(*args):
    if TELEGRAM_LOGGING:
        payload = {
                'chat_id': TELEGRAM_CHANNEL_ID,
                'text': ' '.join(map(str, args)),
                'parse_mode': 'HTML',
                'disable_notification': 'TRUE'
            }
        return requests.post("https://api.telegram.org/bot{token}/sendMessage".format(token=TELEGRAM_TOKEN), data=payload).content
