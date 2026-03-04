import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    console_output: bool = True
) -> logging.Logger:
    """设置日志配置"""
    
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 生成日志文件名
    log_file = os.path.join(log_dir, f"arxiv_survey_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 创建logger
    logger = logging.getLogger("arxiv_survey")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "arxiv_survey") -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name)
