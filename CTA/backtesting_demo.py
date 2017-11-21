# encoding:utf-8
# 开发交易策略
import numpy as np

from vnpy.trader.app.ctaStrategy.ctaTemplate import CtaTemplate
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.app.ctaStrategy.ctaTemplate import BarManager

# 定义合约代码
symbol = 'c1801'
exchange = 'DCE'
vtSymbol = '.'.join([symbol, exchange])

class DoubleMaStrategy(CtaTemplate):
    """双均线策略Demo"""
    className = 'DoubleMaStrategy'
    author = u'用Python的交易员'
    
    # 策略参数
    initDays = 25  # 初始化数据所用的天数
    
    # 策略变量
    barCount = 0
    closeArray = np.zeros(20)
    ma5 = 0
    ma20 = 0    
    lastMa5 = 0
    lastMa20 = 0

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']  

    def __init__(self, ctaEngine, setting):
        """构造函数"""
        super(DoubleMaStrategy, self).__init__(ctaEngine, setting)
        
        # 针对可变对象类型的变量，需要在这里初始化
        self.closeArray = np.zeros(20)
        
        self.bm = BarManager(self.onBar, 5, self.onXminBar)
        
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双均线策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双均线策略启动')
        self.putEvent()
    
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双均线策略停止')
        self.putEvent()
        
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 因为只是展示如何使用框架，这里直接跳过，实盘需要用户基于Tick自行合成K线
        pass
        
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        
        print bar.datetime
        self.bm.updateBar(bar)
        
        # 缓存数据
        self.closeArray[0:19] = self.closeArray[1:20]
        self.closeArray[-1] = bar.close
        
        self.barCount += 1
        if self.barCount < self.initDays:
            return
        
        # 计算快慢均线
        self.ma5 = self.closeArray[15:20].mean()
        self.ma20 = self.closeArray.mean()
        
        # 判断买卖
        crossOver = self.ma5 > self.ma20 and self.lastMa5 <= self.lastMa20  # 金叉上穿
        crossBelow = self.ma5 < self.ma20 and self.lastMa5 >= self.lastMa20  # 死叉下穿
        
        # 金叉和死叉的条件是互斥
        # 所有的委托均以K线收盘价委托，为了保证回测成交超价5%发单
        if crossOver:
            # 如果金叉时手头没有持仓，则直接做多
            if self.pos == 0:
                self.buy(bar.close * 1.05, 10000)
            # 如果有空头持仓，则先平空，再做多
            elif self.pos < 0:
                self.cover(bar.close * 1.05, 10000)
                self.buy(bar.close * 1.05, 10000)
        # 死叉和金叉相反
        elif crossBelow:
            if self.pos == 0:
                self.short(bar.close * 0.95, 10000)
            elif self.pos > 0:
                self.sell(bar.close * 0.95, 10000)
                self.short(bar.close * 0.95, 10000)
                
        # 发出状态更新事件
        self.putEvent()
        
        
    def onXminBar(self, xminBar):
        print xminBar.datetime, '---------------'
        
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    def onStopOrder(self, so):
        """停止单推送"""
        pass    
    
# 加载回测引擎
from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine

# 创建回测引擎实例
engine = BacktestingEngine()

# 设置引擎的回测模式为K线
engine.setBacktestingMode(engine.BAR_MODE)

# 设置回测用的数据起始日期
engine.setStartDate('20171025', initDays=20)

# 设置产品相关参数
engine.setSlippage(0)  # 滑点设为0
engine.setRate(1.5 / 10000)  # 万1.5 ETF手续费
engine.setSize(1)  # ETF每股为1
engine.setPriceTick(0.001)  # ETF最小价格变动
engine.setCapital(1)  # 为了只统计净盈亏，设置初始资金为1

# 设置使用的历史数据库
engine.setDatabase(MINUTE_DB_NAME, symbol)

# 在引擎中创建策略对象
engine.initStrategy(DoubleMaStrategy, {})

# 开始跑回测
engine.runBacktesting()

# 显示回测结果
engine.showDailyResult()

# 显示逐笔回测结果
# engine.showBacktestingResult()

# 显示前10条成交记录
for i in range(len(engine.tradeDict)):
    d = engine.tradeDict[str(i + 1)].__dict__
#     print d
    print 'TradeID: %s, Time: %s, Direction: %s, Price: %s, Volume: %s' % (d['tradeID'], d['dt'], d['direction'], d['price'], d['volume'])
