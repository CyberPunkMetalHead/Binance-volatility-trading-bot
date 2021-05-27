import json
try:

    with open('../coins_bought.json') as f:
        prod_coins = json.load(f)
    
except Exception:
    prod_coins = []
    pass
try:
    with open('../test_coins_bought.json') as f:
        test_coins = json.load(f)
except Exception:
    test_coins = []
    pass
print(f'prod_coins: {len(prod_coins)}')
print(f'test_coins: {len(test_coins)}')
print('\n\n')