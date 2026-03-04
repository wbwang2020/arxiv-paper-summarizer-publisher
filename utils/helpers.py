import re
from typing import List


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    # 替换非法字符
    illegal_chars = r'[\\/*?:"<>|]'
    filename = re.sub(illegal_chars, "_", filename)
    
    # 替换空白字符
    filename = re.sub(r'\s+', "_", filename)
    
    # 截断长度
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    # 移除首尾的下划线
    filename = filename.strip("_")
    
    return filename


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> List[str]:
    """
    将文本分块
    
    Args:
        text: 原始文本
        chunk_size: 每块大小（字符数）
        overlap: 块间重叠大小
        
    Returns:
        文本块列表
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def estimate_tokens(text: str) -> int:
    """
    估算文本的token数量（粗略估计）
    
    Args:
        text: 文本内容
        
    Returns:
        估算的token数
    """
    # 中文字符约1.5个token，英文单词约1.3个token
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    
    return int(chinese_chars * 1.5 + other_chars * 0.3)
