#encoding:utf-8
import tushare as ts
import pymongo
from datetime import datetime

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.app.ctaStrategy.ctaBase import DAILY_DB_NAME

# 定义合约代码
symbol = '510050'
exchange = 'SSE'
vtSymbol = '.'.join([symbol, exchange])

# 下载历史数据
data = ts.get_hist_data(symbol, '2017-01-01')
data = data.sort()

print u'数据下载完成'

# 创建MongoDB连接
client = pymongo.MongoClient('localhost', 27017)
collection = client[DAILY_DB_NAME][vtSymbol]
collection.ensure_index('datetime')

print u'MongoDB连接成功'

# 将数据插入历史数据库
for row in data.iterrows():
    date = row[0]
    data = row[1]
    
    bar = VtBarData()
    bar.vtSymbol = vtSymbol
    bar.symbol = symbol
    bar.exchange = exchange
    bar.date = date
    bar.datetime = datetime.strptime(date, '%Y-%m-%d')
    bar.open = data['open']
    bar.high = data['high']
    bar.low = data['low']
    bar.close = data['close']
    bar.volume = data['volume']
    
    flt = {'datetime': bar.datetime}
    collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)

print u'数据插入完成'