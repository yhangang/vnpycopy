# encoding: UTF-8

"""
感谢Darwin Quant贡献的策略思路。
知乎专栏原文：https://zhuanlan.zhihu.com/p/24448511

策略逻辑：
1. 布林通道（信号）
2. CCI指标（过滤）
3. ATR指标（止损）

适合品种：螺纹钢
适合周期：15分钟


"""

from __future__ import division

from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)

from util.logging.logger import logger
import arrow
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


########################################################################
class BollChannelStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'BollChannelStrategy'
    author = u'量化的猪'

    # 策略参数
    bollWindow = 30                     # 布林通道窗口数
    cciWindow = 30                      # CCI窗口数
    atrWindow = 30                      # ATR窗口数
    bollDev = 3.0                       # 布林通道的偏差
    slMultiplier = 4.0                  # 计算止损距离的乘数
    initDays = 10                       # 初始化数据所用的天数
    fixedSize = 1                       # 每次交易的数量

    # 策略变量
    bollUp = 0                          # 布林通道上轨
    bollDown = 0                        # 布林通道下轨
    cciValue = 0                        # CCI指标数值
    atrValue = 0                        # ATR指标数值
    
    intraTradeHigh = 0                  # 持仓期内的最高点
    intraTradeLow = 0                   # 持仓期内的最低点
    longStop = 0                        # 多头止损
    shortStop = 0                       # 空头止损
    
    downLimit = 0  # 当日最低价限制
    upLimit = 9999  # 当日最高价限制
    amCount = 0       #ArrayManager的K线初始化根数

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollWindow',
                 'bollDev',
                 'cciWindow',
                 'atrWindow',
                 'slMultiplier',
                 'initDays',
                 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'bollUp',
               'bollDown',
               'cciValue',
               'atrValue',
               'intraTradeHigh',
               'intraTradeLow',
               'longStop',
               'shortStop',
               'amCount']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BollChannelStrategy, self).__init__(ctaEngine, setting)
        
        self.bm = BarManager(self.onBar, 15, self.onXminBar)        # 创建K线合成器对象
        self.am = ArrayManager()
        
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
        
        # 到达收盘时段22:40:00以后，强制平仓
        if arrow.get(tick.datetime).hour == 22 and arrow.get(tick.datetime).minute >= 59 and arrow.get(tick.datetime).second >= 30:
            if self.pos > 0:
                self.sell(self.downLimit, abs(self.pos))
            elif self.pos < 0:
                self.cover(self.upLimit, abs(self.pos))
            logger.info("到达当日收盘时间:%s，强制平仓！" % tick.datetime)
            # 发出状态更新事件
            self.putEvent() 
            return 
        
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bm.updateBar(bar)
        self.putEvent() 
    
    #----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到15分钟K线"""
        self.writeCtaLog(u'收到15分钟K线推送 ')
        # 全撤之前发出的委托
        self.cancelAll()
        
        #屏蔽凌晨之后的数据
        if arrow.get(bar.datetime).hour < 9:
            return
        
        # 到达收盘时段22:40:00以后，强制平仓，仅用于回测
#         if arrow.get(bar.datetime).hour == 22 and arrow.get(bar.datetime).minute >= 40:
#             if self.pos > 0:
#                 self.sell(self.downLimit, abs(self.pos))
#             elif self.pos < 0:
#                 self.cover(self.upLimit, abs(self.pos))
#             logger.info("到达当日收盘时间:%s，强制平仓！" % bar.datetime)
#             # 发出状态更新事件
#             self.putEvent() 
#             return 
    
        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        self.amCount = am.count
        if not am.inited:
            return
        
        # 计算指标数值
        self.bollUp, self.bollDown = am.boll(self.bollWindow, self.bollDev)
        self.cciValue = am.cci(self.cciWindow)
        self.atrValue = am.atr(self.atrWindow)
        logger.info("收到15分钟K线推送----时间：%s  最高价:%.2f  最低价：%.2f  bollDown：%.2f   bollUp:%.2f  仓位：%s" % (bar.datetime, bar.high, bar.low, self.bollDown, self.bollUp, self.pos))
        
        # 判断是否要进行交易
    
        # 当前无仓位，发送开仓委托
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low            
            
            if self.cciValue > 0:
                self.buy(self.bollUp, self.fixedSize, True)
                logger.info("%s--------发送开多仓委托，买价:%.2f " % (bar.datetime,self.bollUp))
            elif self.cciValue < 0:
                self.short(self.bollDown, self.fixedSize, True)
                logger.info("%s--------发送开空仓委托，卖价:%.2f " % (bar.datetime,self.bollDown))
    
        # 持有多头仓位
        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            self.longStop = self.intraTradeHigh - self.atrValue * self.slMultiplier
            
            self.sell(self.longStop, abs(self.pos), True)
            logger.info("%s--------发送平多仓委托，价格：%.2f" % (bar.datetime, self.longStop))
            
        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            self.shortStop = self.intraTradeLow + self.atrValue * self.slMultiplier
            
            self.cover(self.shortStop, abs(self.pos), True)
            logger.info("%s--------发送平空仓委托，价格：%.2f" % (bar.datetime, self.shortStop))
    
        # 发出状态更新事件
        self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        logger.info("成交回报  direction:%s  offset:%s  price:%.2f  volume:%s  tradeTime:%s" % (trade.direction, 
                                                                                          trade.offset,
                                                                                          trade.price,
                                                                                           trade.volume,
                                                                                            trade.tradeTime))
        
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
    
