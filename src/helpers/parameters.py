import argparse

import yaml

DEFAULT_SETTINGS_FILE = 'settings.json'


def load_config(file):
    with open(file) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def parse_args():
    x = argparse.ArgumentParser()
    x.add_argument('--debug', '-d', help="extra logging", action='store_true')
    x.add_argument('--config', '-c', help="Path to config.yml")
    x.add_argument('--creds', '-u', help="Path to creds file")
    return x.parse_args()
