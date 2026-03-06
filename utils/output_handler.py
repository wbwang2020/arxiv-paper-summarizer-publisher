#!/usr/bin/env python3
"""
统一输出工具类
支持Logger和Debug方式的输出
确保输出可以重定向到terminal和执行输出界面
"""

import logging
from typing import Optional, Callable, Dict, Any


class OutputHandler:
    """统一输出处理器"""

    def __init__(self, module_id: str, logger: Optional[logging.Logger] = None, debug: bool = False, 
                 log_level: int = logging.INFO, enable_debug: bool = False):
        """
        初始化输出处理器

        Args:
            module_id: 模块ID，用于识别不同模块
            logger: 日志记录器实例
            debug: 是否开启调试模式
            log_level: 日志级别
            enable_debug: 是否启用调试输出
        """
        self.module_id = module_id
        self.logger = logger
        self.debug = debug
        self.log_level = log_level
        self.enable_debug = enable_debug

    def set_logger(self, logger: logging.Logger):
        """设置日志记录器"""
        self.logger = logger

    def set_debug(self, debug: bool):
        """设置调试模式"""
        self.debug = debug

    def set_log_level(self, level: int):
        """设置日志级别"""
        self.log_level = level

    def set_enable_debug(self, enable: bool):
        """设置是否启用调试输出"""
        self.enable_debug = enable

    def info(self, message: str):
        """输出信息级别消息"""
        if self.log_level <= logging.INFO:
            if self.logger:
                self.logger.info(f"[{self.module_id}] {message}")
            else:
                print(f"[{self.module_id}] {message}")

    def debug_print(self, message: str):
        """输出调试级别消息"""
        if self.enable_debug and self.log_level <= logging.DEBUG:
            if self.logger:
                self.logger.debug(f"[{self.module_id}] {message}")
            else:
                print(f"[DEBUG] [{self.module_id}] {message}")

    def warning(self, message: str):
        """输出警告级别消息"""
        if self.log_level <= logging.WARNING:
            if self.logger:
                self.logger.warning(f"[{self.module_id}] {message}")
            else:
                print(f"[警告] [{self.module_id}] {message}")

    def error(self, message: str):
        """输出错误级别消息"""
        if self.log_level <= logging.ERROR:
            if self.logger:
                self.logger.error(f"[{self.module_id}] {message}")
            else:
                print(f"[错误] [{self.module_id}] {message}")

    def critical(self, message: str):
        """输出严重错误级别消息"""
        if self.log_level <= logging.CRITICAL:
            if self.logger:
                self.logger.critical(f"[{self.module_id}] {message}")
            else:
                print(f"[严重] [{self.module_id}] {message}")

    def log(self, level: int, message: str):
        """输出指定级别的消息"""
        if self.log_level <= level:
            if self.logger:
                self.logger.log(level, f"[{self.module_id}] {message}")
            else:
                print(f"[{self.module_id}] {message}")

    def screenshot(self, path: str, screenshot_func: Optional[Callable] = None):
        """保存截图（仅在调试模式下）"""
        if self.debug and self.enable_debug and screenshot_func:
            try:
                screenshot_func(path)
                self.debug_print(f"[截图] 已保存截图: {path}")
            except Exception as e:
                self.error(f"截图失败: {e}")


_output_handlers: Dict[str, OutputHandler] = {}


def get_output_handler(module_id: str, logger: Optional[logging.Logger] = None, 
                      debug: bool = False, log_level: int = logging.INFO, 
                      enable_debug: bool = False) -> OutputHandler:
    """
    创建或获取输出处理器实例

    Args:
        module_id: 模块ID
        logger: 日志记录器实例
        debug: 是否开启调试模式
        log_level: 日志级别
        enable_debug: 是否启用调试输出

    Returns:
        OutputHandler实例
    """
    if module_id not in _output_handlers:
        _output_handlers[module_id] = OutputHandler(
            module_id, logger, debug, log_level, enable_debug
        )
    return _output_handlers[module_id]


def setup_output_handler(module_id: str, logger: logging.Logger, 
                        debug: bool = False, log_level: int = logging.INFO, 
                        enable_debug: bool = False) -> OutputHandler:
    """
    创建并设置输出处理器实例

    Args:
        module_id: 模块ID
        logger: 日志记录器实例
        debug: 是否开启调试模式
        log_level: 日志级别
        enable_debug: 是否启用调试输出

    Returns:
        OutputHandler实例
    """
    return get_output_handler(module_id, logger, debug, log_level, enable_debug)


def get_all_output_handlers() -> Dict[str, OutputHandler]:
    """
    获取所有输出处理器实例

    Returns:
        所有输出处理器实例的字典
    """
    return _output_handlers


def update_module_config(module_id: str, config: Dict[str, Any]):
    """
    更新模块的输出配置

    Args:
        module_id: 模块ID
        config: 配置字典，包含debug、log_level、enable_debug等
    """
    if module_id in _output_handlers:
        handler = _output_handlers[module_id]
        if 'debug' in config:
            handler.set_debug(config['debug'])
        if 'log_level' in config:
            handler.set_log_level(config['log_level'])
        if 'enable_debug' in config:
            handler.set_enable_debug(config['enable_debug'])
