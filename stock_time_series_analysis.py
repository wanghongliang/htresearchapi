# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Dict, Tuple
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime, timedelta


@dataclass
class TimeOrder:
    """带时间戳的买卖订单数据结构"""
    timestamp: datetime  # 时间戳
    price: float  # 价格
    volume: int  # 数量
    is_bid: bool  # 是否为买盘（True为买盘，False为卖盘）


class TimeSeriesAnalyzer:
    """股票买卖盘时间序列分析器"""

    def __init__(self, window_size: int = 20):
        self.orders: List[TimeOrder] = []  # 所有订单数据
        self.window_size = window_size  # 滑动窗口大小
        self.df = None  # 转换后的DataFrame

    def add_orders(self, timestamp: datetime, bids: List[Dict], asks: List[Dict]):
        """
        添加某一时刻的买卖盘数据

        参数:
            timestamp: 时间戳
            bids: 买盘数据，格式如[{"price": 10.0, "volume": 100}, ...]
            asks: 卖盘数据，格式如[{"price": 10.1, "volume": 200}, ...]
        """
        # 添加买盘数据
        for bid in bids:
            self.orders.append(TimeOrder(
                timestamp=timestamp,
                price=bid["price"],
                volume=bid["volume"],
                is_bid=True
            ))

        # 添加卖盘数据
        for ask in asks:
            self.orders.append(TimeOrder(
                timestamp=timestamp,
                price=ask["price"],
                volume=ask["volume"],
                is_bid=False
            ))

    def prepare_dataframe(self):
        """将订单数据转换为DataFrame以便分析"""
        if not self.orders:
            raise ValueError("没有订单数据，请先添加数据")

        # 转换为DataFrame
        data = [{
            "timestamp": order.timestamp,
            "price": order.price,
            "volume": order.volume,
            "is_bid": order.is_bid
        } for order in self.orders]

        self.df = pd.DataFrame(data)
        self.df = self.df.sort_values(by="timestamp")

        # 按时间和买卖盘分组，计算总量
        self.df["bid_volume"] = self.df.apply(lambda x: x["volume"] if x["is_bid"] else 0, axis=1)
        self.df["ask_volume"] = self.df.apply(lambda x: x["volume"] if not x["is_bid"] else 0, axis=1)

        # 按时间聚合
        self.df = self.df.groupby("timestamp").agg({
            "bid_volume": "sum",
            "ask_volume": "sum",
            "price": "mean"  # 该时间点的平均价格
        }).reset_index()

        # 设置时间戳为索引
        self.df = self.df.set_index("timestamp")

        # 计算买卖盘比例和净流量
        self.df["bid_ask_ratio"] = self.df["bid_volume"] / (self.df["ask_volume"] + 1e-6)  # 避免除零
        self.df["net_flow"] = self.df["bid_volume"] - self.df["ask_volume"]

        return self.df

    def calculate_moving_averages(self) -> pd.DataFrame:
        """计算移动平均值"""
        if self.df is None:
            self.prepare_dataframe()

        # 计算不同窗口的移动平均值
        self.df["ma_bid"] = self.df["bid_volume"].rolling(window=self.window_size).mean()
        self.df["ma_ask"] = self.df["ask_volume"].rolling(window=self.window_size).mean()
        self.df["ma_ratio"] = self.df["bid_ask_ratio"].rolling(window=self.window_size).mean()
        self.df["ma_net_flow"] = self.df["net_flow"].rolling(window=self.window_size).mean()

        return self.df

    def detect_trend_changes(self) -> List[Tuple[datetime, str]]:
        """检测趋势变化点"""
        if self.df is None:
            self.calculate_moving_averages()

        trend_changes = []
        prev_ratio = None
        threshold = 0.1  # 变化阈值

        for timestamp, row in self.df.iterrows():
            if pd.isna(row["ma_ratio"]):
                prev_ratio = row["ma_ratio"]
                continue

            if prev_ratio is not None and not pd.isna(prev_ratio):
                # 计算变化率
                change = (row["ma_ratio"] - prev_ratio) / (abs(prev_ratio) + 1e-6)

                if change > threshold:
                    trend_changes.append((timestamp, f"买盘力量增强: {change:.2%}"))
                elif change < -threshold:
                    trend_changes.append((timestamp, f"卖盘力量增强: {change:.2%}"))

            prev_ratio = row["ma_ratio"]

        return trend_changes

    def decompose_trend(self):
        """分解时间序列趋势"""
        if self.df is None:
            self.calculate_moving_averages()

        # 确保数据频率规则
        df_resampled = self.df["net_flow"].resample('1min').mean().interpolate()

        # 分解趋势
        decomposition = seasonal_decompose(df_resampled, model='additive', period=20)

        # 绘制分解结果
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 16))
        decomposition.observed.plot(ax=ax1, title='原始净流量')
        decomposition.trend.plot(ax=ax2, title='趋势成分')
        decomposition.seasonal.plot(ax=ax3, title='季节性成分')
        decomposition.resid.plot(ax=ax4, title='残差成分')
        plt.tight_layout()
        plt.show()

        return decomposition

    def predict_short_term(self, steps: int = 5) -> pd.DataFrame:
        """使用ARIMA模型进行短期预测"""
        if self.df is None:
            self.calculate_moving_averages()

        # 准备数据
        df_resampled = self.df["net_flow"].resample('1min').mean().interpolate()

        # 拟合ARIMA模型
        model = ARIMA(df_resampled.values, order=(5, 1, 0))
        model_fit = model.fit()

        # 预测
        forecast = model_fit.forecast(steps=steps)

        # 生成预测时间戳
        last_time = df_resampled.index[-1]
        forecast_times = [last_time + timedelta(minutes=i + 1) for i in range(steps)]

        # 创建预测结果DataFrame
        forecast_df = pd.DataFrame({
            "timestamp": forecast_times,
            "predicted_net_flow": forecast
        })
        forecast_df = forecast_df.set_index("timestamp")

        return forecast_df

    def analyze_trend(self) -> Dict:
        """综合分析趋势并返回结果"""
        if self.df is None:
            self.calculate_moving_averages()

        # 获取最新数据
        latest = self.df.iloc[-1]

        # 趋势判断
        trend = "震荡整理"
        confidence = 0.0

        # 基于净流量移动平均判断
        if not pd.isna(latest["ma_net_flow"]):
            if latest["ma_net_flow"] > 0:
                # 买盘占优
                strength = min(1.0, latest["ma_net_flow"] / (latest["ma_bid"] + latest["ma_ask"] + 1e-6))
                confidence = strength

                if strength > 0.3:
                    trend = "强烈上涨"
                elif strength > 0.1:
                    trend = "温和上涨"
            else:
                # 卖盘占优
                strength = min(1.0, abs(latest["ma_net_flow"]) / (latest["ma_bid"] + latest["ma_ask"] + 1e-6))
                confidence = strength

                if strength > 0.3:
                    trend = "强烈下跌"
                elif strength > 0.1:
                    trend = "温和下跌"

        # 检测最近的趋势变化
        recent_changes = self.detect_trend_changes()[-3:]  # 最近3个变化点

        return {
            "当前趋势": trend,
            "趋势置信度": confidence,
            "最新买盘量": latest["bid_volume"],
            "最新卖盘量": latest["ask_volume"],
            "最新买卖比": latest["bid_ask_ratio"],
            "最新净流量": latest["net_flow"],
            "近期趋势变化": recent_changes
        }

    def plot_time_series(self):
        """绘制时间序列图表"""
        if self.df is None:
            self.calculate_moving_averages()

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))

        # 绘制买卖盘量及其移动平均线
        self.df["bid_volume"].plot(ax=ax1, label='买盘量', alpha=0.5)
        self.df["ask_volume"].plot(ax=ax1, label='卖盘量', alpha=0.5)
        self.df["ma_bid"].plot(ax=ax1, label=f'买盘{self.window_size}期均线', color='green')
        self.df["ma_ask"].plot(ax=ax1, label=f'卖盘{self.window_size}期均线', color='red')
        ax1.set_title('买卖盘量时间序列')
        ax1.legend()
        ax1.grid(True)

        # 绘制买卖比
        self.df["bid_ask_ratio"].plot(ax=ax2, label='买卖比', alpha=0.5)
        self.df["ma_ratio"].plot(ax=ax2, label=f'买卖比{self.window_size}期均线', color='purple')
        ax2.axhline(y=1.0, color='black', linestyle='--', alpha=0.3)
        ax2.set_title('买卖比时间序列')
        ax2.legend()
        ax2.grid(True)

        # 绘制净流量
        self.df["net_flow"].plot(ax=ax3, label='净流量', alpha=0.5)
        self.df["ma_net_flow"].plot(ax=ax3, label=f'净流量{self.window_size}期均线', color='blue')
        ax3.axhline(y=0.0, color='black', linestyle='--', alpha=0.3)
        ax3.set_title('买卖净流量时间序列')
        ax3.legend()
        ax3.grid(True)

        plt.tight_layout()
        plt.show()


# 示例用法
if __name__ == "__main__":
    # 创建分析器
    analyzer = TimeSeriesAnalyzer(window_size=15)

    # 生成模拟的时间序列数据（1小时的数据，每分钟一个数据点）
    start_time = datetime.now() - timedelta(hours=1)

    # 前30分钟模拟下跌趋势，后30分钟模拟上涨趋势
    for i in range(60):
        current_time = start_time + timedelta(minutes=i)

        # 基础价格
        base_price = 10.0

        # 前30分钟卖盘逐渐增加，后30分钟买盘逐渐增加
        if i < 30:
            # 下跌阶段：卖盘逐渐增加
            bid_volumes = [100 - i, 80 - i // 2, 60 - i // 3, 40 - i // 4, 20 - i // 5]
            ask_volumes = [200 + i, 180 + i // 2, 160 + i // 3, 140 + i // 4, 120 + i // 5]
        else:
            # 上涨阶段：买盘逐渐增加
            bid_volumes = [200 + (i - 30), 180 + (i - 30) // 2, 160 + (i - 30) // 3, 140 + (i - 30) // 4,
                           120 + (i - 30) // 5]
            ask_volumes = [100 - (i - 30), 80 - (i - 30) // 2, 60 - (i - 30) // 3, 40 - (i - 30) // 4,
                           20 - (i - 30) // 5]

        # 确保数量不为负
        bid_volumes = [max(10, v) for v in bid_volumes]
        ask_volumes = [max(10, v) for v in ask_volumes]

        # 创建买盘数据
        bids = [{"price": base_price - 0.01 * j, "volume": bid_volumes[j]} for j in range(5)]
        # 创建卖盘数据
        asks = [{"price": base_price + 0.01 * j, "volume": ask_volumes[j]} for j in range(5)]

        # 添加到分析器
        analyzer.add_orders(current_time, bids, asks)

    # 准备数据分析
    analyzer.prepare_dataframe()
    analyzer.calculate_moving_averages()

    # 打印分析结果
    print("时间序列分析结果:")
    result = analyzer.analyze_trend()
    for key, value in result.items():
        print(f"{key}: {value}")

    # 绘制时间序列图表
    analyzer.plot_time_series()

    # 分解趋势
    analyzer.decompose_trend()

    # 短期预测
    forecast = analyzer.predict_short_term(steps=5)
    print("\n短期净流量预测:")
    print(forecast)
