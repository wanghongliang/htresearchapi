from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import threading
import logging
import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from base import (
    Broker, Account, Position, OrderData, TradeData, Strategy,
    OrderType, OrderSide, OrderStatus
)


class AccountManager:
    """账户管理器"""
    
    def __init__(self, name: str = "AccountManager"):
        self.name = name
        self.logger = logging.getLogger(f"AccountManager.{name}")
        
        # 账户管理
        self.accounts: Dict[str, Account] = {}
        self.account_strategies: Dict[str, List[str]] = defaultdict(list)  # account_id -> [strategy_names]
        
        # 风控参数
        self.max_position_ratio = 0.3  # 单个持仓最大占比
        self.max_daily_loss_ratio = 0.05  # 单日最大亏损比例
        self.max_orders_per_minute = 10  # 每分钟最大订单数
        
        # 订单限制
        self.order_count_tracker: Dict[str, List[datetime]] = defaultdict(list)
        
        self.lock = threading.RLock()
    
    def create_account(self, account_id: str, initial_capital: float, 
                      account_type: str = "stock") -> Optional[Account]:
        """创建账户"""
        try:
            with self.lock:
                if account_id in self.accounts:
                    self.logger.warning(f"Account {account_id} already exists")
                    return None
                
                account = Account(account_id, initial_capital)
                account.account_type = account_type
                
                self.accounts[account_id] = account
                self.logger.info(f"Created account {account_id} with capital {initial_capital}")
                
                return account
                
        except Exception as e:
            self.logger.error(f"Failed to create account {account_id}: {e}")
            return None
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        return self.accounts.get(account_id)
    
    def update_position(self, account_id: str, symbol: str, trade: TradeData) -> bool:
        """更新持仓"""
        try:
            with self.lock:
                account = self.get_account(account_id)
                if not account:
                    self.logger.error(f"Account {account_id} not found")
                    return False
                
                if symbol not in account.positions:
                    account.positions[symbol] = Position(symbol)
                
                position = account.positions[symbol]
                
                if trade.side == OrderSide.BUY:
                    # 买入：增加持仓
                    total_cost = position.quantity * position.avg_price + trade.quantity * trade.price
                    total_quantity = position.quantity + trade.quantity
                    
                    if total_quantity > 0:
                        position.avg_price = total_cost / total_quantity
                    position.quantity = total_quantity
                    
                    # 减少可用资金
                    account.available_capital -= trade.quantity * trade.price
                    
                else:  # SELL
                    # 卖出：减少持仓
                    if position.quantity >= trade.quantity:
                        # 计算已实现盈亏
                        realized_pnl = (trade.price - position.avg_price) * trade.quantity
                        position.realized_pnl += realized_pnl
                        account.total_capital += realized_pnl
                        
                        position.quantity -= trade.quantity
                        
                        # 增加可用资金
                        account.available_capital += trade.quantity * trade.price
                        
                        # 如果持仓为0，清除持仓记录
                        if position.quantity == 0:
                            position.avg_price = 0
                    else:
                        self.logger.error(f"Insufficient position for {symbol}: {position.quantity} < {trade.quantity}")
                        return False
                
                # 记录交易
                account.trades.append(trade)
                
                self.logger.info(f"Updated position for {symbol} in account {account_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update position: {e}")
            return False
    
    def check_buying_power(self, account_id: str, symbol: str, quantity: float, price: float) -> bool:
        """检查购买力"""
        try:
            account = self.get_account(account_id)
            if not account:
                return False
            
            required_capital = quantity * price
            
            # 检查可用资金
            if account.available_capital < required_capital:
                self.logger.warning(f"Insufficient capital: {account.available_capital} < {required_capital}")
                return False
            
            # 检查持仓比例限制
            position_value = required_capital
            if account.total_capital > 0:
                position_ratio = position_value / account.total_capital
                if position_ratio > self.max_position_ratio:
                    self.logger.warning(f"Position ratio too high: {position_ratio} > {self.max_position_ratio}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check buying power: {e}")
            return False
    
    def check_selling_position(self, account_id: str, symbol: str, quantity: float) -> bool:
        """检查卖出持仓"""
        try:
            account = self.get_account(account_id)
            if not account:
                return False
            
            if symbol not in account.positions:
                self.logger.warning(f"No position for {symbol}")
                return False
            
            position = account.positions[symbol]
            if position.quantity < quantity:
                self.logger.warning(f"Insufficient position: {position.quantity} < {quantity}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check selling position: {e}")
            return False
    
    def freeze_capital(self, account_id: str, amount: float) -> bool:
        """冻结资金"""
        try:
            with self.lock:
                account = self.get_account(account_id)
                if not account:
                    return False
                
                if account.available_capital < amount:
                    return False
                
                account.available_capital -= amount
                account.frozen_capital += amount
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to freeze capital: {e}")
            return False
    
    def unfreeze_capital(self, account_id: str, amount: float) -> bool:
        """解冻资金"""
        try:
            with self.lock:
                account = self.get_account(account_id)
                if not account:
                    return False
                
                if account.frozen_capital < amount:
                    return False
                
                account.frozen_capital -= amount
                account.available_capital += amount
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to unfreeze capital: {e}")
            return False
    
    def calculate_portfolio_value(self, account_id: str, current_prices: Dict[str, float]) -> float:
        """计算投资组合价值"""
        try:
            account = self.get_account(account_id)
            if not account:
                return 0.0
            
            total_value = account.available_capital + account.frozen_capital
            
            for symbol, position in account.positions.items():
                if position.quantity > 0 and symbol in current_prices:
                    position_value = position.quantity * current_prices[symbol]
                    total_value += position_value
                    
                    # 更新未实现盈亏
                    position.market_value = position_value
                    position.unrealized_pnl = position_value - (position.quantity * position.avg_price)
            
            account.total_capital = total_value
            return total_value
            
        except Exception as e:
            self.logger.error(f"Failed to calculate portfolio value: {e}")
            return 0.0
    
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """获取账户摘要"""
        account = self.get_account(account_id)
        if not account:
            return {}
        
        return {
            'account_id': account.account_id,
            'total_capital': account.total_capital,
            'available_capital': account.available_capital,
            'frozen_capital': account.frozen_capital,
            'positions_count': len(account.positions),
            'active_orders': len([o for o in account.orders.values() if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]]),
            'total_trades': len(account.trades),
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'realized_pnl': pos.realized_pnl
                }
                for symbol, pos in account.positions.items() if pos.quantity > 0
            }
        }


class SimulatedBroker(Broker):
    """模拟经纪商 - 用于回测和模拟交易"""
    
    def __init__(self, name: str = "SimulatedBroker"):
        super().__init__(name)
        self.logger = logging.getLogger(f"SimulatedBroker.{name}")
        
        # 账户管理器
        self.account_manager = AccountManager(f"{name}_AccountManager")
        
        # 订单管理
        self.pending_orders: Dict[str, OrderData] = {}
        self.order_history: List[OrderData] = []
        
        # 市场数据
        self.current_prices: Dict[str, float] = {}
        
        # 交易费用
        self.commission_rate = 0.0003  # 万分之三
        self.min_commission = 5.0  # 最小手续费
        
        # 滑点设置
        self.slippage_rate = 0.001  # 千分之一
        
        self.is_connected = False
        self.lock = threading.RLock()
    
    def connect(self) -> bool:
        """连接经纪商"""
        self.is_connected = True
        self.logger.info(f"Connected to simulated broker {self.name}")
        return True
    
    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        self.logger.info(f"Disconnected from simulated broker {self.name}")
    
    def add_account(self, account: Account):
        """添加账户"""
        super().add_account(account)
        self.account_manager.accounts[account.account_id] = account
    
    def create_account(self, account_id: str, initial_capital: float) -> Optional[Account]:
        """创建账户"""
        account = self.account_manager.create_account(account_id, initial_capital)
        if account:
            self.add_account(account)
        return account
    
    def submit_order(self, order: OrderData) -> str:
        """提交订单"""
        try:
            with self.lock:
                if not self.is_connected:
                    order.status = OrderStatus.REJECTED
                    self.logger.error("Broker not connected")
                    return order.order_id
                
                # 获取策略账户
                strategy_account = None
                for strategy in self.strategies:
                    if strategy.account:
                        strategy_account = strategy.account
                        break
                
                if not strategy_account:
                    order.status = OrderStatus.REJECTED
                    self.logger.error("No account found for order")
                    return order.order_id
                
                # 风控检查
                if order.side == OrderSide.BUY:
                    if not self.account_manager.check_buying_power(
                        strategy_account.account_id, order.symbol, 
                        order.quantity, order.price or self.current_prices.get(order.symbol, 0)
                    ):
                        order.status = OrderStatus.REJECTED
                        self.logger.warning(f"Order rejected: insufficient buying power")
                        return order.order_id
                else:
                    if not self.account_manager.check_selling_position(
                        strategy_account.account_id, order.symbol, order.quantity
                    ):
                        order.status = OrderStatus.REJECTED
                        self.logger.warning(f"Order rejected: insufficient position")
                        return order.order_id
                
                # 冻结资金（买单）
                if order.side == OrderSide.BUY:
                    required_capital = order.quantity * (order.price or self.current_prices.get(order.symbol, 0))
                    if not self.account_manager.freeze_capital(strategy_account.account_id, required_capital):
                        order.status = OrderStatus.REJECTED
                        return order.order_id
                
                # 添加到待处理订单
                order.status = OrderStatus.SUBMITTED
                self.pending_orders[order.order_id] = order
                strategy_account.orders[order.order_id] = order
                
                # 通知策略
                self.notify_order_update(order)
                
                # 模拟立即成交（市价单）
                if order.order_type == OrderType.MARKET:
                    self._execute_market_order(order)
                
                self.logger.info(f"Submitted order {order.order_id}: {order.side.value} {order.quantity} {order.symbol}")
                return order.order_id
                
        except Exception as e:
            self.logger.error(f"Failed to submit order: {e}")
            order.status = OrderStatus.REJECTED
            return order.order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            with self.lock:
                if order_id not in self.pending_orders:
                    self.logger.warning(f"Order {order_id} not found")
                    return False
                
                order = self.pending_orders[order_id]
                
                if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                    self.logger.warning(f"Cannot cancel order {order_id} with status {order.status}")
                    return False
                
                # 解冻资金（买单）
                if order.side == OrderSide.BUY:
                    strategy_account = None
                    for strategy in self.strategies:
                        if strategy.account:
                            strategy_account = strategy.account
                            break
                    
                    if strategy_account:
                        required_capital = order.quantity * (order.price or self.current_prices.get(order.symbol, 0))
                        self.account_manager.unfreeze_capital(strategy_account.account_id, required_capital)
                
                # 更新订单状态
                order.status = OrderStatus.CANCELLED
                order.update_time = datetime.now()
                
                # 移除待处理订单
                del self.pending_orders[order_id]
                self.order_history.append(order)
                
                # 通知策略
                self.notify_order_update(order)
                
                self.logger.info(f"Cancelled order {order_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def _execute_market_order(self, order: OrderData):
        """执行市价单"""
        try:
            if order.symbol not in self.current_prices:
                self.logger.error(f"No price data for {order.symbol}")
                return
            
            # 计算成交价格（考虑滑点）
            market_price = self.current_prices[order.symbol]
            if order.side == OrderSide.BUY:
                execution_price = market_price * (1 + self.slippage_rate)
            else:
                execution_price = market_price * (1 - self.slippage_rate)
            
            # 创建成交记录
            trade = TradeData(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price
            )
            
            # 计算手续费
            commission = max(trade.quantity * trade.price * self.commission_rate, self.min_commission)
            
            # 更新订单状态
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.update_time = datetime.now()
            
            # 获取策略账户
            strategy_account = None
            for strategy in self.strategies:
                if strategy.account:
                    strategy_account = strategy.account
                    break
            
            if strategy_account:
                # 解冻资金（买单）
                if order.side == OrderSide.BUY:
                    frozen_amount = order.quantity * (order.price or market_price)
                    self.account_manager.unfreeze_capital(strategy_account.account_id, frozen_amount)
                
                # 更新持仓
                self.account_manager.update_position(strategy_account.account_id, order.symbol, trade)
                
                # 扣除手续费
                strategy_account.available_capital -= commission
                strategy_account.total_capital -= commission
            
            # 移除待处理订单
            if order.order_id in self.pending_orders:
                del self.pending_orders[order.order_id]
            
            self.order_history.append(order)
            
            # 通知策略
            self.notify_order_update(order)
            self.notify_trade(trade)
            
            self.logger.info(f"Executed order {order.order_id}: {trade.quantity} @ {trade.price}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute market order: {e}")
    
    def update_market_data(self, symbol: str, price: float):
        """更新市场数据"""
        self.current_prices[symbol] = price
        
        # 检查限价单是否可以成交
        self._check_limit_orders(symbol, price)
    
    def _check_limit_orders(self, symbol: str, current_price: float):
        """检查限价单是否可以成交"""
        try:
            orders_to_execute = []
            
            for order in list(self.pending_orders.values()):
                if order.symbol != symbol or order.order_type != OrderType.LIMIT:
                    continue
                
                should_execute = False
                
                if order.side == OrderSide.BUY and current_price <= order.price:
                    should_execute = True
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    should_execute = True
                
                if should_execute:
                    orders_to_execute.append(order)
            
            # 执行符合条件的限价单
            for order in orders_to_execute:
                self._execute_limit_order(order, current_price)
                
        except Exception as e:
            self.logger.error(f"Failed to check limit orders: {e}")
    
    def _execute_limit_order(self, order: OrderData, execution_price: float):
        """执行限价单"""
        try:
            # 创建成交记录
            trade = TradeData(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price
            )
            
            # 计算手续费
            commission = max(trade.quantity * trade.price * self.commission_rate, self.min_commission)
            
            # 更新订单状态
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.update_time = datetime.now()
            
            # 获取策略账户
            strategy_account = None
            for strategy in self.strategies:
                if strategy.account:
                    strategy_account = strategy.account
                    break
            
            if strategy_account:
                # 解冻资金（买单）
                if order.side == OrderSide.BUY:
                    frozen_amount = order.quantity * order.price
                    self.account_manager.unfreeze_capital(strategy_account.account_id, frozen_amount)
                
                # 更新持仓
                self.account_manager.update_position(strategy_account.account_id, order.symbol, trade)
                
                # 扣除手续费
                strategy_account.available_capital -= commission
                strategy_account.total_capital -= commission
            
            # 移除待处理订单
            if order.order_id in self.pending_orders:
                del self.pending_orders[order.order_id]
            
            self.order_history.append(order)
            
            # 通知策略
            self.notify_order_update(order)
            self.notify_trade(trade)
            
            self.logger.info(f"Executed limit order {order.order_id}: {trade.quantity} @ {trade.price}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute limit order: {e}")
    
    def get_account_info(self, account_id: str) -> Optional[Account]:
        """获取账户信息"""
        return self.account_manager.get_account(account_id)
    
    def get_positions(self, account_id: str) -> Dict[str, Position]:
        """获取持仓信息"""
        account = self.account_manager.get_account(account_id)
        if account:
            return account.positions
        return {}
    
    def get_broker_status(self) -> Dict[str, Any]:
        """获取经纪商状态"""
        return {
            'name': self.name,
            'is_connected': self.is_connected,
            'accounts_count': len(self.accounts),
            'pending_orders': len(self.pending_orders),
            'total_orders': len(self.order_history) + len(self.pending_orders),
            'strategies_count': len(self.strategies),
            'commission_rate': self.commission_rate,
            'slippage_rate': self.slippage_rate
        }