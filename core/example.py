#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易框架使用示例

本示例展示如何使用交易框架进行多策略、多账户的交易：
1. 创建多个交易策略
2. 设置多个账户
3. 配置数据源和指标
4. 运行交易引擎
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

try:
    # Try relative imports first (when used as module)
    from .base import Strategy, BarData, TickData, OrderData, TradeData, OrderType, OrderSide
    from .engine import TradingEngine
    from .data_manager import DataManager, MemoryDataFeed, LiveDataFeed
    from .indicators import IndicatorManager, SimpleMovingAverage, RelativeStrengthIndex, BollingerBands
    from .broker import SimulatedBroker
except ImportError:
    # Fall back to absolute imports (when run directly)
    from base import Strategy, BarData, TickData, OrderData, TradeData, OrderType, OrderSide
    from engine import TradingEngine
    from data_manager import DataManager, MemoryDataFeed, LiveDataFeed
    from indicators import IndicatorManager, SimpleMovingAverage, RelativeStrengthIndex, BollingerBands
    from broker import SimulatedBroker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class MovingAverageCrossStrategy(Strategy):
    """移动平均线交叉策略"""
    
    def __init__(self, name: str, short_period: int = 5, long_period: int = 20):
        super().__init__(name)
        self.short_period = short_period
        self.long_period = long_period
        
        # 指标
        self.short_ma = None
        self.long_ma = None
        
        # 状态
        self.position = 0  # 0: 空仓, 1: 多头, -1: 空头
        self.last_signal = None
        
    def on_start(self):
        """策略启动时调用"""
        self.logger.info(f"Starting MA Cross Strategy: {self.short_period}/{self.long_period}")
        
        # 创建指标
        if self.indicator_manager:
            self.short_ma = self.indicator_manager.create_indicator(
                'SMA', f'{self.name}_short_ma', period=self.short_period
            )
            self.long_ma = self.indicator_manager.create_indicator(
                'SMA', f'{self.name}_long_ma', period=self.long_period
            )
    
    def on_bar(self, bar: BarData):
        """K线数据回调"""
        if not self.short_ma or not self.long_ma:
            return
        
        # 更新指标
        self.short_ma.update(bar.close)
        self.long_ma.update(bar.close)
        
        # 检查指标是否准备就绪
        if not (self.short_ma.is_ready() and self.long_ma.is_ready()):
            return
        
        short_value = self.short_ma.get_value()
        long_value = self.long_ma.get_value()
        
        # 生成交易信号
        signal = None
        if short_value > long_value and self.last_signal != 'buy':
            signal = 'buy'
        elif short_value < long_value and self.last_signal != 'sell':
            signal = 'sell'
        
        if signal:
            self.last_signal = signal
            
            if signal == 'buy' and self.position <= 0:
                # 买入信号
                if self.position < 0:
                    # 先平空头
                    self.close_position(bar.symbol)
                
                # 开多头
                quantity = self.calculate_position_size(bar.symbol, bar.close)
                if quantity > 0:
                    self.buy(bar.symbol, quantity, OrderType.MARKET)
                    self.position = 1
                    self.logger.info(f"MA Cross BUY signal: {bar.symbol} @ {bar.close}")
            
            elif signal == 'sell' and self.position >= 0:
                # 卖出信号
                if self.position > 0:
                    # 先平多头
                    self.close_position(bar.symbol)
                
                # 开空头（如果支持）
                quantity = self.calculate_position_size(bar.symbol, bar.close)
                if quantity > 0:
                    self.sell(bar.symbol, quantity, OrderType.MARKET)
                    self.position = -1
                    self.logger.info(f"MA Cross SELL signal: {bar.symbol} @ {bar.close}")
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """计算仓位大小"""
        if not self.account:
            return 0
        
        # 使用10%的可用资金
        available_capital = self.account.available_capital * 0.1
        quantity = int(available_capital / price / 100) * 100  # 整手交易
        
        return max(quantity, 0)
    
    def close_position(self, symbol: str):
        """平仓"""
        if not self.account or symbol not in self.account.positions:
            return
        
        position = self.account.positions[symbol]
        if position.quantity > 0:
            self.sell(symbol, position.quantity, OrderType.MARKET)
            self.logger.info(f"Close long position: {symbol} {position.quantity}")
        elif position.quantity < 0:
            self.buy(symbol, abs(position.quantity), OrderType.MARKET)
            self.logger.info(f"Close short position: {symbol} {abs(position.quantity)}")
        
        self.position = 0
    
    def on_stop(self):
        """策略停止时调用"""
        self.logger.info(f"Stopping MA Cross Strategy: {self.name}")
    
    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        pass  # 该策略不使用tick数据
    
    def on_order(self, order: OrderData):
        """订单状态更新时调用"""
        self.logger.info(f"Order update: {order.order_id} - {order.status}")
    
    def on_trade(self, trade: TradeData):
        """成交时调用"""
        self.logger.info(f"Trade executed: {trade.symbol} {trade.side} {trade.quantity}@{trade.price}")


class RSIStrategy(Strategy):
    """RSI超买超卖策略"""
    
    def __init__(self, name: str, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(name)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        
        # 指标
        self.rsi = None
        
        # 状态
        self.position = 0
        self.last_rsi = None
    
    def on_start(self):
        """策略启动时调用"""
        self.logger.info(f"Starting RSI Strategy: period={self.period}, oversold={self.oversold}, overbought={self.overbought}")
        
        # 创建RSI指标
        if self.indicator_manager:
            self.rsi = self.indicator_manager.create_indicator(
                'RSI', f'{self.name}_rsi', period=self.period
            )
    
    def on_bar(self, bar: BarData):
        """K线数据回调"""
        if not self.rsi:
            return
        
        # 更新RSI指标
        self.rsi.update(bar.close)
        
        if not self.rsi.is_ready():
            return
        
        current_rsi = self.rsi.get_value()
        
        # RSI策略逻辑
        if self.last_rsi is not None:
            # 超卖反弹买入
            if (self.last_rsi <= self.oversold and current_rsi > self.oversold and 
                self.position <= 0):
                
                if self.position < 0:
                    self.close_position(bar.symbol)
                
                quantity = self.calculate_position_size(bar.symbol, bar.close)
                if quantity > 0:
                    self.buy(bar.symbol, quantity, OrderType.MARKET)
                    self.position = 1
                    self.logger.info(f"RSI BUY signal: {bar.symbol} @ {bar.close}, RSI: {current_rsi:.2f}")
            
            # 超买回调卖出
            elif (self.last_rsi >= self.overbought and current_rsi < self.overbought and 
                  self.position >= 0):
                
                if self.position > 0:
                    self.close_position(bar.symbol)
                
                quantity = self.calculate_position_size(bar.symbol, bar.close)
                if quantity > 0:
                    self.sell(bar.symbol, quantity, OrderType.MARKET)
                    self.position = -1
                    self.logger.info(f"RSI SELL signal: {bar.symbol} @ {bar.close}, RSI: {current_rsi:.2f}")
        
        self.last_rsi = current_rsi
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """计算仓位大小"""
        if not self.account:
            return 0
        
        # 使用8%的可用资金
        available_capital = self.account.available_capital * 0.08
        quantity = int(available_capital / price / 100) * 100  # 整手交易
        
        return max(quantity, 0)
    
    def close_position(self, symbol: str):
        """平仓"""
        if not self.account or symbol not in self.account.positions:
            return
        
        position = self.account.positions[symbol]
        if position.quantity > 0:
            self.sell(symbol, position.quantity, OrderType.MARKET)
            self.logger.info(f"Close long position: {symbol} {position.quantity}")
        elif position.quantity < 0:
            self.buy(symbol, abs(position.quantity), OrderType.MARKET)
            self.logger.info(f"Close short position: {symbol} {abs(position.quantity)}")
        
        self.position = 0
    
    def on_stop(self):
        """策略停止时调用"""
        self.logger.info(f"Stopping RSI Strategy: {self.name}")
    
    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        pass  # 该策略不使用tick数据
    
    def on_order(self, order: OrderData):
        """订单状态更新时调用"""
        self.logger.info(f"Order update: {order.order_id} - {order.status}")
    
    def on_trade(self, trade: TradeData):
        """成交时调用"""
        self.logger.info(f"Trade executed: {trade.symbol} {trade.side} {trade.quantity}@{trade.price}")


class BollingerBandsStrategy(Strategy):
    """布林带策略"""
    
    def __init__(self, name: str, period: int = 20, std_dev: float = 2.0):
        super().__init__(name)
        self.period = period
        self.std_dev = std_dev
        
        # 指标
        self.bb = None
        
        # 状态
        self.position = 0
    
    def on_start(self):
        """策略启动时调用"""
        self.logger.info(f"Starting Bollinger Bands Strategy: period={self.period}, std_dev={self.std_dev}")
        
        # 创建布林带指标
        if self.indicator_manager:
            self.bb = self.indicator_manager.create_indicator(
                'BB', f'{self.name}_bb', period=self.period, std_dev=self.std_dev
            )
    
    def on_bar(self, bar: BarData):
        """K线数据回调"""
        if not self.bb:
            return
        
        # 更新布林带指标
        self.bb.update(bar.close)
        
        if not self.bb.is_ready():
            return
        
        upper, middle, lower = self.bb.get_value()
        
        # 布林带策略逻辑
        if bar.close <= lower and self.position <= 0:
            # 价格触及下轨，买入
            if self.position < 0:
                self.close_position(bar.symbol)
            
            quantity = self.calculate_position_size(bar.symbol, bar.close)
            if quantity > 0:
                self.buy(bar.symbol, quantity, OrderType.MARKET)
                self.position = 1
                self.logger.info(f"BB BUY signal: {bar.symbol} @ {bar.close}, Lower: {lower:.2f}")
        
        elif bar.close >= upper and self.position >= 0:
            # 价格触及上轨，卖出
            if self.position > 0:
                self.close_position(bar.symbol)
            
            quantity = self.calculate_position_size(bar.symbol, bar.close)
            if quantity > 0:
                self.sell(bar.symbol, quantity, OrderType.MARKET)
                self.position = -1
                self.logger.info(f"BB SELL signal: {bar.symbol} @ {bar.close}, Upper: {upper:.2f}")
        
        elif self.position != 0 and lower < bar.close < upper:
            # 价格回到中轨附近，平仓
            if abs(bar.close - middle) / middle < 0.01:  # 1%范围内
                self.close_position(bar.symbol)
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """计算仓位大小"""
        if not self.account:
            return 0
        
        # 使用12%的可用资金
        available_capital = self.account.available_capital * 0.12
        quantity = int(available_capital / price / 100) * 100  # 整手交易
        
        return max(quantity, 0)
    
    def close_position(self, symbol: str):
        """平仓"""
        if not self.account or symbol not in self.account.positions:
            return
        
        position = self.account.positions[symbol]
        if position.quantity > 0:
            self.sell(symbol, position.quantity, OrderType.MARKET)
            self.logger.info(f"Close long position: {symbol} {position.quantity}")
        elif position.quantity < 0:
            self.buy(symbol, abs(position.quantity), OrderType.MARKET)
            self.logger.info(f"Close short position: {symbol} {abs(position.quantity)}")
        
        self.position = 0
    
    def on_stop(self):
        """策略停止时调用"""
        self.logger.info(f"Stopping Bollinger Bands Strategy: {self.name}")
    
    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        pass  # 该策略不使用tick数据
    
    def on_order(self, order: OrderData):
        """订单状态更新时调用"""
        self.logger.info(f"Order update: {order.order_id} - {order.status}")
    
    def on_trade(self, trade: TradeData):
        """成交时调用"""
        self.logger.info(f"Trade executed: {trade.symbol} {trade.side} {trade.quantity}@{trade.price}")


def create_sample_data() -> List[BarData]:
    """创建示例K线数据"""
    import random
    
    bars = []
    base_price = 100.0
    current_time = datetime.now() - timedelta(days=100)
    
    for i in range(100):
        # 模拟价格波动
        change = random.uniform(-0.05, 0.05)  # ±5%波动
        base_price *= (1 + change)
        
        # 生成OHLC数据
        open_price = base_price
        high_price = open_price * (1 + random.uniform(0, 0.03))
        low_price = open_price * (1 - random.uniform(0, 0.03))
        close_price = random.uniform(low_price, high_price)
        
        bar = BarData(
            symbol="000001",
            datetime=current_time + timedelta(days=i),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=random.randint(1000000, 10000000)
        )
        
        bars.append(bar)
        base_price = close_price
    
    return bars


def run_backtest_example():
    """运行回测示例"""
    print("\n=== 交易框架回测示例 ===")
    
    # 1. 创建交易引擎
    engine = TradingEngine("BacktestEngine")
    
    # 2. 创建经纪商
    broker = SimulatedBroker("SimBroker")
    broker.connect()
    
    # 3. 创建账户
    account1 = broker.create_account("account_001", 1000000)  # 100万初始资金
    account2 = broker.create_account("account_002", 500000)   # 50万初始资金
    
    # 4. 创建策略
    ma_strategy = MovingAverageCrossStrategy("MA_Strategy", short_period=5, long_period=20)
    rsi_strategy = RSIStrategy("RSI_Strategy", period=14)
    bb_strategy = BollingerBandsStrategy("BB_Strategy", period=20)
    
    # 5. 分配账户给策略
    ma_strategy.account = account1
    rsi_strategy.account = account1  # 同一账户运行多个策略
    bb_strategy.account = account2   # 不同账户运行策略
    
    # 6. 创建数据源
    sample_data = create_sample_data()
    data_feed = MemoryDataFeed("SampleData")
    data_feed.add_bar_data("AAPL", sample_data)
    
    # 7. 添加组件到引擎
    engine.add_broker(broker)
    engine.add_strategy(ma_strategy, "account_001")
    engine.add_strategy(rsi_strategy, "account_001")
    engine.add_strategy(bb_strategy, "account_002")
    engine.add_data_feed(data_feed)
    
    # 8. 连接策略与经纪商
    engine.connect_strategy_to_broker(ma_strategy.name, broker.name)
    engine.connect_strategy_to_broker(rsi_strategy.name, broker.name)
    engine.connect_strategy_to_broker(bb_strategy.name, broker.name)
    
    # 9. 连接策略与数据源
    engine.connect_strategy_to_data_feed(ma_strategy.name, data_feed.name)
    engine.connect_strategy_to_data_feed(rsi_strategy.name, data_feed.name)
    engine.connect_strategy_to_data_feed(bb_strategy.name, data_feed.name)
    
    # 10. 启动引擎
    print("启动交易引擎...")
    engine.start()
    
    # 11. 运行回测
    print("开始回测...")
    try:
        # 模拟运行一段时间
        for i in range(10):
            time.sleep(0.1)  # 模拟实时运行
            
            # 更新市场数据
            if i < len(sample_data):
                current_bar = sample_data[i]
                broker.update_market_data(current_bar.symbol, current_bar.close)
            
            # 打印进度
            if i % 5 == 0:
                print(f"回测进度: {i+1}/10")
                
                # 打印账户状态
                for account_id in ["account_001", "account_002"]:
                    account = broker.get_account_info(account_id)
                    if account:
                        print(f"  账户 {account_id}: 总资产={account.total_capital:.2f}, 可用资金={account.available_capital:.2f}")
    
    except KeyboardInterrupt:
        print("\n用户中断回测")
    
    finally:
        # 12. 停止引擎
        print("\n停止交易引擎...")
        engine.stop()
        broker.disconnect()
        
        # 13. 打印最终结果
        print("\n=== 回测结果 ===")
        
        # 打印策略统计
        for strategy_name in [ma_strategy.name, rsi_strategy.name, bb_strategy.name]:
            stats = engine.get_strategy_performance(strategy_name)
            if stats:
                print(f"\n策略 {strategy_name}:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
        
        # 打印账户摘要
        for account_id in ["account_001", "account_002"]:
            summary = broker.account_manager.get_account_summary(account_id)
            if summary:
                print(f"\n账户 {account_id} 摘要:")
                for key, value in summary.items():
                    if key != 'positions':
                        print(f"  {key}: {value}")
                    else:
                        print(f"  持仓:")
                        for symbol, pos_info in value.items():
                            print(f"    {symbol}: {pos_info}")
        
        # 打印经纪商状态
        broker_status = broker.get_broker_status()
        print(f"\n经纪商状态:")
        for key, value in broker_status.items():
            print(f"  {key}: {value}")


def run_live_trading_example():
    """运行实盘交易示例（模拟）"""
    print("\n=== 交易框架实盘示例 ===")
    
    # 1. 创建交易引擎
    engine = TradingEngine("LiveEngine")
    
    # 2. 创建经纪商
    broker = SimulatedBroker("LiveBroker")
    broker.connect()
    
    # 3. 创建账户
    account = broker.create_account("live_account", 100000)  # 10万初始资金
    
    # 4. 创建策略
    strategy = MovingAverageCrossStrategy("Live_MA_Strategy", short_period=3, long_period=10)
    strategy.account = account
    
    # 5. 创建实时数据源（模拟）
    live_data_feed = LiveDataFeed("LiveData")
    
    # 6. 添加组件到引擎
    engine.add_broker(broker)
    engine.add_strategy(strategy, "live_account")
    engine.add_data_feed(live_data_feed)
    
    # 7. 连接组件
    engine.connect_strategy_to_broker(strategy.name, broker.name)
    engine.connect_strategy_to_data_feed(strategy.name, live_data_feed.name)
    
    # 8. 启动引擎
    print("启动实盘交易引擎...")
    engine.start()
    
    # 9. 模拟实时数据推送
    print("开始接收实时数据...")
    try:
        base_price = 50.0
        
        for i in range(20):
            # 模拟实时价格变化
            import random
            price_change = random.uniform(-0.02, 0.02)
            base_price *= (1 + price_change)
            
            # 创建实时数据
            current_time = datetime.now()
            bar = BarData(
                symbol="000001",
                datetime=current_time,
                open=base_price,
                high=base_price * 1.01,
                low=base_price * 0.99,
                close=base_price,
                volume=random.randint(100000, 1000000)
            )
            
            # 推送数据到策略
            live_data_feed.notify_bar(bar)
            broker.update_market_data(bar.symbol, bar.close)
            
            print(f"时间: {current_time.strftime('%H:%M:%S')}, 价格: {base_price:.2f}")
            
            time.sleep(1)  # 每秒更新一次
    
    except KeyboardInterrupt:
        print("\n用户中断实盘交易")
    
    finally:
        # 10. 停止引擎
        print("\n停止实盘交易引擎...")
        engine.stop()
        broker.disconnect()
        
        # 11. 打印最终结果
        print("\n=== 实盘交易结果 ===")
        
        summary = broker.account_manager.get_account_summary("live_account")
        if summary:
            print(f"账户摘要:")
            for key, value in summary.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    # 运行回测示例
    run_backtest_example()
    
    print("\n" + "="*50)
    
    # 运行实盘示例
    run_live_trading_example()
    
    print("\n示例运行完成！")