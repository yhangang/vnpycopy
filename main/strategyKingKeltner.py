# encoding: UTF-8

"""
基于King Keltner通道的交易策略，适合用在股指上，
展示了OCO委托和5分钟K线聚合的方法。

"""

from __future__ import division

from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)
import arrow
from util.logging.logger import logger

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

########################################################################
class KkStrategy(CtaTemplate):
    """基于King Keltner通道的交易策略"""
    className = 'KkStrategy'
    author = u'量化的猪'

    # 策略参数
    kkLength = 11  # 计算通道中值的窗口数
    kkDev = 1.618  # 计算通道宽度的偏差
    trailingPrcnt = 0.35  # 移动止损
    initDays = 10  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量

    # 策略变量
    downLimit = 0  # 当日最低价限制
    upLimit = 9999  # 当日最高价限制
    
    kkUp = 0  # KK通道上轨
    kkDown = 0  # KK通道下轨
    intraTradeHigh = 0  # 持仓期内的最高点
    intraTradeLow = 0  # 持仓期内的最低点
    OPENLIMIT = 3
    openCountLimit = OPENLIMIT  # 每日剩余开仓次数
    amCount = 0       #ArrayManager的K线初始化根数
    
    lastBarDay = 0

    buyOrderIDList = []  # OCO委托买入开仓的委托号
    shortOrderIDList = []  # OCO委托卖出开仓的委托号
    orderList = []  # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'kkLength',
                 'kkDev',
                 'trailingPrcnt'] 

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'kkUp',
               'kkDown',
               'openCountLimit',
               'downLimit',
               'upLimit',
               'amCount']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(KkStrategy, self).__init__(ctaEngine, setting)
        
        self.bm = BarManager(self.onBar, 5, self.onFiveBar)  # 创建K线合成器对象
        self.am = ArrayManager(self.kkLength + 1)
        
        self.buyOrderIDList = []  # OCO委托买入开仓的委托号
        self.shortOrderIDList = []  # OCO委托卖出开仓的委托号
        self.orderList = []  # 保存委托代码的列表
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' % self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' % self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）""" 
        self.downLimit = tick.lowerLimit
        self.upLimit = tick.upperLimit
        self.bm.updateTick(tick)
        self.putEvent()

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bm.updateBar(bar)
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到5分钟K线"""
        self.writeCtaLog(u'收到5分钟K线推送 ')
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []    
        
        #判断是否是同一天的bar
        if arrow.get(bar.datetime).day != self.lastBarDay:
            self.lastBarDay = arrow.get(bar.datetime).day
            self.openCountLimit = self.OPENLIMIT
        
        
        # 保存K线数据
        am = self.am
        am.updateBar(bar)
        self.amCount = am.count
        if not am.inited:
            self.putEvent()   
            return             
        
        
        # 到达收盘时段，强制平仓
        if arrow.get(bar.datetime).hour == 14 and arrow.get(bar.datetime).minute >= 50 and arrow.get(bar.datetime).minute < 59:
            if self.pos > 0:
                self.short(self.downLimit, abs(self.pos))
            elif self.pos < 0:
                self.buy(self.upLimit, abs(self.pos))
            logger.info("到达当日收盘时间:%s，强制平仓！" % bar.datetime)
            # 发出状态更新事件
            self.putEvent() 
            return 
        #早上禁止开仓，暂不启用
        elif arrow.get(bar.datetime).hour == 9 and arrow.get(bar.datetime).minute <= 30:
            # 发出状态更新事件
            self.putEvent() 
            return 
            
        
        # 计算指标数值
        self.kkUp, self.kkDown = am.keltner(self.kkLength, self.kkDev)
        logger.info("收到5分钟K线推送----时间：%s  最高价:%.2f  最低价：%.2f  kkDown：%.2f   kkUp:%.2f  仓位：%s" % (bar.datetime, bar.high, bar.low, self.kkDown, self.kkUp, self.pos))
        
        # 判断是否要进行交易
    
        # 当前无仓位，并且未达到当日开仓次数限制，发送OCO开仓委托
        if self.pos == 0:
            if self.openCountLimit >= 1:
                self.intraTradeHigh = bar.high
                self.intraTradeLow = bar.low            
                self.sendOcoOrder(self.kkUp, self.kkDown, self.fixedSize)
                logger.info("%s--------发送OCO委托，买价:%.2f  卖价:%.2f" % (bar.datetime,self.kkUp,self.kkDown))
    
        # 持有多头仓位
        elif self.pos > 0:
            self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
            self.intraTradeLow = bar.low
            
            l = self.short(self.intraTradeHigh * (1 - self.trailingPrcnt / 100),
                                abs(self.pos), True)
            self.orderList.extend(l)
            logger.info("%s--------发送平多仓委托，价格：%.2f" % (bar.datetime, self.intraTradeHigh * (1 - self.trailingPrcnt / 100)))
    
        # 持有空头仓位
        elif self.pos < 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = min(self.intraTradeLow, bar.low)
            
            l = self.buy(self.intraTradeLow * (1 + self.trailingPrcnt / 100),
                               abs(self.pos), True)
            self.orderList.extend(l)
            logger.info("%s--------发送平空仓委托，价格：%.2f" % (bar.datetime, self.intraTradeLow * (1 + self.trailingPrcnt / 100)))
    
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
        
        if self.pos != 0:
            self.openCountLimit -= 1
            # 多头开仓成交后，撤消空头委托
            if self.pos > 0:
                for shortOrderID in self.shortOrderIDList:
                    self.cancelOrder(shortOrderID)
            # 反之同样
            elif self.pos < 0:
                for buyOrderID in self.buyOrderIDList:
                    self.cancelOrder(buyOrderID)
            
            # 移除委托号
            for orderID in (self.buyOrderIDList + self.shortOrderIDList):
                if orderID in self.orderList:
                    self.orderList.remove(orderID)
                
        # 发出状态更新事件
        self.putEvent()
        
    #----------------------------------------------------------------------
    def sendOcoOrder(self, buyPrice, shortPrice, volume):
        """
        发送OCO委托
        
        OCO(One Cancel Other)委托：
        1. 主要用于实现区间突破入场
        2. 包含两个方向相反的停止单
        3. 一个方向的停止单成交后会立即撤消另一个方向的
        """
        # 发送双边的停止单委托，并记录委托号
        self.buyOrderIDList = self.buy(buyPrice, volume, True)
        self.shortOrderIDList = self.short(shortPrice, volume, True)
        
        # 将委托号记录到列表中
        self.orderList.extend(self.buyOrderIDList)
        self.orderList.extend(self.shortOrderIDList)
        
       

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass
