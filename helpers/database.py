import sqlite3
import time
from sqlite3 import Error
import os

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), '../storage/log.db')
DEFAULT_LOG_TABLE = 'logs'
DEFAULT_COIN_TABLE = 'coins'


def connect(db_path=DEFAULT_PATH):
    return sqlite3.connect(db_path)


def create_if_null(db_path=DEFAULT_PATH):
    
    try:
        conn = sqlite3.connect(db_path)
        
        conn.close()
    except Error as e:
        print(e)


def see_if_dbs_exist(db_path=DEFAULT_PATH):

    if not os.path.exists(db_path):
        create_if_null(db_path)
        create_tables(db_path)
        print(f'Creating DBs sqlite v{sqlite3.version} @ {db_path}')
    
        return True
    else:
        print('DBs already there')
        return True

 
def create_tables(db_path=DEFAULT_PATH, log_table=DEFAULT_LOG_TABLE, coin_table=DEFAULT_COIN_TABLE):
    con = connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        f"""
        CREATE TABLE {coin_table}(
            id integer PRIMARY KEY AUTOINCREMENT, 
            symbol text, 
            orderid int, 
            timestamp int, 
            bought_at text, 
            volume float,
            stop_loss float,
            take_profit float
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE {log_table}(
            id integer PRIMARY KEY AUTOINCREMENT,
            timestamp int, 
            date text,
            event text
        )
        """
    )
    con.commit()


def insert_log(conn, log_msg, log_table=DEFAULT_LOG_TABLE):
    ts = int(time.time())
    dt=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
    sql = f"""
        INSERT INTO {log_table}(timestamp,date,event)
              VALUES({ts},'{dt}','{log_msg}')
    """
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

    return cur.lastrowid


def get_coin_id(conn, orderid, coin_table=DEFAULT_COIN_TABLE):
    cur = conn.cursor()
    sql = f'select * from {coin_table} where orderid = {orderid}'
    cur.execute(sql)
    row = cur.fetchall()
    
    # should only be 1 orderid
    return row[0][0]
    

def insert_coin(conn, data, coin_table=DEFAULT_COIN_TABLE):
    #TODO: Structure the data better bought at should be float
    ts = int(time.time())
    
    symbol = data['symbol']
    orderid = data['orderid']
    bought_at = float(data['bought_at'])
    volume = data['volume']
    stop_loss = data['stop_loss']
    take_profit = data['take_profit']
  
    sql = f"""
        INSERT INTO {coin_table}(symbol,orderid,timestamp,bought_at,volume,stop_loss,take_profit)
            VALUES('{symbol}',{orderid},{ts},{bought_at},{volume},{stop_loss},{take_profit})"""
    cur = conn.cursor()

    cur.execute(sql)
    conn.commit()

    return cur.lastrowid


def delete_coin(conn, row_id, coin_table=DEFAULT_COIN_TABLE):
    sql = f'DELETE FROM {coin_table} where id = {row_id}'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
