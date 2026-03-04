#!/usr/bin/env python3
"""
知乎文章主体填充模块
处理文章正文的填充，支持拷贝粘贴和导入文档两种模式
"""
import os
import re
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page


class ContentFiller:
    """文章主体填充处理器"""
    
    def __init__(self, page: 'Page', debug_print_func=None, debug_screenshot_func=None):
        """
        初始化内容填充处理器
        
        Args:
            page: Playwright页面对象
            debug_print_func: 调试输出函数
            debug_screenshot_func: 调试截图函数
        """
        self.page = page
        self._debug_print = debug_print_func or (lambda x: None)
        self._debug_screenshot = debug_screenshot_func or (lambda x: None)
    
    def fill_content(self, content: str, file_path: Optional[str] = None, 
                     content_fill_mode: str = 'copy_paste') -> bool:
        """
        填充文章内容
        
        发布流程（优先级）：
        1. 文件上传模式 (import_document) - 优先使用
        2. 拷贝粘贴模式 (copy_paste) - 备选方案
        3. 键盘输入模式 - 最后备选
        
        Args:
            content: 文章内容
            file_path: 文件路径（用于导入文档模式）
            content_fill_mode: 填充模式 ('copy_paste' 或 'import_document')
            
        Returns:
            是否填充成功
        """
        self._debug_print("\n3. 填充正文...")
        self._debug_print("正在查找内容编辑器...")
        
        # 查找内容编辑器
        content_editor = self._find_content_editor()
        
        if not content_editor:
            self._debug_print("[X] 未找到内容编辑器")
            raise Exception("Content editor not found")
        
        # 根据模式选择填充方式
        self._debug_print("正在填充文章内容...")
        self._debug_print(f"内容长度: {len(content)} 字符")
        
        # 确定使用的填充模式
        fill_mode = self._determine_fill_mode(content_fill_mode, file_path)
        self._debug_print(f"使用正文填充模式: {fill_mode}")
        
        # 执行填充
        fill_success = False
        
        # 模式1：文件上传模式（优先）
        if fill_mode == 'import_document' and file_path:
            self._debug_print("尝试使用文件上传模式...")
            fill_success = self._fill_by_import(file_path)
            if fill_success:
                self._debug_print("[OK] 文件上传模式成功")
            else:
                self._debug_print("[!] 文件上传模式失败，尝试拷贝粘贴模式...")
                # 不直接返回失败，继续尝试其他模式
                fill_success = False
        
        # 模式2：拷贝粘贴模式（备选）
        if not fill_success:
            self._debug_print("尝试使用拷贝粘贴模式...")
            try:
                self._fill_by_copy_paste(content, content_editor)
                # 验证内容是否成功填充
                word_count = self._check_word_count(content_editor)
                if word_count >= 100:
                    fill_success = True
                    self._debug_print("[OK] 拷贝粘贴模式成功")
                else:
                    self._debug_print(f"[!] 拷贝粘贴模式内容不足: {word_count} 字符")
            except Exception as e:
                self._debug_print(f"[!] 拷贝粘贴模式失败: {e}")
        
        # 模式3：键盘输入模式（最后备选）
        if not fill_success:
            self._debug_print("尝试使用键盘输入模式...")
            try:
                self._fill_by_keyboard_input(content)
                word_count = self._check_word_count(content_editor)
                if word_count >= 100:
                    fill_success = True
                    self._debug_print("[OK] 键盘输入模式成功")
                else:
                    self._debug_print(f"[!] 键盘输入模式内容不足: {word_count} 字符")
            except Exception as e:
                self._debug_print(f"[!] 键盘输入模式失败: {e}")
        
        if not fill_success:
            self._debug_print("[X] 所有填充方式均失败")
            raise Exception("Failed to fill content with all methods")
        
        # 检测字数
        self._check_word_count(content_editor)
        
        self._debug_print("\n5. 测试发布按钮状态...")
        time.sleep(2)
        
        self._debug_print("[OK] 文章内容填充完成")
        return True
    
    def _determine_fill_mode(self, content_fill_mode: str, file_path: Optional[str]) -> str:
        """
        确定实际使用的填充模式
        
        Args:
            content_fill_mode: 配置的填充模式
            file_path: 文件路径
            
        Returns:
            实际使用的填充模式
        """
        # 如果配置为import_document且文件存在，使用文件上传模式
        if content_fill_mode == 'import_document' and file_path and os.path.exists(file_path):
            return 'import_document'
        
        # 否则使用拷贝粘贴模式
        return 'copy_paste'
    
    def _find_content_editor(self):
        """查找内容编辑器元素"""
        content_selectors = [
            '.DraftEditor-root .public-DraftEditor-content',
            '[contenteditable="true"]',
            '.WriteIndex-writeWrapper .DraftEditor-editorContainer',
            'div[data-contents="true"]'
        ]
        
        for selector in content_selectors:
            try:
                self._debug_print(f"尝试选择器: {selector}")
                content_editor = self.page.wait_for_selector(selector, timeout=5000)
                if content_editor:
                    self._debug_print(f"[OK] 找到内容编辑器: {selector}")
                    return content_editor
            except Exception as e:
                self._debug_print(f"[!] 选择器 {selector} 失败: {e}")
                continue
        
        return None
    
    def _fill_by_copy_paste(self, content: str, content_editor) -> None:
        """
        使用拷贝粘贴方式填充内容
        按照以下流程实现：
        第一步：初始化，即找到内容编辑器的焦点并清空内容
        第二步：以纯文本模式将markdown文件中的内容用剪贴板API拷贝粘贴文本，如果检测到状态栏中字符数满足发布需求，则发布内容
        第三步：如检测到状态栏中字符数不满足发布需求，则转为键盘输入模式，以原markdown文件中的一行文本为字符块进行输入，检测内容长度并发布
        
        Args:
            content: 文章内容
            content_editor: 内容编辑器元素
        """
        self._debug_print("\n=== 开始拷贝粘贴模式内容填充 ===")
        
        # 第一步：初始化，即找到内容编辑器的焦点并清空内容
        self._debug_print("第一步：初始化编辑器...")
        self._initialize_editor(content_editor)
        
        # 第二步：以纯文本模式将markdown文件中的内容用剪贴板API拷贝粘贴文本
        self._debug_print("\n第二步：使用剪贴板API拷贝粘贴纯文本内容...")
        paste_success = self._paste_via_clipboard(content, content_editor)
        
        # 检测状态栏中字符数是否满足发布需求
        word_count = self._check_word_count(content_editor)
        
        # 判断是否使用拷贝粘贴的结果，还是转为键盘输入模式
        if paste_success and word_count >= 100:
            # 使用拷贝粘贴的结果
            self._debug_print(f"[OK] 状态栏字数满足发布需求: {word_count} 字符")
            self._debug_print("[OK] 内容填充完成，准备发布")
            
            # 检查Markdown解析对话框
            self._handle_markdown_dialog()
            
            # 再次检查字数，确认Markdown解析后内容是否正确
            word_count_after_parse = self._check_word_count(content_editor)
            self._debug_print(f"Markdown解析后字数: {word_count_after_parse} 字符")
            
            if word_count_after_parse < 100:
                self._debug_print("[!] Markdown解析后字数不足，可能解析失败")
                self._debug_print("转为键盘输入模式...")
                self._fill_by_keyboard_input(content)
            else:
                self._debug_print("[OK] Markdown解析成功，内容已正确填充")
            
            # 保存截图
            self._debug_screenshot("debug_content_filled.png")
        else:
            # 转为键盘输入模式
            if not paste_success:
                self._debug_print("[!] 剪贴板粘贴失败，转为键盘输入模式...")
            else:
                self._debug_print(f"[!] 状态栏字数不满足发布需求: {word_count} 字符")
            
            self._debug_print("转为键盘输入模式...")
            self._fill_by_keyboard_input(content)
        
        self._debug_print("\n=== 拷贝粘贴模式内容填充完成 ===")
    
    def _initialize_editor(self, content_editor) -> None:
        """
        初始化编辑器：找到内容编辑器的焦点并清空内容
        
        Args:
            content_editor: 内容编辑器元素
        """
        self._debug_print("找到内容编辑器的焦点...")
        content_editor.click()
        time.sleep(0.5)
        
        self._debug_print("清空编辑器内容...")
        try:
            # 使用JavaScript清空编辑器内容
            self.page.evaluate('''
                (editor) => {
                    editor.focus();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand('delete', false, null);
                    return true;
                }
            ''', content_editor)
            time.sleep(0.3)
            self._debug_print("[OK] 成功清空编辑器内容")
        except Exception as e:
            self._debug_print(f"[!] JavaScript清空内容失败: {e}")
            # 备用方法：使用键盘清空
            self._debug_print("使用键盘清空内容...")
            content_editor.click()
            time.sleep(0.5)
            self.page.keyboard.press('Control+A')
            time.sleep(0.5)
            self.page.keyboard.press('Delete')
            time.sleep(0.5)
            self._debug_print("[OK] 成功使用键盘清空编辑器内容")
    
    def _paste_via_clipboard(self, content: str, content_editor) -> bool:
        """
        使用剪贴板API拷贝粘贴文本
        
        Args:
            content: 文章内容
            content_editor: 内容编辑器元素
            
        Returns:
            是否粘贴成功
        """
        try:
            self._debug_print("使用Clipboard API写入纯文本内容...")
            
            # 使用clipboard API写入纯文本内容
            result = self.page.evaluate('''
                async (content) => {
                    try {
                        // 使用Clipboard API写入纯文本
                        await navigator.clipboard.writeText(content);
                        return true;
                    } catch (err) {
                        console.error('Clipboard write failed:', err);
                        return false;
                    }
                }
            ''', content)
            
            if not result:
                self._debug_print("[!] Clipboard API写入失败")
                return False
            
            self._debug_print("粘贴内容到编辑器...")
            self.page.keyboard.press('Control+V')
            time.sleep(2)
            
            self._debug_print("[OK] 已成功使用剪贴板粘贴Markdown内容")
            
            # 检查Markdown解析对话框（在粘贴后立即检查）
            self._debug_print("检查是否有Markdown解析对话框...")
            self._handle_markdown_dialog()
            
            # 在编辑器内容末端输入空格，触发Markdown解析检测
            self._debug_print("在编辑器内容末端输入空格...")
            self.page.keyboard.press('End')
            time.sleep(0.5)
            self.page.keyboard.type(' ')
            time.sleep(0.5)
            
            # 再次检查Markdown解析对话框（确保没有遗漏）
            self._handle_markdown_dialog()
            
            return True
            
        except Exception as e:
            self._debug_print(f"[!] 剪贴板粘贴失败: {e}")
            return False
    
    def _fill_by_keyboard_input(self, content: str) -> None:
        """
        使用键盘输入方式填充内容（备用方法）
        以原markdown文件中的一行文本为字符块进行输入
        
        Args:
            content: 文章内容
        """
        self._debug_print("使用键盘输入模式填充内容...")
        self._debug_print("以原markdown文件中的一行文本为字符块进行输入...")
        
        # 清空编辑器
        self._debug_print("清空编辑器...")
        self.page.keyboard.press('Control+A')
        time.sleep(0.5)
        self.page.keyboard.press('Delete')
        time.sleep(0.5)
        
        # 按行分割内容
        lines = content.split('\n')
        self._debug_print(f"总行数: {len(lines)}")
        
        # 将行组合成文本块（每块约500字符，避免过多换行）
        chunk_size = 500
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            if current_length + line_length > chunk_size and current_chunk:
                # 当前块已满，保存并开始新块
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                # 添加到当前块
                current_chunk.append(line)
                current_length += line_length
        
        # 添加最后一个块
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        self._debug_print(f"内容分块数: {len(chunks)}")
        
        # 逐块输入
        for i, chunk in enumerate(chunks):
            self._debug_print(f"处理块 {i+1}/{len(chunks)}...")
            # 直接输入整个文本块（保留换行符）
            self.page.keyboard.type(chunk)
            # 每块输入完成后等待一下
            time.sleep(0.5)
        
        self._debug_print("[OK] 已完成键盘输入填充内容")
        time.sleep(3)
        
        # 检查Markdown解析对话框
        self._handle_markdown_dialog()
        
        # 保存截图
        self._debug_screenshot("debug_keyboard_input.png")
        
        # 检测内容长度
        content_editor = self._find_content_editor()
        if content_editor:
            word_count = self._check_word_count(content_editor)
            if word_count < 10:
                self._debug_print(f"[!] 键盘输入后内容可能未正确填充，字数: {word_count}")
            else:
                self._debug_print(f"[OK] 键盘输入内容验证成功，字数: {word_count}")
    
    def _fill_by_import(self, file_path: str) -> bool:
        """
        使用导入文档方式填充内容
        
        Args:
            file_path: Markdown文件路径
            
        Returns:
            是否成功
        """
        self._debug_print("使用导入文档方式填充正文...")
        
        try:
            # 直接使用文件输入框方式上传文件
            self._debug_print("直接使用文件输入框方式上传文件...")
            self._upload_via_file_input(file_path)
            
            # 等待文档导入完成
            self._debug_print("等待文档导入完成...")
            time.sleep(10)  # 增加等待时间，确保文档导入完成
            
            # 验证内容是否真正导入成功
            content_editor = self._find_content_editor()
            if content_editor:
                word_count = self._check_word_count(content_editor)
                self._debug_print(f"导入后检测到字数: {word_count}")
                if word_count >= 100:
                    self._debug_print("[OK] 导入成功，字数足够")
                    return True
                else:
                    self._debug_print(f"[!] 导入后字数不足: {word_count}，视为失败")
                    # 不回退到其他方法，直接返回失败
                    return False
            else:
                self._debug_print("[!] 未找到内容编辑器")
                return False
            
        except Exception as e:
            self._debug_print(f"[!] 导入文档时出错: {e}")
            import traceback
            traceback.print_exc()
            # 不回退到其他方法，直接返回失败
            return False
    
    def _find_import_button(self):
        """查找导入按钮"""
        import_button_selectors = [
            'button:has-text("导入")',
            'span:has-text("导入")',
            '[class*="import"]',
            '[title*="导入"]'
        ]
        
        for selector in import_button_selectors:
            try:
                import_button = self.page.query_selector(selector)
                if import_button and import_button.is_visible():
                    self._debug_print(f"[OK] 找到'导入'按钮: {selector}")
                    return import_button
            except Exception:
                continue
        
        return None
    
    def _find_import_doc_option(self):
        """查找导入文档选项"""
        import_doc_selectors = [
            'button:has-text("导入文档")',
            'span:has-text("导入文档")',
            'li:has-text("导入文档")',
            'div:has-text("导入文档")',
            'text="导入文档 MD/Doc"',
            'text="导入文档"'
        ]
        
        for selector in import_doc_selectors:
            try:
                import_doc_option = self.page.query_selector(selector)
                if import_doc_option and import_doc_option.is_visible():
                    self._debug_print(f"[OK] 找到'导入文档'选项: {selector}")
                    return import_doc_option
            except Exception:
                continue
        
        return None
    
    def _upload_file(self, file_path: str) -> None:
        """
        上传文件
        
        Args:
            file_path: 文件路径
        """
        self._debug_print("等待文件上传对话框...")
        time.sleep(2)
        
        self._debug_print("使用系统文件对话框方式上传文件...")
        
        # 查找上传区域
        upload_area_selectors = [
            'div:has-text("点击选择本地文档或拖动文件到窗口上传")',
            'span:has-text("点击选择本地文档")',
            '[class*="upload"]',
            'input[type="file"]'
        ]
        
        upload_area = None
        for selector in upload_area_selectors:
            try:
                upload_area = self.page.query_selector(selector)
                if upload_area:
                    self._debug_print(f"[OK] 找到上传区域: {selector}")
                    break
            except Exception:
                continue
        
        if not upload_area:
            self._debug_print("[!] 未找到上传区域，尝试使用隐藏文件输入框方式...")
            self._upload_via_file_input(file_path)
            return
        
        # 点击上传区域
        upload_area.click()
        self._debug_print("[OK] 点击了上传区域，等待系统文件对话框打开...")
        time.sleep(3)
        
        # 使用键盘输入文件路径
        abs_file_path = os.path.abspath(file_path)
        file_dir = os.path.dirname(abs_file_path)
        file_name = os.path.basename(abs_file_path)
        
        self._debug_print(f"文件绝对路径: {abs_file_path}")
        self._debug_print(f"文件目录: {file_dir}")
        self._debug_print(f"文件名: {file_name}")
        
        # 输入文件路径
        self.page.keyboard.press('Alt')
        time.sleep(0.5)
        self.page.keyboard.type('n')
        time.sleep(1)
        
        self.page.keyboard.type(abs_file_path)
        time.sleep(1)
        
        self._debug_screenshot("debug_file_dialog_path_entered.png")
        
        time.sleep(5)
        
        # 按回车确认
        self.page.keyboard.press('Enter')
        time.sleep(2)
        
        self._debug_print("[OK] 已完成系统文件对话框操作")
        self._debug_print("等待文档导入完成...")
        time.sleep(5)
        
        self._debug_print("[OK] 文档导入完成")
    
    def _upload_via_file_input(self, file_path: str) -> None:
        """
        通过文件输入框上传文件
        
        Args:
            file_path: 文件路径
        """
        # 首先尝试找到工具栏中的导入按钮，然后点击导入按钮打开文件选择对话框
        self._debug_print("尝试找到工具栏中的导入按钮...")
        
        # 查找工具栏中的导入按钮，使用更具体的选择器
        import_button_selectors = [
            'button[title*="导入"]',
            'button:has-text("导入"):not(:has-text("导入文档"))',
            '[class*="toolbar"] button:has-text("导入")',
            '[class*="editor-toolbar"] button:has-text("导入")',
            'span:has-text("导入"):not(:has-text("导入文档"))'
        ]
        
        import_button = None
        for selector in import_button_selectors:
            try:
                import_button = self.page.query_selector(selector)
                if import_button and import_button.is_visible():
                    self._debug_print(f"[OK] 找到工具栏'导入'按钮: {selector}")
                    break
            except Exception:
                continue
        
        if import_button:
            self._debug_print("点击工具栏导入按钮...")
            try:
                import_button.click()
                self._debug_print("[OK] 已点击工具栏导入按钮")
                time.sleep(2)
            except Exception as e:
                self._debug_print(f"[!] 点击工具栏导入按钮失败: {e}")
        
        # 查找导入文档选项
        self._debug_print("尝试找到导入文档选项...")
        import_doc_selectors = [
            'button:has-text("导入文档")',
            'span:has-text("导入文档")',
            'li:has-text("导入文档")',
            'div:has-text("导入文档")',
            'text="导入文档 MD/Doc"',
            'text="导入文档"',
            'div[class*="menu"] button:has-text("导入文档")',
            'div[class*="dropdown"] button:has-text("导入文档")'
        ]
        
        import_doc_option = None
        for selector in import_doc_selectors:
            try:
                import_doc_option = self.page.query_selector(selector)
                if import_doc_option and import_doc_option.is_visible():
                    self._debug_print(f"[OK] 找到'导入文档'选项: {selector}")
                    break
            except Exception:
                continue
        
        if import_doc_option:
            self._debug_print("点击导入文档选项...")
            try:
                import_doc_option.click()
                self._debug_print("[OK] 已点击导入文档选项")
                time.sleep(3)  # 增加等待时间，确保文件选择对话框完全打开
            except Exception as e:
                self._debug_print(f"[!] 点击导入文档选项失败: {e}")
        
        # 查找文件输入框，优先查找支持Markdown的输入框
        file_input_selectors = [
            'input[type="file"][accept*=".md"]',
            'input[type="file"][accept*=".markdown"]',
            'input[type="file"][accept*=".txt"]',
            'input[type="file"][accept*=".doc"]',
            'input[type="file"]'
        ]
        
        file_input = None
        for selector in file_input_selectors:
            try:
                file_input = self.page.query_selector(selector)
                if file_input:
                    # 检查元素是否可见
                    is_visible = file_input.is_visible()
                    self._debug_print(f"[OK] 找到文件输入框: {selector}, 可见性: {is_visible}")
                    break
            except Exception as e:
                self._debug_print(f"[!] 查找文件输入框时出错: {e}")
                continue
        
        if not file_input:
            self._debug_print("[!] 未找到文件输入框")
            return
        
        abs_file_path = os.path.abspath(file_path)
        self._debug_print(f"上传文件: {file_path}")
        self._debug_print(f"绝对路径: {abs_file_path}")
        
        if not os.path.exists(abs_file_path):
            self._debug_print(f"[X] 文件不存在: {abs_file_path}")
            return
        
        self._debug_print(f"文件大小: {os.path.getsize(abs_file_path)} 字节")
        
        # 直接使用set_input_files方法设置文件，跳过点击操作
        self._debug_print("直接使用set_input_files方法设置文件...")
        try:
            # 检查文件输入框属性
            self._debug_print(f"文件输入框类型: {file_input.get_attribute('type')}")
            self._debug_print(f"文件输入框accept属性: {file_input.get_attribute('accept')}")
            self._debug_print(f"文件输入框name属性: {file_input.get_attribute('name')}")
            
            # 先清空文件输入框
            file_input.set_input_files([])
            self._debug_print("[OK] 已清空文件输入框")
            
            # 然后设置文件
            file_input.set_input_files(abs_file_path)
            self._debug_print("[OK] 已成功设置文件")
            
            # 检查是否成功设置
            files = file_input.evaluate("el => el.files")
            if files:
                if isinstance(files, dict):
                    # 处理字典类型的返回值
                    self._debug_print(f"文件输入框中的文件数量: {len(files)}")
                    for key, value in files.items():
                        self._debug_print(f"文件 {key}: {value}")
                else:
                    # 处理FileList类型的返回值
                    self._debug_print(f"文件输入框中的文件数量: {files.length}")
                    if files.length > 0:
                        self._debug_print(f"第一个文件名称: {files[0].name}")
                        self._debug_print(f"第一个文件大小: {files[0].size}")
        except Exception as e:
            self._debug_print(f"[!] 设置文件失败: {e}")
            import traceback
            traceback.print_exc()
            # 不回退到拷贝粘贴方式，直接返回
            return
        
        time.sleep(2)
        
        # 检测"文档导入中"对话框
        self._debug_print("检测'文档导入中'对话框...")
        try:
            import_dialog_selectors = [
                'div:has-text("文档导入中")',
                'span:has-text("文档导入中")',
                'p:has-text("文档导入中")',
                'div[class*="loading"][class*="import"]'
            ]
            
            dialog_found = False
            for selector in import_dialog_selectors:
                try:
                    dialog = self.page.query_selector(selector)
                    if dialog and dialog.is_visible():
                        self._debug_print(f"[OK] 发现'文档导入中'对话框: {selector}")
                        dialog_found = True
                        break
                except Exception:
                    continue
            
            if dialog_found:
                # 等待对话框消失
                self._debug_print("等待'文档导入中'对话框消失...")
                start_time = time.time()
                max_wait = 30
                while time.time() - start_time < max_wait:
                    try:
                        dialog_still_visible = False
                        for selector in import_dialog_selectors:
                            dialog = self.page.query_selector(selector)
                            if dialog and dialog.is_visible():
                                dialog_still_visible = True
                                break
                        if not dialog_still_visible:
                            self._debug_print("[OK] '文档导入中'对话框已消失")
                            break
                        time.sleep(2)
                    except Exception:
                        break
        except Exception as e:
            self._debug_print(f"[!] 检测'文档导入中'对话框时出错: {e}")
        
        # 等待文档导入完成
        self._debug_print("等待文档导入完成...")
        time.sleep(5)
        
        # 通过状态栏字数检查导入是否成功
        self._debug_print("通过状态栏字数检查导入是否成功...")
        try:
            word_count = self._check_word_count(None)  # 传入None会重新查找编辑器
            if word_count >= 100:
                self._debug_print(f"[OK] 导入成功，检测到字数: {word_count}")
            else:
                self._debug_print(f"[!] 导入可能失败，字数不足: {word_count}")
                # 不回退到拷贝粘贴方式，直接返回
                return
        except Exception as e:
            self._debug_print(f"[!] 检查字数时出错: {e}")
        
        self._debug_print("[OK] 文档导入完成")
    
    def _fallback_to_copy_paste(self, file_path: str) -> None:
        """
        回退到拷贝粘贴方式
        
        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content_editor = self.page.query_selector('.DraftEditor-root .public-DraftEditor-content')
            if content_editor:
                self._fill_by_copy_paste(content, content_editor)
        except Exception as e:
            self._debug_print(f"[!] 拷贝粘贴也失败: {e}")
    
    def _handle_markdown_dialog(self) -> bool:
        """
        处理Markdown解析对话框
        
        对话框特征：
        - 文本以"识别到特殊格式"开始
        - 包含"确认并解析"蓝色按钮
        
        Returns:
            是否成功处理对话框
        """
        self._debug_print("检查是否有Markdown解析对话框...")
        time.sleep(1)
        
        try:
            # 查找包含"识别到特殊格式"的对话框
            dialog_selectors = [
                'div:has-text("识别到特殊格式")',
                'span:has-text("识别到特殊格式")',
                'p:has-text("识别到特殊格式")',
                '[class*="modal"]:has-text("识别到特殊格式")',
                '[class*="dialog"]:has-text("识别到特殊格式")',
                '[class*="Modal"]:has-text("识别到特殊格式")',
                '[class*="Dialog"]:has-text("识别到特殊格式")'
            ]
            
            dialog_found = False
            for selector in dialog_selectors:
                try:
                    dialog = self.page.query_selector(selector)
                    if dialog and dialog.is_visible():
                        self._debug_print(f"[OK] 找到Markdown解析对话框: {selector}")
                        dialog_found = True
                        break
                except Exception:
                    continue
            
            if not dialog_found:
                self._debug_print("[!] 未找到Markdown解析对话框")
                return False
            
            # 在对话框中查找"确认并解析"超链接或按钮
            button_selectors = [
                'a:has-text("确认并解析")',
                'span:has-text("确认并解析")',
                'div:has-text("确认并解析")',
                'button:has-text("确认并解析")',
                '[class*="link"]:has-text("确认并解析")',
                '[class*="Link"]:has-text("确认并解析")',
                '[class*="Button"]:has-text("确认并解析")',
                '[class*="btn"]:has-text("确认并解析")',
                '[class*="primary"]:has-text("确认并解析")'
            ]
            
            for selector in button_selectors:
                try:
                    confirm_btn = self.page.query_selector(selector)
                    if confirm_btn and confirm_btn.is_visible():
                        self._debug_print(f"[OK] 找到确认按钮: {selector}")
                        # 先滚动到元素位置
                        confirm_btn.scroll_into_view_if_needed()
                        time.sleep(0.3)
                        # 使用JavaScript点击，避免视口问题
                        self.page.evaluate('(elem) => elem.click()', confirm_btn)
                        self._debug_print("[OK] 已点击确认并解析按钮")
                        # 点击后对话框消失，无需等待回复
                        time.sleep(0.5)
                        return True
                except Exception as e:
                    self._debug_print(f"按钮选择器 {selector} 失败: {e}")
                    continue
            
            self._debug_print("[!] 未找到确认按钮")
            return False
            
        except Exception as e:
            self._debug_print(f"[!] 处理Markdown解析对话框时出错: {e}")
            return False
    
    def _check_word_count(self, content_editor) -> int:
        """
        检查编辑器字数
        
        Args:
            content_editor: 内容编辑器元素，如果为None则重新查找
            
        Returns:
            字数统计
        """
        self._debug_print("\n4. 检测状态栏中的字数...")
        word_count = 0
        
        # 如果content_editor为None，重新查找
        if content_editor is None:
            self._debug_print("content_editor为None，重新查找编辑器...")
            content_editor = self._find_content_editor()
            if not content_editor:
                self._debug_print("[!] 未找到内容编辑器")
                return 0
        
        try:
            self._debug_print("正在查找状态栏中的字数信息...")
            
            word_count_selectors = [
                '.WriteIndex-statusBar span:has-text("字数")',
                '.WriteIndex-statusBar span:nth-child(1)',
                '.WriteIndex-statusBar',
                '[class*="statusBar"] span:has-text("字数")',
                '[class*="status"] span:has-text("字数")',
                'span:has-text("字数")',
                'div:has-text("字数")'
            ]
            
            for selector in word_count_selectors:
                try:
                    self._debug_print(f"尝试选择器: {selector}")
                    word_count_elem = self.page.query_selector(selector)
                    if word_count_elem:
                        word_count_text = word_count_elem.text_content()
                        self._debug_print(f"找到字数信息: {word_count_text}")
                        
                        match = re.search(r'字数[：:](\d+)', word_count_text)
                        if match:
                            word_count = int(match.group(1))
                            self._debug_print(f"提取到字数: {word_count}")
                            break
                except Exception as e:
                    self._debug_print(f"选择器 {selector} 失败: {e}")
                    continue
            
            # 检查字数是否为0
            if word_count == 0:
                self._debug_print("[!] 字数为0，说明编辑内容没有被有效粘贴在正文中")
                self._debug_print("尝试重新填充内容...")
                
                content_editor.click()
                time.sleep(0.5)
                
                # 重新设置内容
                self.page.evaluate('''
                    (content) => {
                        const editor = document.querySelector('.DraftEditor-root .public-DraftEditor-content');
                        if (editor) {
                            editor.textContent = content;
                            return true;
                        }
                        return false;
                    }
                ''', content_editor.text_content())
                
                self._debug_print("[OK] 已尝试重新填充内容")
                time.sleep(2)
            else:
                self._debug_print(f"[OK] 字数正常: {word_count} 字符")
                
        except Exception as e:
            self._debug_print(f"[!] 检测字数时出错: {e}")
        
        return word_count
