#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易框架核心模块

这是一个参考backtrader架构设计的Python交易框架，支持：
- 多账户管理
- 多策略并行运行
- 多数据源支持
- 丰富的技术指标
- 灵活的经纪商接口
- 完整的事件驱动架构

主要组件：
- TradingEngine: 核心交易引擎
- Strategy: 策略基类
- DataFeed: 数据源基类
- Broker: 经纪商基类
- Indicator: 指标基类
- Account: 账户管理

使用示例：
    from core import TradingEngine, Strategy, SimulatedBroker
    
    # 创建引擎
    engine = TradingEngine("MyEngine")
    
    # 创建经纪商和策略
    broker = SimulatedBroker("MyBroker")
    strategy = MyStrategy("MyStrategy")
    
    # 添加到引擎
    engine.add_broker(broker)
    engine.add_strategy(strategy)
    
    # 启动交易
    engine.start()
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "Trading Framework Team"
__email__ = "support@tradingframework.com"
__description__ = "A Python trading framework inspired by backtrader"

# 核心基础类
from .base import (
    # 枚举类型
    OrderType,
    OrderSide, 
    OrderStatus,
    
    # 数据结构
    BarData,
    TickData,
    OrderData,
    TradeData,
    Position,
    Account,
    
    # 抽象基类
    Strategy,
    DataFeed,
    Indicator,
    Broker
)

# 交易引擎
from .engine import TradingEngine

# 数据管理
from .data_manager import (
    DataManager,
    MemoryDataFeed,
    LiveDataFeed
)

# 指标系统
from .indicators import (
    IndicatorManager,
    SimpleMovingAverage,
    ExponentialMovingAverage,
    RelativeStrengthIndex as RSI,
    BollingerBands,
    MACD,
    StochasticOscillator,
    AverageTrueRange as ATR
)

# 经纪商和账户管理
from .broker import (
    AccountManager,
    SimulatedBroker
)

# 便捷别名
SMA = SimpleMovingAverage
EMA = ExponentialMovingAverage
BB = BollingerBands
Stoch = StochasticOscillator

# 导出的主要类和函数
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__email__',
    '__description__',
    
    # 枚举类型
    'OrderType',
    'OrderSide',
    'OrderStatus',
    
    # 数据结构
    'BarData',
    'TickData', 
    'OrderData',
    'TradeData',
    'Position',
    'Account',
    
    # 核心抽象类
    'Strategy',
    'DataFeed',
    'Indicator',
    'Broker',
    
    # 核心引擎
    'TradingEngine',
    
    # 数据管理
    'DataManager',
    'MemoryDataFeed',
    'LiveDataFeed',
    
    # 指标系统
    'IndicatorManager',
    'SimpleMovingAverage',
    'SMA',
    'ExponentialMovingAverage', 
    'EMA',
    'RelativeStrengthIndex',
    'RSI',
    'BollingerBands',
    'BB',
    'MACD',
    'StochasticOscillator',
    'Stoch',
    'AverageTrueRange',
    'ATR',
    
    # 经纪商和账户
    'AccountManager',
    'SimulatedBroker'
]


def get_version():
    """获取框架版本信息"""
    return {
        'version': __version__,
        'author': __author__,
        'email': __email__,
        'description': __description__
    }


def create_engine(name: str = "TradingEngine") -> TradingEngine:
    """创建交易引擎的便捷函数"""
    return TradingEngine(name)


def create_broker(name: str = "SimulatedBroker", broker_type: str = "simulated") -> Broker:
    """创建经纪商的便捷函数
    
    Args:
        name: 经纪商名称
        broker_type: 经纪商类型，目前支持 'simulated'
    
    Returns:
        Broker: 经纪商实例
    """
    if broker_type.lower() == "simulated":
        return SimulatedBroker(name)
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")


def create_data_feed(name: str, data_type: str = "memory", data=None) -> DataFeed:
    """创建数据源的便捷函数
    
    Args:
        name: 数据源名称
        data_type: 数据源类型，支持 'memory', 'live'
        data: 数据（仅对memory类型有效）
    
    Returns:
        DataFeed: 数据源实例
    """
    if data_type.lower() == "memory":
        return MemoryDataFeed(name, data or [])
    elif data_type.lower() == "live":
        return LiveDataFeed(name)
    else:
        raise ValueError(f"Unsupported data feed type: {data_type}")


def create_indicator_manager(name: str = "IndicatorManager") -> IndicatorManager:
    """创建指标管理器的便捷函数"""
    return IndicatorManager(name)


# 框架信息打印
def print_framework_info():
    """打印框架信息"""
    info = get_version()
    print(f"""    
╔══════════════════════════════════════════════════════════════╗
║                    Trading Framework                         ║
║                                                              ║
║  Version: {info['version']:<50} ║
║  Author:  {info['author']:<50} ║
║  Email:   {info['email']:<50} ║
║                                                              ║
║  {info['description']:<58} ║
║                                                              ║
║  主要特性:                                                    ║
║  • 多账户管理                                                 ║
║  • 多策略并行运行                                             ║
║  • 多数据源支持                                               ║
║  • 丰富的技术指标                                             ║
║  • 灵活的经纪商接口                                           ║
║  • 完整的事件驱动架构                                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


# 快速开始示例
def quick_start_example():
    """快速开始示例"""
    print("\n=== 交易框架快速开始示例 ===")
    
    # 1. 创建引擎
    engine = create_engine("QuickStartEngine")
    print("✓ 创建交易引擎")
    
    # 2. 创建经纪商
    broker = create_broker("QuickBroker")
    broker.connect()
    print("✓ 创建并连接经纪商")
    
    # 3. 创建账户
    account = broker.create_account("demo_account", 100000)
    print("✓ 创建演示账户（初始资金: 100,000）")
    
    # 4. 创建简单策略
    class SimpleStrategy(Strategy):
        def on_start(self):
            self.logger.info("简单策略启动")
        
        def on_bar(self, bar):
            self.logger.info(f"收到K线数据: {bar.symbol} @ {bar.close}")
    
    strategy = SimpleStrategy("SimpleStrategy")
    strategy.account = account
    print("✓ 创建简单策略")
    
    # 5. 创建示例数据
    from datetime import datetime, timedelta
    sample_bars = [
        BarData(
            symbol="DEMO",
            datetime=datetime.now() - timedelta(minutes=i),
            open=100.0 + i,
            high=102.0 + i,
            low=98.0 + i,
            close=101.0 + i,
            volume=1000000
        ) for i in range(5)
    ]
    
    data_feed = create_data_feed("DemoData", "memory", sample_bars)
    print("✓ 创建示例数据源")
    
    # 6. 组装引擎
    engine.add_broker(broker)
    engine.add_strategy(strategy)
    engine.add_data_feed(data_feed)
    
    engine.connect_strategy_broker(strategy.name, broker.name)
    engine.connect_strategy_data(strategy.name, data_feed.name, "DEMO")
    print("✓ 组装交易引擎")
    
    # 7. 运行演示
    print("\n开始运行演示...")
    engine.start()
    
    import time
    time.sleep(2)  # 运行2秒
    
    engine.stop()
    broker.disconnect()
    
    print("\n✓ 演示完成！")
    print("\n要了解更多功能，请查看 example.py 文件中的完整示例。")


if __name__ == "__main__":
    # 打印框架信息
    print_framework_info()
    
    # 运行快速开始示例
    quick_start_example()