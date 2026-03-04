#!/usr/bin/env python3
"""
知乎文章题目设置模块
处理文章标题的填写和验证
"""
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


class TitleSettingsHandler:
    """题目设置处理器"""
    
    # 知乎标题最大长度（100个汉字）
    MAX_TITLE_LENGTH = 100
    
    def __init__(self, page: 'Page', debug_print_func=None, debug_screenshot_func=None):
        """
        初始化题目设置处理器
        
        Args:
            page: Playwright页面对象
            debug_print_func: 调试输出函数
            debug_screenshot_func: 调试截图函数
        """
        self.page = page
        self._debug_print = debug_print_func or (lambda x: None)
        self._debug_screenshot = debug_screenshot_func or (lambda x: None)
    
    def set_title(self, title: str) -> str:
        """
        设置文章标题
        
        Args:
            title: 原始标题
            
        Returns:
            处理后的标题
        """
        self._debug_print("\n1. 编辑题目...")
        
        # 检查标题长度并截断
        processed_title = self._validate_and_truncate_title(title)
        
        # 填写标题
        self._fill_title_input(processed_title)
        
        # 验证标题填写结果
        self._verify_title_input(processed_title)
        
        # 保存截图
        self._debug_screenshot("debug_title_filled.png")
        
        time.sleep(1)
        
        return processed_title
    
    def _validate_and_truncate_title(self, title: str) -> str:
        """
        验证标题长度并截断
        
        Args:
            title: 原始标题
            
        Returns:
            处理后的标题
        """
        if len(title) > self.MAX_TITLE_LENGTH:
            self._debug_print(f"[!] 标题长度超过{self.MAX_TITLE_LENGTH}字({len(title)}字)，将截断")
            title = title[:self.MAX_TITLE_LENGTH - 3] + "..."
            self._debug_print(f"截断后标题: {title}")
        
        self._debug_print(f"正在填写标题: {title[:50]}...")
        self._debug_print(f"完整标题长度: {len(title)} 字符")
        
        return title
    
    def _fill_title_input(self, title: str) -> None:
        """
        填写标题输入框
        
        Args:
            title: 标题内容
        """
        title_input = self.page.query_selector(
            'textarea[placeholder*="标题"], .WriteIndex-titleInput textarea'
        )
        
        if not title_input:
            self._debug_print("[X] 未找到标题输入框")
            raise Exception("Title input not found")
        
        # 先清空输入框
        title_input.fill("")
        time.sleep(0.5)
        
        # 再填写标题
        title_input.fill(title)
        time.sleep(0.5)
        
        self._debug_print("[OK] 标题已填写")
    
    def _verify_title_input(self, expected_title: str) -> bool:
        """
        验证标题是否正确填写
        
        Args:
            expected_title: 期望的标题
            
        Returns:
            是否验证通过
        """
        title_input = self.page.query_selector(
            'textarea[placeholder*="标题"], .WriteIndex-titleInput textarea'
        )
        
        if not title_input:
            return False
        
        actual_title = title_input.input_value()
        self._debug_print(f"实际填写的标题: {actual_title}")
        
        if actual_title != expected_title:
            self._debug_print(f"[!] 标题填写不一致!")
            self._debug_print(f"  期望: {expected_title}")
            self._debug_print(f"  实际: {actual_title}")
            return False
        
        return True
    
    def get_current_title(self) -> Optional[str]:
        """
        获取当前填写的标题
        
        Returns:
            当前标题，未找到返回None
        """
        title_input = self.page.query_selector(
            'textarea[placeholder*="标题"], .WriteIndex-titleInput textarea'
        )
        
        if title_input:
            return title_input.input_value()
        
        return None
