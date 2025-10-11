from pytdx.hq import TdxHq_API, TDXParams
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime


class TdxMarketTool:
    """
    TdxHq_API工具类封装
    提供分笔交易记录和实时行情信息功能
    """
    
    def __init__(self, host: str = '116.205.163.254', port: int = 7709):
        """
        初始化TDX行情工具
        
        Args:
            host: TDX服务器地址
            port: TDX服务器端口
        """
        self.host = host
        self.port = port
        self.api = TdxHq_API()
        self.is_connected = False
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        连接到TDX服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.is_connected = self.api.connect(self.host, self.port)
            if self.is_connected:
                self.logger.info(f"成功连接到TDX服务器 {self.host}:{self.port}")
            else:
                self.logger.error(f"连接TDX服务器失败 {self.host}:{self.port}")
            return self.is_connected
        except Exception as e:
            self.logger.error(f"连接TDX服务器异常: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """
        断开与TDX服务器的连接
        """
        try:
            if self.is_connected:
                self.api.disconnect()
                self.is_connected = False
                self.logger.info("已断开TDX服务器连接")
        except Exception as e:
            self.logger.error(f"断开连接异常: {e}")
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.disconnect()
    
    def _get_market_code(self, symbol: str) -> int:
        """
        根据股票代码获取市场代码
        
        Args:
            symbol: 股票代码
            
        Returns:
            int: 市场代码 (0=深圳, 1=上海)
        """
        if symbol.startswith(('6', '5')):
            return TDXParams.MARKET_SH  # 上海市场
        elif symbol.startswith(('0', '3')):
            return TDXParams.MARKET_SZ  # 深圳市场
        else:
            # 默认返回深圳市场
            return TDXParams.MARKET_SZ
    
    def get_transaction_data(self, symbol: str, start: int = 0, count: int = 30) -> List[Dict[str, Any]]:
        """
        获取分笔交易记录
        
        Args:
            symbol: 股票代码 (如 '000001', '600000')
            start: 起始位置
            count: 获取数量
            
        Returns:
            List[Dict]: 分笔交易数据列表
            数据格式: [{'time': '14:56', 'price': 11.41, 'vol': 330, 'num': 9, 'buyorsell': 0}, ...]
            buyorsell: 0=买盘, 1=卖盘, 2=中性盘
        """
        if not self.is_connected:
            self.logger.error("未连接到TDX服务器")
            return []
        
        try:
            market_code = self._get_market_code(symbol)
            data = self.api.get_transaction_data(market_code, symbol, start, count)
            
            # 转换为标准格式
            result = []
            for item in data:
                result.append({
                    'time': item['time'],
                    'price': float(item['price']),
                    'volume': int(item['vol']),
                    'num_trades': int(item['num']),
                    'direction': self._parse_direction(item['buyorsell']),
                    'raw_direction': item['buyorsell']
                })
            
            self.logger.info(f"获取股票 {symbol} 分笔交易数据 {len(result)} 条")
            return result
            
        except Exception as e:
            self.logger.error(f"获取分笔交易数据异常: {e}")
            return []
    
    def get_realtime_quotes(self, symbols: List[Tuple[int, str]]) -> List[Dict[str, Any]]:
        """
        获取实时行情信息
        
        Args:
            symbols: 股票代码列表，格式为 [(market, code), ...]
                    market: 0=深圳, 1=上海
                    code: 股票代码
                    
        Returns:
            List[Dict]: 实时行情数据列表
        """
        if not self.is_connected:
            self.logger.error("未连接到TDX服务器")
            return []
        
        try:
            data = self.api.get_security_quotes(symbols)
            
            # 转换为标准格式
            result = []
            for item in data:
                result.append({
                    'code': item['code'],
                    'name': item.get('name', ''),
                    'price': float(item['price']),
                    'last_close': float(item['last_close']),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'volume': int(item['vol']),
                    'amount': float(item.get('amount', 0)),
                    'bid1': float(item.get('bid1', 0)),
                    'ask1': float(item.get('ask1', 0)),
                    'bid1_vol': int(item.get('bid1_vol', 0)),
                    'ask1_vol': int(item.get('ask1_vol', 0)),
                    'change': float(item['price']) - float(item['last_close']),
                    'change_rate': (float(item['price']) - float(item['last_close'])) / float(item['last_close']) * 100 if float(item['last_close']) > 0 else 0
                })
            
            self.logger.info(f"获取实时行情数据 {len(result)} 条")
            return result
            
        except Exception as e:
            self.logger.error(f"获取实时行情数据异常: {e}")
            return []
    
    def get_realtime_quote_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        根据股票代码获取单个股票的实时行情
        
        Args:
            symbol: 股票代码 (如 '000001', '600000')
            
        Returns:
            Dict: 实时行情数据，如果获取失败返回None
        """
        market_code = self._get_market_code(symbol)
        quotes = self.get_realtime_quotes([(market_code, symbol)])
        
        if quotes:
            return quotes[0]
        return None
    
    def get_minute_data(self, symbol: str, count: int = 240) -> List[Dict[str, Any]]:
        """
        获取分时行情数据
        
        Args:
            symbol: 股票代码
            count: 获取数量
            
        Returns:
            List[Dict]: 分时行情数据列表
        """
        if not self.is_connected:
            self.logger.error("未连接到TDX服务器")
            return []
        
        try:
            market_code = self._get_market_code(symbol)
            data = self.api.get_minute_time_data(market_code, symbol)
            
            # 转换为标准格式
            result = []
            for item in data:
                result.append({
                    'time': item.get('time', ''),
                    'price': float(item.get('price', 0)),
                    'volume': int(item.get('vol', 0)),
                    'amount': float(item.get('amount', 0))
                })
            
            self.logger.info(f"获取股票 {symbol} 分时数据 {len(result)} 条")
            return result
            
        except Exception as e:
            self.logger.error(f"获取分时数据异常: {e}")
            return []
    
    def _parse_direction(self, buyorsell: int) -> str:
        """
        解析买卖方向
        
        Args:
            buyorsell: 原始方向值
            
        Returns:
            str: 方向描述
        """
        direction_map = {
            0: 'buy',      # 买盘
            1: 'sell',     # 卖盘
            2: 'neutral'   # 中性盘
        }
        return direction_map.get(buyorsell, 'unknown')
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        获取市场状态信息
        
        Returns:
            Dict: 市场状态信息
        """
        return {
            'connected': self.is_connected,
            'server': f"{self.host}:{self.port}",
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def batch_get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个股票的实时行情
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            Dict: 以股票代码为key的行情数据字典
        """
        # 构建查询参数
        query_symbols = []
        for symbol in symbols:
            market_code = self._get_market_code(symbol)
            query_symbols.append((market_code, symbol))
        
        # 获取行情数据
        quotes = self.get_realtime_quotes(query_symbols)
        
        # 转换为字典格式
        result = {}
        for quote in quotes:
            result[quote['code']] = quote
        
        return result