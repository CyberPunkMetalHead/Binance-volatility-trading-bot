from pymongo import MongoClient
import random

# SETUP
def fake_orderid():
    """returns a fake order id by hashing the current time"""
    return random.randint(100000000,999999999)

def my_client():
    return MongoClient('localhost', 27017)

def initialize_database(database, tables=['portfolio', 'trades']):
    client = my_client()
    db = client[database]
    ids = []
    print('MONGO: DBs and Collections are not created until data is stored in them...')
    for table in tables:
        print(f'MONGO: the {table} table does exist in {database} database, creating now...')
        x = db[table]
       


def see_if_db_exists(default_dbs=['bvt','bvt-test']):
    client = my_client()
    dbnames = client.list_database_names()

    for db in default_dbs:
        if db not in dbnames:
            print(f'MONGO: the {db} does not exist, creating now...')
            initialize_database(db)



# CRUD
def insert_trades(data, database, table='trades'):
    client = my_client()
    db = client[database]
    table = db[table]
    x = table.insert_one(data)
    return x

def delete_portolio_item(data, database,table='portfolio'):
    client = my_client()
    db = client[database]
    table = db[table]
    x = table.delete_one(data)
    return x.raw_result

def insert_portfolio(data,database,table='portfolio'):
    """inserts entry into porfolio collection

    Args:
        client (class): dbclient
        data (dict): 
            example: {
            
                "symbol": "BTCUSDT",
                "orderid": 0,
                "timestamp": 1621952968.171957,
                "bought_at": "37871.49000000",
                "volume": 26.405087,
                "stop_loss": -2.9,
                "take_profit": 0.8
            }
    Returns:
        [str]: db_row_id
    """
    client = my_client()
    db = client[database]
    table = db[table]
    x = table.insert_one(data)
    return x

