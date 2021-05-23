

def ensure_user_has_enough_funds(client, MAX_COINS, QUANTITY, PAIR_WITH):
    """Ensures user has enough currency so the script wont fail on buying

    Returns:
        bool, str:
    """
    balance = client.get_asset_balance(asset=PAIR_WITH)
    free = int(float(balance['free']))
    locked_currency = int(float(balance['locked']))
    TOTAL_FUNDS_REQUIRED = (MAX_COINS * QUANTITY)

    
    if TOTAL_FUNDS_REQUIRED > free:
        message = f"Your current config set {MAX_COINS} coins at a quanity of {QUANTITY} {PAIR_WITH}. This requires you to have {TOTAL_FUNDS_REQUIRED} {PAIR_WITH} in your account (MAX_COINS * QUANTITY)."
        message += f" You do not have enough {PAIR_WITH} in your account for the current config. You have {free} {PAIR_WITH}."
        if locked_currency:
            message += f" You also have {locked_currency} {PAIR_WITH} locked."
            ready = False
        
    else:
        ready = True
        message = f"You have {free}{PAIR_WITH}. Proceeding..."

    return ready, message