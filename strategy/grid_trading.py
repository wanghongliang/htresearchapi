import time
import random
from datetime import datetime, timedelta
import sys
import os

# 添加utils目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from singleton_order_database import OrderDatabase


class GridTrading:
    def __init__(self, initial_price, profit_target=0.003, buy_timeout=30, sell_timeout=60, 
                 db_host='localhost', db_name='m_htresearch', db_user='whl', db_password='Whl308221710_'):
        """
        初始化网格交易策略
        :param initial_price: 初始价格
        :param profit_target: 目标利润率，默认为0.3%
        :param buy_timeout: 买单超时时间(秒)，默认为30秒
        :param sell_timeout: 卖单超时时间(秒)，默认为60秒
        :param db_host: 数据库主机
        :param db_name: 数据库名称
        :param db_user: 数据库用户名
        :param db_password: 数据库密码
        """
        self.current_price = initial_price
        self.profit_target = profit_target
        self.buy_timeout = buy_timeout
        self.sell_timeout = sell_timeout
        self.holding_position = False  # 是否持有仓位
        self.last_order_time = None
        self.last_order_type = None  # 'buy' 或 'sell'
        self.order_price = 0
        self.current_order_id = None  # 当前订单ID
        self.last_buy_order_id = None  # 最后一个买单ID，用于关联卖单
        
        # 初始化数据库连接
        self.db = OrderDatabase(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        # 连接数据库
        if not self.db.connect():
            raise Exception("无法连接到数据库")
    
    def __del__(self):
        """析构函数，确保数据库连接正确关闭"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    def get_current_price(self):
        """模拟获取当前价格，实际应用中应从交易所API获取"""
        # 模拟价格小幅波动，上下浮动不超过0.5%
        fluctuation = random.uniform(-0.005, 0.005)
        self.current_price *= (1 + fluctuation)
        return self.current_price

    def place_buy_order(self):
        """下买单"""
        price = self.get_current_price()
        self.last_order_time = datetime.now()
        self.last_order_type = 'buy'
        self.order_price = price
        
        # 将买单保存到数据库
        self.current_order_id = self.db.insert_order(
            order_type='buy',
            price=price,
            status='pending',
            placed_time=self.last_order_time
        )
        
        if self.current_order_id:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 下买单，价格: {price:.4f}，订单ID: {self.current_order_id}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 下买单，价格: {price:.4f}，数据库保存失败")
        
        return price

    def place_sell_order(self, buy_price):
        """下卖单，基于买入价格设置目标利润"""
        target_price = buy_price * (1 + self.profit_target)
        self.last_order_time = datetime.now()
        self.last_order_type = 'sell'
        self.order_price = target_price
        
        # 将卖单保存到数据库，关联到最后一个买单
        self.current_order_id = self.db.insert_order(
            order_type='sell',
            price=target_price,
            status='pending',
            placed_time=self.last_order_time,
            related_order_id=self.last_buy_order_id
        )
        
        if self.current_order_id:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，订单ID: {self.current_order_id}")
        else:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，数据库保存失败")
        
        return target_price

    def check_order_status(self):
        """检查订单状态，模拟订单是否成交"""
        current_price = self.get_current_price()
        current_time = datetime.now()

        # 检查是否超时
        if self.last_order_type == 'buy':
            timeout = self.buy_timeout
            # 买单成交条件：当前价格小于等于买单价格（可以以更低或等于价格买入）
            if current_price <= self.order_price:
                # 模拟有一定概率成交
                if random.random() < 0.7:  # 70%概率成交
                    # 更新数据库中的订单状态为已成交
                    if self.current_order_id:
                        self.db.update_order_status(
                            order_id=self.current_order_id,
                            status='filled',
                            filled_time=current_time
                        )
                        self.last_buy_order_id = self.current_order_id  # 记录买单ID用于关联卖单
                    
                    print(f"[{current_time.strftime('%H:%M:%S')}] 买单成交，价格: {current_price:.4f}，订单ID: {self.current_order_id}")
                    self.holding_position = True
                    return 'filled'
        elif self.last_order_type == 'sell':
            timeout = self.sell_timeout
            # 卖单成交条件：当前价格大于等于卖单价格（可以以更高或等于价格卖出）
            if current_price >= self.order_price:
                # 模拟有一定概率成交
                if random.random() < 0.7:  # 70%概率成交
                    profit = (current_price - (self.order_price / (1 + self.profit_target))) / (
                                self.order_price / (1 + self.profit_target)) * 100
                    
                    # 更新数据库中的订单状态为已成交，并记录利润
                    if self.current_order_id:
                        self.db.update_order_status(
                            order_id=self.current_order_id,
                            status='filled',
                            filled_time=current_time,
                            profit=profit
                        )
                    
                    print(
                        f"[{current_time.strftime('%H:%M:%S')}] 卖单成交，价格: {current_price:.4f}，收益: {profit:.4f}%，订单ID: {self.current_order_id}")
                    self.holding_position = False
                    return 'filled'

        # 检查是否超时
        if (current_time - self.last_order_time) > timedelta(seconds=timeout):
            # 更新数据库中的订单状态为超时
            if self.current_order_id:
                self.db.update_order_status(
                    order_id=self.current_order_id,
                    status='timeout'
                )
            
            print(
                f"[{current_time.strftime('%H:%M:%S')}] {self.last_order_type}单超时未成交，当前价格: {current_price:.4f}，订单ID: {self.current_order_id}")
            return 'timeout'

        return 'pending'

    def run(self, duration=None):
        """运行网格交易策略"""
        print("开始网格交易策略...")
        print(f"初始价格: {self.current_price:.4f}，目标收益: {self.profit_target * 100:.2f}%")
        print(f"买单超时: {self.buy_timeout}秒，卖单超时: {self.sell_timeout}秒")
        print("----------------------------------------")

        start_time = datetime.now()

        # 初始下一个买单
        self.place_buy_order()

        try:
            while True:
                # 检查是否达到运行时长
                if duration and (datetime.now() - start_time) > timedelta(seconds=duration):
                    print("\n交易时长已到，结束交易")
                    break

                # 检查订单状态
                status = self.check_order_status()

                if status == 'filled':
                    # 订单成交，根据类型下相反订单
                    if self.last_order_type == 'buy':
                        # 买单成交，下卖单
                        self.place_sell_order(self.order_price)
                    else:
                        # 卖单成交，下买单
                        self.place_buy_order()
                elif status == 'timeout':
                    # 订单超时，重新下相同类型的订单
                    if self.last_order_type == 'buy':
                        self.place_buy_order()
                    else:
                        self.place_sell_order(self.order_price / (1 + self.profit_target))  # 根据利润率反推买入价

                # 每秒检查一次
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n用户中断，结束交易")


if __name__ == "__main__":
    # 初始化策略，初始价格设为100，运行300秒（5分钟）
    grid_trader = GridTrading(initial_price=100.0)
    grid_trader.run(duration=30000000)
