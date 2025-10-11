#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格交易策略数据库集成测试脚本
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from strategy.grid_trading import GridTrading
from utils.singleton_order_database import OrderDatabase

def test_database_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    try:
        db = OrderDatabase(
            host='localhost',
            database='m_htresearch',
            user='whl',
            password='Whl308221710_'
        )
        
        if db.connect():
            print("✓ 数据库连接成功")
            db.close()
            return True
        else:
            print("✗ 数据库连接失败")
            return False
    except Exception as e:
        print(f"✗ 数据库连接异常: {e}")
        return False

def test_grid_trading_with_db():
    """测试网格交易策略的数据库集成"""
    print("\n测试网格交易策略数据库集成...")
    try:
        # 创建网格交易实例
        grid_trader = GridTrading(
            trader=None,          # 模拟交易，不需要真实trader
            symbol='000001',      # 股票代码
            initial_price=100.0,
            quantity=10.0,        # 下单数量
            profit_target=0.005,  # 0.5%利润目标
            buy_timeout=5,        # 5秒买单超时
            sell_timeout=10       # 10秒卖单超时
        )
        
        print("✓ GridTrading实例创建成功")
        print("✓ 数据库连接已建立")
        print("✓ 未完成订单加载完成")
        
        # 运行短时间测试（30秒）
        print("\n开始运行网格交易测试（30秒）...")
        grid_trader.run(duration=30)
        
        print("\n✓ 网格交易测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 网格交易测试失败: {e}")
        return False

def test_load_pending_orders():
    """测试加载未完成订单功能"""
    print("\n测试加载未完成订单功能...")
    try:
        db = OrderDatabase(
            host='localhost',
            database='m_htresearch',
            user='whl',
            password='Whl308221710_'
        )
        
        if db.connect():
            # 测试获取未完成订单
            pending_orders = db.get_pending_orders()
            
            print(f"✓ 成功获取未完成订单: {len(pending_orders)} 条")
            
            if pending_orders:
                print("\n未完成订单详情:")
                print("-" * 140)
                print(f"{'ID':<5} {'代码':<8} {'类型':<6} {'价格':<10} {'数量':<10} {'状态':<8} {'确认':<6} {'下单时间':<20} {'成交时间':<20} {'关联订单':<8}")
                print("-" * 140)
                
                for order in pending_orders:
                    placed_time = order['placed_time'].strftime('%Y-%m-%d %H:%M:%S') if order['placed_time'] else 'N/A'
                    filled_time = order['filled_time'].strftime('%Y-%m-%d %H:%M:%S') if order['filled_time'] else 'N/A'
                    confirm = '是' if order['confirm'] == 1 else '否'
                    related_id = str(order['related_order_id']) if order['related_order_id'] else 'N/A'
                    
                    print(f"{order['id']:<5} {order['symbol']:<8} {order['order_type']:<6} {order['price']:<10.4f} {order['quantity']:<10.4f} {order['status']:<8} {confirm:<6} {placed_time:<20} {filled_time:<20} {related_id:<8}")
            
            db.close()
            return True
        else:
            print("✗ 无法连接到数据库")
            return False
            
    except Exception as e:
        print(f"✗ 测试加载未完成订单失败: {e}")
        return False

def query_recent_orders():
    """查询最近的订单记录"""
    print("\n查询最近的订单记录...")
    try:
        db = OrderDatabase(
            host='localhost',
            database='m_htresearch',
            user='whl',
            password='Whl308221710_'
        )
        
        if db.connect():
            # 查询最近10条订单
            query = """
            SELECT id, symbol, order_type, price, quantity, status, placed_time, filled_time, profit, related_order_id, confirm
            FROM orders 
            ORDER BY placed_time DESC 
            LIMIT 10
            """
            
            db.cursor.execute(query)
            orders = db.cursor.fetchall()
            
            if orders:
                print(f"\n找到 {len(orders)} 条最近的订单记录:")
                print("-" * 140)
                print(f"{'ID':<5} {'代码':<8} {'类型':<6} {'价格':<10} {'数量':<10} {'状态':<8} {'确认':<6} {'下单时间':<20} {'成交时间':<20} {'利润':<8} {'关联订单':<8}")
                print("-" * 140)
                
                for order in orders:
                    placed_time = order['placed_time'].strftime('%Y-%m-%d %H:%M:%S') if order['placed_time'] else 'N/A'
                    filled_time = order['filled_time'].strftime('%Y-%m-%d %H:%M:%S') if order['filled_time'] else 'N/A'
                    profit = f"{order['profit']:.4f}" if order['profit'] is not None else 'N/A'
                    confirm = '是' if order['confirm'] == 1 else '否'
                    related_id = str(order['related_order_id']) if order['related_order_id'] else 'N/A'
                    
                    print(f"{order['id']:<5} {order['symbol']:<8} {order['order_type']:<6} {order['price']:<10.4f} {order['quantity']:<10.4f} {order['status']:<8} {confirm:<6} {placed_time:<20} {filled_time:<20} {profit:<8} {related_id:<8}")
            else:
                print("没有找到订单记录")
            
            db.close()
            return True
        else:
            print("✗ 无法连接到数据库")
            return False
            
    except Exception as e:
        print(f"✗ 查询订单记录失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("网格交易策略数据库集成测试")
    print("=" * 60)
    
    # 测试数据库连接
    if not test_database_connection():
        print("\n数据库连接测试失败，请检查数据库配置")
        sys.exit(1)
    
    # 测试加载未完成订单功能
    test_load_pending_orders()
    
    # 测试网格交易策略
    if test_grid_trading_with_db():
        # 查询订单记录
        query_recent_orders()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)