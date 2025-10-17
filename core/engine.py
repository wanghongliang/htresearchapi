from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from base import (
    Strategy, DataFeed, Broker, Account, Indicator,
    BarData, TickData, OrderData, TradeData
)


class TradingEngine:
    """交易引擎 - 核心调度器"""
    
    def __init__(self, name: str = "TradingEngine"):
        self.name = name
        self.logger = self._setup_logger()
        
        # 核心组件
        self.strategies: Dict[str, Strategy] = {}
        self.data_feeds: Dict[str, DataFeed] = {}
        self.brokers: Dict[str, Broker] = {}
        self.accounts: Dict[str, Account] = {}
        self.indicators: Dict[str, Indicator] = {}
        
        # 策略与账户的映射关系
        self.strategy_accounts: Dict[str, str] = {}  # strategy_name -> account_id
        self.account_strategies: Dict[str, List[str]] = {}  # account_id -> [strategy_names]
        
        # 运行状态
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.main_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger(f"TradingEngine.{self.name}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def add_strategy(self, strategy: Strategy, account_id: str) -> bool:
        """添加策略并绑定账户"""
        try:
            with self.lock:
                if strategy.name in self.strategies:
                    self.logger.warning(f"Strategy {strategy.name} already exists")
                    return False
                
                if account_id not in self.accounts:
                    self.logger.error(f"Account {account_id} not found")
                    return False
                
                # 添加策略
                self.strategies[strategy.name] = strategy
                strategy.account = self.accounts[account_id]
                
                # 建立映射关系
                self.strategy_accounts[strategy.name] = account_id
                if account_id not in self.account_strategies:
                    self.account_strategies[account_id] = []
                self.account_strategies[account_id].append(strategy.name)
                
                self.logger.info(f"Added strategy {strategy.name} to account {account_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add strategy {strategy.name}: {e}")
            return False
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """移除策略"""
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    self.logger.warning(f"Strategy {strategy_name} not found")
                    return False
                
                # 停止策略
                strategy = self.strategies[strategy_name]
                if strategy.is_running:
                    strategy.on_stop()
                    strategy.is_running = False
                
                # 移除映射关系
                account_id = self.strategy_accounts.get(strategy_name)
                if account_id and account_id in self.account_strategies:
                    self.account_strategies[account_id].remove(strategy_name)
                    if not self.account_strategies[account_id]:
                        del self.account_strategies[account_id]
                
                # 移除策略
                del self.strategies[strategy_name]
                del self.strategy_accounts[strategy_name]
                
                self.logger.info(f"Removed strategy {strategy_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove strategy {strategy_name}: {e}")
            return False
    
    def add_account(self, account: Account) -> bool:
        """添加账户"""
        try:
            with self.lock:
                if account.account_id in self.accounts:
                    self.logger.warning(f"Account {account.account_id} already exists")
                    return False
                
                self.accounts[account.account_id] = account
                self.logger.info(f"Added account {account.account_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add account {account.account_id}: {e}")
            return False
    
    def add_data_feed(self, data_feed: DataFeed) -> bool:
        """添加数据源"""
        try:
            with self.lock:
                if data_feed.name in self.data_feeds:
                    self.logger.warning(f"DataFeed {data_feed.name} already exists")
                    return False
                
                self.data_feeds[data_feed.name] = data_feed
                self.logger.info(f"Added data feed {data_feed.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add data feed {data_feed.name}: {e}")
            return False
    
    def add_broker(self, broker: Broker) -> bool:
        """添加经纪商"""
        try:
            with self.lock:
                if broker.name in self.brokers:
                    self.logger.warning(f"Broker {broker.name} already exists")
                    return False
                
                self.brokers[broker.name] = broker
                self.logger.info(f"Added broker {broker.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add broker {broker.name}: {e}")
            return False
    
    def connect_strategy_to_data_feed(self, strategy_name: str, data_feed_name: str) -> bool:
        """连接策略到数据源"""
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    self.logger.error(f"Strategy {strategy_name} not found")
                    return False
                
                if data_feed_name not in self.data_feeds:
                    self.logger.error(f"DataFeed {data_feed_name} not found")
                    return False
                
                strategy = self.strategies[strategy_name]
                data_feed = self.data_feeds[data_feed_name]
                
                strategy.data_feeds[data_feed_name] = data_feed
                data_feed.add_subscriber(strategy)
                
                self.logger.info(f"Connected strategy {strategy_name} to data feed {data_feed_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect strategy to data feed: {e}")
            return False
    
    def connect_strategy_to_broker(self, strategy_name: str, broker_name: str) -> bool:
        """连接策略到经纪商"""
        try:
            with self.lock:
                if strategy_name not in self.strategies:
                    self.logger.error(f"Strategy {strategy_name} not found")
                    return False
                
                if broker_name not in self.brokers:
                    self.logger.error(f"Broker {broker_name} not found")
                    return False
                
                strategy = self.strategies[strategy_name]
                broker = self.brokers[broker_name]
                
                strategy.broker = broker
                broker.add_strategy(strategy)
                
                self.logger.info(f"Connected strategy {strategy_name} to broker {broker_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect strategy to broker: {e}")
            return False
    
    def start(self) -> bool:
        """启动交易引擎"""
        try:
            if self.is_running:
                self.logger.warning("Trading engine is already running")
                return False
            
            self.logger.info("Starting trading engine...")
            
            # 连接所有数据源
            for data_feed in self.data_feeds.values():
                if not data_feed.connect():
                    self.logger.error(f"Failed to connect data feed {data_feed.name}")
                    return False
            
            # 连接所有经纪商
            for broker in self.brokers.values():
                if not broker.connect():
                    self.logger.error(f"Failed to connect broker {broker.name}")
                    return False
            
            # 启动所有策略
            for strategy in self.strategies.values():
                try:
                    strategy.on_start()
                    strategy.is_running = True
                    self.logger.info(f"Started strategy {strategy.name}")
                except Exception as e:
                    self.logger.error(f"Failed to start strategy {strategy.name}: {e}")
                    return False
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # 启动主循环
            self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()
            
            self.logger.info("Trading engine started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start trading engine: {e}")
            return False
    
    def stop(self) -> bool:
        """停止交易引擎"""
        try:
            if not self.is_running:
                self.logger.warning("Trading engine is not running")
                return False
            
            self.logger.info("Stopping trading engine...")
            
            self.is_running = False
            self.stop_time = datetime.now()
            
            # 停止所有策略
            for strategy in self.strategies.values():
                try:
                    strategy.on_stop()
                    strategy.is_running = False
                    self.logger.info(f"Stopped strategy {strategy.name}")
                except Exception as e:
                    self.logger.error(f"Failed to stop strategy {strategy.name}: {e}")
            
            # 断开所有数据源
            for data_feed in self.data_feeds.values():
                try:
                    data_feed.disconnect()
                except Exception as e:
                    self.logger.error(f"Failed to disconnect data feed {data_feed.name}: {e}")
            
            # 断开所有经纪商
            for broker in self.brokers.values():
                try:
                    broker.disconnect()
                except Exception as e:
                    self.logger.error(f"Failed to disconnect broker {broker.name}: {e}")
            
            # 等待主线程结束
            if self.main_thread and self.main_thread.is_alive():
                self.main_thread.join(timeout=5)
            
            self.logger.info("Trading engine stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop trading engine: {e}")
            return False
    
    def _main_loop(self):
        """主循环"""
        self.logger.info("Main loop started")
        
        while self.is_running:
            try:
                # 这里可以添加定期任务，如状态检查、性能监控等
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(1)
        
        self.logger.info("Main loop stopped")
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        """获取策略性能统计"""
        if strategy_name not in self.strategies:
            return {}
        
        strategy = self.strategies[strategy_name]
        account_id = self.strategy_accounts.get(strategy_name)
        
        if not account_id or account_id not in self.accounts:
            return {}
        
        account = self.accounts[account_id]
        
        return {
            'strategy_name': strategy_name,
            'account_id': account_id,
            'total_capital': account.total_capital,
            'available_capital': account.available_capital,
            'frozen_capital': account.frozen_capital,
            'positions_count': len(account.positions),
            'orders_count': len(account.orders),
            'trades_count': len(account.trades),
            'is_running': strategy.is_running
        }
    
    def get_engine_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'name': self.name,
            'is_running': self.is_running,
            'start_time': self.start_time,
            'stop_time': self.stop_time,
            'strategies_count': len(self.strategies),
            'accounts_count': len(self.accounts),
            'data_feeds_count': len(self.data_feeds),
            'brokers_count': len(self.brokers),
            'running_strategies': [name for name, strategy in self.strategies.items() if strategy.is_running]
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        if self.executor:
            self.executor.shutdown(wait=True)