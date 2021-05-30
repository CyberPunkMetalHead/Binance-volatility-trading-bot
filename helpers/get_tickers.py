#from tradingview_ta import Interval, get_multiple_analysis


def get_new_tickers(client, PAIR_WITH, FIATS):
    """Get all tickers that can be paired with current base currency"""
    prices = client.get_all_tickers()
    # test_tickers = []
    tickers = []
    # new_analysis = []

    # MY_EXCHANGE = "BINANCE"
    # MY_SCREENER = "CRYPTO"
    # MY_FIRST_INTERVAL = Interval.INTERVAL_1_MINUTE
    # PAIR_WITH = "USDT"

    # analysis = get_multiple_analysis(exchange=MY_EXCHANGE, screener=MY_SCREENER, interval=MY_FIRST_INTERVAL, timeout=10)
    # clears tickers.txt
    with open("tickers.txt", "r+") as handle:
        handle.truncate(0)

    for coin in prices:

        if coin["symbol"].endswith(PAIR_WITH) and all(item not in coin["symbol"] for item in FIATS):
            value = coin["symbol"].replace(PAIR_WITH, "")
            # # print(coin["symbol"], value)

            if value:
                # test_tickers.append(f"{MY_EXCHANGE}:{coin['symbol']}")
                tickers.append(value)
                #     # saved for future use if needed
                #     # appends tickers.txt
                with open("tickers.txt", "a+") as handle:
                    handle.write(value + "\n")
    # print(test_tickers)
    # new_analysis = get_multiple_analysis(screener=MY_SCREENER, interval=MY_FIRST_INTERVAL, symbols=test_tickers)
    # print(new_analysis)

    return tickers
