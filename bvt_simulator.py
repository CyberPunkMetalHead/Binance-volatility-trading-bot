#!/usr/bin/env python
# coding: utf-8

import backtrader as bt
import matplotlib.pyplot as plt
import pandas
from datetime import datetime
import time
import os
import yaml
import pprint
from colorama import init
init()

# https://backtest-rookies.com/2017/08/22/backtrader-multiple-data-feeds-indicators/
# https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot
# https://github.com/CyberPunkMetalHead/backtesting-for-cryptocurrency-trading

'''
Simulation of binance volitility trading bot with Backtrader

Still in development.

problems:

- at the start you need patience  
- tradingview_ta desion making. tradingview_ta does not support historical data. 
- plotting is a mess.

nextstep:

- parameter optimization with genetic algorithm (CHANGE_IN_PRICE, STOP_LOSS, TAKE_PROFIT)
	script is finish, needs testing 

support my work with XMR:

82qBQZdxqAua1jqGnZ2gXQ2p5pwp4x433JbUWkVcJSLLWQwLf7gHrPPB5AFfu9wPDT2aonCieW1WhBTL1S8DHAmA91xTWEn

'''

# backtrader strategy
class bvtStrategy(bt.Strategy):
    #oneplot = Force all datas to plot on the same master.
    params = dict(oneplot=False)

    def __init__(self):
        
        for i, d in enumerate(self.datas):
            if i > 0: 
                if self.p.oneplot == True:
                    d.plotinfo.plotmaster = self.datas[0]

    def log(self, txt, dt=None, dtt=None):
        dt = dt or self.datas[0].datetime.date(0)
        dtt = dtt or self.datas[0].datetime.time(0)
        print('{0} {1} {2}'.format(dt.isoformat(),dtt.isoformat(),txt))

    def notify_trade(self, trade):
        """ notification of closed trades."""
        if trade.isclosed:
            if trade.pnlcomm > 0: # green plus
                self.log('\033[32m{} SELL EXECUTED, PnL Gross {}, Net {}\033[39m'.format(
                                                trade.data._name,
                                                round(trade.pnl,4), # current profit and loss of the trade 
                                                round(trade.pnlcomm,4))) # current profit and loss of the trade minus commission 
            else: # red minus
                self.log('\033[91m{} SELL EXECUTED, PnL Gross {}, Net {}\033[39m'.format(
                                                trade.data._name,
                                                round(trade.pnl,4), # current profit and loss of the trade 
                                                round(trade.pnlcomm,4))) # current profit and loss of the trade minus commission 

    def notify_order(self, order):
        """ notification of changes to orders """    
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('\033[31m{0} Order Canceled/Margin/Rejected\033[39m'.format(order.data._name))

        if order.status in [order.Completed]: 
            if order.isbuy():
                # MAX_COINS, USE_TRAILING_STOP_LOSS
                boughtCoins[order.data._name] = {
                    'stop_loss': STOP_LOSS,
                    'take_profit': TAKE_PROFIT,
                }
                self.log('{0} BUY  EXECUTED, Price: {1:8.4f}, Cost: {2:8.4f}, Comm: {3:8.4f}'.format(
                    order.data._name,
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm))
                
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                del(boughtCoins[order.data._name])
            #     self.log('{0} SELL EXECUTED, Price: {1:8.4f}, Cost: {2:8.4f}, Comm{3:8.4f}'.format(
            #         order.data._name,
            #         order.executed.price, 
            #         order.executed.value,
            #         order.executed.comm))

    def next(self):
        # for each coin 
        for i, d in enumerate(self.datas): 
            shares = 0 # buy volume
            dtd, dtt, dn = self.datetime.date(),  self.datetime.time(), d._name
            pos = self.getposition(d).size
            
            # no open trade with coin
            if not self.getposition(d).size:      
                if d.close[0] > d.close[-1] + (d.close[-1]*CHANGE_IN_PRICE/100):
                    # check max coins reached 
                    if len(boughtCoins) == MAX_COINS:
                        self.log('\033[31mMAX_COINS reached, cant buy {0}\033[39m'.format(dn))
                        pass
                    else:
                        shares = QUANTITY / d.close[0] 
                        shares = round(shares,6)
                        self.order = self.buy(data=d, size=shares)

            # trade open with coin     
            else:  
                # more or less copy paste from bvt 
                TP = self.getposition(d).price + (self.getposition(d).price * boughtCoins[dn]['take_profit']) / 100
                SL = self.getposition(d).price + (self.getposition(d).price * boughtCoins[dn]['stop_loss']) / 100
                PriceChange = (d.close[0] - self.getposition(d).price) / self.getposition(d).price * 100
                if d.close[0] > TP and USE_TRAILING_STOP_LOSS:
                    boughtCoins[dn]['stop_loss'] = boughtCoins[dn]['take_profit'] - TRAILING_STOP_LOSS
                    boughtCoins[dn]['take_profit'] = PriceChange + TRAILING_TAKE_PROFIT
                    self.log(f"\033[37m{dn} TP reached, adjusting TP {boughtCoins[dn]['take_profit']:.2f} and SL {boughtCoins[dn]['stop_loss']:.2f} accordingly to lock-in profit\033[39m")

                if d.close[0] < SL or d.close[0] > TP and not USE_TRAILING_STOP_LOSS:
                    self.order = self.close(data=d)

class OandaCSVData(bt.feeds.GenericCSVData):
    params = (
        ('nullvalue', float('NaN')),
        ('fromdate', datetime(2021, 1, 1)),
        ('todate', datetime(2021, 6, 1)),
        ('dtformat', lambda x: datetime.utcfromtimestamp(float(x) / 1000.0)),
        ('datetime', 0),
        ('high', 1),
        ('low', 2),
        ('open', 3),
        ('close', 4),
        ('volume', -1),
        ('openinterest', -1),
        ('timeframe', bt.feeds.TimeFrame.Minutes),
    )

def backtesting(plot=False, logging=False, **strategy_params):

    # set account balance double as required 
    initial_capital = (QUANTITY * MAX_COINS) * 2

    # create an instance of cerebro
    cerebro = bt.Cerebro()

    # add our strategy
    cerebro.addstrategy(bvtStrategy, oneplot=False)

    # list of coins 
    with open('data/coins.txt', 'r') as f:
        coins = f.readlines()
        coins = [coin.strip('\n') for coin in coins]

    # create our data list
    datalist = []
    since = '1 Jan 2021'
    for coin in coins:
        #[0] = Data file, [1] = Data name
        datalist.append(('data/'+coin+'_'+since+'.csv', coin))
        
    # loop through the list adding to cerebro.
    for i in range(len(datalist)):
        data = OandaCSVData(dataname=datalist[i][0])
        cerebro.resampledata(data, name=datalist[i][1], timeframe=bt.TimeFrame.Minutes, compression=TIME_DIFFERENCE)

    # set our desired cash start
    cerebro.broker.setcash(initial_capital)

    # add commision
    cerebro.broker.setcommission(commission=TRADING_FEE, margin=False)

    # add analyzer 
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    #cerebro.addanalyzer(bt.analyzers.BasicerebroTradeStats, filter='all') # backtrader beta    

    # run everything
    strats = cerebro.run()

    # get results
    profit = cerebro.broker.getvalue() - initial_capital
    max_dd = strats[0].analyzers.drawdown.get_analysis()["max"]["moneydown"]
    pmd = profit / (max_dd if max_dd > 0 else 1)

    if logging:
        print(f"Starting Portfolio Value: {initial_capital:,.2f}")
        print(f"Final Portfolio Value:    {cerebro.broker.getvalue():,.2f}")
        print(f"Total Profit:             {profit:,.2f}")
        print(f"Maximum Drawdown:         {max_dd:,.2f}")
        print(f"Profit / Max DD:          {pmd}")

    #if plot:
        figure = cerebro.plot(volume=False,style ='bar')
        #figure.savefig('bvt_plot.png')

# read the actual config file from bvt bot.
def load_config(file):
    try:
        with open(file) as file:
            return yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError as fe:
        exit(f'Could not find {file}')
        
parsed_config = load_config('config.yml') 

CHANGE_IN_PRICE = parsed_config['trading_options']['CHANGE_IN_PRICE']
STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
QUANTITY = parsed_config['trading_options']['QUANTITY']
MAX_COINS = parsed_config['trading_options']['MAX_COINS']
TRADING_FEE = .00075 # .00075 is 0.075% in backtrader 
USE_TRAILING_STOP_LOSS = parsed_config['trading_options']['USE_TRAILING_STOP_LOSS']
TRAILING_STOP_LOSS = parsed_config['trading_options']['TRAILING_STOP_LOSS']
TRAILING_TAKE_PROFIT = parsed_config['trading_options']['TRAILING_TAKE_PROFIT']
TIME_DIFFERENCE = parsed_config['trading_options']['TIME_DIFFERENCE'] 

#pp = pprint.PrettyPrinter(indent=4)
#pp.pprint(parsed_config)

# simple way for MAX_COINS and USE_TRAILING_STOP_LOSS
global boughtCoins
boughtCoins = {}

# start stop watch 
t = time.perf_counter()

# run backtest
backtesting(logging=True, plot=False)

# end stop watch
end_t = time.perf_counter()
print(f"Time Elapsed: {end_t - t:,.2f}")