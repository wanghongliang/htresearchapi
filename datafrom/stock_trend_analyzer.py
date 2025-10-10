import numpy as np
from datetime import datetime


class StockTrendAnalyzer:
    def __init__(self):
        # 初始化数据存储
        self.data = []
        self.buy_volumes = []
        self.sell_volumes = []
        self.prices = []
        self.timestamps = []

        # 分析结果
        self.analysis_result = {}

    def load_data(self, trade_data):
        """加载并解析分笔交易数据"""
        for line in trade_data:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    # 解析时间
                    time_str = parts[0]
                    timestamp = datetime.strptime(time_str, "%H:%M")

                    # 解析价格和成交量
                    price = float(parts[1])
                    volume = int(parts[2])
                    direction = parts[3]

                    # 存储数据
                    self.data.append({
                        'timestamp': timestamp,
                        'price': price,
                        'volume': volume,
                        'direction': direction
                    })

                    self.prices.append(price)
                    self.timestamps.append(timestamp)

                    if direction == "B":
                        self.buy_volumes.append(volume)
                    elif direction == "S":
                        self.sell_volumes.append(volume)
                except Exception as e:
                    print(f"解析数据出错: {e}, 数据行: {line}")

    def calculate_volume_strength(self):
        """计算买卖盘力量对比"""
        total_buy = sum(self.buy_volumes)
        total_sell = sum(self.sell_volumes)
        total_volume = total_buy + total_sell

        # 计算买卖盘比例和强度
        if total_volume > 0:
            buy_ratio = total_buy / total_volume
            sell_ratio = total_sell / total_volume
            volume_strength = (total_buy - total_sell) / total_volume
        else:
            buy_ratio = 0
            sell_ratio = 0
            volume_strength = 0

        self.analysis_result['volume'] = {
            'total_buy': total_buy,
            'total_sell': total_sell,
            'total_volume': total_volume,
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'volume_strength': volume_strength  # 正值表示买盘强，负值表示卖盘强
        }

    def calculate_price_trend(self, window=3):
        """计算价格趋势"""
        if len(self.prices) < 2:
            self.analysis_result['price_trend'] = {
                'trend': 'stable',
                'change_rate': 0,
                'confidence': 0
            }
            return

        # 计算整体价格变化率
        start_price = self.prices[0]
        end_price = self.prices[-1]
        overall_change_rate = (end_price - start_price) / start_price

        # 计算近期价格变化趋势（使用滑动窗口）
        trends = []
        for i in range(window, len(self.prices)):
            window_prices = self.prices[i - window:i]
            window_change = (window_prices[-1] - window_prices[0]) / window_prices[0]
            trends.append(window_change)

        # 判断整体趋势
        if len(trends) > 0:
            recent_trend = np.mean(trends)
            # 确定趋势类型
            if recent_trend > 0.005:  # 上涨趋势阈值
                trend_type = 'up'
            elif recent_trend < -0.005:  # 下跌趋势阈值
                trend_type = 'down'
            else:
                trend_type = 'stable'

            # 计算趋势置信度（基于趋势一致性）
            trend_consistency = sum(1 for t in trends if t > 0) / len(trends) if len(trends) > 0 else 0.5
            if trend_type == 'down':
                trend_consistency = 1 - trend_consistency

            confidence = min(1.0, abs(recent_trend) * 100 * trend_consistency)
        else:
            trend_type = 'stable'
            recent_trend = 0
            confidence = 0

        self.analysis_result['price_trend'] = {
            'trend': trend_type,
            'overall_change_rate': overall_change_rate,
            'recent_trend': recent_trend,
            'confidence': confidence
        }

    def analyze_volume_price_relationship(self):
        """分析量价关系"""
        if len(self.prices) < 2 or len(self.data) < 2:
            self.analysis_result['volume_price_relation'] = 'insufficient_data'
            return

        # 计算价格变化和成交量变化
        price_changes = []
        volume_changes = []

        for i in range(1, len(self.data)):
            price_change = (self.data[i]['price'] - self.data[i - 1]['price']) / self.data[i - 1]['price']
            volume_change = self.data[i]['volume'] - self.data[i - 1]['volume']

            price_changes.append(price_change)
            volume_changes.append(volume_change)

        # 计算量价相关性
        if len(price_changes) > 1 and len(volume_changes) > 1:
            correlation = np.corrcoef(price_changes, volume_changes)[0, 1]
        else:
            correlation = 0

        # 判断量价配合情况
        price_trend = self.analysis_result['price_trend']['trend']
        volume_strength = self.analysis_result['volume']['volume_strength']

        if price_trend == 'up' and volume_strength > 0.1:
            relation = 'bullish_confirmation'  # 量价齐升，看涨确认
        elif price_trend == 'down' and volume_strength < -0.1:
            relation = 'bearish_confirmation'  # 量价齐跌，看跌确认
        elif price_trend == 'up' and volume_strength < 0:
            relation = 'bullish_divergence'  # 价升量缩，看涨背离
        elif price_trend == 'down' and volume_strength > 0:
            relation = 'bearish_divergence'  # 价跌量增，看跌背离
        else:
            relation = 'neutral'  # 中性

        self.analysis_result['volume_price_relation'] = {
            'relation': relation,
            'correlation': correlation
        }

    def predict_trend(self):
        """综合所有因素预测趋势"""
        # 提取分析结果
        volume_strength = self.analysis_result['volume']['volume_strength']
        price_trend = self.analysis_result['price_trend']['trend']
        trend_confidence = self.analysis_result['price_trend']['confidence']
        volume_price_relation = self.analysis_result['volume_price_relation']['relation']

        # 计算趋势分数
        trend_score = 0

        # 成交量因素
        trend_score += volume_strength * 3

        # 价格趋势因素
        if price_trend == 'up':
            trend_score += 2 * trend_confidence
        elif price_trend == 'down':
            trend_score -= 2 * trend_confidence

        # 量价关系因素
        if volume_price_relation == 'bullish_confirmation':
            trend_score += 2
        elif volume_price_relation == 'bearish_confirmation':
            trend_score -= 2
        elif volume_price_relation == 'bullish_divergence':
            trend_score += 1
        elif volume_price_relation == 'bearish_divergence':
            trend_score -= 1

        # 确定最终预测
        if trend_score > 1.5:
            prediction = 'strong_up'
        elif trend_score > 0.3:
            prediction = 'mild_up'
        elif trend_score < -1.5:
            prediction = 'strong_down'
        elif trend_score < -0.3:
            prediction = 'mild_down'
        else:
            prediction = 'neutral'

        self.analysis_result['prediction'] = {
            'trend_score': trend_score,
            'prediction': prediction
        }

    def full_analysis(self, trade_data):
        """执行完整分析流程"""
        self.load_data(trade_data)
        self.calculate_volume_strength()
        self.calculate_price_trend()
        self.analyze_volume_price_relationship()
        self.predict_trend()
        return self.analysis_result

    def print_analysis_report(self):
        """打印分析报告"""
        if not self.analysis_result:
            print("尚未进行分析，请先调用full_analysis方法")
            return

        print("=" * 50)
        print("股票分笔交易数据分析报告")
        print("=" * 50)

        # 成交量分析
        vol_data = self.analysis_result['volume']
        print(f"\n成交量分析:")
        print(f"  总买入量: {vol_data['total_buy']}")
        print(f"  总卖出量: {vol_data['total_sell']}")
        print(f"  买入占比: {vol_data['buy_ratio']:.2%}")
        print(f"  卖出占比: {vol_data['sell_ratio']:.2%}")
        print(f"  量能强度: {vol_data['volume_strength']:.2f}")

        # 价格趋势分析
        price_data = self.analysis_result['price_trend']
        print(f"\n价格趋势分析:")
        print(f"  整体价格变化率: {price_data['overall_change_rate']:.2%}")
        print(
            f"  近期趋势: {'上涨' if price_data['trend'] == 'up' else '下跌' if price_data['trend'] == 'down' else '横盘'}")
        print(f"  趋势置信度: {price_data['confidence']:.2%}")

        # 量价关系分析
        relation_data = self.analysis_result['volume_price_relation']
        relation_desc = {
            'bullish_confirmation': '量价齐升（看涨确认）',
            'bearish_confirmation': '量价齐跌（看跌确认）',
            'bullish_divergence': '价升量缩（看涨背离）',
            'bearish_divergence': '价跌量增（看跌背离）',
            'neutral': '中性关系',
            'insufficient_data': '数据不足'
        }.get(relation_data['relation'], relation_data['relation'])

        print(f"\n量价关系分析:")
        print(f"  量价关系: {relation_desc}")
        print(f"  量价相关性: {relation_data['correlation']:.2f}")

        # 趋势预测
        pred_data = self.analysis_result['prediction']
        pred_desc = {
            'strong_up': '强烈上涨',
            'mild_up': '温和上涨',
            'strong_down': '强烈下跌',
            'mild_down': '温和下跌',
            'neutral': '横盘整理'
        }.get(pred_data['prediction'], pred_data['prediction'])

        print(f"\n趋势预测:")
        print(f"  趋势得分: {pred_data['trend_score']:.2f}")
        print(f"  预测结果: {pred_desc}")
        print("\n" + "=" * 50)


# 示例用法
if __name__ == "__main__":
    # 模拟分笔交易数据（时间 价格 成交量 买卖方向）
    trade_data = [
        "09:30 11.35 253 B",
        "09:31 11.36 187 B",
        "09:32 11.37 421 B",
        "09:33 11.37 356 S",
        "09:34 11.38 529 B",
        "09:35 11.38 215 S",
        "09:36 11.39 1254 B",  # 大买盘
        "09:37 11.40 876 B",
        "09:38 11.40 654 S",
        "09:39 11.41 987 B",
        "09:40 11.42 1532 B",  # 大买盘
        "09:41 11.42 753 S",
        "09:42 11.43 621 B",
        "09:43 11.43 429 S",
        "09:44 11.44 873 B",
    ]

    # 创建分析器并执行分析
    analyzer = StockTrendAnalyzer()
    result = analyzer.full_analysis(trade_data)

    # 打印分析报告
    analyzer.print_analysis_report()
