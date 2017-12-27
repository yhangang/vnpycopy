# encoding:utf-8
# 开发交易策略

from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME, TICK_DB_NAME

from main.strategyBollChannel import BollChannelStrategy
from main.strategyKingKeltner import KkStrategy
from util.logging.logger import logger


# 定义合约代码
symbol = 'IH'
exchange = '**'
vtSymbol = '.'.join([symbol, exchange])
    
# 加载回测引擎

# 创建回测引擎实例
engine = BacktestingEngine()

# 设置引擎的回测模式为K线
engine.setBacktestingMode(engine.BAR_MODE)

# 设置回测用的数据起始日期
engine.setStartDate('20160101', initDays=3)
# engine.setEndDate('20171108')

# 设置产品相关参数
engine.setSlippage(0)  # 滑点设为0
engine.setRate(0.5 / 10000)  # 手续费
engine.setSize(200)  # 合约乘数
engine.setPriceTick(0.2)  # 股指期货最小价格变动
engine.setCapital(1)  # 为了只统计净盈亏，设置初始资金为1

# 设置使用的历史数据库
engine.setDatabase(MINUTE_DB_NAME, symbol)

# 在引擎中创建策略对象
engine.initStrategy(KkStrategy, {})

# 开始跑回测
engine.runBacktesting()

# 显示所有成交记录
# for i in range(len(engine.tradeDict)):
#     d = engine.tradeDict[str(i + 1)].__dict__
#     logger.info('TradeID: %s, Time: %s, Direction: %s, Offset: %s, Price: %s, Volume: %s' % (d['tradeID'], d['dt'], d['direction'], d['offset'], d['price'], d['volume']))


# 显示回测结果
engine.showDailyResult()

# 显示逐笔回测结果
# engine.showBacktestingResult()