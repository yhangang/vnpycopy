# encoding: UTF-8

"""
日内策略。根据正玄波信号决定开仓和平仓，同时添加追踪止损。

"""

import arrow
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarManager,
                                                     ArrayManager)

from util.logging.logger import logger
 
 
########################################################################
class SinewaveStrategy(CtaTemplate):
    """日内策略"""
    className = 'SinewaveStrategy'
    author = u'量化的猪'

    # 策略参数
    initDays = 0  # 初始化数据所用的天数
    upLimit = 9999  # 涨停板价格，用于发市价单
    downLimit = 1  # 跌停板价格，用于发市价单
    max_drawdown = 50  # 可容忍的最大回撤
    excess_count = 5  # 正玄波D需超出B的点数
    excess_count2 = 10  # 开仓时大于excess_count的点数限制，防止成本过高
    
    # 策略变量
    volume = 1  # 交易手数
    drawdown_bench = 0  # 当前仓位最高价或最低价，用于计算回撤
    space = 0  # 持仓情况，0:空仓,1:多头仓,-1:空头仓
    daily_max_open_count = 2  # 每天开仓次数限制
    daily_open_count = 0  # 当日开仓次数 


    
    

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'space',
               'upLimit',
               'downLimit']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(SinewaveStrategy, self).__init__(ctaEngine, setting)
        
        # 创建K线合成器对象
        self.bm = BarManager(self.onBar, xmin=5, onXminBar=self.onXminBar)
        self.am = ArrayManager()
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' % self.name)
    
        # 初始化步骤
        self.__init_up_step()
        self.__init_down_step()
        self.__init__open_state()
        
        

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
        self.bm.updateTick(tick)

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.cancelAll()
        self.bm.updateBar(bar)
        # 发出状态更新事件
        self.putEvent()
        
    def onXminBar(self, bar):
        """收到X分钟Bar推送（必须由用户继承实现）"""
#         logger.debug(str(bar.datetime) + '---------------------')
        # 仓位不空时，首先计算回撤，超过容忍值则强制平仓
        if self.space == 1:
            if bar.close <= self.drawdown_bench - self.max_drawdown:
                self.sell(self.downLimit, self.volume)
                logger.info("时间：%s  平/多  价格：%s" % (bar.datetime, bar.close))
                self.space = 0
            elif bar.close > self.drawdown_bench:
                self.drawdown_bench = bar.close
        elif self.space == -1:
            if bar.close >= self.drawdown_bench + self.max_drawdown:
                self.cover(self.upLimit, self.volume)
                logger.info("时间：%s  平/空  价格：%s" % (bar.datetime, bar.close))
                self.space = 0
            elif bar.close < self.drawdown_bench:
                self.drawdown_bench = bar.close
        
        # 上午的交易时段
        if (arrow.get(bar.datetime).hour >= 9 and  arrow.get(bar.datetime).hour <= 10) \
        or (arrow.get(bar.datetime).hour == 11 and arrow.get(bar.datetime).minute < 30):
            # 当前为开多头仓信号
            if self.pre_space == 1:
                if bar.close <= self.open_up and bar.close >= self.open_down \
                and self.daily_open_count <= self.daily_max_open_count:
                    self.buy(self.upLimit, self.volume)
                    logger.info("时间：%s  开/多  价格：%s" % (bar.datetime, bar.close))
                    self.space = 1
                    self.daily_open_count += 1
                    self.drawdown_bench = bar.close
                    self.__init__open_state()
                elif bar.close < self.open_down:
                    self.__init__open_state()
            # 当前为开空头仓信号
            elif self.pre_space == -1:
                if bar.close <= self.open_up and bar.close >= self.open_down \
                and self.daily_open_count <= self.daily_max_open_count:
                    self.short(self.downLimit, self.volume)
                    logger.info("时间：%s  开/空  价格：%s" % (bar.datetime, bar.close))
                    self.space = -1
                    self.daily_open_count += 1
                    self.drawdown_bench = bar.close
                    self.__init__open_state()
                elif bar.close > self.open_up:
                    self.__init__open_state()
            # 找到向上正玄波    
            if self.find_up_sinewave(bar) == True:
                if self.space == 0:  # 空仓时开多头仓
                    if bar.close <= self.open_up and bar.close > self.open_down \
                    and self.daily_open_count <= self.daily_max_open_count:
                        self.buy(self.upLimit, self.volume)
                        logger.info("时间：%s  开/多  价格：%s" % (bar.datetime, bar.close))
                        self.space = 1
                        self.daily_open_count += 1
                        self.drawdown_bench = bar.close
                        self.__init__open_state()
                    else:
                        self.pre_space = 1  # 预开仓情况，0:未出现开仓信号,1:准备开多头仓,-1:准备开空头仓
                    
                elif self.space == 1:  # 多头仓时不处理
                    return
                else:  # 空仓时平多开空
                    self.cover(self.upLimit, self.volume)
                    logger.info("时间：%s  平/空  价格：%s" % (bar.datetime, bar.close))
                    self.space = 0
                    if bar.close <= self.open_up and bar.close > self.open_down \
                    and self.daily_open_count <= self.daily_max_open_count:
                        self.buy(self.upLimit, self.volume)
                        logger.info("时间：%s  开/多  价格：%s" % (bar.datetime, bar.close))
                        self.space = 1
                        self.daily_open_count += 1
                        self.drawdown_bench = bar.close
                        self.__init__open_state()
                    else:
                        self.pre_space = 1  # 预开仓情况，0:未出现开仓信号,1:准备开多头仓,-1:准备开空头仓
            # 找到向下正玄波    
            elif self.find_down_sinewave(bar) == True:
                if self.space == 0:  # 空仓时开空头仓
                    if bar.close >= self.open_down and bar.close < self.open_up \
                    and self.daily_open_count <= self.daily_max_open_count:
                        self.short(self.downLimit, self.volume)
                        logger.info("时间：%s  开/空  价格：%s" % (bar.datetime, bar.close))
                        self.space = -1
                        self.daily_open_count += 1
                        self.drawdown_bench = bar.close
                        self.__init__open_state()
                    else:
                        self.pre_space = -1  # 预开仓情况，0:未出现开仓信号,1:准备开多头仓,-1:准备开空头仓
                elif self.space == 1:  # 多头仓时平多开空
                    self.sell(self.downLimit, self.volume)
                    logger.info("时间：%s  平/多  价格：%s" % (bar.datetime, bar.close))
                    self.space = 0
                    if bar.close >= self.open_down and bar.close < self.open_up \
                    and self.daily_open_count <= self.daily_max_open_count:
                        self.short(self.downLimit, self.volume)
                        logger.info("时间：%s  开/空  价格：%s" % (bar.datetime, bar.close))
                        self.space = -1
                        self.daily_open_count += 1
                        self.drawdown_bench = bar.close
                        self.__init__open_state()
                    else:
                        self.pre_space = -1  # 预开仓情况，0:未出现开仓信号,1:准备开多头仓,-1:准备开空头仓
                else:  # 空头仓时不处理
                    return
                    
        # 下午交易时段
        elif (arrow.get(bar.datetime).hour >= 13 and  arrow.get(bar.datetime).hour <= 13) \
        or (arrow.get(bar.datetime).hour == 14 and arrow.get(bar.datetime).minute <= 50):
            if self.space == 0:  # 下午若空仓，直接退出，当日不开新仓
                return
            elif self.space == 1:  # 多头仓，寻找向下正玄波
                if self.find_down_sinewave(bar) == True:
                    self.sell(self.downLimit, self.volume)
                    logger.info("时间：%s  平/多  价格：%s" % (bar.datetime, bar.close))
                    self.space = 0
            else:  # 空头仓
                if self.find_up_sinewave(bar) == True:
                    self.cover(self.upLimit, self.volume)
                    logger.info("时间：%s  平/空  价格：%s" % (bar.datetime, bar.close))
                    self.space = 0
        # 收盘之前平仓            
        else:
            # 收盘前初始化下一日参数
            self.__init_up_step()
            self.__init_down_step()
            self.__init__open_state()
            self.daily_open_count = 0 
            
            if self.space == 0:
                return
            elif self.space == 1:  # 多头仓，直接平仓
                self.sell(self.downLimit, self.volume)
                logger.info("时间：%s  平/多  价格：%s" % (bar.datetime, bar.close))
                self.space = 0
            else:  # 空头仓，直接平仓
                self.cover(self.upLimit, self.volume)
                logger.info("时间：%s  平/空  价格：%s" % (bar.datetime, bar.close))
                self.space = 0
     
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
    
    # 初始化开仓信号状态   
    def __init__open_state(self):
        self.pre_space = 0  # 预开仓情况，0:未出现开仓信号,1:准备开多头仓,-1:准备开空头仓
        self.open_up = 0  # 开仓点上限
        self.open_down = 0  # 开仓点下限
        
    # 初始化向上正玄波状态
    def __init_down_step(self):
        self.up_step = 0  # 状态标志，0:尚未开始,1:A,2:B,3:C,4:D
        self.up_a = 0  # a阶段价格
        self.up_b = 0  # b阶段价格
        self.up_c = 0  # c阶段价格
        self.up_d = 0  # d阶段价格
        
    # 初始化向下正玄波状态
    def __init_up_step(self):
        self.down_step = 0  # 状态标志，0:尚未开始,1:A,2:B,3:C,4:D
        self.down_a = 0  # a阶段价格
        self.down_b = 0  # b阶段价格
        self.down_c = 0  # c阶段价格
        self.down_d = 0  # d阶段价格
        
    # 寻找向上正玄波   
    def find_down_sinewave(self, bar):
        # 初始阶段
        if self.up_step == 0:
            self.up_a = bar.close
            self.up_step = 1
        # A阶段   
        elif self.up_step == 1:
            if bar.close > self.up_a:
                self.up_b = bar.close
                self.up_step = 2
            else:
                self.up_a = bar.close
                self.up_step = 1
        # B阶段
        elif self.up_step == 2:
            if bar.close >= self.up_b:
                self.up_b = bar.close
                self.up_step = 2
            elif bar.close < self.up_b and bar.close > self.up_a:
                self.up_c = bar.close
                self.up_step = 3
            else:
                self.up_a = bar.close
                self.up_step = 1
        # C阶段
        elif self.up_step == 3:
            if bar.close > self.up_c and bar.close >= self.up_b + self.excess_count:
                # 首先记录本次正玄波的开仓范围
                self.open_up = self.up_b + self.excess_count + self.excess_count2
                self.open_down = self.up_c
                
                self.up_a = self.up_c
                self.up_b = bar.close
                self.up_step = 2
                return True
            elif bar.close > self.up_c and bar.close < self.up_b + self.excess_count:
                self.up_d = bar.close
                self.up_step = 4
            elif bar.close <= self.up_c and bar.close > self.up_a:
                self.up_c = bar.close
                self.up_step = 3
            else:
                self.up_a = bar.close
                self.up_step = 1
        # D阶段        
        else:
            if bar.close >= self.up_d and bar.close >= self.up_b + self.excess_count:
                # 首先记录本次正玄波的开仓范围
                self.open_up = self.up_b + self.excess_count + self.excess_count2
                self.open_down = self.up_c
                
                self.up_a = self.up_c
                self.up_b = bar.close
                self.up_step = 2
                return True
            elif bar.close >= self.up_d and bar.close < self.up_b + self.excess_count:
                self.up_d = bar.close
                self.up_step = 4
            elif bar.close < self.up_d and bar.close > self.up_c:
                self.up_a = self.up_c
                self.up_b = self.up_d
                self.up_c = bar.close
                self.up_step = 3
            else:
                self.up_a = bar.close
                self.up_step = 1
        # 若没有找到信号，统一返回失败        
        return False
                
    # 寻找向下正玄波   
    def find_up_sinewave(self, bar):
        # 初始阶段
        if self.down_step == 0:
            self.down_a = bar.close
            self.down_step = 1
        # A阶段   
        elif self.down_step == 1:
            if bar.close < self.down_a:
                self.down_b = bar.close
                self.down_step = 2
            else:
                self.down_a = bar.close
                self.down_step = 1
        # B阶段
        elif self.down_step == 2:
            if bar.close <= self.down_b:
                self.down_b = bar.close
                self.down_step = 2
            elif bar.close > self.down_b and bar.close < self.down_a:
                self.down_c = bar.close
                self.down_step = 3
            else:
                self.down_a = bar.close
                self.down_step = 1
        # C阶段
        elif self.down_step == 3:
            if bar.close < self.down_c and bar.close <= self.down_b - self.excess_count:
                # 首先记录本次正玄波的开仓范围
                self.open_up = self.down_c
                self.open_down = self.down_b - self.excess_count - self.excess_count2
                
                self.down_a = self.down_c
                self.down_b = bar.close
                self.down_step = 2
                return True
            elif bar.close < self.down_c and bar.close > self.down_b - self.excess_count:
                self.down_d = bar.close
                self.down_step = 4
            elif bar.close >= self.down_c and bar.close < self.down_a:
                self.down_c = bar.close
                self.down_step = 3
            else:
                self.down_a = bar.close
                self.down_step = 1
        # D阶段        
        else:
            if bar.close <= self.down_d and bar.close <= self.down_b - self.excess_count:
                # 首先记录本次正玄波的开仓范围
                self.open_up = self.down_c
                self.open_down = self.down_b - self.excess_count - self.excess_count2
                
                self.down_a = self.down_c
                self.down_b = bar.close
                self.down_step = 2
                return True
            elif bar.close <= self.down_d and bar.close > self.down_b - self.excess_count:
                self.down_d = bar.close
                self.down_step = 4
            elif bar.close > self.down_d and bar.close < self.down_c:
                self.down_a = self.down_c
                self.down_b = self.down_d
                self.down_c = bar.close
                self.down_step = 3
            else:
                self.down_a = bar.close
                self.down_step = 1
        # 若没有找到信号，统一返回失败        
        return False
