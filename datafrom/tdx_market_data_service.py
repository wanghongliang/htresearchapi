#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

from utils.tdx_market_tool import TdxMarketTool
from datetime import datetime
import time


class MarketDataService:
    """
    市场数据服务类
    基于TdxMarketTool提供高级市场数据功能
    """

    def __init__(self, host: str = '116.205.163.254', port: int = 7709):
        self.tool = TdxMarketTool(host, port)

    def get_stock_quote(self, symbol: str) -> dict:
        """
        获取股票快照数据（实时行情 + 分笔交易）

        Args:
            symbol: 股票代码

        Returns:
            dict: 包含实时行情和最新分笔交易的综合数据
        """
        with self.tool as tool:
            if not tool.is_connected:
                return {'error': '连接TDX服务器失败'}

            # 获取实时行情
            quote = tool.get_realtime_quote_by_symbol(symbol)
            if not quote:
                return {'error': f'获取股票 {symbol} 实时行情失败'}


            return {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'quote': quote
            }
    def get_stock_snapshot(self, symbol: str) -> dict:
        """
        获取股票快照数据（实时行情 + 分笔交易）

        Args:
            symbol: 股票代码

        Returns:
            dict: 包含实时行情和最新分笔交易的综合数据
        """
        with self.tool as tool:
            if not tool.is_connected:
                return {'error': '连接TDX服务器失败'}

            # 获取实时行情
            quote = tool.get_realtime_quote_by_symbol(symbol)
            if not quote:
                return {'error': f'获取股票 {symbol} 实时行情失败'}

            # 获取最新分笔交易
            transactions = tool.get_transaction_data(symbol, start=0, count=5)

            return {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'quote': quote,
                'latest_transactions': transactions
            }

    def monitor_stock_price(self, symbol: str, target_price: float, duration: int = 60):
        """
        监控股票价格变化

        Args:
            symbol: 股票代码
            target_price: 目标价格
            duration: 监控时长（秒）
        """
        print(f"开始监控股票 {symbol}，目标价格: {target_price}")
        print(f"监控时长: {duration} 秒")
        print("-" * 50)

        start_time = time.time()

        with self.tool as tool:
            if not tool.is_connected:
                print("连接TDX服务器失败")
                return

            while time.time() - start_time < duration:
                quote = tool.get_realtime_quote_by_symbol(symbol)

                if quote:
                    current_price = quote['price']
                    change_rate = quote['change_rate']

                    status = "📈" if change_rate > 0 else "📉" if change_rate < 0 else "➡️"

                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] {symbol} 当前价格: {current_price:.2f} ({change_rate:+.2f}%) {status}")

                    # 检查是否达到目标价格
                    if current_price >= target_price:
                        print(f"🎯 价格达到目标! 当前价格: {current_price:.2f} >= 目标价格: {target_price}")
                        break

                time.sleep(5)  # 每5秒检查一次

        print("监控结束")

    def analyze_trading_activity(self, symbol: str, count: int = 50):
        """
        分析股票交易活跃度

        Args:
            symbol: 股票代码
            count: 分析的分笔交易数量
        """
        with self.tool as tool:
            if not tool.is_connected:
                print("连接TDX服务器失败")
                return

            transactions = tool.get_transaction_data(symbol, start=0, count=count)

            if not transactions:
                print(f"未获取到股票 {symbol} 的分笔交易数据")
                return

            # 统计买卖盘情况
            buy_volume = sum(t['volume'] for t in transactions if t['direction'] == 'buy')
            sell_volume = sum(t['volume'] for t in transactions if t['direction'] == 'sell')
            neutral_volume = sum(t['volume'] for t in transactions if t['direction'] == 'neutral')
            total_volume = buy_volume + sell_volume + neutral_volume

            # 计算平均价格
            avg_price = sum(t['price'] for t in transactions) / len(transactions)

            # 价格波动
            prices = [t['price'] for t in transactions]
            price_range = max(prices) - min(prices)

            print(f"\n股票 {symbol} 交易活跃度分析 (最近 {len(transactions)} 笔交易)")
            print("=" * 60)
            print(f"总成交量: {total_volume:,} 手")
            print(f"买盘成交: {buy_volume:,} 手 ({buy_volume / total_volume * 100:.1f}%)")
            print(f"卖盘成交: {sell_volume:,} 手 ({sell_volume / total_volume * 100:.1f}%)")
            print(f"中性成交: {neutral_volume:,} 手 ({neutral_volume / total_volume * 100:.1f}%)")
            print(f"平均价格: {avg_price:.2f}")
            print(f"价格波动: {price_range:.2f}")

            # 判断买卖力量对比
            if buy_volume > sell_volume * 1.2:
                trend = "买盘占优 🟢"
            elif sell_volume > buy_volume * 1.2:
                trend = "卖盘占优 🔴"
            else:
                trend = "买卖均衡 🟡"

            print(f"市场趋势: {trend}")

    def get_market_overview(self, symbols: list):
        """
        获取市场概览

        Args:
            symbols: 股票代码列表
        """
        with self.tool as tool:
            if not tool.is_connected:
                print("连接TDX服务器失败")
                return

            quotes_dict = tool.batch_get_quotes(symbols)

            if not quotes_dict:
                print("未获取到市场数据")
                return

            print(f"\n市场概览 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            print("=" * 80)
            print(f"{'代码':<8} {'名称':<12} {'现价':<8} {'涨跌':<8} {'涨跌幅':<8} {'成交量':<12} {'趋势':<6}")
            print("-" * 80)

            for symbol in symbols:
                if symbol in quotes_dict:
                    quote = quotes_dict[symbol]

                    # 趋势判断
                    if quote['change_rate'] > 2:
                        trend = "🚀"
                    elif quote['change_rate'] > 0:
                        trend = "📈"
                    elif quote['change_rate'] < -2:
                        trend = "💥"
                    elif quote['change_rate'] < 0:
                        trend = "📉"
                    else:
                        trend = "➡️"

                    print(
                        f"{quote['code']:<8} {quote['name']:<12} {quote['price']:<8.2f} {quote['change']:<8.2f} {quote['change_rate']:<8.2f}% {quote['volume']:<12,} {trend:<6}")
                else:
                    print(f"{symbol:<8} {'数据获取失败':<12}")
