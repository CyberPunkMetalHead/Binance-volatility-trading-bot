# The main modules that executes the script repeatedly

# import local dependencies
from trade import buy
from sell import sell_coins
from update_portfolio import update_portfolio
from remove_coins import remove_from_portfolio

if __name__ == '__main__':

    while True:
        orders, last_price, volume = buy()
        update_portfolio(orders, last_price, volume)
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
