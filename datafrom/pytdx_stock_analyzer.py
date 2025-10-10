import numpy as np
from datetime import datetime as _datetime
from collections import OrderedDict


class PytdxStockAnalyzer:
    def __init__(self):
        # 初始化数据存储
        self.data = []
        self.buy_volumes = []
        self.sell_volumes = []
        self.neutral_volumes = []  # 中性交易
        self.prices = []
        self.timestamps = []

        # 分析结果
        self.analysis_result = {}

        # pytdx中buyorsell的含义映射
        # 0: 买入, 1: 卖出, 2: 中性/未知
        self.direction_map = {
            0: 'buy',
            1: 'sell',
            2: 'neutral'
        }

    def load_pytdx_data(self, transaction_data):
        """加载并解析pytdx返回的分笔交易数据"""
        # transaction_data 应为get_transaction_data返回的OrderedDict列表
        for item in transaction_data:
            try:

                print(item)
                # 解析时间
                time_str = str(item['time'])
                # 确保时间格式正确，添加日期部分（实际分析中可能需要真实日期）
                timestamp = _datetime.strptime(time_str, "%H:%M")

                # 提取价格、成交量和买卖方向
                price = float(item['price'])
                volume = int(item['vol'])  # pytdx中vol字段表示成交量
                buyorsell = item['buyorsell']

                # 存储数据
                direction = self.direction_map.get(buyorsell, 'neutral')
                self.data.append({
                    'timestamp': timestamp,
                    'price': price,
                    'volume': volume,
                    'direction': direction,
                    'raw_direction': buyorsell
                })

                self.prices.append(price)
                self.timestamps.append(timestamp)

                # 按方向累加成交量
                if direction == 'buy':
                    self.buy_volumes.append(volume)
                elif direction == 'sell':
                    self.sell_volumes.append(volume)
                else:
                    self.neutral_volumes.append(volume)

            except Exception as e:
                print(f"解析数据出错: {e}, 数据项: {item}")

    def calculate_volume_strength(self):
        """计算买卖盘力量对比"""
        total_buy = sum(self.buy_volumes)
        total_sell = sum(self.sell_volumes)
        total_neutral = sum(self.neutral_volumes)
        total_volume = total_buy + total_sell + total_neutral

        # 计算买卖盘比例和强度
        if total_volume > 0:
            buy_ratio = total_buy / total_volume
            sell_ratio = total_sell / total_volume
            neutral_ratio = total_neutral / total_volume
            # 量能强度：正值表示买盘强，负值表示卖盘强
            volume_strength = (total_buy - total_sell) / (total_buy + total_sell) if (total_buy + total_sell) > 0 else 0
        else:
            buy_ratio = 0
            sell_ratio = 0
            neutral_ratio = 0
            volume_strength = 0

        self.analysis_result['volume'] = {
            'total_buy': total_buy,
            'total_sell': total_sell,
            'total_neutral': total_neutral,
            'total_volume': total_volume,
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'neutral_ratio': neutral_ratio,
            'volume_strength': volume_strength
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
            # 确定趋势类型（可根据需要调整阈值）
            if recent_trend > 0.002:  # 上涨趋势阈值
                trend_type = 'up'
            elif recent_trend < -0.002:  # 下跌趋势阈值
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

    def full_analysis(self, transaction_data):
        """执行完整分析流程"""
        self.load_pytdx_data(transaction_data)
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

        print("=" * 70)
        print("股票分笔交易数据分析报告 (基于pytdx数据)")
        print("=" * 70)

        # 成交量分析
        vol_data = self.analysis_result['volume']
        print(f"\n成交量分析:")
        print(f"  总买入量: {vol_data['total_buy']:,}")
        print(f"  总卖出量: {vol_data['total_sell']:,}")
        print(f"  中性成交量: {vol_data['total_neutral']:,}")
        print(f"  总成交量: {vol_data['total_volume']:,}")
        print(f"  买入占比: {vol_data['buy_ratio']:.2%}")
        print(f"  卖出占比: {vol_data['sell_ratio']:.2%}")
        print(f"  量能强度: {vol_data['volume_strength']:.2f} (正值为买盘强，负值为卖盘强)")

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
        print("\n" + "=" * 70)


# 示例用法
if __name__ == "__main__":
    # 示例数据：pytdx的get_transaction_data返回的结构
    sample_data = [
        OrderedDict([('time', '14:55'), ('price', 11.41), ('vol', 162), ('num', 16), ('buyorsell', 0)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 138), ('num', 11), ('buyorsell', 1)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 518), ('num', 26), ('buyorsell', 1)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 230), ('num', 14), ('buyorsell', 1)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 555), ('num', 22), ('buyorsell', 1)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 229), ('num', 27), ('buyorsell', 1)]),
        OrderedDict([('time', '14:55'), ('price', 11.41), ('vol', 306), ('num', 10), ('buyorsell', 0)]),
        OrderedDict([('time', '14:55'), ('price', 11.4), ('vol', 244), ('num', 12), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 191), ('num', 16), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 5549), ('num', 142), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 64), ('num', 12), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 429), ('num', 29), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 687), ('num', 18), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 334), ('num', 14), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 250), ('num', 30), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 750), ('num', 89), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 322), ('num', 14), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 131), ('num', 17), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 1359), ('num', 14), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 216), ('num', 16), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 228), ('num', 58), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 141), ('num', 23), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 337), ('num', 14), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 84), ('num', 11), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 582), ('num', 25), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 112), ('num', 16), ('buyorsell', 1)]),
        OrderedDict([('time', '14:56'), ('price', 11.41), ('vol', 330), ('num', 9), ('buyorsell', 0)]),
        OrderedDict([('time', '14:56'), ('price', 11.4), ('vol', 82), ('num', 17), ('buyorsell', 1)]),
        OrderedDict([('time', '14:57'), ('price', 11.4), ('vol', 197), ('num', 12), ('buyorsell', 1)]),
        OrderedDict([('time', '15:00'), ('price', 11.4), ('vol', 15332), ('num', 610), ('buyorsell', 2)])
    ]

    # # 创建分析器并执行分析
    # analyzer = PytdxStockAnalyzer()
    # result = analyzer.full_analysis( sample_data )
    #
    # # 打印分析报告
    # analyzer.print_analysis_report()


    from pytdx.exhq import *
    from pytdx.hq import *

    from pytdx.hq import TdxHq_API

    api = TdxHq_API()

    data = []
    with api.connect('116.205.163.254', 7709):

        #003816
        #MARKET_SH  MARKET_SZ
        #td = api.get_transaction_data(TDXParams.MARKET_SH, '513630', 0, 30)
        td = api.get_transaction_data(TDXParams.MARKET_SH, '513630', 0, 30)
        for ord in td:
            print( ord )
            data.append( ord )
        #print(td)

    # 创建分析器并执行分析
    analyzer = PytdxStockAnalyzer()
    result = analyzer.full_analysis( data )

    # 打印分析报告
    analyzer.print_analysis_report()

    api.disconnect()
