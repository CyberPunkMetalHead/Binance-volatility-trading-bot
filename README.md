# Binance Volitility Trading Bot

This Binance trading bot analyses the changes in price across all coins on Binance and place trades on the most volatile ones. 
In addition to that, this Binance trading algorithm will also keep track of all the coins bought and sell them according to your specified Stop Loss and Take Profit.



The bot will listen to changes in price accross all coins on Binance. By default we're only picking USDT pairs. We're excluding Margin (like BTCDOWNUSDT) and Fiat pairs

> Information below is an example and is all configurable

- The bot checks if the any coin has gone up by more than 3% in the last 5 minutes
- The bot will buy 100 USDT of the most volatile coins on Binance
- The bot will sell at 6% profit or 3% stop loss
- The bot works with both Main and Testnet


You can follow the [Biance volatility bot guide](https://www.cryptomaton.org/2021/05/08/how-to-code-a-binance-trading-bot-that-detects-the-most-volatile-coins-on-binance/) for a step-by-step walkthrough

## READ BEFORE USE
1. If you use the mainnet, you will be using REAL money.
2. To ensure you do not do this, ALWAYS check the `TESTNET` variable in the script.
3. This might change when you pull / rebase. Always review (we're hoping to param this.)


## Usage

1. Install Dependencies
    - Easy mode (might clash with current depends)
        ```sh
        pip install -r requirements.txt
        ```
    - Prefered Method (venv)
        ```sh
        python3 -m venv .venv
      
        source .venv/bin/activate # linux
        source .venv/scripts/activate # windows
    
        pip install -r requirements.txt
        ```


2. Copy `creds.example.yml` to `creds.yml` (or whatever you want.) and update the creds.

    ```sh
    cp creds.example.yml > creds.yml
    ```
   ***
   ###in ubuntu use  
   
   ``` sh 
   cp creds.example.yml  creds.yml
   ```
   ***
    ```yml
    # MAIN NET
    prod:
        access_key: replace_me
        secret_key: replace_me

    # TEST NET
    test:
        access_key: replace_me
        secret_key: replace_me
    ```


3. Configure input params as in `config.yml`

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

5. Use the `--help` flag if you want to see supported arguments

## Troubleshooting

1. Read the [FAQ](FAQ.md)
2. Open an issue / check us out on `#troubleshooting` at [Discord](https://discord.gg/buD27Dmvu3) 🚀 
    - Do not spam, do not berate, we are all humans like you, this is an open source project, not a full time job. 
