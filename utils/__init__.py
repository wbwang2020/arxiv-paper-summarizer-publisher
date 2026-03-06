from .logger import get_logger, setup_logging
from .helpers import sanitize_filename, truncate_text, chunk_text, estimate_tokens
from .progress import ProgressBar, PaperProgress, BatchProgress, progress_spinner, print_header, print_section
from .output_handler import OutputHandler, get_output_handler, setup_output_handler

# 日志级别映射
LOG_LEVEL_MAP = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# 日志级别转换函数
def get_log_level(level_str: str, default: int = 20) -> int:
    """
    将字符串形式的日志级别转换为整数
    
    Args:
        level_str: 日志级别字符串，如 "INFO"
        default: 默认日志级别，默认值为 20 (INFO)
        
    Returns:
        对应的日志级别整数
    """
    return LOG_LEVEL_MAP.get(level_str.upper(), default)

__all__ = [
    "get_logger",
    "setup_logging",
    "sanitize_filename",
    "truncate_text",
    "chunk_text",
    "estimate_tokens",
    "ProgressBar",
    "PaperProgress",
    "BatchProgress",
    "progress_spinner",
    "print_header",
    "print_section",
    "OutputHandler",
    "get_output_handler",
    "setup_output_handler",
    "get_log_level",
    "LOG_LEVEL_MAP",
]
