"""
{
    "s": "BNBBTC",   # pair
    "st": "TRADING", # status
    "b": "BNB",      # pair
    "q": "BTC",      # base currency
    "ba": "",
    "qa": "฿",
    "i": "0.01000000",
    "ts": "0.000001",
    "an": "BNB",
    "qn": "Bitcoin",
    "o": "0.009115",
    "h": "0.009312",
    "l": "0.009077",
    "c": "0.009087",    # price
    "v": "136281.190000",
    "qv": "1253.70501168",
    "y": 0,
    "as": 136281.19,
    "pm": "BTC",
    "pn": "BTC",
    "cs": 168137036,    # capacity in tokens (can be null)
    "tags": [
        "pos",
        "mining-zone",
        "BSC"
    ],
    "pom": false,
    "pomt": null,
    "etf": false
}
"""
import re
from typing import List

import requests

from VolScan import txcolors


class BinanceMarketCapFetcher:
    PRODUCTS_URL = 'https://www.binance.com/exchange-api/v2/public/asset-service/product/get-products'

    def __init__(self, n_top=100, base_coin='usdt', output_filename='tickers_new.txt', exclude_list=None):
        self.n_top = n_top
        self.base_coin = base_coin
        self.output_filename = output_filename
        self.exclude_list = exclude_list or []

    def execute(self):
        list_of_top_n = self._fetch_market_cap_top_for_coin(self.n_top, self.base_coin)
        with open(self.output_filename, 'w+') as f:
            for p in list_of_top_n:
                if p['b'] not in self.exclude_list:
                    f.write(f"{p['b']}\n")

    @classmethod
    def _fetch_market_cap_top_for_coin(cls, n_top: int, base_coin: str) -> List[dict]:
        products = cls._fetch_products(cls.PRODUCTS_URL)
        products = cls._filter_products_by_base_coin(base_coin=base_coin, products=products)
        products = cls._sort_products_by_capacity(products)[:n_top]
        return cls._sort_products_by_name(products)

    @classmethod
    def _fetch_products(cls, url: str) -> List[dict]:
        response = requests.get(url)
        data = response.json()
        return data['data']

    @staticmethod
    def _capacity_sorting_key(product):
        coin_price = product.get('c')
        coin_count = product.get('cs')
        if coin_count and coin_price:
            return float(coin_count) * float(coin_price)
        return 0.0

    @classmethod
    def _sort_products_by_capacity(cls, products: List[dict]) -> List[dict]:
        return sorted(products, key=cls._capacity_sorting_key, reverse=True)

    @classmethod
    def _sort_products_by_name(cls, products: List[dict]) -> List[dict]:
        return sorted(products, key=lambda p: p['b'])

    @classmethod
    def _filter_products_by_base_coin(cls, base_coin: str, products):
        return [p for p in products if p['q'].lower() == base_coin.lower()]


SELL_PROFIT = '\033[32m'


def create_ticker_list(path, base_coin, exclude_list, url):
    response = requests.get(url)

    with open(path, 'w') as f:
        for line in response.text.splitlines():
            if line.endswith(base_coin):
                currency = re.sub(r'BINANCE:(.*)' + base_coin, r'\1', line)
                if currency not in exclude_list:
                    f.writelines(currency + '\n')
    print(f'{SELL_PROFIT}>> Tickers CREATED from {url} tickers!!! {path} <<')
