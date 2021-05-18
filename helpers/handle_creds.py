def load_correct_creds(creds):
    return creds['prod']['access_key'], creds['prod']['secret_key']





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
        if e.code == -2015:
            return False, "Your API key is not formatted correctly..."
        elif e.code == -2014:
            return False, "Your API key is either incorrect, IP blocked, or incorrect tld/permissons..."
        else:
            return False, e
    
    except Exception as e:
        print(f"Fallback exception occured:\n{e}")
        return False, "fail"
