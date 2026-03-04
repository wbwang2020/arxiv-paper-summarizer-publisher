#!/usr/bin/env python3
"""
知乎文章发布设置模块
处理创作声明选择、专栏选择、话题添加等发布设置
"""
import re
import time
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


class PublishSettingsHandler:
    """发布设置处理器"""
    
    def __init__(self, page: 'Page', debug_print_func=None, debug_screenshot_func=None):
        """
        初始化发布设置处理器
        
        Args:
            page: Playwright页面对象
            debug_print_func: 调试输出函数
            debug_screenshot_func: 调试截图函数
        """
        self.page = page
        self._debug_print = debug_print_func or (lambda x: None)
        self._debug_screenshot = debug_screenshot_func or (lambda x: None)
    
    def configure_publish_settings(self, column_name: Optional[str] = None) -> bool:
        """
        配置所有发布设置
        
        Args:
            column_name: 专栏名称
            
        Returns:
            是否配置成功
        """
        self._debug_print("\n2. 编辑发布设置...")
        
        # 选择创作声明
        self._select_creation_declaration()
        
        # 选择专栏
        if column_name:
            self._select_column(column_name)
        
        # 添加话题
        self._add_topic()
        
        return True
    
    def _select_creation_declaration(self) -> bool:
        """
        选择创作声明为"包含AI辅助创作"
        "创作声明"是静态文本，后面有一个对应的下拉选择框
        
        Returns:
            是否选择成功
        """
        try:
            self._debug_print("选择创作声明为'包含AI辅助创作'...")
            
            # 步骤1：查找"创作声明"相关的下拉选择区域
            self._debug_print("步骤1：查找创作声明下拉选择区域...")
            
            # 直接查找创作声明相关的下拉选择区域
            dropdown_selectors = [
                'div:has-text("创作声明")',
                'span:has-text("创作声明")',
                'label:has-text("创作声明")',
                'div[class*="creation"]',
                'div[class*="declaration"]',
                'div[role="combobox"]',
                'div[class*="select"]',
                'div[class*="dropdown"]'
            ]
            
            dropdown_area = None
            for selector in dropdown_selectors:
                try:
                    self._debug_print(f"尝试选择器: {selector}")
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        if element.is_visible():
                            # 检查元素是否包含创作声明相关的文本
                            text = element.text_content()
                            if "创作声明" in text or any(keyword in element.get_attribute('class') or '' for keyword in ['select', 'dropdown', 'combobox']):
                                dropdown_area = element
                                self._debug_print(f"[OK] 找到创作声明下拉选择区域: {selector}")
                                break
                    if dropdown_area:
                        break
                except Exception as e:
                    self._debug_print(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not dropdown_area:
                self._debug_print("[X] 未找到创作声明下拉选择区域")
                return False
            
            # 步骤2：点击下拉区域展开选项
            self._debug_print("\n步骤2：点击下拉区域展开选项...")
            dropdown_area.click()
            time.sleep(1)
            
            # 步骤3：在下拉列表中选择"包含AI辅助创作"
            self._debug_print("\n步骤3：在下拉列表中选择'包含AI辅助创作'...")
            
            # 等待下拉列表出现
            time.sleep(0.5)
            
            # 使用正则表达式查找下拉选项，处理字符间可能出现的空格
            # "包含AI辅助创作" 可能变成 "包含 AI 辅 助 创 作" 等各种形式
            option_found = self._select_option_by_regex(r'包含\s*A\s*I\s*辅\s*助\s*创\s*作')
            
            if not option_found:
                self._debug_print("[!] 未找到'包含AI辅助创作'选项，尝试使用键盘选择...")
                # 尝试使用键盘向下箭头选择
                for _ in range(5):
                    self.page.keyboard.press('ArrowDown')
                    time.sleep(0.2)
                self.page.keyboard.press('Enter')
                self._debug_print("[OK] 已尝试使用键盘选择")
            
            return True
            
        except Exception as e:
            self._debug_print(f"[!] 选择创作声明时出错: {e}")
            return False
    
    def _select_option_by_regex(self, pattern: str) -> bool:
        """
        使用正则表达式选择下拉选项
        
        Args:
            pattern: 正则表达式模式
            
        Returns:
            是否成功选择
        """
        self._debug_print(f"使用正则表达式查找选项: {pattern}")
        
        # 定义可能的选择器
        option_selectors = [
            'li',
            'div[role="option"]',
            'span',
            'div',
            'option',
            '[class*="option"]',
            '[class*="item"]'
        ]
        
        for selector in option_selectors:
            try:
                options = self.page.query_selector_all(selector)
                for option in options:
                    try:
                        if option.is_visible():
                            text = option.text_content()
                            if text and re.search(pattern, text):
                                self._debug_print(f"[OK] 找到匹配选项: {text.strip()}")
                                option.click()
                                self._debug_print("[OK] 已选择匹配选项")
                                time.sleep(1)
                                return True
                    except Exception:
                        continue
            except Exception as e:
                self._debug_print(f"选择器 {selector} 失败: {e}")
                continue
        
        return False
    
    def _handle_creation_declaration_dialog(self) -> bool:
        """
        处理创作声明弹出的"我知道了"对话框
        
        Returns:
            是否处理了对话框
        """
        try:
            # 查找"我知道了"按钮
            dialog_selectors = [
                'button:has-text("我知道了")',
                'div:has-text("我知道了")',
                'span:has-text("我知道了")',
                'a:has-text("我知道了")',
                '[class*="Button"]:has-text("我知道了")',
                '[class*="btn"]:has-text("我知道了")'
            ]
            
            for selector in dialog_selectors:
                try:
                    dialog_btn = self.page.query_selector(selector)
                    if dialog_btn and dialog_btn.is_visible():
                        self._debug_print(f"[OK] 发现'我知道了'对话框，点击确认...")
                        dialog_btn.click()
                        time.sleep(1)
                        self._debug_print("[OK] 已关闭'我知道了'对话框")
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            self._debug_print(f"处理'我知道了'对话框时出错: {e}")
            return False
    
    def _select_column(self, column_name: str) -> bool:
        """
        选择专栏 - 通过"专栏收录"条目中的"发布到专栏"选择专栏
        
        Args:
            column_name: 专栏名称
            
        Returns:
            是否选择成功
        """
        self._debug_print(f"\n2.1 选择专栏: {column_name}")
        
        try:
            # 步骤1: 查找"专栏收录"静态文本
            self._debug_print("寻找'专栏收录'静态文本...")
            column_collect_elem = self._find_column_collect_element()
            
            if not column_collect_elem:
                self._debug_print("[X] 未找到'专栏收录'文本")
                return False
            
            # 步骤2: 查找"发布到专栏"选项按钮
            publish_button = self._find_publish_to_column_button(column_collect_elem)
            
            if not publish_button:
                self._debug_print("[X] 未找到'发布到专栏'选项按钮")
                return False
            
            # 步骤3: 点击"发布到专栏"选项
            self._debug_print("点击'发布到专栏'选项...")
            publish_button.click()
            time.sleep(2)
            
            # 步骤4: 等待专栏下拉列表出现
            self._debug_print("等待专栏下拉列表出现...")
            time.sleep(1)
            
            # 步骤5: 在下拉列表中选择目标专栏
            column_option = self._find_column_option(column_name)
            
            if not column_option:
                self._debug_print(f"[X] 未找到目标专栏: {column_name}")
                return False
            
            # 步骤6: 点击目标专栏
            self._debug_print(f"点击目标专栏: {column_name}")
            column_option.click()
            time.sleep(1)
            
            self._debug_print("[OK] 成功选择专栏")
            self._debug_screenshot("debug_column_selected.png")
            
            return True
            
        except Exception as e:
            self._debug_print(f"[X] 选择专栏时出错: {e}")
            return False
    
    def _find_column_collect_element(self):
        """查找"专栏收录"元素"""
        column_collect_selectors = [
            'text="专栏收录"',
            'span:has-text("专栏收录")',
            'div:has-text("专栏收录")',
            'label:has-text("专栏收录")',
            '//span[contains(text(), "专栏收录")]',
            '//div[contains(text(), "专栏收录")]'
        ]
        
        for selector in column_collect_selectors:
            try:
                self._debug_print(f"尝试选择器: {selector}")
                elem = self.page.query_selector(selector)
                if elem:
                    self._debug_print(f"[OK] 找到'专栏收录'文本: {selector}")
                    return elem
            except Exception as e:
                self._debug_print(f"选择器 {selector} 失败: {e}")
                continue
        
        return None
    
    def _find_publish_to_column_button(self, column_collect_elem):
        """
        查找"发布到专栏"按钮
        
        Args:
            column_collect_elem: "专栏收录"元素
            
        Returns:
            按钮元素或None
        """
        self._debug_print("在'专栏收录'附近查找'发布到专栏'选项按钮...")
        
        publish_to_column_selectors = [
            'input[type="radio"][value*="column"]',
            'input[type="radio"]',
            'span:has-text("发布到专栏")',
            'label:has-text("发布到专栏")',
            'div:has-text("发布到专栏")',
            '//span[contains(text(), "发布到专栏")]',
            '//label[contains(text(), "发布到专栏")]'
        ]
        
        for selector in publish_to_column_selectors:
            try:
                self._debug_print(f"尝试选择器: {selector}")
                elem = self.page.query_selector(selector)
                if elem:
                    elem_text = elem.text_content() if elem else ""
                    if "发布到专栏" in elem_text or "column" in selector.lower():
                        self._debug_print(f"[OK] 找到'发布到专栏'选项: {selector}")
                        return elem
            except Exception as e:
                self._debug_print(f"选择器 {selector} 失败: {e}")
                continue
        
        # 如果还没找到，尝试在父容器中查找
        if column_collect_elem:
            self._debug_print("在父容器中查找'发布到专栏'选项...")
            try:
                parent = column_collect_elem.evaluate_handle('el => el.parentElement')
                parent_elem = parent.as_element()
                if parent_elem:
                    publish_button = parent_elem.query_selector(
                        'span:has-text("发布到专栏"), label:has-text("发布到专栏")'
                    )
                    if publish_button:
                        self._debug_print("[OK] 在父容器中找到'发布到专栏'选项")
                        return publish_button
            except Exception as e:
                self._debug_print(f"在父容器中查找失败: {e}")
        
        return None
    
    def _find_column_option(self, column_name: str):
        """
        查找专栏选项
        
        Args:
            column_name: 专栏名称
            
        Returns:
            选项元素或None
        """
        self._debug_print(f"在下拉列表中查找目标专栏: {column_name}")
        
        column_option_selectors = [
            f'li:has-text("{column_name}")',
            f'option:has-text("{column_name}")',
            f'span:has-text("{column_name}")',
            f'div:has-text("{column_name}")',
            f'[title="{column_name}"]',
            f'//li[contains(text(), "{column_name}")]',
            f'//option[contains(text(), "{column_name}")]',
            f'//span[contains(text(), "{column_name}")]'
        ]
        
        for selector in column_option_selectors:
            try:
                self._debug_print(f"尝试选择器: {selector}")
                elem = self.page.query_selector(selector)
                if elem:
                    self._debug_print(f"[OK] 找到目标专栏: {selector}")
                    return elem
            except Exception as e:
                self._debug_print(f"选择器 {selector} 失败: {e}")
                continue
        
        return None
    
    def _add_topic(self, topic_keyword: str = "人工智能") -> bool:
        """
        添加文章话题
        
        Args:
            topic_keyword: 话题关键词
            
        Returns:
            是否添加成功
        """
        self._debug_print("\n2.2 添加文章话题...")
        
        try:
            self._debug_print("检查是否需要添加话题...")
            add_topic_button = self.page.query_selector('button:has-text("添加话题")')
            
            if not add_topic_button or not add_topic_button.is_visible():
                return False
            
            self._debug_print("发现'添加话题'按钮，尝试添加话题...")
            add_topic_button.click()
            time.sleep(1)
            
            # 输入话题关键词
            topic_input = self.page.query_selector('input[placeholder*="话题"]')
            if not topic_input:
                return False
            
            self._debug_print(f"输入话题关键词: {topic_keyword}")
            topic_input.fill(topic_keyword)
            time.sleep(1)
            
            # 尝试按回车选择话题
            self._debug_print("尝试按回车选择话题...")
            topic_input.press('Enter')
            time.sleep(1)
            self._debug_print("[OK] 已尝试按回车选择话题")
            
            return True
            
        except Exception as e:
            self._debug_print(f"[!] 添加话题时出错: {e}")
            return False
