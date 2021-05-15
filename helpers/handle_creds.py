def load_correct_creds(creds, TESTNET):
    if TESTNET:
        return creds['test']['access_key'], creds['prod']['secret_key']
    else:
        return creds['prod']['access_key'], creds['prod']['secret_key']
