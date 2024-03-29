# -*- coding: utf-8 -*-
# 引入掘金量化api，用于下载数据
'''
需要安装掘金量化客户端及python依赖包，注册用户及登录
具体用法见其官网：http://www.myquant.cn
'''
from datetime import datetime
import json

from gmsdk.api import StrategyBase
import pymongo
from vnpy.trader.app.ctaStrategy.ctaBase import DAILY_DB_NAME
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.ctaBase import TICK_DB_NAME
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtObject import VtTickData




# 引入工具类
# 引入vnpy数据库配置
class MyStrategy(StrategyBase):
    
    def __init__(self, *args, **kwargs):
        super(MyStrategy, self).__init__(*args, **kwargs)
        
        # 创建MongoDB连接
        self.client = pymongo.MongoClient('localhost', 27017)
        print u'MongoDB连接成功'
        
        
    def on_login(self):
        print('掘金账号登录成功')
    
    def on_error(self, err_code, msg):
        print('get error: %s - %s' % (err_code, msg))
        
    def on_tick(self, tick):
        print tick.strtime
        vtTick = VtTickData()
        
        # 代码相关
        vtTick.symbol = tick.sec_id              # 合约代码
        vtTick.exchange = tick.exchange            # 交易所代码
        vtTick.vtSymbol = vtTick.symbol + '.' + vtTick.exchange         # 合约在vt系统中的唯一代码，通常是 合约代码.交易所代码
        
        # 成交数据
        vtTick.lastPrice = tick.last_price            # 最新成交价
        vtTick.lastVolume = tick.last_volume             # 最新成交量
        vtTick.volume = tick.cum_volume                  # 今天总成交量
        vtTick.openInterest = tick.cum_position           # 持仓量
        
        dt = datetime.fromtimestamp(tick.utc_time) 
        vtTick.time = dt.strftime('%H:%M:%S.%f')                # 时间 11:20:56.5
        vtTick.date = dt.strftime('%Y%m%d')               # 日期 20151009
        vtTick.datetime = dt                   # python的datetime时间对象
        
        # 常规行情
        vtTick.openPrice = tick.open            # 今日开盘价
        vtTick.highPrice = tick.high            # 今日最高价
        vtTick.lowPrice = tick.low             # 今日最低价
        vtTick.preClosePrice = tick.pre_close   #昨收
        
        vtTick.upperLimit = tick.upper_limit           # 涨停价
        vtTick.lowerLimit = tick.lower_limit           # 跌停价
        
        # 五档行情，有几档行情就插入几档行情
        try:
            vtTick.bidPrice1 = tick.bids[0][0]
            vtTick.askPrice1 = tick.asks[0][0]
            vtTick.bidVolume1 = tick.bids[0][1]
            vtTick.askVolume1 = tick.asks[0][1]
            
            vtTick.bidPrice2 = tick.bids[1][0]
            vtTick.askPrice2 = tick.asks[1][0]
            vtTick.bidVolume2 = tick.bids[1][1]
            vtTick.askVolume2 = tick.asks[1][1]
            
            vtTick.bidPrice3 = tick.bids[2][0]
            vtTick.askPrice3 = tick.asks[2][0]
            vtTick.bidVolume3 = tick.bids[2][1]
            vtTick.askVolume3 = tick.asks[2][1]
            
            vtTick.bidPrice4 = tick.bids[3][0]
            vtTick.askPrice4 = tick.asks[3][0]
            vtTick.bidVolume4 = tick.bids[3][1]
            vtTick.askVolume4 = tick.asks[3][1]
            
            vtTick.bidPrice5 = tick.bids[4][0]
            vtTick.askPrice5 = tick.asks[4][0]   
            vtTick.bidVolume5 = tick.bids[4][1]
            vtTick.askVolume5 = tick.asks[4][1] 
            
        except:
            pass
        
        self.tick_collection = self.client[TICK_DB_NAME][vtTick.symbol] 
        self.tick_collection.ensure_index('datetime')
        flt = {'datetime': vtTick.datetime}
        self.tick_collection.update_one(flt, {'$set':vtTick.__dict__}, upsert=True)
        
    
    def on_bar(self, bar):
        print bar.strtime
        vtBar = VtBarData()
        vtBar.symbol = bar.sec_id          # 代码
        vtBar.exchange = bar.exchange        # 交易所
        vtBar.vtSymbol = vtBar.symbol + '.' + vtBar.exchange       # vt系统代码
    
        vtBar.open = bar.open             # OHLC
        vtBar.high = bar.high
        vtBar.low = bar.low
        vtBar.close = bar.close
        
        dt = datetime.fromtimestamp(bar.utc_time) 
        vtBar.date = dt.strftime('%Y%m%d')            # bar开始的时间，日期
        vtBar.time = dt.strftime('%H:%M:%S.%f')           # 时间
        vtBar.datetime = dt          # python的datetime时间对象
        
        vtBar.volume = bar.volume             # 成交量
        vtBar.openInterest = bar.position       # 持仓量
    
        self.bar_collection = self.client[MINUTE_DB_NAME][vtBar.symbol]
        self.bar_collection.ensure_index('datetime')
        flt = {'datetime': vtBar.datetime}
        self.bar_collection.update_one(flt, {'$set':vtBar.__dict__}, upsert=True)
      
                
    def on_backtest_finish(self, indicator):
        print('数据插入成功') 
    



if __name__ == '__main__':
#     strategy = MyStrategy(config_file='config.ini')
#     ret = strategy.run()
#     string = strategy.get_strerror(ret)
#     print string.decode('gb2312')

    setting = {}
    with open("symbol.json") as f:
        setting = json.load(f)          #加载配置文件
    subscribe_symbols = setting["symbol"]
    
        
    mystrategy = MyStrategy(
        username='18217641619',
        password='yh8013209',
        strategy_id='strategy_1',
        subscribe_symbols=subscribe_symbols,
        mode=4,
        td_addr='localhost:8001')
    ret = mystrategy.backtest_config(
        start_time='2018-03-07 9:00:00',
        end_time='2018-12-31 15:00:00',
        initial_cash=1000000,
        transaction_ratio=1,
        commission_ratio=0,
        slippage_ratio=0,
        price_type=1,
        bench_symbol='')
    
    ret = mystrategy.run()
    string = mystrategy.get_strerror(ret)
    print string.decode('gb2312')
