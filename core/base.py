from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import uuid


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单
    STOP = "stop"      # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"      # 待处理
    SUBMITTED = "submitted"  # 已提交
    PARTIAL = "partial"      # 部分成交
    FILLED = "filled"        # 完全成交
    CANCELLED = "cancelled"  # 已取消
    REJECTED = "rejected"    # 已拒绝


class BarData:
    """K线数据"""
    def __init__(self, symbol: str, datetime: datetime, open: float, high: float, 
                 low: float, close: float, volume: float):
        self.symbol = symbol
        self.datetime = datetime
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class TickData:
    """Tick数据"""
    def __init__(self, symbol: str, datetime: datetime, last_price: float, 
                 bid_price: float, ask_price: float, volume: float):
        self.symbol = symbol
        self.datetime = datetime
        self.last_price = last_price
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.volume = volume


class OrderData:
    """订单数据"""
    def __init__(self, symbol: str, order_type: OrderType, side: OrderSide, 
                 quantity: float, price: Optional[float] = None):
        self.order_id = str(uuid.uuid4())
        self.symbol = symbol
        self.order_type = order_type
        self.side = side
        self.quantity = quantity
        self.price = price
        self.filled_quantity = 0.0
        self.status = OrderStatus.PENDING
        self.create_time = datetime.now()
        self.update_time = datetime.now()


class TradeData:
    """成交数据"""
    def __init__(self, order_id: str, symbol: str, side: OrderSide, 
                 quantity: float, price: float):
        self.trade_id = str(uuid.uuid4())
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.trade_time = datetime.now()


class Position:
    """持仓数据"""
    def __init__(self, symbol: str, quantity: float = 0.0, avg_price: float = 0.0):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.market_value = 0.0
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0


class Account:
    """账户数据"""
    def __init__(self, account_id: str, initial_capital: float):
        self.account_id = account_id
        self.initial_capital = initial_capital
        self.total_capital = initial_capital
        self.available_capital = initial_capital
        self.frozen_capital = 0.0
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, OrderData] = {}
        self.trades: List[TradeData] = []


class Strategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.account: Optional[Account] = None
        self.broker: Optional['Broker'] = None
        self.data_feeds: Dict[str, 'DataFeed'] = {}
        self.indicators: Dict[str, 'Indicator'] = {}
        self.is_running = False
    
    @abstractmethod
    def on_start(self):
        """策略启动时调用"""
        pass
    
    @abstractmethod
    def on_stop(self):
        """策略停止时调用"""
        pass
    
    @abstractmethod
    def on_bar(self, bar: BarData):
        """收到K线数据时调用"""
        pass
    
    @abstractmethod
    def on_tick(self, tick: TickData):
        """收到Tick数据时调用"""
        pass
    
    @abstractmethod
    def on_order(self, order: OrderData):
        """订单状态更新时调用"""
        pass
    
    @abstractmethod
    def on_trade(self, trade: TradeData):
        """成交时调用"""
        pass
    
    def buy(self, symbol: str, quantity: float, price: Optional[float] = None, 
            order_type: OrderType = OrderType.MARKET) -> str:
        """买入"""
        if self.broker:
            order = OrderData(symbol, order_type, OrderSide.BUY, quantity, price)
            return self.broker.submit_order(order)
        raise RuntimeError("Broker not set")
    
    def sell(self, symbol: str, quantity: float, price: Optional[float] = None, 
             order_type: OrderType = OrderType.MARKET) -> str:
        """卖出"""
        if self.broker:
            order = OrderData(symbol, order_type, OrderSide.SELL, quantity, price)
            return self.broker.submit_order(order)
        raise RuntimeError("Broker not set")
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if self.broker:
            return self.broker.cancel_order(order_id)
        return False


class DataFeed(ABC):
    """数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.symbols: List[str] = []
        self.subscribers: List[Strategy] = []
    
    @abstractmethod
    def connect(self) -> bool:
        """连接数据源"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开数据源"""
        pass
    
    @abstractmethod
    def subscribe(self, symbols: List[str]):
        """订阅数据"""
        pass
    
    @abstractmethod
    def get_bars(self, symbol: str, start_date: datetime, end_date: datetime) -> List[BarData]:
        """获取历史K线数据"""
        pass
    
    def add_subscriber(self, strategy: Strategy):
        """添加订阅者"""
        if strategy not in self.subscribers:
            self.subscribers.append(strategy)
    
    def remove_subscriber(self, strategy: Strategy):
        """移除订阅者"""
        if strategy in self.subscribers:
            self.subscribers.remove(strategy)
    
    def notify_bar(self, bar: BarData):
        """通知K线数据"""
        for subscriber in self.subscribers:
            subscriber.on_bar(bar)
    
    def notify_tick(self, tick: TickData):
        """通知Tick数据"""
        for subscriber in self.subscribers:
            subscriber.on_tick(tick)


class Indicator(ABC):
    """指标基类"""
    
    def __init__(self, name: str, period: int = 20):
        self.name = name
        self.period = period
        self.values: List[float] = []
        self.data_buffer: List[float] = []
    
    @abstractmethod
    def calculate(self, data: Union[BarData, float]) -> Optional[float]:
        """计算指标值"""
        pass
    
    def update(self, data: Union[BarData, float]):
        """更新指标"""
        value = self.calculate(data)
        if value is not None:
            self.values.append(value)
    
    def get_value(self, index: int = -1) -> Optional[float]:
        """获取指标值"""
        if self.values and abs(index) <= len(self.values):
            return self.values[index]
        return None
    
    def get_values(self, count: int = None) -> List[float]:
        """获取指标值列表"""
        if count is None:
            return self.values.copy()
        return self.values[-count:] if count <= len(self.values) else self.values.copy()


class Broker(ABC):
    """经纪商基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.accounts: Dict[str, Account] = {}
        self.strategies: List[Strategy] = []
    
    @abstractmethod
    def connect(self) -> bool:
        """连接经纪商"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def submit_order(self, order: OrderData) -> str:
        """提交订单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass
    
    @abstractmethod
    def get_account_info(self, account_id: str) -> Optional[Account]:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_positions(self, account_id: str) -> Dict[str, Position]:
        """获取持仓信息"""
        pass
    
    def add_account(self, account: Account):
        """添加账户"""
        self.accounts[account.account_id] = account
    
    def add_strategy(self, strategy: Strategy):
        """添加策略"""
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            strategy.broker = self
    
    def notify_order_update(self, order: OrderData):
        """通知订单更新"""
        for strategy in self.strategies:
            strategy.on_order(order)
    
    def notify_trade(self, trade: TradeData):
        """通知成交"""
        for strategy in self.strategies:
            strategy.on_trade(trade)