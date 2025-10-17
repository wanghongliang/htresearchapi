# 交易框架 (Trading Framework)

一个参考 backtrader 架构设计的 Python 交易框架，支持多账户、多策略、多数据源的量化交易系统。

## 🚀 主要特性

- **多账户管理**: 支持同时管理多个交易账户
- **多策略并行**: 一个账户可以运行多个策略，多个策略可以共享账户
- **多数据源支持**: 支持历史数据回测和实时数据交易
- **丰富的技术指标**: 内置常用技术指标（MA、RSI、MACD、布林带等）
- **灵活的经纪商接口**: 支持模拟交易和实盘交易接口
- **事件驱动架构**: 完整的事件驱动系统，支持策略间通信
- **风险管理**: 内置风控系统，支持仓位管理和资金管理

## 📦 框架结构

```
core/
├── __init__.py          # 框架入口，导出所有核心类
├── base.py              # 基础抽象类和数据结构
├── engine.py            # 核心交易引擎
├── data_manager.py      # 数据源管理器
├── indicators.py        # 技术指标系统
├── broker.py            # 经纪商和账户管理
├── example.py           # 完整使用示例
└── README.md            # 说明文档
```

## 🛠️ 核心组件

### 1. TradingEngine (交易引擎)
核心调度器，负责管理所有组件的生命周期和事件分发。

### 2. Strategy (策略基类)
所有交易策略的基类，提供标准的策略接口。

### 3. Broker (经纪商接口)
处理订单执行、账户管理和风险控制。

### 4. DataFeed (数据源)
提供历史数据和实时数据流。

### 5. Indicator (技术指标)
计算各种技术指标，支持策略决策。

### 6. Account (账户管理)
管理资金、持仓和交易记录。

## 🚀 快速开始

### 安装依赖

```bash
pip install pandas numpy logging threading
```

### 基础使用示例

```python
from core import (
    TradingEngine, Strategy, SimulatedBroker, 
    MemoryDataFeed, BarData, OrderType
)
from datetime import datetime, timedelta

# 1. 创建简单策略
class MyStrategy(Strategy):
    def on_start(self):
        self.logger.info("策略启动")
    
    def on_bar(self, bar):
        # 简单的买入策略
        if bar.close > 100:
            self.buy(bar.symbol, 100, OrderType.MARKET)

# 2. 创建交易引擎
engine = TradingEngine("MyEngine")

# 3. 创建经纪商和账户
broker = SimulatedBroker("MyBroker")
broker.connect()
account = broker.create_account("account_001", 100000)

# 4. 创建策略
strategy = MyStrategy("MyStrategy")
strategy.account = account

# 5. 创建数据源
sample_data = [
    BarData(
        symbol="STOCK001",
        datetime=datetime.now(),
        open=100, high=105, low=95, close=102,
        volume=1000000
    )
]
data_feed = MemoryDataFeed("MyData", sample_data)

# 6. 组装引擎
engine.add_broker(broker)
engine.add_strategy(strategy)
engine.add_data_feed(data_feed)

engine.connect_strategy_broker(strategy.name, broker.name)
engine.connect_strategy_data(strategy.name, data_feed.name, "STOCK001")

# 7. 启动交易
engine.start()

# 8. 运行一段时间后停止
import time
time.sleep(5)
engine.stop()
broker.disconnect()
```

## 📊 策略开发

### 创建自定义策略

```python
from core import Strategy, BarData, OrderType

class MovingAverageStrategy(Strategy):
    def __init__(self, name, short_period=5, long_period=20):
        super().__init__(name)
        self.short_period = short_period
        self.long_period = long_period
        self.prices = []
        
    def on_start(self):
        self.logger.info(f"MA策略启动: {self.short_period}/{self.long_period}")
        
    def on_bar(self, bar):
        self.prices.append(bar.close)
        
        # 保持价格列表长度
        if len(self.prices) > self.long_period:
            self.prices.pop(0)
            
        # 计算移动平均线
        if len(self.prices) >= self.long_period:
            short_ma = sum(self.prices[-self.short_period:]) / self.short_period
            long_ma = sum(self.prices) / len(self.prices)
            
            # 交易信号
            if short_ma > long_ma:
                # 买入信号
                quantity = self.calculate_position_size(bar.symbol, bar.close)
                if quantity > 0:
                    self.buy(bar.symbol, quantity, OrderType.MARKET)
                    
    def calculate_position_size(self, symbol, price):
        if not self.account:
            return 0
        # 使用10%的可用资金
        available = self.account.available_capital * 0.1
        return int(available / price / 100) * 100  # 整手交易
```

### 使用技术指标

```python
from core import Strategy, IndicatorManager

class RSIStrategy(Strategy):
    def on_start(self):
        # 创建指标管理器
        self.indicator_manager = IndicatorManager("RSI_Indicators")
        
        # 创建RSI指标
        self.rsi = self.indicator_manager.create_indicator(
            'rsi', 'my_rsi', period=14
        )
        
    def on_bar(self, bar):
        # 更新指标
        self.rsi.update(bar.close)
        
        if self.rsi.is_ready():
            rsi_value = self.rsi.get_value()
            
            # RSI策略逻辑
            if rsi_value < 30:  # 超卖
                self.buy(bar.symbol, 100, OrderType.MARKET)
            elif rsi_value > 70:  # 超买
                self.sell(bar.symbol, 100, OrderType.MARKET)
```

## 🏦 多账户管理

```python
# 创建多个账户
account1 = broker.create_account("account_001", 1000000)  # 主账户
account2 = broker.create_account("account_002", 500000)   # 备用账户

# 创建多个策略
strategy1 = MovingAverageStrategy("MA_Strategy")
strategy2 = RSIStrategy("RSI_Strategy")
strategy3 = BollingerBandsStrategy("BB_Strategy")

# 分配账户
strategy1.account = account1
strategy2.account = account1  # 同一账户运行多个策略
strategy3.account = account2  # 不同账户运行策略

# 添加到引擎
engine.add_strategy(strategy1)
engine.add_strategy(strategy2)
engine.add_strategy(strategy3)
```

## 📈 数据源配置

### 历史数据回测

```python
from core import MemoryDataFeed, BarData

# 准备历史数据
historical_data = [
    BarData(symbol="STOCK001", datetime=datetime(2023, 1, 1), 
            open=100, high=105, low=95, close=102, volume=1000000),
    BarData(symbol="STOCK001", datetime=datetime(2023, 1, 2), 
            open=102, high=108, low=100, close=106, volume=1200000),
    # ... 更多数据
]

# 创建内存数据源
data_feed = MemoryDataFeed("HistoricalData", historical_data)
```

### 实时数据交易

```python
from core import LiveDataFeed

# 创建实时数据源
live_feed = LiveDataFeed("LiveData")

# 在实际应用中，你需要连接到数据提供商
# 例如：连接到股票API、期货API等
```

## 🛡️ 风险管理

框架内置多层风险管理机制：

### 1. 资金管理
- 可用资金检查
- 冻结资金管理
- 持仓比例限制

### 2. 订单风控
- 每分钟订单数量限制
- 单笔订单金额限制
- 持仓集中度控制

### 3. 账户风控
- 单日最大亏损限制
- 总资产监控
- 强制平仓机制

```python
# 配置风控参数
broker.account_manager.max_position_ratio = 0.3      # 单个持仓最大30%
broker.account_manager.max_daily_loss_ratio = 0.05   # 单日最大亏损5%
broker.account_manager.max_orders_per_minute = 10    # 每分钟最多10个订单
```

## 📊 性能监控

```python
# 获取策略统计
stats = engine.get_strategy_stats("MyStrategy")
print(f"策略统计: {stats}")

# 获取账户摘要
summary = broker.account_manager.get_account_summary("account_001")
print(f"账户摘要: {summary}")

# 获取经纪商状态
status = broker.get_broker_status()
print(f"经纪商状态: {status}")
```

## 🔧 高级功能

### 1. 策略间通信
策略可以通过事件系统进行通信：

```python
class MasterStrategy(Strategy):
    def on_bar(self, bar):
        # 发送信号给其他策略
        self.send_signal("market_trend", "bullish")

class SlaveStrategy(Strategy):
    def on_signal(self, signal_name, signal_data):
        if signal_name == "market_trend" and signal_data == "bullish":
            # 根据主策略信号调整交易
            self.adjust_position()
```

### 2. 自定义指标

```python
from core import Indicator

class CustomIndicator(Indicator):
    def __init__(self, name, period=20):
        super().__init__(name)
        self.period = period
        self.values = []
        
    def update(self, value):
        self.values.append(value)
        if len(self.values) > self.period:
            self.values.pop(0)
            
    def get_value(self):
        if len(self.values) >= self.period:
            # 自定义计算逻辑
            return sum(self.values) / len(self.values)
        return None
        
    def is_ready(self):
        return len(self.values) >= self.period
```

## 📝 完整示例

查看 `example.py` 文件获取完整的使用示例，包括：
- 多策略回测示例
- 实时交易示例
- 技术指标使用示例
- 风险管理示例

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个框架。

## 📄 许可证

MIT License

## 📞 联系方式

- Email: support@tradingframework.com
- 项目地址: [GitHub Repository]

---

**注意**: 这是一个教育和研究用途的交易框架。在实际交易中使用前，请充分测试并了解相关风险。