import traceback
from pymongo import MongoClient
from time import time
DEF_COLLECTIONS = [
    'trades', 'portfolio'
]
DEF_DB_NAME="bvt"
DEF_DB_CLIENT = "mongodb://localhost:27017/"
def timestamp():
    return int(time())

def delete_database(db_client=DEF_DB_CLIENT):
    c = MongoClient(db_client)
    c.drop_database('bvt')


def insert_dummy_data(db_client=DEF_DB_CLIENT, db_name=DEF_DB_NAME, collections=DEF_COLLECTIONS):
    """Important: In MongoDB, a collection is not created until it gets content!"""
    c = MongoClient(db_client)
    mydb = c[db_name]
    for table in collections:
        if table == "trades":
            data = {
                "timestamp": timestamp(),
                "operation": "XXX",
                "amount": 0.0,
                "symbol": "XXX",
                "bought_at": 0.0,
                "sold_at": 0.0,
                "profit_usd": 0,
                "profit_percentage": 0
            }
        if table == "portfolio":
            data = {
                "symbol": "XXX",
                "orderid": 0,
                "timestamp": timestamp(),
                "bought_at": "4.68200000",
                "volume": 0,
                "stop_loss": -1,
                "take_profit": 0
            }

        mycol = mydb[table]

        x = mycol.insert_one(data)
        
    return True



def initalize_db(db_client=DEF_DB_CLIENT, db_name=DEF_DB_NAME, collections=DEF_COLLECTIONS):
    c = MongoClient(db_client)
    db_names = c.list_database_names()
    print(db_names)
    if db_name in db_names:
        print('db exists')
        return False, c[db_name].list_collection_names()
    else:
        print('db doesnt exist creating now')
        # make db
        mydb = c[db_name]

        # make collections
        for table in collections:
            mydb[table]

        return mydb
        

def insert(data, collection, db_client=DEF_DB_CLIENT, db_name=DEF_DB_NAME):
    c = MongoClient(db_client)
    mydb = c[db_name]
    mycol = mydb[collection]
    x = mycol.insert_one(data)
    return x.inserted_id

def delete(data, collection, db_client=DEF_DB_CLIENT, db_name=DEF_DB_NAME):
    c = MongoClient(db_client)
    mydb = c[db_name]
    mycol = mydb[collection]
    x = mycol.delete_one(data)
    return x.deleted_count