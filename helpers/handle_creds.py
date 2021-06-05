from sys import exit


def load_correct_creds(creds):
    try:

        return creds['prod']['access_key'], creds['prod']['secret_key']
    
    except TypeError as te:
        message = 'Your credentials are formatted incorectly\n'
        message += f'TypeError:Exception:\n\t{str(te)}'
        exit(message)
    except Exception as e:
        message = 'oopsies, looks like you did something real bad. Fallback Exception caught...\n'
        message += f'Exception:\n\t{str(e)}'
        exit(message)
        

def test_api_key(client, BinanceAPIException):
    """Checks to see if API keys supplied returns errors

    Args:
        client (class): binance client class
        BinanceAPIException (clas): binance exeptions class

    Returns:
        bool | msg: true/false depending on success, and message
    """
    try:
        client.get_account()
        return True, "API key validated succesfully"
    
    except BinanceAPIException as e:   
    
      
        if e.code in  [-2015,-2014]:
            bad_key = "Your API key is not formatted correctly..."
            america = "If you are in america, you will have to update the config to set AMERICAN_USER: True"
            ip_b = "If you set an IP block on your keys make sure this IP address is allowed. check ipinfo.io/ip"
            
            msg = f"Your API key is either incorrect, IP blocked, or incorrect tld/permissons...\n  most likely: {bad_key}\n  {america}\n  {ip_b}"

        elif e.code == -2021:
            issue = "https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot/issues/28"
            desc = "Ensure your OS is time synced with a timeserver. See issue."
            msg = f"Timestamp for this request was 1000ms ahead of the server's time.\n  {issue}\n  {desc}"
        elif e.code == -1021:
            desc = "Your operating system time is not properly synced... Please sync ntp time with 'pool.ntp.org'"
            msg = f"{desc}\nmaybe try this:\n\tsudo ntpdate pool.ntp.org"
        else:
            msg = "Encountered an API Error code that was not caught nicely, please open issue...\n"
            msg += str(e)

        return False, msg
    
    except Exception as e:
        return False, f"Fallback exception occured:\n{e}"

