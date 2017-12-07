### 使用vn.py开源量化框构建的量化交易系统
### vn.py - By Traders, For Traders.
### http://www.vnpy.org/

---
### 简介
项目名称:拉普拉斯 （Lapras）
版本：0.1
模块：

	——vnpy默认模块，提供交易框架和API
	
	——util模块，工具类
	
	——main模块，主程序目录及策略文件
	


---
### 环境准备

**Windows**

1. 支持的操作系统：Windows 7/8/10/Server 2008
2. 安装[MongoDB](https://www.mongodb.org/downloads#production)，并[将MongoDB配置为系统服务](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-windows/#configure-a-windows-service-for-mongodb-community-edition)
3. 安装[Anaconda](http://www.continuum.io/downloads)，**注意必须是Python 2.7 32位版本**
4. 安装[Visual C++ Redistributable Packages for VS2013 x86版本](https://support.microsoft.com/en-us/help/3138367/update-for-visual-c-2013-and-visual-c-redistributable-package)
5. 安装python依赖：

	pip install pymongo msgpack-python websocket-client qdarkstyle configparser

	conda install -c quantopian ta-lib=0.4.9

