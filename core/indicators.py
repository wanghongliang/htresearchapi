from typing import Dict, List, Optional, Union, Any
from collections import deque
import math
import logging

from base import Indicator, BarData


class SimpleMovingAverage(Indicator):
    """简单移动平均线 (SMA)"""
    
    def __init__(self, name: str = "SMA", period: int = 20):
        super().__init__(name, period)
        self.data_buffer = deque(maxlen=period)
    
    def calculate(self, data: Union[BarData, float]) -> Optional[float]:
        """计算SMA值"""
        if isinstance(data, BarData):
            price = data.close
        else:
            price = float(data)
        
        self.data_buffer.append(price)
        
        if len(self.data_buffer) < self.period:
            return None
        
        return sum(self.data_buffer) / len(self.data_buffer)


class ExponentialMovingAverage(Indicator):
    """指数移动平均线 (EMA)"""
    
    def __init__(self, name: str = "EMA", period: int = 20):
        super().__init__(name, period)
        self.multiplier = 2.0 / (period + 1)
        self.ema_value: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[float]:
        """计算EMA值"""
        if isinstance(data, BarData):
            price = data.close
        else:
            price = float(data)
        
        if self.ema_value is None:
            self.ema_value = price
        else:
            self.ema_value = (price * self.multiplier) + (self.ema_value * (1 - self.multiplier))
        
        return self.ema_value


class RelativeStrengthIndex(Indicator):
    """相对强弱指数 (RSI)"""
    
    def __init__(self, name: str = "RSI", period: int = 14):
        super().__init__(name, period)
        self.price_changes = deque(maxlen=period)
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.prev_price: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[float]:
        """计算RSI值"""
        if isinstance(data, BarData):
            price = data.close
        else:
            price = float(data)
        
        if self.prev_price is None:
            self.prev_price = price
            return None
        
        change = price - self.prev_price
        self.price_changes.append(change)
        
        gain = max(change, 0)
        loss = max(-change, 0)
        
        self.gains.append(gain)
        self.losses.append(loss)
        
        self.prev_price = price
        
        if len(self.gains) < self.period:
            return None
        
        avg_gain = sum(self.gains) / len(self.gains)
        avg_loss = sum(self.losses) / len(self.losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class BollingerBands(Indicator):
    """布林带 (Bollinger Bands)"""
    
    def __init__(self, name: str = "BB", period: int = 20, std_dev: float = 2.0):
        super().__init__(name, period)
        self.std_dev = std_dev
        self.data_buffer = deque(maxlen=period)
        self.upper_band: Optional[float] = None
        self.middle_band: Optional[float] = None
        self.lower_band: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[Dict[str, float]]:
        """计算布林带值"""
        if isinstance(data, BarData):
            price = data.close
        else:
            price = float(data)
        
        self.data_buffer.append(price)
        
        if len(self.data_buffer) < self.period:
            return None
        
        # 计算中轨（移动平均线）
        self.middle_band = sum(self.data_buffer) / len(self.data_buffer)
        
        # 计算标准差
        variance = sum((x - self.middle_band) ** 2 for x in self.data_buffer) / len(self.data_buffer)
        std_deviation = math.sqrt(variance)
        
        # 计算上轨和下轨
        self.upper_band = self.middle_band + (self.std_dev * std_deviation)
        self.lower_band = self.middle_band - (self.std_dev * std_deviation)
        
        return {
            'upper': self.upper_band,
            'middle': self.middle_band,
            'lower': self.lower_band
        }
    
    def get_upper_band(self) -> Optional[float]:
        return self.upper_band
    
    def get_middle_band(self) -> Optional[float]:
        return self.middle_band
    
    def get_lower_band(self) -> Optional[float]:
        return self.lower_band


class MACD(Indicator):
    """移动平均收敛散度 (MACD)"""
    
    def __init__(self, name: str = "MACD", fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(name, slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        self.fast_ema = ExponentialMovingAverage("FastEMA", fast_period)
        self.slow_ema = ExponentialMovingAverage("SlowEMA", slow_period)
        self.signal_ema = ExponentialMovingAverage("SignalEMA", signal_period)
        
        self.macd_line: Optional[float] = None
        self.signal_line: Optional[float] = None
        self.histogram: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[Dict[str, float]]:
        """计算MACD值"""
        if isinstance(data, BarData):
            price = data.close
        else:
            price = float(data)
        
        # 计算快速和慢速EMA
        fast_ema_value = self.fast_ema.calculate(price)
        slow_ema_value = self.slow_ema.calculate(price)
        
        if fast_ema_value is None or slow_ema_value is None:
            return None
        
        # 计算MACD线
        self.macd_line = fast_ema_value - slow_ema_value
        
        # 计算信号线
        signal_value = self.signal_ema.calculate(self.macd_line)
        if signal_value is not None:
            self.signal_line = signal_value
            self.histogram = self.macd_line - self.signal_line
        
        return {
            'macd': self.macd_line,
            'signal': self.signal_line,
            'histogram': self.histogram
        }
    
    def get_macd_line(self) -> Optional[float]:
        return self.macd_line
    
    def get_signal_line(self) -> Optional[float]:
        return self.signal_line
    
    def get_histogram(self) -> Optional[float]:
        return self.histogram


class StochasticOscillator(Indicator):
    """随机振荡器 (Stochastic)"""
    
    def __init__(self, name: str = "STOCH", k_period: int = 14, d_period: int = 3):
        super().__init__(name, k_period)
        self.k_period = k_period
        self.d_period = d_period
        
        self.high_buffer = deque(maxlen=k_period)
        self.low_buffer = deque(maxlen=k_period)
        self.close_buffer = deque(maxlen=k_period)
        self.k_values = deque(maxlen=d_period)
        
        self.k_value: Optional[float] = None
        self.d_value: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[Dict[str, float]]:
        """计算随机振荡器值"""
        if not isinstance(data, BarData):
            return None
        
        self.high_buffer.append(data.high)
        self.low_buffer.append(data.low)
        self.close_buffer.append(data.close)
        
        if len(self.high_buffer) < self.k_period:
            return None
        
        # 计算%K值
        highest_high = max(self.high_buffer)
        lowest_low = min(self.low_buffer)
        current_close = data.close
        
        if highest_high == lowest_low:
            self.k_value = 50.0
        else:
            self.k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        
        self.k_values.append(self.k_value)
        
        # 计算%D值（%K的移动平均）
        if len(self.k_values) >= self.d_period:
            self.d_value = sum(list(self.k_values)[-self.d_period:]) / self.d_period
        
        return {
            'k': self.k_value,
            'd': self.d_value
        }
    
    def get_k_value(self) -> Optional[float]:
        return self.k_value
    
    def get_d_value(self) -> Optional[float]:
        return self.d_value


class AverageTrueRange(Indicator):
    """平均真实范围 (ATR)"""
    
    def __init__(self, name: str = "ATR", period: int = 14):
        super().__init__(name, period)
        self.tr_values = deque(maxlen=period)
        self.prev_close: Optional[float] = None
    
    def calculate(self, data: Union[BarData, float]) -> Optional[float]:
        """计算ATR值"""
        if not isinstance(data, BarData):
            return None
        
        if self.prev_close is None:
            self.prev_close = data.close
            return None
        
        # 计算真实范围 (True Range)
        tr1 = data.high - data.low
        tr2 = abs(data.high - self.prev_close)
        tr3 = abs(data.low - self.prev_close)
        
        true_range = max(tr1, tr2, tr3)
        self.tr_values.append(true_range)
        
        self.prev_close = data.close
        
        if len(self.tr_values) < self.period:
            return None
        
        # 计算ATR（真实范围的移动平均）
        atr = sum(self.tr_values) / len(self.tr_values)
        return atr


class IndicatorManager:
    """指标管理器"""
    
    def __init__(self, name: str = "IndicatorManager"):
        self.name = name
        self.logger = logging.getLogger(f"IndicatorManager.{name}")
        
        # 指标注册表
        self.indicators: Dict[str, Indicator] = {}
        self.symbol_indicators: Dict[str, List[str]] = {}  # symbol -> [indicator_names]
        
        # 指标工厂
        self.indicator_factory = {
            'SMA': SimpleMovingAverage,
            'EMA': ExponentialMovingAverage,
            'RSI': RelativeStrengthIndex,
            'BB': BollingerBands,
            'MACD': MACD,
            'STOCH': StochasticOscillator,
            'ATR': AverageTrueRange
        }
    
    def create_indicator(self, indicator_type: str, name: str, **kwargs) -> Optional[Indicator]:
        """创建指标"""
        try:
            if indicator_type not in self.indicator_factory:
                self.logger.error(f"Unknown indicator type: {indicator_type}")
                return None
            
            indicator_class = self.indicator_factory[indicator_type]
            indicator = indicator_class(name=name, **kwargs)
            
            self.logger.info(f"Created indicator {name} of type {indicator_type}")
            return indicator
            
        except Exception as e:
            self.logger.error(f"Failed to create indicator {name}: {e}")
            return None
    
    def add_indicator(self, indicator: Indicator, symbol: str = None) -> bool:
        """添加指标"""
        try:
            if indicator.name in self.indicators:
                self.logger.warning(f"Indicator {indicator.name} already exists")
                return False
            
            self.indicators[indicator.name] = indicator
            
            if symbol:
                if symbol not in self.symbol_indicators:
                    self.symbol_indicators[symbol] = []
                self.symbol_indicators[symbol].append(indicator.name)
            
            self.logger.info(f"Added indicator {indicator.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add indicator {indicator.name}: {e}")
            return False
    
    def remove_indicator(self, indicator_name: str) -> bool:
        """移除指标"""
        try:
            if indicator_name not in self.indicators:
                self.logger.warning(f"Indicator {indicator_name} not found")
                return False
            
            # 从符号映射中移除
            for symbol, indicator_list in self.symbol_indicators.items():
                if indicator_name in indicator_list:
                    indicator_list.remove(indicator_name)
            
            # 移除空的符号映射
            self.symbol_indicators = {k: v for k, v in self.symbol_indicators.items() if v}
            
            # 移除指标
            del self.indicators[indicator_name]
            
            self.logger.info(f"Removed indicator {indicator_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove indicator {indicator_name}: {e}")
            return False
    
    def update_indicators(self, symbol: str, data: Union[BarData, float]):
        """更新指标"""
        try:
            if symbol not in self.symbol_indicators:
                return
            
            for indicator_name in self.symbol_indicators[symbol]:
                if indicator_name in self.indicators:
                    indicator = self.indicators[indicator_name]
                    indicator.update(data)
            
        except Exception as e:
            self.logger.error(f"Failed to update indicators for {symbol}: {e}")
    
    def get_indicator(self, indicator_name: str) -> Optional[Indicator]:
        """获取指标"""
        return self.indicators.get(indicator_name)
    
    def get_indicator_value(self, indicator_name: str, index: int = -1) -> Optional[float]:
        """获取指标值"""
        indicator = self.get_indicator(indicator_name)
        if indicator:
            return indicator.get_value(index)
        return None
    
    def get_symbol_indicators(self, symbol: str) -> List[str]:
        """获取符号的所有指标"""
        return self.symbol_indicators.get(symbol, [])
    
    def get_all_indicators(self) -> Dict[str, Indicator]:
        """获取所有指标"""
        return self.indicators.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """获取指标管理器状态"""
        return {
            'name': self.name,
            'total_indicators': len(self.indicators),
            'indicators': list(self.indicators.keys()),
            'symbol_indicators': dict(self.symbol_indicators),
            'available_types': list(self.indicator_factory.keys())
        }
    
    def register_indicator_type(self, type_name: str, indicator_class):
        """注册新的指标类型"""
        self.indicator_factory[type_name] = indicator_class
        self.logger.info(f"Registered new indicator type: {type_name}")