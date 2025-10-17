# -*- coding: utf-8 -*-
import abc
import functools
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional
import traceback
from pywinauto import findwindows, timings, Application
from pywinauto.keyboard import send_keys
from pywinauto.controls.uia_controls import ComboBoxWrapper

from utils.file_manager import  FileManager
import configparser

# 确保只在Windows系统上运行
if not sys.platform.startswith("win"):
    raise RuntimeError("此代码只能在Windows系统上运行")

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IClientTrader(abc.ABC):
    """客户端交易器接口定义"""

    @property
    @abc.abstractmethod
    def app(self):
        pass

    @property
    @abc.abstractmethod
    def main(self):
        pass

    @abc.abstractmethod
    def wait(self, seconds: float):
        pass

    @abc.abstractmethod
    def refresh(self):
        pass

    @abc.abstractmethod
    def is_exist_pop_dialog(self):
        pass


class HTClientTrader(IClientTrader):
    """华泰证券客户端交易器实现，使用最新配置信息"""

    # 根据提供的配置信息更新控件ID和参数
    CONFIG = {
        "DEFAULT_EXE_PATH": "",
        "TITLE": "网上股票交易系统5.0",
        "LOGIN_WINDOW_TITLE": "网上股票交易系统5.0 - 登录",

        # 交易所类型控件ID（深圳A股、上海A股）
        "TRADE_STOCK_EXCHANGE_CONTROL_ID": 1003,

        # 撤销界面上的全部撤销按钮
        "TRADE_CANCEL_ALL_ENTRUST_CONTROL_ID": 30001,

        # 交易相关控件ID
        "TRADE_SECURITY_CONTROL_ID": 1032,  # 证券代码输入框
        "TRADE_PRICE_CONTROL_ID": 1033,  # 价格输入框
        "TRADE_AMOUNT_CONTROL_ID": 1034,  # 数量输入框
        "TRADE_SUBMIT_CONTROL_ID": 1006,  # 提交按钮
        "TRADE_MARKET_TYPE_CONTROL_ID": 1541,  # 市价类型下拉框

        # 通用表格控件ID
        "COMMON_GRID_CONTROL_ID": 1047,

        # 表格相关参数
        "COMMON_GRID_LEFT_MARGIN": 10,
        "COMMON_GRID_FIRST_ROW_HEIGHT": 30,
        "COMMON_GRID_ROW_HEIGHT": 16,

        # 菜单路径
        "BALANCE_MENU_PATH": ["查询[F4]", "资金股票"],
        "POSITION_MENU_PATH": ["查询[F4]", "资金股票"],
        "TODAY_ENTRUSTS_MENU_PATH": ["查询[F4]", "当日委托"],
        "TODAY_TRADES_MENU_PATH": ["查询[F4]", "当日成交"],

        # 资金信息控件ID
        "BALANCE_CONTROL_ID_GROUP": {
            "资金余额": 1012,
            "可用金额": 1016,
            "可取金额": 1017,
            "股票市值": 1014,
            "总资产": 1015,
        },

        # 对话框相关
        "POP_DIALOD_TITLE_CONTROL_ID": 1365,

        # 表格数据类型
        "GRID_DTYPE": {
            "操作日期": str,
            "委托编号": str,
            "申请编号": str,
            "合同编号": str,
            "证券代码": str,
            "股东代码": str,
            "资金帐号": str,
            "资金帐户": str,
            "发生日期": str,
        },

        # 撤单相关
        "CANCEL_ENTRUST_ENTRUST_FIELD": "委托编号",
        "CANCEL_ENTRUST_GRID_LEFT_MARGIN": 50,
        "CANCEL_ENTRUST_GRID_FIRST_ROW_HEIGHT": 30,
        "CANCEL_ENTRUST_GRID_ROW_HEIGHT": 16,

        # 新股申购
        "AUTO_IPO_SELECT_ALL_BUTTON_CONTROL_ID": 1098,
        "AUTO_IPO_BUTTON_CONTROL_ID": 1006,
        "AUTO_IPO_MENU_PATH": ["新股申购", "批量新股申购"],
        "AUTO_IPO_NUMBER": '申购数量'
    }

    _editor_need_type_keys = False
    _connected = False

    def __init__(self):
        self._app = None
        self._main = None
        self._toolbar = None

    @property
    def app(self):
        return self._app

    @property
    def main(self):
        return self._main

    @property
    def connected(self):
        return self._connected

    def enable_type_keys_for_editor(self):
        self._editor_need_type_keys = True

    def connect(self, exe_path=None) -> bool:
        """直接连接已登录的客户端"""
        if not exe_path:
            exe_path = self.CONFIG["DEFAULT_EXE_PATH"] or r'C:\htzqzyb2\xiadan.exe'

        # 增强路径检查
        if not os.path.exists(exe_path):
            logger.error(f"客户端路径不存在: {exe_path}")
            # 尝试常见路径
            common_paths = [
                r'C:\htwt\xiadan.exe',
                r'C:\htzqzyb2\xiadan.exe',
                r'C:\Program Files\htzqzyb2\xiadan.exe',
                r'C:\Program Files (x86)\htzqzyb2\xiadan.exe',
                r'C:\华泰证券\xiadan.exe'
            ]
            for path in common_paths:
                if os.path.exists(path):
                    exe_path = path
                    logger.info(f"自动找到客户端路径: {exe_path}")
                    break
            else:
                return False

        try:
            # 尝试两种backend
            for backend in ["win32", "uia"]:
                try:
                    self._app = Application(backend=backend).connect(path=exe_path, timeout=10)
                    logger.info(f"使用{backend} backend成功连接到客户端")
                    break
                except:
                    continue

            if not self._app:
                logger.error("两种backend都无法连接到客户端")
                return False

            self._close_prompt_windows()
            self._main = self._app.window(title=self.CONFIG["TITLE"])

            if not self._main.exists():
                logger.error("未找到华泰证券主窗口")
                return False

            self._main.wait("exists enabled visible ready", timeout=30)
            self._init_toolbar()
            self._connected = True
            logger.info(f"成功连接到客户端: {exe_path}")
            return True
        except Exception as e:
            logger.error(f"连接客户端失败: {str(e)}", exc_info=True)
            self._connected = False
            return False

    def get_listbox_info(self, listbox):
        """获取ListBox控件的详细信息"""
        try:
            # 基本信息
            info = {
                "窗口标题": listbox.parent().window_text(),
                "控件类名": listbox.class_name(),
                "控件ID": listbox.control_id(),
                "位置与大小": listbox.rectangle(),
                "可见性": listbox.is_visible(),
                "启用状态": listbox.is_enabled(),
                "项数量": len(listbox.items()),
                "选中项数量": len(listbox.selected_items()) if hasattr(listbox, 'selected_items') else 0
            }

            # 尝试获取前5项内容（避免内容过多）
            items = listbox.items()
            info["部分项内容"] = items[:5] + (["..."] if len(items) > 5 else [])

            return info
        except Exception as e:
            return {"错误": f"获取信息失败: {str(e)}"}


    def get_control_info(self, listbox):
        """获取control控件的详细信息"""
        try:
            # 基本信息
            info = {
                "窗口标题": listbox.parent().window_text(),
                "控件类名": listbox.class_name(),
                "控件ID": listbox.control_id(),
                "位置与大小": listbox.rectangle(),
                "可见性": listbox.is_visible(),
                "启用状态": listbox.is_enabled(),
            }

            print(info)

            return info
        except Exception as e:
            return {"错误": f"获取信息失败: {str(e)}"}

    def login(self, user: str, password: str, exe_path: str, comm_password: Optional[str] = None) -> bool:
        """登录华泰证券客户端，使用灵活的控件识别方式"""
        # 华泰证券要求必须提供通讯密码
        if comm_password is None:
            logger.error("华泰证券登录必须提供通讯密码")
            return False

        # 验证客户端路径
        if not exe_path or not os.path.exists(exe_path):
            logger.error(f"客户端路径不存在: {exe_path}")
            # 尝试默认路径和常见路径
            default_path = self.CONFIG["DEFAULT_EXE_PATH"]
            if default_path and os.path.exists(default_path):
                exe_path = default_path
                logger.info(f"使用默认路径: {exe_path}")
            else:
                common_paths = [
                    r'C:\htwt\xiadan.exe',
                    r'C:\htzqzyb2\xiadan.exe',
                    r'C:\Program Files\htzqzyb2\xiadan.exe',
                    r'C:\Program Files (x86)\htzqzyb2\xiadan.exe',
                    r'C:\华泰证券\xiadan.exe'
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        exe_path = path
                        logger.info(f"自动找到客户端路径: {exe_path}")
                        break
                else:
                    return False

        # 重置状态
        self._app = None
        self._main = None
        self._connected = False

        try:
            run_exe_path = self._run_exe_path(exe_path)
            connected = False

            # 先尝试连接已运行的客户端
            for backend in ["win32", "uia"]:
                try:
                    self._app = Application(backend=backend).connect(path=run_exe_path, timeout=5)
                    logger.info(f"使用{backend} backend连接到已运行的客户端")
                    connected = True
                    break
                except Exception as e:
                    logger.debug(f"使用{backend} backend连接已运行客户端失败: {str(e)}")

            if not connected:
                # 没有运行的客户端，启动新的
                logger.info(f"启动客户端: {exe_path}")
                # 尝试两种backend启动
                for backend in ["win32", "uia"]:
                    try:
                        self._app = Application(backend=backend).start(exe_path)
                        logger.info(f"使用{backend} backend启动客户端成功")
                        break
                    except Exception as e:
                        logger.debug(f"使用{backend} backend启动客户端失败: {str(e)}")

                if not self._app:
                    logger.error("两种backend都无法启动客户端")
                    return False

                # 等待登录窗口出现
                logger.info("等待登录窗口出现...")
                login_window = None
                start_time = time.time()
                timeout = 30  # 30秒超时

                while time.time() - start_time < timeout:
                    try:
                        # 尝试通过标题找到登录窗口
                        login_window = self._app.window(title_re=".*登录.*")
                        if login_window.exists():
                            logger.info("找到登录窗口")
                            break
                    except Exception as e:
                        logger.debug(f"查找登录窗口失败: {str(e)}")

                    time.sleep(1)

                if not login_window or not login_window.exists():
                    logger.error("超时未找到登录窗口")
                    return False


                # 等待登录窗口就绪
                login_window.wait("ready", timeout=10)

                # 灵活查找输入框
                logger.info("查找登录输入框...")

                user_edit = login_window.Edit1
                pwd_edit = login_window.Edit2

                #
                # user_edits = login_window.Edit1
                #
                # print( self.get_control_info( user_edits ))
                #
                # # 查找用户名/账号输入框
                # user_edits = []
                # for title in ["客户号", "用户名", "资金账号"]:
                #     try:
                #         user_edits = login_window.Edit.children(title=title)
                #         if user_edits:
                #             break
                #     except:
                #         continue
                #
                # # 如果找不到带标题的，就按位置取第一个输入框
                # if not user_edits:
                #     try:
                #         user_edits = login_window.Edit
                #         if isinstance(user_edits, list):
                #             user_edit = user_edits[0]
                #         else:
                #             user_edit = user_edits
                #     except Exception as e:
                #         logger.error(f"无法找到用户名输入框: {str(e)}")
                #         return False
                # else:
                #     user_edit = user_edits[0]
                #
                # # 查找密码输入框
                # pwd_edits = []
                # for title in ["密码", "交易密码"]:
                #     try:
                #         pwd_edits = login_window.Edit.children(title=title)
                #         if pwd_edits:
                #             break
                #     except:
                #         continue
                #
                # if not pwd_edits:
                #     try:
                #         edits = login_window.Edit
                #         if isinstance(edits, list) and len(edits) >= 2:
                #             pwd_edit = edits[1]
                #         else:
                #             logger.error("无法找到密码输入框")
                #             return False
                #     except Exception as e:
                #         logger.error(f"无法找到密码输入框: {str(e)}")
                #         return False
                # else:
                #     pwd_edit = pwd_edits[0]

                # # 查找通讯密码输入框
                # comm_pwd_edits = []
                # for title in ["通讯密码", "验证码"]:
                #     try:
                #         comm_pwd_edits = login_window.Edit.children(title=title)
                #         if comm_pwd_edits:
                #             break
                #     except:
                #         continue
                #
                # if not comm_pwd_edits:
                #     try:
                #         edits = login_window.Edit
                #         if isinstance(edits, list) and len(edits) >= 3:
                #             comm_pwd_edit = edits[2]
                #         else:
                #             logger.error("无法找到通讯密码输入框")
                #             return False
                #     except Exception as e:
                #         logger.error(f"无法找到通讯密码输入框: {str(e)}")
                #         return False
                # else:
                #     comm_pwd_edit = comm_pwd_edits[0]

                # 查找登录按钮
                login_button = None
                for title in ["登录", "确定", "登录(L)"]:
                    try:
                        login_button = login_window.Button.children(title=title)[0]
                        if login_button:
                            break
                    except:
                        continue

                if not login_button:
                    try:
                        buttons = login_window.Button
                        if isinstance(buttons, list):
                            login_button = buttons[0]  # 取第一个按钮
                        else:
                            login_button = buttons
                    except Exception as e:
                        logger.error(f"无法找到登录按钮: {str(e)}")
                        return False

                # # 输入登录信息
                logger.info("输入用户名...")
                user_edit.set_focus()
                user_edit.type_keys(user)
                self.wait(0.5)

                logger.info("输入密码...")
                pwd_edit.set_focus()
                pwd_edit.type_keys(password)
                self.wait(0.5)

                # logger.info("输入通讯密码...")
                # comm_pwd_edit.set_focus()
                # comm_pwd_edit.type_keys(comm_password)
                # self.wait(0.5)

                # 点击登录
                logger.info("点击登录按钮...")
                login_button.click()
                self.wait(2)

                # 等待客户端启动完成
                logger.info("等待客户端登录完成...")
                for backend in ["win32", "uia"]:
                    try:
                        self._app = Application(backend=backend).connect(path=run_exe_path, timeout=60)
                        logger.info(f"登录后使用{backend} backend连接成功")
                        break
                    except Exception as e:
                        logger.debug(f"登录后连接失败: {str(e)}")
                        time.sleep(5)


            # 获取主窗口并验证
            self._main = self._app.window(title=self.CONFIG["TITLE"])
            if not self._main.exists():
                # 尝试通过标题模糊匹配
                self._main = self._app.window(title_re=".*网上证券.*")
                # 打印窗口标题以确认
                print(f"找到窗口: {self._main.window_text()}")

            for i in range(0,5):
                try:
                    self._main.wait("exists enabled visible ready", timeout=30)
                except Exception as e :
                    print(f"exists enabled visible {e}")
                    traceback.print_exc()

                # 关闭登录后可能出现的提示窗口
                self._close_prompt_windows()
                time.sleep(5)

            # 关闭登录后可能出现的提示窗口
            self._close_prompt_windows()
            self._init_toolbar()
            self._connected = True
            logger.info("登录成功")
            return True

        except Exception as e:
            logger.error(f"登录验证失败: {str(e)}", exc_info=True)
            self._connected = False
            return False

    @property
    def balance(self) -> Dict[str, float]:
        """获取资金余额信息"""
        if not self._connected:
            logger.error("未连接到客户端")
            return {}

        self._switch_left_menus(self.CONFIG["BALANCE_MENU_PATH"])
        return self._get_balance_from_statics()

    @property
    def position(self) -> List[Dict]:
        """获取持仓信息"""
        if not self._connected:
            logger.error("未连接到客户端")
            return []

        self._switch_left_menus(self.CONFIG["POSITION_MENU_PATH"])
        return self._get_grid_data(self.CONFIG["COMMON_GRID_CONTROL_ID"])

    @property
    def today_entrusts(self) -> List[Dict]:
        """获取当日委托信息"""
        if not self._connected:
            logger.error("未连接到客户端")
            return []

        self._switch_left_menus(self.CONFIG["TODAY_ENTRUSTS_MENU_PATH"])
        return self._get_grid_data(self.CONFIG["COMMON_GRID_CONTROL_ID"])

    @property
    def today_trades(self) -> List[Dict]:
        """获取当日成交信息"""
        if not self._connected:
            logger.error("未连接到客户端")
            return []

        self._switch_left_menus(self.CONFIG["TODAY_TRADES_MENU_PATH"])
        return self._get_grid_data(self.CONFIG["COMMON_GRID_CONTROL_ID"])

    @property
    def cancel_entrusts(self) -> List[Dict]:
        """获取可撤单信息"""
        if not self._connected:
            logger.error("未连接到客户端")
            return []

        self.refresh()
        self._switch_left_menus(["撤单[F3]"])
        return self._get_grid_data(self.CONFIG["COMMON_GRID_CONTROL_ID"])

    def cancel_entrust(self, entrust_no: str) -> Dict[str, str]:
        """撤销指定委托单（使用合同编号）"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self.refresh()
        for i, entrust in enumerate(self.cancel_entrusts):

            _en_no = entrust.get(self.CONFIG["CANCEL_ENTRUST_ENTRUST_FIELD"])
            print(f"entrust_no={_en_no}")

            if _en_no == int(entrust_no):
                self._cancel_entrust_by_double_click(i+1)
                return self._handle_pop_dialogs()
        return {"message": "委托单状态错误不能撤单, 该委托单可能已经成交或者已撤"}

    def cancel_all_entrusts(self) -> Dict[str, str]:
        """撤销所有可撤委托单"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self.refresh()
        self._switch_left_menus(["撤单[F3]"])

        try:
            self._app.top_window().child_window(
                control_id=self.CONFIG["TRADE_CANCEL_ALL_ENTRUST_CONTROL_ID"],
                class_name="Button",
                title_re="""全撤.*"""
            ).click()
            self.wait(0.2)

            if self.is_exist_pop_dialog():
                w = self._app.top_window()
                if w is not None and "是(Y)" in w.window_text():
                    w["是(Y)"].click()
                    self.wait(0.2)

            self.close_pop_dialog()
            return {"message": "全部撤单操作已提交"}
        except Exception as e:
            logger.error(f"全部撤单失败: {str(e)}")
            return {"message": f"全部撤单失败: {str(e)}"}

    def buy(self, security: str, price: float, amount: int) -> Dict[str, str]:
        """买入股票"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self._switch_left_menus(["买入[F1]"])
        return self._trade(security, price, amount)

    def sell(self, security: str, price: float, amount: int) -> Dict[str, str]:
        """卖出股票"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self._switch_left_menus(["卖出[F2]"])
        return self._trade(security, price, amount)

    def market_buy(self, security: str, amount: int, ttype: Optional[str] = None) -> Dict[str, str]:
        """市价买入"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self._switch_left_menus(["市价委托", "买入"])
        return self._market_trade(security, amount, ttype)

    def market_sell(self, security: str, amount: int, ttype: Optional[str] = None) -> Dict[str, str]:
        """市价卖出"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        self._switch_left_menus(["市价委托", "卖出"])
        return self._market_trade(security, amount, ttype)

    def auto_ipo(self) -> Dict[str, str]:
        """自动申购新股（批量新股申购）"""
        if not self._connected:
            return {"message": "未连接到客户端"}

        try:
            self._switch_left_menus(self.CONFIG["AUTO_IPO_MENU_PATH"])

            stock_list = self._get_grid_data(self.CONFIG["COMMON_GRID_CONTROL_ID"])

            if len(stock_list) == 0:
                return {"message": "今日无新股"}

            invalid_list_idx = [
                i for i, v in enumerate(stock_list)
                if v.get(self.CONFIG["AUTO_IPO_NUMBER"], 0) <= 0
            ]

            if len(stock_list) == len(invalid_list_idx):
                return {"message": "没有发现可以申购的新股"}

            self._click(self.CONFIG["AUTO_IPO_SELECT_ALL_BUTTON_CONTROL_ID"])
            self.wait(0.1)

            for row in invalid_list_idx:
                self._click_grid_by_row(row)
            self.wait(0.1)

            self._click(self.CONFIG["AUTO_IPO_BUTTON_CONTROL_ID"])
            self.wait(0.1)

            return self._handle_pop_dialogs()
        except Exception as e:
            logger.error(f"自动申购新股失败: {str(e)}")
            return {"message": f"自动申购失败: {str(e)}"}

    def refresh(self):
        """刷新数据"""
        if self._main:
            self._main.type_keys('{F5}')
            self.wait(0.5)

    def wait(self, seconds: float):
        """等待指定秒数"""
        time.sleep(seconds)

    def exit(self):
        """退出客户端"""
        if self._app:
            try:
                self._app.kill()
                self._connected = False
                logger.info("客户端已退出")
            except Exception as e:
                logger.error(f"退出客户端失败: {str(e)}")

    def is_exist_pop_dialog(self) -> bool:
        """检查是否存在弹出对话框"""
        self.wait(0.5)
        try:
            return self._main.wrapper_object() != self._app.top_window().wrapper_object()
        except (findwindows.ElementNotFoundError, timings.TimeoutError, RuntimeError) as ex:
            logger.exception("检查弹出对话框超时")
            return False

    def close_pop_dialog(self):
        """关闭弹出对话框"""
        try:
            if self._main.wrapper_object() != self._app.top_window().wrapper_object():
                w = self._app.top_window()
                if w is not None:
                    w.close()
                    self.wait(0.2)
        except (findwindows.ElementNotFoundError, timings.TimeoutError, RuntimeError) as ex:
            logger.warning(f"关闭弹出对话框失败: {str(ex)}")

    # 内部辅助方法
    def _init_toolbar(self):
        """初始化工具栏"""
        try:
            self._toolbar = self._main.child_window(class_name="ToolbarWindow32")
        except Exception as e:
            logger.warning(f"初始化工具栏失败: {str(e)}")

    def _get_balance_from_statics(self) -> Dict[str, float]:
        """从静态控件获取资金信息（使用新的资金控件ID）"""
        result = {}
        for key, control_id in self.CONFIG["BALANCE_CONTROL_ID_GROUP"].items():
            try:
                value_text = self._main.child_window(
                    control_id=control_id, class_name="Static"
                ).window_text()
                value_text = re.sub(r'[^\d.]', '', value_text)
                result[key] = float(value_text) if value_text else 0.0
            except Exception as e:
                logger.warning(f"获取资金信息 {key} 失败: {str(e)}")
                result[key] = 0.0
                traceback.print_exc()

        return result

    def _get_grid_data(self, control_id: int) -> List[Dict]:
        """获取表格数据（使用新的表格控件ID和参数）"""
        # try:
        #     grid = self._main.child_window(control_id=control_id, class_name="CVirtualGridCtrl")
        #
        #     grid.click(coords=(10, 10))
        #     send_keys('^a')  # Ctrl+A
        #     self.wait(0.2)
        #
        #     # send_keys('^c')  # Ctrl+C
        #     # self.wait(0.5)
        #
        #     send_keys('^s')  # Ctrl+C
        #     self.wait(0.5)
        #
        #     data = self._get_clipboard_text()
        #     if not data:
        #         return []
        #
        #     lines = [line.strip() for line in data.split('\r\n') if line.strip()]
        #     if len(lines) < 2:
        #         return []
        #
        #     headers = [h.strip() for h in re.split(r'\t+', lines[0])]
        #     result = []
        #
        #     for line in lines[1:]:
        #         values = [v.strip() for v in re.split(r'\t+', line)]
        #         row = {}
        #         # 应用数据类型转换
        #         for i, header in enumerate(headers):
        #             if i < len(values):
        #                 dtype = self.CONFIG["GRID_DTYPE"].get(header, str)
        #                 try:
        #                     row[header] = dtype(values[i])
        #                 except:
        #                     row[header] = values[i]
        #         result.append(row)
        #
        #     return result
        # except Exception as e:
        #     logger.error(f"获取表格数据失败: {str(e)}")
        #     return []

        """通过 Ctrl+S 保存表格为 Excel，再读取文件获取数据"""
        try:
            # 1. 聚焦表格控件
            grid = self._main.child_window(control_id=control_id, class_name="CVirtualGridCtrl")
            grid.click(coords=(10, 10))
            self.wait(0.5)

            # 2. 发送 Ctrl+S 触发“另存为”
            send_keys('^s')
            self.wait(1)  # 等待对话框弹出

            # 3. 处理“另存为”对话框
            save_dialog = self._app.window(title="另存为")
            save_dialog.wait("visible", timeout=10)  # 等待对话框可见
            #
            # # 3.1 选择保存位置（示例：桌面）
            # desktop_item = save_dialog.child_window(title="桌面", control_type="ListItem")
            # desktop_item.click_input()
            # self.wait(2.5)

            # 3.2 设置文件名
            file_name = "ht_table.xls"
            #file_name_edit = save_dialog.child_window(title="文件名:", control_type="Edit")
            #file_name_edit = save_dialog.child_window(control_id=999, control_type="Edit")

            fm = FileManager()
            # 3.3 拼接保存路径
            save_path = os.path.join(os.path.expanduser("~"), "Documents", file_name)

            if fm.file_exists(save_path):
                fm.delete_file( save_path )


            # 筛选所有 Edit 控件
            edit_controls = [ctrl for ctrl in save_dialog.children() if ctrl.class_name() == "Edit"]

            # 取第一个 Edit 控件
            if edit_controls:
                edit_ctrl = edit_controls[0]
                edit_ctrl.type_keys(file_name)

            # file_name_edit = save_dialog.child_window(class_name="Edit", found_index=1)
            # file_name_edit.set_edit_text(file_name)
            self.wait(.5)


            # 筛选所有 Edit 控件
            button_controls = [ctrl for ctrl in save_dialog.children() if ctrl.class_name() == "Button"]

            # 遍历所有子控件，筛选出按钮
            for ctrl in button_controls:
                # 检查控件是否为按钮类型（不同应用可能有不同的类名）
                if "button" in ctrl.class_name().lower():
                    try:
                        # # 收集按钮信息
                        # button_info = {
                        #     "标题": ctrl.window_text(),
                        #     "类名": ctrl.class_name(),
                        #     "控件ID": ctrl.control_id(),
                        #     "自动化ID": ctrl.automation_id() if hasattr(ctrl, 'automation_id') else "N/A",
                        #     "是否可见": ctrl.is_visible(),
                        #     "是否启用": ctrl.is_enabled()
                        # }

                        if '保存' in ctrl.window_text():
                            ctrl.click()

                        # # 打印按钮信息
                        # print(f"按钮标题: {button_info['标题']}")
                        # print(f"类名: {button_info['类名']}")
                        # print(f"控件ID: {button_info['控件ID']}")
                        # print(f"自动化ID: {button_info['自动化ID']}")
                        # print(
                        #     f"状态: {'可见' if button_info['是否可见'] else '隐藏'} / {'启用' if button_info['是否启用'] else '禁用'}")
                        # print("-" * 50)

                    except Exception as e:
                        print(f"获取控件信息时出错: {str(e)}")
                        print("-" * 50)


            for i in range(0,5):
                if fm.file_exists(save_path):
                    break
                self.wait(.5)


            print(f"save_path={save_path}")

            # # 4. 点击“保存”按钮
            # save_button = save_dialog.child_window(title="保存(S)", control_type="Button")
            # if save_button.exists():
            #     save_button.click()
            #
            # # 3.4 点击“保存”按钮
            # save_button = save_dialog.child_window(title="保存(&S)", control_type="Button")
            # if save_button.exists():
            #     save_button.click_input()

            self.wait(2)  # 等待保存完成

            # 4. 读取 Excel 文件
            if os.path.exists(save_path):


                # # 根据文件格式选择引擎
                # if save_path.endswith('.xlsx'):
                #     df = pd.read_excel(save_path, engine='openpyxl')
                # elif save_path.endswith('.xls'):
                #     df = pd.read_excel(save_path, engine='xlrd')
                # else:
                #     raise ValueError("文件不是Excel格式")
                #df = pd.read_excel(save_path)
                text_data = fm.read_txt_file( save_path, encoding='gbk' )
                data = self.text_to_list_dict( text_data )
                # （可选）删除临时文件
                os.remove(save_path)
                logger.info(f"已删除临时文件: {save_path}")

                return data
            else:
                logger.error(f"保存的文件不存在: {save_path}")
                return []

        except Exception as e:
            logger.error(f"获取表格数据失败: {str(e)}", exc_info=True)
            return []

    def text_to_list_dict(self,text):
        # 按行分割文本
        lines = text.strip().split('\n')

        # 如果没有数据，返回空列表
        if len(lines) < 2:
            return []

        # 提取表头作为字典的键
        headers = [header.strip() for header in lines[0].split('\t')]
        headers = list(filter(None, headers))
        result = []
        # 处理每一行数据
        for line in lines[1:]:
            # 分割每行数据
            values = line.split('\t')

            # 创建字典并添加到结果列表
            item = {}
            for i, header in enumerate(headers):
                # 尝试将数值转换为适当的类型
                value = values[i].strip()
                try:
                    # 先尝试转换为整数
                    item[header] = int(value)
                except ValueError:
                    try:
                        # 再尝试转换为浮点数
                        item[header] = float(value)
                    except ValueError:
                        # 无法转换则保持字符串
                        item[header] = value

            result.append(item)

        return result

    def _trade(self, security: str, price: float, amount: int) -> Dict[str, str]:
        """执行交易（使用新的交易控件ID）"""
        try:
            self._set_trade_params(security, price, amount)
            self._submit_trade()
            return self._handle_pop_dialogs()
        except Exception as e:
            logger.error(f"交易执行失败: {str(e)}")
            return {"message": f"交易失败: {str(e)}"}

    def _market_trade(self, security: str, amount: int, ttype: Optional[str] = None) -> Dict[str, str]:
        """执行市价交易"""
        try:
            code = security[-6:]
            self._type_edit_control_keys(self.CONFIG["TRADE_SECURITY_CONTROL_ID"], code)

            if ttype is not None:
                retry = 0
                retry_max = 10
                while retry < retry_max:
                    try:
                        self._set_market_trade_type(ttype)
                        break
                    except:
                        retry += 1
                        self.wait(0.1)
                if retry >= retry_max:
                    return {"message": f"设置市价类型 {ttype} 失败"}

            self._type_edit_control_keys(self.CONFIG["TRADE_AMOUNT_CONTROL_ID"], str(int(amount)))
            self._submit_trade()

            return self._handle_pop_dialogs()
        except Exception as e:
            logger.error(f"市价交易失败: {str(e)}")
            return {"message": f"交易失败: {str(e)}"}

    def _set_trade_params(self, security: str, price: float, amount: int):
        """设置交易参数（使用新的控件ID）"""
        code = security[-6:]

        self._type_edit_control_keys(self.CONFIG["TRADE_SECURITY_CONTROL_ID"], code)
        self.wait(0.1)

        # 设置交易所类型（使用新的控件ID）
        if security.lower().startswith("sz"):
            self._set_stock_exchange_type("深圳Ａ股")
        elif security.lower().startswith("sh"):
            self._set_stock_exchange_type("上海Ａ股")

        self.wait(0.1)

        rounded_price = round(price, 3)
        self._type_edit_control_keys(self.CONFIG["TRADE_PRICE_CONTROL_ID"], str(rounded_price))
        self._type_edit_control_keys(self.CONFIG["TRADE_AMOUNT_CONTROL_ID"], str(int(amount)))

    def _set_market_trade_type(self, ttype: str):
        """设置市价交易类型（使用新的控件ID）"""
        try:
            combo_box = ComboBoxWrapper(self._main.child_window(
                control_id=self.CONFIG["TRADE_MARKET_TYPE_CONTROL_ID"],
                class_name="ComboBox"
            ).element_info)

            items = combo_box.texts()
            for i, item in enumerate(items):
                if i == 0:
                    continue
                if ttype in item:
                    combo_box.select(i - 1)
                    return
            raise ValueError(f"未找到市价类型: {ttype}")
        except Exception as e:
            logger.error(f"设置市价类型失败: {str(e)}")
            raise

    def _set_stock_exchange_type(self, ttype: str):
        """设置股票市场类型（使用新的控件ID）"""
        try:
            combo_box = ComboBoxWrapper(self._main.child_window(
                control_id=self.CONFIG["TRADE_STOCK_EXCHANGE_CONTROL_ID"],
                class_name="ComboBox"
            ).element_info)

            items = combo_box.texts()
            for i, item in enumerate(items):
                if i == 0:
                    continue
                if ttype in item:
                    combo_box.select(i - 1)
                    return
            raise ValueError(f"未找到市场类型: {ttype}")
        except Exception as e:
            logger.error(f"设置市场类型失败: {str(e)}")
            raise

    def _submit_trade(self):
        """提交交易（使用新的提交按钮ID）"""
        self.wait(0.2)
        self._main.child_window(
            control_id=self.CONFIG["TRADE_SUBMIT_CONTROL_ID"], class_name="Button"
        ).click()

    def _click(self, control_id: int):
        """点击指定控件"""
        self._app.top_window().child_window(
            control_id=control_id, class_name="Button"
        ).click()

    def _click_grid_by_row(self, row: int):
        """点击表格指定行（使用新的表格参数）"""
        x = self.CONFIG["COMMON_GRID_LEFT_MARGIN"]
        y = (
                self.CONFIG["COMMON_GRID_FIRST_ROW_HEIGHT"]
                + self.CONFIG["COMMON_GRID_ROW_HEIGHT"] * row
        )
        self._app.top_window().child_window(
            control_id=self.CONFIG["COMMON_GRID_CONTROL_ID"],
            class_name="CVirtualGridCtrl",
        ).click(coords=(x, y))

    def _type_edit_control_keys(self, control_id: int, text: str):
        """向编辑控件输入文本"""
        try:
            edit_control = self._main.child_window(control_id=control_id, class_name="Edit")
            self._type_edit(edit_control, text)
        except Exception as e:
            logger.error(f"向控件输入文本失败: {str(e)}")
            raise

    def _type_edit(self, edit_control, text: str):
        """向编辑控件输入文本"""
        if not self._editor_need_type_keys:
            try:
                edit_control.set_edit_text(text)
            except:
                edit_control.click()
                send_keys('^a')
                send_keys(text)
        else:
            edit_control.click()
            send_keys('^a')
            send_keys(text)

    def _switch_left_menus(self, path: List[str], sleep: float = 0.2):
        """切换左侧菜单（使用新的菜单路径配置）"""
        try:
            self.close_pop_dialog()
            menu_handle = self._get_left_menus_handle()
            menu_item = menu_handle.get_item(path)
            menu_item.select()
            self._main.type_keys('{F5}')
            self.wait(sleep)
        except Exception as e:
            logger.error(f"切换左侧菜单 {path} 失败: {str(e)}")
            if path and len(path) > 0 and '[' in path[0] and ']' in path[0]:
                shortcut = path[0].split('[')[1].split(']')[0]
                try:
                    self._main.type_keys(f"{{{shortcut}}}")
                    self.wait(sleep)
                except:
                    pass

    @functools.lru_cache()
    def _get_left_menus_handle(self):
        """获取左侧菜单句柄"""
        count = 3
        while count > 0:
            try:
                handle = self._main.child_window(control_id=129, class_name="SysTreeView32")
                handle.wait("ready", 2)
                return handle
            except Exception as ex:
                logger.warning(f"尝试获取左侧菜单时发生错误: {str(ex)}")
                count -= 1
                self.wait(1)
        raise Exception("无法获取左侧菜单句柄")

    def _cancel_entrust_by_double_click(self, row: int):
        """通过双击撤销指定行的委托（使用新的撤单表格参数）"""
        x = self.CONFIG["CANCEL_ENTRUST_GRID_LEFT_MARGIN"]
        y = (
                self.CONFIG["CANCEL_ENTRUST_GRID_FIRST_ROW_HEIGHT"]
                + self.CONFIG["CANCEL_ENTRUST_GRID_ROW_HEIGHT"] * row
        )
        self._app.top_window().child_window(
            control_id=self.CONFIG["COMMON_GRID_CONTROL_ID"],
            class_name="CVirtualGridCtrl",
        ).double_click(coords=(x, y))

    def _handle_pop_dialogs(self) -> Dict[str, str]:
        """处理弹出对话框（使用新的对话框控件ID）"""
        self.wait(0.5)
        if not self.is_exist_pop_dialog():
            return {"message": "success"}

        try:
            dialog = self._app.top_window()
            title = dialog.window_text()

            static_texts = dialog.children(class_name="Static")
            message = "\n".join([t.window_text() for t in static_texts if t.window_text()])

            ok_buttons = []
            for btn_text in ["确定", "是(&Y)", "OK", "确认"]:
                try:
                    ok_buttons = dialog.children(title=btn_text, class_name="Button")
                    if ok_buttons:
                        break
                except:
                    continue

            if ok_buttons:
                ok_buttons[0].click()
                self.wait(0.2)



                # 同时查找委托编号和合同编号
                entrust_match = re.search(r'(委托编号|合同编号)[:：]\s*(\w+)', message)
                if entrust_match:
                    return {
                        "message": "success",
                        "entrust_id": entrust_match.group(2)
                    }
                entrust_id = self._close_prompt_windows()
                return {"message": message if message else "success","entrust_id":entrust_id}
            else:
                dialog.close()
                return {"message": f"关闭对话框: {title}"}
        except Exception as e:
            logger.error(f"处理对话框失败: {str(e)}")
            return {"message": f"处理对话框失败: {str(e)}"}

    def _close_prompt_windows(self):
        """关闭提示窗口"""
        self.wait(1)
        if not self._app:
            return
        entrust_id = ''
        for window in self._app.windows(class_name="#32770", visible_only=True):
            title = window.window_text()
            message = ''
            try:
                static_texts = window.children(class_name="Edit")
                message = "\n".join([t.window_text() for t in static_texts if t.window_text()])

                # 同时查找委托编号和合同编号
                entrust_match = re.search(r'(委托编号|合同编号)[:：]\s*(\w+)', message)
                if entrust_match:
                    entrust_id = entrust_match.group(2)

            except Exception as e :
                print(f" exception : {e}")

            print(f"title={title} message={message}")
            if title != self.CONFIG["TITLE"] :
                logger.info(f"关闭提示窗口: {title}")
                try:
                    window.close()
                except:
                    pass
                self.wait(0.2)
        self.wait(1)

        return entrust_id

    def _get_clipboard_text(self) -> str:
        """获取剪贴板文本"""
        try:
            return self._app.clipboard.GetText()
        except Exception as e:
            logger.error(f"获取剪贴板内容失败: {str(e)}")
            return ""

    def _run_exe_path(self, exe_path: str) -> str:
        """获取实际运行的可执行文件路径"""
        return os.path.join(os.path.dirname(exe_path), "xiadan.exe")

    def _is_logged_in(self) -> bool:
        """检查是否已经登录"""
        try:
            if self._app:
                for window in self._app.windows():
                    if self.CONFIG["TITLE"] in window.window_text():
                        return True
        except:
            pass
        return False


def read_config(config_path: str) -> dict:
    """读取config.ini配置文件并返回字典"""
    config = configparser.ConfigParser()
    # 读取文件（指定utf-8编码防止中文乱码）
    config.read(config_path, encoding='utf-8')

    # 初始化结果字典
    result = {}

    # 读取 [Trader] 节
    if 'Trader' in config:
        result['exe_path'] = config.get('Trader', 'exe_path')  # 字符串

    # 读取 [Account] 节
    if 'Account' in config:
        result['user'] = config.get('Account', 'user')  # 字符串
        result['password'] = config.get('Account', 'password')  # 字符串


    return result


# 使用示例
if __name__ == "__main__":
    # 初始化交易器
    trader = HTClientTrader()

    try:
        config_data = read_config("../config.ini")



        # 登录客户端
        login_success = trader.login(
            user=config_data['user'],
            password=config_data['password'],
            exe_path=config_data['exe_path'],  # 华泰证券客户端路径
            comm_password=""
        )

        if not login_success:
            print("登录失败")
            sys.exit(1)

        # # 获取资金信息
        # balance = trader.balance
        # print("资金信息:", balance)
        #
        # # 获取持仓信息
        # positions = trader.position
        # print("持仓信息:", positions)
        # #
        # # 获取当日委托
        # today_entrusts = trader.today_entrusts
        # print("当日委托:", today_entrusts)
        #
        #
        message =  trader.buy('513630',1.561,300)
        print( message['entrust_id'],message )
        #
        message =  trader.sell('513630',1.581,300)
        print( message )
        # trader.cancel_entrust(str(339))
        # trader.cancel_entrust(str(339))
        # trader.cancel_entrust(str(340))
        # time.sleep(10)
    except Exception as e:
        print(f"操作出错: {str(e)}")
    finally:
        # 退出客户端
        # trader.exit()  # 实际使用时取消注释
        pass
