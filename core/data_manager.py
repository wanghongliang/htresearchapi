from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import threading
import time
import logging
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from base import DataFeed, BarData, TickData, Strategy


class MemoryDataFeed(DataFeed):
    """内存数据源 - 用于回测和模拟"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.bar_data: Dict[str, List[BarData]] = defaultdict(list)
        self.tick_data: Dict[str, List[TickData]] = defaultdict(list)
        self.current_index: Dict[str, int] = defaultdict(int)
        self.is_connected = False
    
    def connect(self) -> bool:
        """连接数据源"""
        self.is_connected = True
        return True
    
    def disconnect(self):
        """断开数据源"""
        self.is_connected = False
    
    def subscribe(self, symbols: List[str]):
        """订阅数据"""
        self.symbols.extend(symbols)
    
    def add_bar_data(self, symbol: str, bars: List[BarData]):
        """添加K线数据"""
        self.bar_data[symbol].extend(bars)
        self.bar_data[symbol].sort(key=lambda x: x.datetime)
    
    def add_tick_data(self, symbol: str, ticks: List[TickData]):
        """添加Tick数据"""
        self.tick_data[symbol].extend(ticks)
        self.tick_data[symbol].sort(key=lambda x: x.datetime)
    
    def get_bars(self, symbol: str, start_date: datetime, end_date: datetime) -> List[BarData]:
        """获取历史K线数据"""
        if symbol not in self.bar_data:
            return []
        
        result = []
        for bar in self.bar_data[symbol]:
            if start_date <= bar.datetime <= end_date:
                result.append(bar)
        
        return result
    
    def get_next_bar(self, symbol: str) -> Optional[BarData]:
        """获取下一个K线数据"""
        if symbol not in self.bar_data:
            return None
        
        current_idx = self.current_index[symbol]
        if current_idx >= len(self.bar_data[symbol]):
            return None
        
        bar = self.bar_data[symbol][current_idx]
        self.current_index[symbol] += 1
        return bar
    
    def reset_index(self, symbol: str = None):
        """重置索引"""
        if symbol:
            self.current_index[symbol] = 0
        else:
            self.current_index.clear()


class LiveDataFeed(DataFeed):
    """实时数据源 - 连接外部数据提供商"""
    
    def __init__(self, name: str, data_provider: Any = None):
        super().__init__(name)
        self.data_provider = data_provider
        self.is_connected = False
        self.is_streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(f"LiveDataFeed.{name}")
    
    def connect(self) -> bool:
        """连接数据源"""
        try:
            if self.data_provider:
                # 这里应该调用实际的数据提供商连接方法
                # self.data_provider.connect()
                pass
            
            self.is_connected = True
            self.logger.info(f"Connected to live data feed {self.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to live data feed {self.name}: {e}")
            return False
    
    def disconnect(self):
        """断开数据源"""
        try:
            self.stop_streaming()
            
            if self.data_provider:
                # 这里应该调用实际的数据提供商断开方法
                # self.data_provider.disconnect()
                pass
            
            self.is_connected = False
            self.logger.info(f"Disconnected from live data feed {self.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from live data feed {self.name}: {e}")
    
    def subscribe(self, symbols: List[str]):
        """订阅数据"""
        self.symbols.extend(symbols)
        
        if self.data_provider:
            # 这里应该调用实际的数据提供商订阅方法
            # self.data_provider.subscribe(symbols)
            pass
    
    def start_streaming(self):
        """开始数据流"""
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._stream_data, daemon=True)
        self.stream_thread.start()
        self.logger.info(f"Started streaming for {self.name}")
    
    def stop_streaming(self):
        """停止数据流"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
        
        self.logger.info(f"Stopped streaming for {self.name}")
    
    def _stream_data(self):
        """数据流处理线程"""
        while self.is_streaming and self.is_connected:
            try:
                # 这里应该从实际的数据提供商获取数据
                # 示例：模拟数据生成
                for symbol in self.symbols:
                    # 模拟生成Tick数据
                    tick = self._generate_mock_tick(symbol)
                    if tick:
                        self.notify_tick(tick)
                
                time.sleep(1)  # 控制数据频率
                
            except Exception as e:
                self.logger.error(f"Error in data streaming: {e}")
                time.sleep(1)
    
    def _generate_mock_tick(self, symbol: str) -> Optional[TickData]:
        """生成模拟Tick数据（仅用于演示）"""
        import random
        
        base_price = 100.0
        price = base_price + random.uniform(-5, 5)
        
        return TickData(
            symbol=symbol,
            datetime=datetime.now(),
            last_price=price,
            bid_price=price - 0.01,
            ask_price=price + 0.01,
            volume=random.randint(100, 1000)
        )
    
    def get_bars(self, symbol: str, start_date: datetime, end_date: datetime) -> List[BarData]:
        """获取历史K线数据"""
        if self.data_provider:
            # 这里应该调用实际的数据提供商历史数据方法
            # return self.data_provider.get_historical_bars(symbol, start_date, end_date)
            pass
        
        return []


class DataManager:
    """数据管理器 - 统一管理多个数据源"""
    
    def __init__(self, name: str = "DataManager"):
        self.name = name
        self.logger = logging.getLogger(f"DataManager.{name}")
        
        # 数据源管理
        self.data_feeds: Dict[str, DataFeed] = {}
        self.primary_feed: Optional[str] = None
        
        # 数据缓存
        self.bar_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.tick_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        
        # 订阅管理
        self.symbol_subscribers: Dict[str, List[Strategy]] = defaultdict(list)
        self.feed_subscribers: Dict[str, List[Strategy]] = defaultdict(list)
        
        # 数据处理
        self.data_processors: List[Callable] = []
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 运行状态
        self.is_running = False
        self.lock = threading.RLock()
    
    def add_data_feed(self, data_feed: DataFeed, is_primary: bool = False) -> bool:
        """添加数据源"""
        try:
            with self.lock:
                if data_feed.name in self.data_feeds:
                    self.logger.warning(f"DataFeed {data_feed.name} already exists")
                    return False
                
                self.data_feeds[data_feed.name] = data_feed
                
                if is_primary or not self.primary_feed:
                    self.primary_feed = data_feed.name
                
                self.logger.info(f"Added data feed {data_feed.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add data feed {data_feed.name}: {e}")
            return False
    
    def remove_data_feed(self, feed_name: str) -> bool:
        """移除数据源"""
        try:
            with self.lock:
                if feed_name not in self.data_feeds:
                    self.logger.warning(f"DataFeed {feed_name} not found")
                    return False
                
                # 断开连接
                data_feed = self.data_feeds[feed_name]
                data_feed.disconnect()
                
                # 移除数据源
                del self.data_feeds[feed_name]
                
                # 更新主数据源
                if self.primary_feed == feed_name:
                    self.primary_feed = next(iter(self.data_feeds.keys()), None)
                
                self.logger.info(f"Removed data feed {feed_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove data feed {feed_name}: {e}")
            return False
    
    def subscribe_symbol(self, symbol: str, strategy: Strategy, feed_name: str = None) -> bool:
        """订阅股票数据"""
        try:
            with self.lock:
                # 确定使用的数据源
                target_feed = feed_name or self.primary_feed
                if not target_feed or target_feed not in self.data_feeds:
                    self.logger.error(f"DataFeed {target_feed} not found")
                    return False
                
                # 添加订阅
                if strategy not in self.symbol_subscribers[symbol]:
                    self.symbol_subscribers[symbol].append(strategy)
                
                if strategy not in self.feed_subscribers[target_feed]:
                    self.feed_subscribers[target_feed].append(strategy)
                
                # 订阅数据源
                data_feed = self.data_feeds[target_feed]
                if symbol not in data_feed.symbols:
                    data_feed.subscribe([symbol])
                
                self.logger.info(f"Subscribed strategy {strategy.name} to symbol {symbol} on feed {target_feed}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to subscribe symbol {symbol}: {e}")
            return False
    
    def unsubscribe_symbol(self, symbol: str, strategy: Strategy) -> bool:
        """取消订阅股票数据"""
        try:
            with self.lock:
                if symbol in self.symbol_subscribers:
                    if strategy in self.symbol_subscribers[symbol]:
                        self.symbol_subscribers[symbol].remove(strategy)
                        
                        if not self.symbol_subscribers[symbol]:
                            del self.symbol_subscribers[symbol]
                
                self.logger.info(f"Unsubscribed strategy {strategy.name} from symbol {symbol}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe symbol {symbol}: {e}")
            return False
    
    def add_data_processor(self, processor: Callable):
        """添加数据处理器"""
        self.data_processors.append(processor)
    
    def process_bar_data(self, bar: BarData):
        """处理K线数据"""
        try:
            # 缓存数据
            self.bar_cache[bar.symbol].append(bar)
            
            # 应用数据处理器
            for processor in self.data_processors:
                try:
                    processor(bar)
                except Exception as e:
                    self.logger.error(f"Error in data processor: {e}")
            
            # 分发给订阅者
            if bar.symbol in self.symbol_subscribers:
                for strategy in self.symbol_subscribers[bar.symbol]:
                    try:
                        strategy.on_bar(bar)
                    except Exception as e:
                        self.logger.error(f"Error notifying strategy {strategy.name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error processing bar data: {e}")
    
    def process_tick_data(self, tick: TickData):
        """处理Tick数据"""
        try:
            # 缓存数据
            self.tick_cache[tick.symbol].append(tick)
            
            # 应用数据处理器
            for processor in self.data_processors:
                try:
                    processor(tick)
                except Exception as e:
                    self.logger.error(f"Error in data processor: {e}")
            
            # 分发给订阅者
            if tick.symbol in self.symbol_subscribers:
                for strategy in self.symbol_subscribers[tick.symbol]:
                    try:
                        strategy.on_tick(tick)
                    except Exception as e:
                        self.logger.error(f"Error notifying strategy {strategy.name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error processing tick data: {e}")
    
    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        """获取最新K线数据"""
        if symbol in self.bar_cache and self.bar_cache[symbol]:
            return self.bar_cache[symbol][-1]
        return None
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick数据"""
        if symbol in self.tick_cache and self.tick_cache[symbol]:
            return self.tick_cache[symbol][-1]
        return None
    
    def get_bars(self, symbol: str, count: int = 100) -> List[BarData]:
        """获取K线数据列表"""
        if symbol in self.bar_cache:
            return list(self.bar_cache[symbol])[-count:]
        return []
    
    def get_ticks(self, symbol: str, count: int = 100) -> List[TickData]:
        """获取Tick数据列表"""
        if symbol in self.tick_cache:
            return list(self.tick_cache[symbol])[-count:]
        return []
    
    def start(self) -> bool:
        """启动数据管理器"""
        try:
            if self.is_running:
                self.logger.warning("DataManager is already running")
                return False
            
            # 连接所有数据源
            for data_feed in self.data_feeds.values():
                if not data_feed.connect():
                    self.logger.error(f"Failed to connect data feed {data_feed.name}")
                    return False
                
                # 启动实时数据流（如果支持）
                if isinstance(data_feed, LiveDataFeed):
                    data_feed.start_streaming()
            
            self.is_running = True
            self.logger.info("DataManager started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start DataManager: {e}")
            return False
    
    def stop(self) -> bool:
        """停止数据管理器"""
        try:
            if not self.is_running:
                self.logger.warning("DataManager is not running")
                return False
            
            # 断开所有数据源
            for data_feed in self.data_feeds.values():
                try:
                    if isinstance(data_feed, LiveDataFeed):
                        data_feed.stop_streaming()
                    data_feed.disconnect()
                except Exception as e:
                    self.logger.error(f"Failed to disconnect data feed {data_feed.name}: {e}")
            
            self.is_running = False
            self.executor.shutdown(wait=True)
            
            self.logger.info("DataManager stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop DataManager: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取数据管理器状态"""
        return {
            'name': self.name,
            'is_running': self.is_running,
            'data_feeds': list(self.data_feeds.keys()),
            'primary_feed': self.primary_feed,
            'subscribed_symbols': list(self.symbol_subscribers.keys()),
            'cached_symbols': {
                'bars': list(self.bar_cache.keys()),
                'ticks': list(self.tick_cache.keys())
            }
        }