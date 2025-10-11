#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TdxMarketTool工具类测试示例
演示如何使用封装的TDX行情工具获取分笔交易记录和实时行情信息
"""

from utils.tdx_market_tool import TdxMarketTool
import json
import time


def test_transaction_data():
    """
    测试获取分笔交易记录
    """
    print("=" * 60)
    print("测试分笔交易记录功能")
    print("=" * 60)
    
    # 使用上下文管理器自动连接和断开
    with TdxMarketTool() as tool:
        if not tool.is_connected:
            print("连接TDX服务器失败")
            return
        
        # 测试获取分笔交易数据
        symbols = ['000001', '600000', '513630']  # 平安银行、浦发银行、纳指ETF
        
        for symbol in symbols:
            print(f"\n获取股票 {symbol} 的分笔交易记录:")
            print("-" * 50)
            
            transaction_data = tool.get_transaction_data(symbol, start=0, count=10)
            
            if transaction_data:
                print(f"{'时间':<8} {'价格':<8} {'成交量':<8} {'笔数':<6} {'方向':<8}")
                print("-" * 50)
                
                for trade in transaction_data:
                    direction_desc = {
                        'buy': '买盘',
                        'sell': '卖盘', 
                        'neutral': '中性盘',
                        'unknown': '未知'
                    }.get(trade['direction'], '未知')
                    
                    print(f"{trade['time']:<8} {trade['price']:<8.2f} {trade['volume']:<8} {trade['num_trades']:<6} {direction_desc:<8}")
            else:
                print(f"未获取到股票 {symbol} 的分笔交易数据")
            
            time.sleep(0.5)  # 避免请求过于频繁


def test_realtime_quotes():
    """
    测试获取实时行情信息
    """
    print("\n" + "=" * 60)
    print("测试实时行情信息功能")
    print("=" * 60)
    
    with TdxMarketTool() as tool:
        if not tool.is_connected:
            print("连接TDX服务器失败")
            return
        
        # 测试单个股票行情
        print("\n单个股票实时行情:")
        print("-" * 50)
        
        symbol = '000001'
        quote = tool.get_realtime_quote_by_symbol(symbol)
        
        if quote:
            print(f"股票代码: {quote['code']}")
            print(f"股票名称: {quote['name']}")
            print(f"当前价格: {quote['price']:.2f}")
            print(f"昨日收盘: {quote['last_close']:.2f}")
            print(f"今日开盘: {quote['open']:.2f}")
            print(f"最高价格: {quote['high']:.2f}")
            print(f"最低价格: {quote['low']:.2f}")
            print(f"成交量: {quote['volume']:,}")
            print(f"涨跌额: {quote['change']:.2f}")
            print(f"涨跌幅: {quote['change_rate']:.2f}%")
            print(f"买一价: {quote['bid1']:.2f} ({quote['bid1_vol']}手)")
            print(f"卖一价: {quote['ask1']:.2f} ({quote['ask1_vol']}手)")
        else:
            print(f"未获取到股票 {symbol} 的实时行情")
        
        # 测试批量获取行情
        print("\n批量获取实时行情:")
        print("-" * 80)
        
        symbols = ['000001', '600000', '000002', '600036']
        quotes_dict = tool.batch_get_quotes(symbols)
        
        if quotes_dict:
            print(f"{'代码':<8} {'名称':<12} {'现价':<8} {'涨跌幅':<8} {'成交量':<12}")
            print("-" * 80)
            
            for symbol in symbols:
                if symbol in quotes_dict:
                    quote = quotes_dict[symbol]
                    print(f"{quote['code']:<8} {quote['name']:<12} {quote['price']:<8.2f} {quote['change_rate']:<8.2f}% {quote['volume']:<12,}")
                else:
                    print(f"{symbol:<8} {'未获取到数据':<12}")
        else:
            print("未获取到批量行情数据")


def test_minute_data():
    """
    测试获取分时行情数据
    """
    print("\n" + "=" * 60)
    print("测试分时行情数据功能")
    print("=" * 60)
    
    with TdxMarketTool() as tool:
        if not tool.is_connected:
            print("连接TDX服务器失败")
            return
        
        symbol = '000001'
        print(f"\n获取股票 {symbol} 的分时行情数据:")
        print("-" * 50)
        
        minute_data = tool.get_minute_data(symbol)
        
        if minute_data:
            print(f"{'时间':<8} {'价格':<8} {'成交量':<10} {'成交额':<12}")
            print("-" * 50)
            
            # 只显示前10条数据
            for i, data in enumerate(minute_data[:10]):
                print(f"{data['time']:<8} {data['price']:<8.2f} {data['volume']:<10} {data['amount']:<12.0f}")
            
            if len(minute_data) > 10:
                print(f"... (共 {len(minute_data)} 条数据)")
        else:
            print(f"未获取到股票 {symbol} 的分时数据")


def test_market_status():
    """
    测试获取市场状态
    """
    print("\n" + "=" * 60)
    print("测试市场状态功能")
    print("=" * 60)
    
    tool = TdxMarketTool()
    
    # 测试未连接状态
    status = tool.get_market_status()
    print("\n未连接状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 测试连接状态
    tool.connect()
    status = tool.get_market_status()
    print("\n已连接状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    tool.disconnect()


def main():
    """
    主测试函数
    """
    print("TdxMarketTool 工具类测试")
    print("=" * 60)
    
    try:
        # 测试市场状态
        test_market_status()
        
        # 测试分笔交易记录
        test_transaction_data()
        
        # 测试实时行情
        test_realtime_quotes()
        
        # 测试分时数据
        test_minute_data()
        
        print("\n" + "=" * 60)
        print("所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()