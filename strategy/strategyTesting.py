# encoding: UTF-8

"""

"""

import arrow
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)
from vnpy.trader.vtObject import VtBarData

from util.logging.logger import logger


########################################################################
class TestingStrategy(CtaTemplate):
    """"""
    className = 'TestingStrategy'
    author = u'量化的猪'

    # 策略参数
    initDays = 0           # 初始化数据所用的天数

    # 策略变量
    downLimit = 0
    upLimit = 0

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'upLimit',
               'downLimit']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TestingStrategy, self).__init__(ctaEngine, setting)
        
        # 创建K线合成器对象
        self.bm = BarManager(self.onBar)
        self.am = ArrayManager()
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)


        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.downLimit = tick.lowerLimit
        self.upLimit = tick.upperLimit
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.cancelAll()
        self.writeCtaLog(u'%s 收到1分钟K线推送' % bar.datetime)
        
        if arrow.get(bar.datetime).minute % 4 == 0:
            self.buy(self.upLimit, 1)
            self.space = "多头仓"
            self.writeCtaLog(str(bar.datetime) + "  买多")
        elif arrow.get(bar.datetime).minute % 4 == 1:
            self.sell(self.downLimit, 1)
            self.writeCtaLog(str(bar.datetime) + "  平多")
            self.space = "空仓"
        elif arrow.get(bar.datetime).minute % 4 == 2:
            self.short(self.downLimit, 1)
            self.writeCtaLog(str(bar.datetime) + "  买空")
            self.space = "空头仓"
        else:
            self.cover(self.upLimit, 1)
            self.writeCtaLog(str(bar.datetime) + "  平空")
            self.space = "空仓"

        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass