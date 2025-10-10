from flask import Flask, request, jsonify, g
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
import configparser  # 新增：用于读取配置文件

# 导入之前定义的交易客户端类
from ht_client_trader import HTClientTrader  # 请替换为实际的模块名

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoLoginTraderServer:
    """带自动登录功能的交易客户端HTTP服务类，基于Flask实现"""

    def __init__(self,
                 host: str = '0.0.0.0',
                 port: int = 5000,
                 debug: bool = False,
                 config_path: str = "config.ini"):  # 新增：配置文件路径
        """初始化Flask应用和交易客户端管理"""
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.debug = debug
        self.config_path = config_path  # 新增：配置文件路径
        self.auto_login_session_id = None  # 新增：自动登录的会话ID

        # 存储会话ID到交易客户端实例的映射
        self.trader_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = threading.Lock()

        # 会话超时时间（30分钟）
        self.session_timeout = timedelta(minutes=30)

        # 注册路由
        self._register_routes()

        # 配置请求钩子
        @self.app.before_request
        def before_request():
            """请求处理前的钩子，验证会话ID"""
            if request.path not in ['/api/trader/connect', '/api/trader/login']:
                session_id = request.args.get('session_id')
                # 新增：如果未提供session_id，尝试使用自动登录的会话ID
                if not session_id and self.auto_login_session_id:
                    session_id = self.auto_login_session_id

                if not session_id or session_id not in self.trader_sessions:
                    g.valid_session = False
                    return jsonify({
                        'code': 401,
                        'message': '无效的会话ID，请重新连接或登录',
                        'data': None
                    }), 401

                # 检查会话是否超时
                session_data = self.trader_sessions[session_id]
                if datetime.now() - session_data['last_active'] > self.session_timeout:
                    g.valid_session = False
                    with self.session_lock:
                        del self.trader_sessions[session_id]
                    # 如果超时的是自动登录会话，重置自动登录会话ID
                    if session_id == self.auto_login_session_id:
                        self.auto_login_session_id = None
                    return jsonify({
                        'code': 401,
                        'message': '会话已超时，请重新连接或登录',
                        'data': None
                    }), 401

                # 更新最后活动时间
                session_data['last_active'] = datetime.now()
                g.trader = session_data['trader']
                g.session_id = session_id
                g.valid_session = True

        # 新增：自动登录处理
        self._auto_login()

    def _read_config(self) -> dict:
        """读取配置文件，获取登录信息"""
        config = configparser.ConfigParser()
        try:
            # 读取文件（指定utf-8编码防止中文乱码）
            config.read(self.config_path, encoding='utf-8')

            # 初始化结果字典
            result = {}

            # 读取 [Trader] 节
            if 'Trader' in config:
                result['exe_path'] = config.get('Trader', 'exe_path', fallback='')  # 字符串

            # 读取 [Account] 节
            if 'Account' in config:
                result['user'] = config.get('Account', 'user', fallback='')  # 字符串
                result['password'] = config.get('Account', 'password', fallback='')  # 字符串
                result['comm_password'] = config.get('Account', 'comm_password', fallback='')  # 新增：通讯密码

            return result
        except Exception as e:
            logger.error(f"读取配置文件失败: {str(e)}")
            return {}

    def _auto_login(self) -> bool:
        """自动登录交易客户端"""
        logger.info("开始自动登录交易客户端...")

        # 读取配置
        config_data = self._read_config()

        # 验证配置是否完整
        required_fields = ['user', 'password', 'comm_password']
        for field in required_fields:
            if not config_data.get(field):
                logger.error(f"配置文件缺少必要信息: {field}，自动登录失败")
                return False

        try:
            # 创建交易客户端实例
            trader = HTClientTrader()

            # 执行登录
            success = trader.login(
                user=config_data['user'],
                password=config_data['password'],
                exe_path=config_data.get('exe_path'),
                comm_password=config_data['comm_password']
            )

            if success:
                # 创建会话并保存会话ID
                self.auto_login_session_id = self._create_session(trader)
                logger.info(f"自动登录成功，会话ID: {self.auto_login_session_id}")
                return True
            else:
                logger.error("自动登录失败，请检查配置信息")
                return False
        except Exception as e:
            logger.error(f"自动登录发生错误: {str(e)}", exc_info=True)
            return False

    def _register_routes(self):
        """注册所有API路由"""
        # 基础连接与登录接口
        self.app.add_url_rule('/api/trader/connect', 'connect', self.connect, methods=['POST'])
        self.app.add_url_rule('/api/trader/login', 'login', self.login, methods=['POST'])
        self.app.add_url_rule('/api/trader/exit', 'exit', self.exit, methods=['POST'])

        # 数据查询接口
        self.app.add_url_rule('/api/trader/balance', 'get_balance', self.get_balance, methods=['GET'])
        self.app.add_url_rule('/api/trader/position', 'get_position', self.get_position, methods=['GET'])
        self.app.add_url_rule('/api/trader/today-entrusts', 'get_today_entrusts', self.get_today_entrusts,
                              methods=['GET'])
        self.app.add_url_rule('/api/trader/today-trades', 'get_today_trades', self.get_today_trades, methods=['GET'])
        self.app.add_url_rule('/api/trader/cancel-entrusts', 'get_cancel_entrusts', self.get_cancel_entrusts,
                              methods=['GET'])

        # 交易操作接口
        self.app.add_url_rule('/api/trader/buy', 'buy', self.buy, methods=['POST'])
        self.app.add_url_rule('/api/trader/sell', 'sell', self.sell, methods=['POST'])
        self.app.add_url_rule('/api/trader/market-buy', 'market_buy', self.market_buy, methods=['POST'])
        self.app.add_url_rule('/api/trader/market-sell', 'market_sell', self.market_sell, methods=['POST'])
        self.app.add_url_rule('/api/trader/cancel-entrust', 'cancel_entrust', self.cancel_entrust, methods=['POST'])
        self.app.add_url_rule('/api/trader/cancel-all-entrusts', 'cancel_all_entrusts', self.cancel_all_entrusts,
                              methods=['POST'])
        self.app.add_url_rule('/api/trader/auto-ipo', 'auto_ipo', self.auto_ipo, methods=['POST'])

        # 工具类接口
        self.app.add_url_rule('/api/trader/refresh', 'refresh', self.refresh, methods=['POST'])

        # 新增：获取当前会话状态接口
        self.app.add_url_rule('/api/trader/session-status', 'session_status', self.session_status, methods=['GET'])

    def _generate_session_id(self) -> str:
        """生成唯一的会话ID"""
        return str(uuid.uuid4())

    def _create_session(self, trader: HTClientTrader) -> str:
        """创建新的会话并返回会话ID"""
        session_id = self._generate_session_id()
        with self.session_lock:
            self.trader_sessions[session_id] = {
                'trader': trader,
                'last_active': datetime.now(),
                'created_at': datetime.now(),
                'is_auto_login': self.auto_login_session_id is None  # 标记是否为自动登录会话
            }
        return session_id

    def session_status(self):
        """获取当前会话状态"""
        try:
            if self.auto_login_session_id and self.auto_login_session_id in self.trader_sessions:
                session_data = self.trader_sessions[self.auto_login_session_id]
                return jsonify({
                    'code': 200,
                    'message': '会话状态查询成功',
                    'data': {
                        'is_logged_in': True,
                        'session_id': self.auto_login_session_id,
                        'created_at': session_data['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                        'last_active': session_data['last_active'].strftime('%Y-%m-%d %H:%M:%S'),
                        'is_auto_login': session_data.get('is_auto_login', False)
                    }
                })
            else:
                return jsonify({
                    'code': 200,
                    'message': '会话状态查询成功',
                    'data': {
                        'is_logged_in': False,
                        'session_id': None
                    }
                })
        except Exception as e:
            logger.error(f"查询会话状态失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    def connect(self):
        """连接已登录的客户端"""
        try:
            data = request.get_json() or {}
            exe_path = data.get('exe_path')

            trader = HTClientTrader()
            success = trader.connect(exe_path=exe_path)

            if success:
                session_id = self._create_session(trader)
                logger.info(f"客户端连接成功，会话ID: {session_id}")
                return jsonify({
                    'code': 200,
                    'message': '成功连接客户端',
                    'data': {
                        'exe_path': exe_path or trader.CONFIG["DEFAULT_EXE_PATH"],
                        'session_id': session_id
                    }
                })
            else:
                logger.error("客户端连接失败")
                return jsonify({
                    'code': 400,
                    'message': '连接客户端失败，请检查路径是否正确',
                    'data': None
                })
        except Exception as e:
            logger.error(f"连接客户端时发生错误: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'连接失败: {str(e)}',
                'data': None
            })

    def login(self):
        """登录客户端"""
        try:
            data = request.get_json() or {}

            # 验证必填参数
            required_fields = ['user', 'password', 'comm_password']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f'缺少必填参数: {field}',
                        'data': None
                    })

            trader = HTClientTrader()
            success = trader.login(
                user=data['user'],
                password=data['password'],
                exe_path=data.get('exe_path'),
                comm_password=data['comm_password']
            )

            if success:
                session_id = self._create_session(trader)
                logger.info(f"用户 {data['user']} 登录成功，会话ID: {session_id}")
                return jsonify({
                    'code': 200,
                    'message': '登录成功',
                    'data': {
                        'session_id': session_id,
                        'main_window_title': trader.CONFIG["TITLE"]
                    }
                })
            else:
                logger.error(f"用户 {data['user']} 登录失败")
                return jsonify({
                    'code': 401,
                    'message': '登录失败，请检查账号密码',
                    'data': None
                })
        except Exception as e:
            logger.error(f"登录时发生错误: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'登录失败: {str(e)}',
                'data': None
            })

    def exit(self):
        """退出客户端"""
        try:
            if not hasattr(g, 'valid_session') or not g.valid_session:
                return jsonify({
                    'code': 401,
                    'message': '无效的会话',
                    'data': None
                })

            # 调用交易客户端的退出方法
            g.trader.exit()

            # 移除会话
            with self.session_lock:
                if g.session_id in self.trader_sessions:
                    # 如果是自动登录会话，重置自动登录会话ID
                    if g.session_id == self.auto_login_session_id:
                        self.auto_login_session_id = None
                    del self.trader_sessions[g.session_id]

            logger.info(f"会话 {g.session_id} 已退出")
            return jsonify({
                'code': 200,
                'message': '客户端已退出',
                'data': None
            })
        except Exception as e:
            logger.error(f"退出客户端时发生错误: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'退出失败: {str(e)}',
                'data': None
            })

    # 以下方法与之前版本相同，省略实现以节省空间
    # 实际使用时需要保留这些方法的实现
    def get_balance(self):
        try:
            balance = g.trader.balance
            return jsonify({
                'code': 200,
                'message': '查询成功',
                'data': balance
            })
        except Exception as e:
            logger.error(f"获取资金余额失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    def get_position(self):
        try:
            position = g.trader.position
            return jsonify({
                'code': 200,
                'message': '查询成功',
                'data': position
            })
        except Exception as e:
            logger.error(f"获取持仓信息失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    # 其他方法的实现与之前相同...
    def get_today_entrusts(self):
        try:
            entrusts = g.trader.today_entrusts
            return jsonify({
                'code': 200,
                'message': '查询成功',
                'data': entrusts
            })
        except Exception as e:
            logger.error(f"获取当日委托失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    def get_today_trades(self):
        try:
            trades = g.trader.today_trades
            return jsonify({
                'code': 200,
                'message': '查询成功',
                'data': trades
            })
        except Exception as e:
            logger.error(f"获取当日成交失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    def get_cancel_entrusts(self):
        try:
            cancel_entrusts = g.trader.cancel_entrusts
            return jsonify({
                'code': 200,
                'message': '查询成功',
                'data': cancel_entrusts
            })
        except Exception as e:
            logger.error(f"获取可撤单信息失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            })

    def buy(self):
        try:
            data = request.get_json() or {}

            required_fields = ['security', 'price', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f'缺少必填参数: {field}',
                        'data': None
                    })

            result = g.trader.buy(
                security=data['security'],
                price=float(data['price']),
                amount=int(data['amount'])
            )

            code = 200 if result.get('message') == 'success' else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '买入操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"买入股票失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'买入失败: {str(e)}',
                'data': None
            })

    # 其他交易方法的实现...
    def sell(self):
        try:
            data = request.get_json() or {}

            required_fields = ['security', 'price', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f'缺少必填参数: {field}',
                        'data': None
                    })

            result = g.trader.sell(
                security=data['security'],
                price=float(data['price']),
                amount=int(data['amount'])
            )

            code = 200 if result.get('message') == 'success' else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '卖出操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"卖出股票失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'卖出失败: {str(e)}',
                'data': None
            })

    def market_buy(self):
        """市价买入股票"""
        try:
            data = request.get_json() or {}

            # 验证必填参数
            required_fields = ['security', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f'缺少必填参数: {field}',
                        'data': None
                    })

            result = g.trader.market_buy(
                security=data['security'],
                amount=int(data['amount']),
                ttype=data.get('ttype')
            )

            code = 200 if result.get('message') == 'success' else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '市价买入操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"市价买入股票失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'市价买入失败: {str(e)}',
                'data': None
            })

    def market_sell(self):
        """市价卖出股票"""
        try:
            data = request.get_json() or {}

            # 验证必填参数
            required_fields = ['security', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f'缺少必填参数: {field}',
                        'data': None
                    })

            result = g.trader.market_sell(
                security=data['security'],
                amount=int(data['amount']),
                ttype=data.get('ttype')
            )

            code = 200 if result.get('message') == 'success' else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '市价卖出操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"市价卖出股票失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'市价卖出失败: {str(e)}',
                'data': None
            })

    def cancel_entrust(self):
        """撤销指定委托"""
        try:
            data = request.get_json() or {}

            if 'entrust_no' not in data:
                return jsonify({
                    'code': 400,
                    'message': '缺少必填参数: entrust_no',
                    'data': None
                })

            result = g.trader.cancel_entrust(data['entrust_no'])

            code = 200 if '成功' in result.get('message', '') else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '撤单操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"撤销委托失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'撤单失败: {str(e)}',
                'data': None
            })

    def cancel_all_entrusts(self):
        """撤销所有委托"""
        try:
            result = g.trader.cancel_all_entrusts()

            code = 200 if '成功' in result.get('message', '') else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '全部撤单操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"全部撤单失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'全部撤单失败: {str(e)}',
                'data': None
            })

    def auto_ipo(self):
        """自动申购新股"""
        try:
            result = g.trader.auto_ipo()

            code = 200 if '成功' in result.get('message', '') or '完成' in result.get('message', '') else 400
            return jsonify({
                'code': code,
                'message': result.get('message', '新股申购操作完成'),
                'data': result
            })
        except Exception as e:
            logger.error(f"自动申购新股失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'新股申购失败: {str(e)}',
                'data': None
            })

    def refresh(self):
        """刷新数据"""
        try:
            g.trader.refresh()
            return jsonify({
                'code': 200,
                'message': '数据刷新完成',
                'data': None
            })
        except Exception as e:
            logger.error(f"刷新数据失败: {str(e)}", exc_info=True)
            return jsonify({
                'code': 500,
                'message': f'刷新失败: {str(e)}',
                'data': None
            })


    def run(self):
        """启动Flask服务"""
        # 检查自动登录是否成功
        if self.auto_login_session_id:
            logger.info(f"自动登录成功，启动交易客户端HTTP服务，地址: http://{self.host}:{self.port}")
            logger.info(f"自动登录会话ID: {self.auto_login_session_id}")
        else:
            logger.warning(f"自动登录失败，仍将启动HTTP服务，地址: http://{self.host}:{self.port}")

        self.app.run(host=self.host, port=self.port, debug=self.debug, threaded=True)


if __name__ == '__main__':
    # 创建并启动服务，指定配置文件路径
    server = AutoLoginTraderServer(
        host='0.0.0.0',
        port=5000,
        debug=True,
        config_path="config.ini"  # 配置文件路径
    )
    server.run()
