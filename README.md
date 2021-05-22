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
        .\.venv/scripts/activate # windows
    
        pip install -r requirements.txt
        ```


2. Copy `creds.example.yml` to `creds.yml` (or whatever you want.) and update the creds.

    ```sh
    cp creds.example.yml > creds.yml
    ```
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
    - Systemd service (**linux only**)
    
    	The systemd-version used for this setup is `219`, we'll be using a `venv` for python and `nano` for text-operations, the sample user is called `ec2-user` and the bot is cloned to `/home/ec2-user/bot`.
        
        `Paste code in nano = mouse-rightclick`

    	`SAVE file in nano = CTRL + O followed by ENTER`
        
    	`EXIT file in nano = CTRL + X`

    	Create the service config file via opening the texteditor 'nano'
        ```sh
        sudo nano /lib/systemd/system/binancebot.service
        ```

        Paste the following code into the file, edit paths and user in WorkingDirectory, User and ExecStart to suite your settings, SAVE and EXIT
        ```sh
        [Unit]
        Description=Binance Bot Service
        After=multi-user.target

        [Service]
        Type=idle
        WorkingDirectory=/home/ec2-user/bot
        User=ec2-user
        ExecStart=/home/ec2-user/bot/.venv/bin/python3 -u '/home/ec2-user/bot/Binance Detect Moonings.py'
        StandardOutput=syslog
        StandardError=syslog
        SyslogIdentifier=binance-bot

        [Install]
        WantedBy=multi-user.target
        ```

        Create the rsyslog configuration via opening the texteditor 'nano'
        ```sh
        sudo nano /etc/rsyslog.d/binancebot.conf
        ```

        Paste the following code into the file (rightclick), SAVE and EXIT
        ```sh
        template(name="bot-tmplt" type="string"
        		 string="%msg:1:$%\n"
        		)
        if $programname == "binance-bot" then /var/log/binancebot/bot.log;bot-tmplt
        & stop
		```

		Create the logfile folder
		```sh
        sudo mkdir /var/log/binancebot
        ```

        Just to be on the safe side: Create the logfile in the folder, SAVE and EXIT
		```sh
        sudo nano /var/log/binancebot/bot.log
        ```

        Refresh services list
		```sh
        sudo systemctl daemon-reload
        ```

        Restart rsyslog service (i think this could be skipped as we are rebooting soon)
		```sh
        sudo systemctl restart rsyslog
        ```

        Enable the Binance Bot service to run at system boot
		```sh
        sudo systemctl enable binancebot
        ```

        Reboot the machine
		```sh
        sudo reboot
        ```

        Now we have setup the bot as a service and it autostarts with the machine. 
        
        **How to / Commands:**
        
        We can manually start, stop, restart and view the status of the service with the following commands:
        ```sh
        sudo systemctl start binancebot
        ```
        ```sh
        sudo systemctl stop binancebot
        ```
        ```sh
        sudo systemctl restart binancebot
        ```
        ```sh
        sudo systemctl status binancebot
        ```

        To view the log file we can use e.g. tail or mutlitail (if installed)
        ```sh
        tail -f -n 100 /var/log/binancebot/bot.log
        ```

        Any changes to the config files of either of the services will need to be applied with at least:
        ```sh
        sudo systemctl daemon-reload
        sudo systemctl restart SERVICENAME
        ```

        Changing the config.yml of the bot requires `sudo systemctl restart binancebot` to be applied.

5. Use the `--help` flag if you want to see supported arguments

## Troubleshooting

1. Read the [FAQ](FAQ.md)
2. Open an issue / check us out on `#troubleshooting` at [Discord](https://discord.gg/buD27Dmvu3) 🚀 
    - Do not spam, do not berate, we are all humans like you, this is an open source project, not a full time job. 
