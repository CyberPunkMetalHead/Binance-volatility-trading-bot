# Binance Volitility Trading Bot

This Binance trading bot analyses the changes in price across all coins on Binance and place trades on the most volatile ones. 
In addition to that, this Binance trading algorithm will also keep track of all the coins bought and sell them according to your specified Stop Loss and Take Profit.



The bot will listen to changes in price accross all coins on Binance. By default we're only picking USDT pairs. We're excluding Margin (like BTCDOWNUSDT) and Fiat pairs

> Information below is an example and is all configurable

- The bot checks if the any coin has gone up by more than 3% in the last 5 minutes
- The bot will buy 100 USDT of the most volatile coins on Binance
- The bot will sell at 6% profit or 3% stop loss
- The bot works with both Main and Testnet


You can follow the [following guide](https://www.cryptomaton.org/2021/05/08/how-to-code-a-binance-trading-bot-that-detects-the-most-volatile-coins-on-binance/) for a step-by-step walkthrough

## READ BEFORE USE
1. If you use the mainnet, you will be using REAL money.
2. To ensure you do not do this, ALWAYS check the `TESTNET` variable in the script.
3. This might change when you pull / rebase. Always review (we're hoping to param this.)


## Usage

1. Install Dependencies
    ```sh
    pip install -r requirements.txt
    ```

2. Set environment variables for API Keys
    - Linux
        ```sh
        # FOR MAINNET
        export binance_api_stalkbot_live="Your key"
        export binance_secret_stalkbot_live="Your secret"

        # TESTNET
        export binance_api_stalkbot_testnet="Your key"
        export binance_secret_stalkbot_testnet="Your secret"
        ```
    - [Windows](https://superuser.com/questions/79612/setting-and-getting-windows-environment-variables-from-the-command-prompt)


3. Configure input params as necessary
    ```py
    ####################################################
    #                   USER INPUTS                    #
    # You may edit to adjust the parameters of the bot #
    ####################################################
    # select what to pair the coins to and pull all coins paied with PAIR_WITH
    
    PAIR_WITH = 'USDT'

    # Define the size of each trade, by default in USDT
    QUANTITY = 15

    # Define max numbers of coins to hold
    MAX_COINS = 10
    ... # redacted full list
    ```

4. Run the script
    - Standard 
        ```sh
        python3 Binance\ Detect\ Moonings.py
        ```
    - Background process (**linux only**)
        ```sh
        nohup python3 -u Binance\ Detect\ Moonings.py >> log.txt 2>&1 &
        ```
        The logs are stored in log.txt. To stop the process either look in your process list with `ps aux | grep -i python3` and kill with `kill PROCESS_ID` or `killall python3` when you know what you're doing.


## Troubleshooting

1. Read the [FAQ](FAQ.md)
2. Open an issue / check us out on `#troubleshooting` at [Discord](https://discord.gg/buD27Dmvu3) 🚀 
    - Do not spam, do not berate, we are all humans like you, this is an open source project, not a full time job. 