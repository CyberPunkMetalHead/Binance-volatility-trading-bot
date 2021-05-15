from src.remove_coins import remove_from_portfolio
from src.sell import sell_coins
from src.trade import buy
from src.update_portfolio import update_portfolio


def main():
    while True:
        orders, last_price, volume = buy()
        update_portfolio(orders, last_price, volume)
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)


if __name__ == '__main__':
    main()
