"""
进度显示工具
提供美观的进度条和状态显示
"""

import sys
import time
from typing import Optional
from contextlib import contextmanager


class ProgressBar:
    """进度条类"""
    
    def __init__(self, total: int, desc: str = "", width: int = 50):
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()
        
    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        self._draw()
        
    def _draw(self):
        """绘制进度条"""
        if self.total == 0:
            return
            
        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)
        
        # 计算ETA
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = elapsed / self.current * (self.total - self.current)
            eta_str = f"ETA: {self._format_time(eta)}"
        else:
            eta_str = "ETA: --:--"
            
        # 格式化输出
        status = f"\r{self.desc} |{bar}| {self.current}/{self.total} ({percent*100:.1f}%) {eta_str}"
        sys.stdout.write(status)
        sys.stdout.flush()
        
        if self.current >= self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def close(self):
        """关闭进度条"""
        if self.current < self.total:
            sys.stdout.write("\n")
            sys.stdout.flush()


class PaperProgress:
    """论文处理进度显示"""
    
    STEPS = [
        ("", "下载PDF"),
        ("", "提取文本"),
        ("", "AI总结"),
        ("", "保存本地"),
        ("", "发布知乎"),
    ]
    
    def __init__(self, arxiv_id: str, total_steps: int = 5):
        self.arxiv_id = arxiv_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_start_time = time.time()
        
    def start_step(self, step_num: int, step_name: str):
        """开始一个新步骤"""
        self.current_step = step_num
        self.step_start_time = time.time()
        
        emoji, short_name = self.STEPS[step_num - 1] if step_num <= len(self.STEPS) else ("⏳", step_name)
        
        # 打印步骤信息
        progress = f"[{step_num}/{self.total_steps}]"
        print(f"\n{'='*60}")
        print(f"{emoji} {progress} {step_name}")
        print(f"{'='*60}")
        
    def complete_step(self, message: str = ""):
        """完成当前步骤"""
        elapsed = time.time() - self.step_start_time
        if message:
            print(f"完成: {message} (耗时: {elapsed:.1f}s)")
        else:
            print(f"完成 (耗时: {elapsed:.1f}s)")
            
    def error(self, message: str):
        """显示错误"""
        print(f"错误: {message}")
        
    def info(self, message: str):
        """显示信息"""
        print(f"{message}")
        
    def warning(self, message: str):
        """显示警告"""
        print(f"警告: {message}")


class BatchProgress:
    """批量处理进度显示"""
    
    def __init__(self, total_papers: int):
        self.total_papers = total_papers
        self.current = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        
    def start_paper(self, arxiv_id: str, title: str):
        """开始处理一篇论文"""
        self.current += 1
        print(f"\n{'#'*70}")
        print(f"# 处理论文 [{self.current}/{self.total_papers}]: {arxiv_id}")
        print(f"# 标题: {title[:50]}...")
        print(f"{'#'*70}")
        
    def mark_success(self):
        """标记成功"""
        self.success += 1
        
    def mark_failed(self):
        """标记失败"""
        self.failed += 1
        
    def mark_skipped(self):
        """标记跳过"""
        self.skipped += 1
        
    def show_summary(self):
        """显示总结"""
        elapsed = time.time() - self.start_time
        
        print(f"\n{'='*70}")
        print(f"处理完成总结")
        print(f"{'='*70}")
        print(f"  总计: {self.total_papers} 篇论文")
        print(f"  成功: {self.success}")
        print(f"  失败: {self.failed}")
        print(f"  跳过: {self.skipped}")
        print(f"  总耗时: {elapsed:.1f}s")
        print(f"{'='*70}")


@contextmanager
def progress_spinner(message: str):
    """进度旋转器上下文管理器"""
    import threading
    
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    stop_event = threading.Event()
    
    def spin():
        i = 0
        while not stop_event.is_set():
            char = spinner_chars[i % len(spinner_chars)]
            sys.stdout.write(f"\r{char} {message}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write(f"\r{message}\n")
        sys.stdout.flush()
    
    thread = threading.Thread(target=spin)
    thread.start()
    
    try:
        yield
    finally:
        stop_event.set()
        thread.join()


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")
