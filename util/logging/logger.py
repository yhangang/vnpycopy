# encoding:utf-8
import logging


class Logger:
    def __new__(cls,*args,**kwargs):
        if not hasattr(cls,'_inst'):
            cls._inst=super(Logger,cls).__new__(cls,*args,**kwargs)
        return cls._inst
    
    def __init__(self, path):
        self.logger = logging.getLogger(path)
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        # 设置CMD日志
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        # 设置文件日志
        fh = logging.FileHandler(path)
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        self.logger.addHandler(sh)
        self.logger.addHandler(fh)
 
    def debug(self, message):
        self.logger.debug(message)
 
    def info(self, message):
        self.logger.info(message)
 
    def war(self, message):
        self.logger.warn(message)
 
    def error(self, message):
        self.logger.error(message)
 
    def cri(self, message):
        self.logger.critical(message)
 
#初始化logger供其他程序调用   
logger = Logger('log.log')
