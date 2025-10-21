import mysql.connector
from mysql.connector import Error
from datetime import datetime
import weakref


class OrderDatabase:
    # 单例实例变量
    _instance = None

    def __new__(cls, *args, **kwargs):
        """确保只创建一个实例"""
        if not cls._instance:
            cls._instance = super(OrderDatabase, cls).__new__(cls)
        return cls._instance

    def __init__(self, host, database, user, password, port=3306):
        """初始化数据库连接参数，只在第一次实例化时初始化"""
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            # 检查参数是否与第一次初始化相同
            if (self.host != host or self.database != database or
                    self.user != user or self.password != password or self.port != port):
                raise ValueError("单例模式下，数据库连接参数必须保持一致")
            return

        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None
        self.cursor = None
        self._initialized = True
        # 使用弱引用追踪连接状态
        self._connection_ref = None

    def __del__(self):
        """对象销毁时安全关闭数据库连接"""
        # 确保在对象被销毁时正确关闭资源
        try:
            self.close()
        except Exception as e:
            print(f"关闭数据库连接时发生异常: {e}")

    def connect(self):
        """建立数据库连接"""
        try:
            # 如果已有连接且连接有效，则不需要重新连接
            if self.connection and self.connection.is_connected():
                return True

            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )

            # 创建弱引用以便追踪
            self._connection_ref = weakref.ref(self.connection)

            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                print(f"成功连接到MySQL服务器版本: {db_info}")

                # 重新创建游标
                self._create_cursor()

                # 创建订单表（如果不存在）
                #self._create_order_table()
                return True

        except Error as e:
            print(f"连接数据库时发生错误: {e}")
            self.connection = None
            self.cursor = None
            return False

    def _create_cursor(self):
        """创建游标，确保在有效连接上"""
        if self.connection and self.connection.is_connected():
            self.cursor = self.connection.cursor(dictionary=True)
        else:
            self.cursor = None
            print("无法创建游标，连接无效")

    def _create_order_table(self):
        """创建订单表"""
        if not self.cursor:
            print("游标不存在，无法创建订单表")
            return

        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                order_type ENUM('buy', 'sell') NOT NULL,
                price DECIMAL(10, 4) NOT NULL,
                quantity DECIMAL(10, 4) NOT NULL DEFAULT 1.0,
                status ENUM('pending', 'filled', 'timeout') NOT NULL,
                placed_time DATETIME NOT NULL,
                filled_time DATETIME NULL,
                profit DECIMAL(10, 4) NULL,
                related_order_id INT NULL,
                confirm TINYINT(1) DEFAULT 0,
                FOREIGN KEY (related_order_id) REFERENCES orders(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            # 检查并添加confirm、quantity和symbol字段（如果表已存在但没有该字段）
            alter_table_queries = [
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS confirm TINYINT(1) DEFAULT 0",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS quantity DECIMAL(10, 4) NOT NULL DEFAULT 1.0",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS symbol VARCHAR(20) NOT NULL DEFAULT ''"
            ]

            self.cursor.execute(create_table_query)
            for alter_query in alter_table_queries:
                self.cursor.execute(alter_query)
            self.connection.commit()
            print("订单表检查/创建成功")

        except Error as e:
            print(f"创建订单表时发生错误: {e}")
            if self.connection:
                self.connection.rollback()

    def get_pending_orders(self):
        """获取未完成的订单 (status='pending' 或 status='filled' and confirm=0)"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return []

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return []

        try:
            query = """
            SELECT * FROM orders 
            WHERE ( status = 'pending' AND confirm = 0 )
               OR (status = 'filled' AND confirm = 0)
            ORDER BY placed_time ASC
            """
            
            self.cursor.execute(query)
            orders = self.cursor.fetchall()
            
            print(f"找到 {len(orders)} 个未完成的订单")
            return orders

        except Error as e:
            print(f"查询未完成订单时发生错误: {e}")
            return []
    


    def insert_order(self, symbol, order_type, price, quantity=1.0, status='pending', placed_time=None,
                     filled_time=None, profit=None, related_order_id=None, confirm=0):
        """插入新订单记录"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return None

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return None

        try:
            if placed_time is None:
                placed_time = datetime.now()

            insert_query = """
            INSERT INTO orders 
            (symbol, order_type, price, quantity, status, placed_time, filled_time, profit, related_order_id, confirm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                symbol,
                order_type,
                price,
                quantity,
                status,
                placed_time,
                filled_time,
                profit,
                related_order_id,
                confirm
            )

            self.cursor.execute(insert_query, values)
            self.connection.commit()

            order_id = self.cursor.lastrowid
            print(f"订单已插入，ID: {order_id}")
            return order_id

        except Error as e:
            print(f"插入订单时发生错误: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def update_order_status(self, order_id, status, filled_time=None, profit=None):
        """更新订单状态"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return False

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return False

        try:
            update_fields = ["status = %s"]
            values = [status]

            if status == 'filled' and filled_time is None:
                filled_time = datetime.now()

            if filled_time:
                update_fields.append("filled_time = %s")
                values.append(filled_time)

            if profit is not None:
                update_fields.append("profit = %s")
                values.append(profit)

            values.append(order_id)

            update_query = f"""
            UPDATE orders 
            SET {', '.join(update_fields)}
            WHERE id = %s
            """

            self.cursor.execute(update_query, values)
            self.connection.commit()

            if self.cursor.rowcount > 0:
                print(f"订单ID {order_id} 已更新为状态: {status}")
                return True
            else:
                print(f"未找到订单ID {order_id} 或无需更新")
                return False

        except Error as e:
            print(f"更新订单状态时发生错误: {e}")
            if self.connection:
                self.connection.rollback()
            return False


    def update_order_confirm(self, order_id, filled_time=None, profit=None):
        """更新订单状态"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return False

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return False

        try:

            update_query = f"""
             UPDATE orders 
                SET confirm = 1 
                WHERE id IN (
                    SELECT related_order_id FROM (
                        SELECT related_order_id FROM orders WHERE id = %s
                    ) AS temp
                ) or id = %s;
                            
            """

            self.cursor.execute(update_query, [order_id,order_id])
            self.connection.commit()

            if self.cursor.rowcount > 0:
                print(f"订单ID {order_id} 已更新confirm")
                return True
            else:
                print(f"未找到订单ID {order_id} 或无需更新")
                return False

        except Error as e:
            print(f"更新订单状态时发生错误: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def update_order_entrust_id(self, order_id, entrust_id):
        """更新订单状态"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return False

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return False

        try:

            update_query = f"""
             UPDATE orders 
                SET entrustment_id = %s 
                WHERE  id = %s;

            """

            self.cursor.execute(update_query, [entrust_id, order_id])
            self.connection.commit()

            if self.cursor.rowcount > 0:
                print(f"订单ID {order_id} 已更新 entrustment_id")
                return True
            else:
                print(f"未找到订单ID {order_id} 或无需更新")
                return False

        except Error as e:
            print(f"更新订单状态时发生错误: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def get_order(self, order_id):
        """获取指定ID的订单信息"""
        # 检查连接状态并尝试重连
        if not (self.connection and self.connection.is_connected()):
            print("数据库连接已断开，尝试重新连接...")
            if not self.connect():
                return None

        # 确保游标存在
        if not self.cursor:
            self._create_cursor()
            if not self.cursor:
                return None

        try:
            query = "SELECT * FROM orders WHERE id = %s"
            self.cursor.execute(query, (order_id,))
            return self.cursor.fetchone()

        except Error as e:
            print(f"查询订单时发生错误: {e}")
            return None

    def close(self):
        """安全关闭数据库连接和游标，解决弱引用错误"""
        # 先关闭游标，再关闭连接
        if self.cursor:
            try:
                # 检查连接是否仍然存在
                if self._connection_ref and self._connection_ref():
                    self.cursor.close()
            except ReferenceError:
                print("游标引用的连接已不存在，无需关闭游标")
            finally:
                self.cursor = None

        # 关闭连接
        if self.connection:
            try:
                if self.connection.is_connected():
                    self.connection.close()
            except Error as e:
                print(f"关闭连接时发生错误: {e}")
            finally:
                self.connection = None
                self._connection_ref = None

        print("数据库资源已释放")


# 使用示例
if __name__ == "__main__":
    # 第一次创建实例
    db = OrderDatabase(
        host='localhost',
        database='m_htresearch',
        user='whl',
        password='Whl308221710_'
    )

    # 连接数据库
    if db.connect():
        # 插入一个买单
        buy_order_id = db.insert_order(
            order_type='buy',
            price=100.50
        )

        # 更新买单状态
        if buy_order_id:
            db.update_order_status(
                order_id=buy_order_id,
                status='filled'
            )

            # 插入卖单
            sell_order_id = db.insert_order(
                order_type='sell',
                price=100.80,
                related_order_id=buy_order_id
            )

            # 更新卖单状态
            if sell_order_id:
                db.update_order_status(
                    order_id=sell_order_id,
                    status='filled',
                    profit=0.30
                )

    # 显式关闭（可选，对象销毁时会自动调用）
    db.close()
