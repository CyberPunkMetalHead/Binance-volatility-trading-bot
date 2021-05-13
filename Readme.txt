This Binance trading bot analyses the changes in price across all coins on Binance and place trades on the most volatile ones. 
In addition to that, this Binance trading algorithm will also keep track of all the coins bought and sell them according to your specified Stop Loss and Take Profit.

The bot will listen to changes in price accross all Coins on Binance*
By default we're only picking USDT pairs
We're excluding Margin (like BTCDOWNUSDT) and Fiat pairs
The bot checks if the any coin has gone up by more than 3% in the last 5 minutes
The bot will buy 100 USDT of the most volatile coins on Binance
The bot will sell at 6% profit or 3% stop loss
The bot works with both Main and Testnet

Requirements: python-binance .7.9

For a step-by-step guide on how to implement and configure this bot please see the guide at: 
https://www.cryptomaton.org/2021/05/08/how-to-code-a-binance-trading-bot-that-detects-the-most-volatile-coins-on-binance/

In order to run this script in the background without demonizing, you can execute it in the following way (Linux only):
# nohup python3 -u Binance\ Detect\ Moonings.py >> log.txt 2>&1 &
The logs are stored in log.txt.
To stop the process either look in your process list with `ps aux | grep -i python3` and kill with `kill PROCESS_ID` or `killall python3` when you know what you're doing.
