import time
import random
import traceback
from datetime import datetime, timedelta
import sys
import os
from logging import exception

from trader.ht_client_trader import HTClientTrader,read_config

# 添加utils目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from utils.singleton_order_database import OrderDatabase
from datafrom.tdx_market_data_service import MarketDataService

class GridTrading:
    def __init__(self, trader, quoteService, symbol, initial_price, quantity=1.0, profit_target=0.0012, buy_timeout=30, sell_timeout=60,
                 db_host='192.168.0.116', db_name='m_htresearch', db_user='whl', db_password='Whl308221710_'):
        """
        初始化网格交易策略
        :param symbol: 股票代码
        :param initial_price: 初始价格
        :param quantity: 下单数量，默认为1.0
        :param profit_target: 目标利润率，默认为0.3%
        :param buy_timeout: 买单超时时间(秒)，默认为30秒
        :param sell_timeout: 卖单超时时间(秒)，默认为60秒
        :param db_host: 数据库主机
        :param db_name: 数据库名称
        :param db_user: 数据库用户名
        :param db_password: 数据库密码
        """
        self.symbol = symbol
        self.current_price = initial_price
        self.quantity = quantity
        self.profit_target = profit_target
        self.buy_timeout = buy_timeout
        self.sell_timeout = sell_timeout
        self.holding_position = False  # 是否持有仓位
        self.last_order_time = None
        self.last_order_type = None  # 'buy' 或 'sell'
        self.order_price = 0
        self.current_order_id = None  # 当前订单ID
        self.last_buy_order_id = None  # 最后一个买单ID，用于关联卖单
        self.trader = trader
        self.quoteService = quoteService

        self.has_orders = None


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
        
        # 从数据库加载没有完成的订单
        self.load_pending_orders()
    
    def load_pending_orders(self):
        """从数据库加载未完成的订单"""
        try:
            pending_orders = self.db.get_pending_orders()
            
            if not pending_orders:
                print("没有找到未完成的订单")
                self.has_orders = []
                return []
            
            print(f"加载到 {len(pending_orders)} 个未完成的订单:")
            
            # 按时间排序，处理最新的订单
            latest_order = None
            for order in pending_orders:
                print(f"  订单ID: {order['id']}, 类型: {order['order_type']}, 价格: {order['price']:.4f}, 状态: {order['status']}, 确认: {order['confirm']}")
                
                # 找到最新的pending订单作为当前活跃订单
                if order['status'] == 'pending':
                    if latest_order is None or order['placed_time'] > latest_order['placed_time']:
                        latest_order = order
            
            # 恢复最新的pending订单状态
            if latest_order:
                self.current_order_id = latest_order['id']
                self.last_order_type = latest_order['order_type']
                self.order_price = float(latest_order['price'])
                self.last_order_time = latest_order['placed_time']
                
                print(f"恢复活跃订单: ID={self.current_order_id}, 类型={self.last_order_type}, 价格={self.order_price:.4f}")
                
                # 如果是卖单，说明有持仓
                if self.last_order_type == 'sell':
                    self.holding_position = True
                    # 找到关联的买单ID
                    if latest_order['related_order_id']:
                        self.last_buy_order_id = latest_order['related_order_id']
                else:
                    self.holding_position = False
            
            # 处理已成交但未确认的订单
            filled_unconfirmed = [order for order in pending_orders if order['status'] == 'filled' and order['confirm'] == 0]
            if filled_unconfirmed:
                print(f"\n发现 {len(filled_unconfirmed)} 个已成交但未确认的订单:")
                for order in filled_unconfirmed:
                    print(f"  订单ID: {order['id']}, 类型: {order['order_type']}, 价格: {order['price']:.4f}")
                    # 可以选择自动确认或提示用户
                    # self.db.update_order_confirm(order['id'], 1)
            self.has_orders = pending_orders

            print( self.has_orders )

        except Exception as e:
            print(f"加载未完成订单时发生错误: {e}")
    
    def confirm_order(self, order_id):
        """确认订单"""
        return self.db.update_order_confirm(order_id, 1)
    
    def __del__(self):
        """析构函数，确保数据库连接正确关闭"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    def get_current_price(self):
        """模拟获取当前价格，实际应用中应从交易所API获取"""
        # 模拟价格小幅波动，上下浮动不超过0.5%
        fluctuation = random.uniform(-0.005, 0.005)
        self.current_price *= (1 + fluctuation)

        quote = self.quoteService.get_stock_quote(self.symbol)
        if self.symbol.startswith(('5')):
            return round(quote['quote']['price']/10,3)

        return quote['quote']['price']

    def place_buy_order(self, offset_ratio = 1.0):
        """下买单"""
        price = self.get_current_price()
        price = round( price*float(offset_ratio), 3)
        self.last_order_time = datetime.now()
        self.last_order_type = 'buy'
        self.order_price = price
        
        # 将买单保存到数据库
        self.current_order_id = self.db.insert_order(
            symbol=self.symbol,
            order_type='buy',
            price=price,
            quantity=self.quantity,
            status='pending',
            placed_time=self.last_order_time
        )



        entrustment_id = -1
        try:
            entrustment_message = self.trader.buy(self.symbol,price,self.quantity)
            if 'entrust_id' in entrustment_message.keys():
                entrustment_id = entrustment_message['entrust_id']
            print(f"entrustment_message={entrustment_message}")
        except Exception as e:
            print(e)
            traceback.print_exc()

        self.db.update_order_entrust_id( self.current_order_id, entrustment_id)

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
            symbol=self.symbol,
            order_type='sell',
            price=target_price,
            quantity=self.quantity,
            status='pending',
            placed_time=self.last_order_time,
            related_order_id=self.last_buy_order_id
        )


        entrustment_id = -3
        try:
            entrustment_message = self.trader.sell(self.symbol,target_price,self.quantity)
            if 'entrust_id' in entrustment_message.keys():
                entrustment_id = entrustment_message['entrust_id']
            print(f"entrustment_message={entrustment_message}")
        except Exception as e:
            print(e)
            traceback.print_exc()

        self.db.update_order_entrust_id( self.current_order_id, entrustment_id)


        if self.current_order_id:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，订单ID: {self.current_order_id}")
        else:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，数据库保存失败")
        
        return target_price

    def place_sell_order_related(self, symbol,buy_price,last_buy_order_id):
        """下卖单，基于买入价格设置目标利润"""
        target_price = round(buy_price * (1 + self.profit_target),3)
        self.last_order_time = datetime.now()
        self.last_order_type = 'sell'
        self.order_price = target_price

        # 将卖单保存到数据库，关联到最后一个买单
        self.current_order_id = self.db.insert_order(
            symbol=symbol,
            order_type='sell',
            price=target_price,
            quantity=self.quantity,
            status='pending',
            placed_time=self.last_order_time,
            related_order_id=last_buy_order_id
        )



        entrustment_id = -1
        try:
            entrustment_message = self.trader.sell(self.symbol,target_price,self.quantity)
            if 'entrust_id' in entrustment_message.keys():
                entrustment_id = entrustment_message['entrust_id']
            print(f"entrustment_message={entrustment_message}")
        except Exception as e:
            print(e)
            traceback.print_exc()

        self.db.update_order_entrust_id( self.current_order_id, entrustment_id)


        if self.current_order_id:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，订单ID: {self.current_order_id}")
        else:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 下卖单，目标价格: {target_price:.4f} (目标收益: {self.profit_target * 100:.2f}%)，数据库保存失败")

        return target_price

    def get_today_entrusts(self):
        print("start query ht entrusts !")
        #查询当日委托
        today_entrusts = self.trader.today_entrusts
        print("当日委托:", today_entrusts)
        return  today_entrusts


    def check_order_status_by_entrusts(self, order, entrusts):
        """检查订单状态，模拟订单是否成交"""
        current_price = self.get_current_price()
        current_time = datetime.now()
        timeout = self.buy_timeout

        if order['status'] != 'pending':
            return order['status']

        for record in entrusts:
            print(record)
            if '委托编号' in record.keys():
                entrusts_id = record['委托编号']
                filled_num = record['成交数量']
                if entrusts_id ==  (order['entrustment_id']):
                    if filled_num>0:
                        self.db.update_order_status(
                            order_id=order['current_order_id'],
                            status='filled',
                            filled_time=current_time
                        )
                        self.last_buy_order_id = order['current_order_id']  # 记录买单ID用于关联卖单
                        self.holding_position = True

                        #卖成交
                        if order['last_order_type'] == 'sell':
                            self.db.update_order_confirm(
                                order_id=order['current_order_id']
                            )

                        return 'filled'

                    # 检查是否超时
                    elif (current_time - order['last_order_time']) > timedelta(seconds=timeout):

                        if '备注' in record.keys():
                            if '已撤' in record['备注']:
                                self.db.update_order_status(
                                            order_id=order['current_order_id'],
                                            status='cancel'
                                        )
                                return 'cancel'
                            else:
                                if current_price > float(order['price'])*float(1.006):
                                    self.trader.cancel_entrust( str(entrusts_id))
                                else:
                                    print(f" quote current_price={current_price} order price = {order['price']}")


        return 'pending'

    def get_sell_order_by_id(self, order_id):
        '''
        根据订单查找关联的订单
        '''
        for ord in self.has_orders:
            print(f"get_sell_order_by_id order_id={order_id}")
            if ord['related_order_id'] == order_id :
                print(ord)
                return ord

        return None



    def is_trading_time(self):
        """检查当前时间是否在交易时间范围内"""
        now = datetime.now()
        current_time = now.time()
        
        # 上午交易时间: 9:29 - 11:30
        morning_start = datetime.strptime('09:29', '%H:%M').time()
        morning_end = datetime.strptime('11:30', '%H:%M').time()
        
        # 下午交易时间: 12:59 - 15:00
        afternoon_start = datetime.strptime('12:59', '%H:%M').time()
        afternoon_end = datetime.strptime('15:00', '%H:%M').time()
        
        # 检查是否在交易时间范围内
        is_morning_trading = morning_start <= current_time <= morning_end
        is_afternoon_trading = afternoon_start <= current_time <= afternoon_end
        
        return is_morning_trading or is_afternoon_trading
    
    def is_after_market_close(self):
        """检查当前时间是否在收盘后"""
        now = datetime.now()
        current_time = now.time()
        
        # 股市收盘时间: 15:00
        market_close_time = datetime.strptime('15:10', '%H:%M').time()
        
        # 检查是否在收盘后（15:00之后）
        return current_time > market_close_time
    
    def run(self, duration=None):
        """运行网格交易策略"""
        print("开始网格交易策略...")
        print(f"初始价格: {self.current_price:.4f}，目标收益: {self.profit_target * 100:.2f}%")
        print(f"买单超时: {self.buy_timeout}秒，卖单超时: {self.sell_timeout}秒")
        print("交易时间: 9:29-11:30, 12:59-15:00")
        print("----------------------------------------")

        start_time = datetime.now()

        try:
            while True:


                if self.is_after_market_close():
                    current_time = datetime.now().strftime('%H:%M:%S')
                    today_entrusts = self.get_today_entrusts()
                    for ord in self.has_orders:
                        print( ord )
                        #收盘后，把所有的空订单记录状态设为取消
                        if ( ord['status'] == 'pending' ) or  ord['order_type'] == 'sell':
                            #把orders 表的 sell记录 状态更新为 cancel
                            self.db.update_order_status(
                                order_id=ord['id'],
                                status='cancel'
                            )
                    time.sleep(60)  # 等待1分钟后再检查
                    continue

                # 检查是否在交易时间范围内
                if not self.is_trading_time():
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"\n[{current_time}] 当前不在交易时间范围内，等待中...")
                    time.sleep(60)  # 等待1分钟后再检查
                    continue

                # 检查是否达到运行时长
                if duration and (datetime.now() - start_time) > timedelta(seconds=duration):
                    print("\n交易时长已到，结束交易")
                    break

                #1. 没有需要平仓的订单，或者 卖单60秒没有成交， 下新订单

                #找出最后的订单时间
                last_sell_ord = None
                last_buy_ord = None
                last_buy_ord_padding = None

                if self.has_orders:
                    today_entrusts = self.get_today_entrusts()
                    for ord in self.has_orders:
                        print( ord )

                        try:
                            #根据订单记录，查询订单状态
                            ord_status = self.check_order_status_by_entrusts(
                                {'price':ord['price'],'entrustment_id': ord['entrustment_id'], 'last_order_type': ord['order_type'], 'current_order_id': ord['id'],
                                 'last_order_time': ord['placed_time'],'status':ord['status']}, today_entrusts)

                            print(f"ord_status={ord_status}")
                            if ord['status'] == 'filled' and ord['order_type'] == 'buy':
                                # 判断是否有卖单
                                if self.get_sell_order_by_id(ord['id']) is None:
                                    # 买单成交，下卖单
                                    self.place_sell_order_related(self.symbol,float(ord['price']), ord['id'])

                            if ord['status'] == 'filled':
                                if last_sell_ord is not None:
                                    if last_sell_ord['filled_time']<ord['filled_time']:
                                        last_sell_ord = ord
                                else:
                                    last_sell_ord = ord

                                if ord['order_type'] == 'buy':
                                    if last_buy_ord is not None:
                                        if last_buy_ord['filled_time'] < ord['filled_time']:
                                            last_buy_ord = ord
                                    else:
                                        last_buy_ord = ord
                            else:
                                if ord['order_type'] == 'buy':
                                    last_buy_ord_padding = ord


                        except Exception as e:
                            print(f" exception e={e}")
                            traceback.print_exc()

                if last_sell_ord is not None and (datetime.now() -last_sell_ord['filled_time'] ).total_seconds()>60:
                    print( f"last_sell_ord = {last_sell_ord}")



                try:
                    #print("total_seconds={}".format((datetime.now() -last_sell_ord['filled_time'] ).total_seconds()))

                    #如果没有买单信息，需要下一个买单
                    if self.has_orders is not None and len(self.has_orders) == 0:
                        self.place_buy_order(0.9995)

                    elif last_buy_ord is not None:
                        current_price = self.get_current_price()
                        buy_price  = float(last_buy_ord['price'])*0.998
                        buy_time = last_buy_ord['filled_time']
                        print(f"current_price={current_price} 可以下单的价格：price = {buy_price} buy_time={buy_time} last_buy_ord_padding={last_buy_ord_padding}")

                        if last_buy_ord_padding is None:
                            if current_price < buy_price:
                                self.place_buy_order()

                except Exception as e :
                    print(f" exception {e}")
                    traceback.print_exc()

                #重新加载订单数据
                self.load_pending_orders()

                # 每秒检查一次
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n用户中断，结束交易")
        except Exception as e:
            print(f"e={e}" )
            traceback.print_exc()

def start_trading():
    # 初始化交易器
    trader = HTClientTrader()

    try:
        config_data = read_config("./config.ini")

        # 登录客户端
        login_success = trader.login(
            user=config_data['user'],
            password=config_data['password'],
            exe_path=config_data['exe_path'],  # 华泰证券客户端路径
            comm_password=""
        )

        if not login_success:
            print("登录失败")
            sys.exit(1)

        symbol = '513630'
        ##symbol = '600000'
        # 创建市场数据服务
        service = MarketDataService()
        # 分析交易活跃度
        service.analyze_trading_activity(symbol, count=30)

        # 初始化策略，初始价格设为100，运行300秒（5分钟）
        grid_trader = GridTrading(trader, service, symbol, initial_price=100.0, quantity=1000)
        grid_trader.run(duration=30000000)

    except Exception as e:
        print(f"操作出错: {str(e)}")
        traceback.print_exc()
    finally:
        # 退出客户端
        # trader.exit()  # 实际使用时取消注释
        pass


if __name__ == "__main__":
    start_trading()
