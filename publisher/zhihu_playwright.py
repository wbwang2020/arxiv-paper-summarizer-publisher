#!/usr/bin/env python3
"""
使用 Playwright 自动化发布文章到知乎专栏
作为知乎API的替代方案

模块结构：
- title_settings: 题目设置模块
- publish_settings: 发布设置模块  
- content_filler: 文章主体填充模块
"""
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from config import ZhihuConfig, StorageConfig
from models import ArxivPaper, PaperSummary
from storage.storage import PaperStorage
from utils import get_logger

# 导入子模块
from publisher.zhihu_modules import TitleSettingsHandler, PublishSettingsHandler, ContentFiller

logger = get_logger()


class ZhihuPlaywrightPublisher:
    """使用 Playwright 的知乎文章发布器"""
    
    BASE_URL = "https://www.zhihu.com"
    EDITOR_URL = "https://zhuanlan.zhihu.com/write"
    
    def __init__(self, config: ZhihuConfig):
        """
        初始化发布器
        
        Args:
            config: 知乎配置
        """
        self.config = config
        self.cookie = config.cookie
        self.debug = config.debug
        self.playwright = None  # 保存 playwright 实例
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 初始化存储管理器
        storage_config = StorageConfig()
        self.storage = PaperStorage(storage_config)
        
        # 初始化子模块（将在浏览器初始化后设置）
        self.title_handler: Optional[TitleSettingsHandler] = None
        self.publish_settings_handler: Optional[PublishSettingsHandler] = None
        self.content_filler: Optional[ContentFiller] = None
    
    def _debug_print(self, message: str):
        """调试模式下输出信息"""
        if self.debug:
            print(message)
    
    def _debug_screenshot(self, path: str):
        """调试模式下保存截图"""
        if self.debug and self.page:
            try:
                self.page.screenshot(path=path)
                print(f"[CAMERA] 已保存截图: {path}")
            except Exception as e:
                print(f"[!] 截图失败: {e}")
    
    def _init_handlers(self):
        """初始化子模块处理器"""
        if self.page:
            self.title_handler = TitleSettingsHandler(
                self.page, 
                self._debug_print, 
                self._debug_screenshot
            )
            self.publish_settings_handler = PublishSettingsHandler(
                self.page,
                self._debug_print,
                self._debug_screenshot
            )
            self.content_filler = ContentFiller(
                self.page,
                self._debug_print,
                self._debug_screenshot
            )
        
    def _parse_cookies(self) -> list:
        """
        解析Cookie字符串为Playwright可用的格式
        
        Returns:
            Cookie列表
        """
        cookies = []
        if not self.cookie:
            return cookies
        
        # 解析Cookie字符串
        for item in self.cookie.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.zhihu.com',
                    'path': '/'
                })
        
        return cookies
    
    def _init_browser(self, headless: bool = False):
        """
        初始化浏览器
        
        Args:
            headless: 是否无头模式（调试时可设为False）
        """
        logger.info("正在初始化Playwright浏览器...")
        self._debug_print("正在初始化浏览器...")
        
        try:
            self.playwright = sync_playwright().start()
            logger.info("Playwright启动成功")
        except Exception as e:
            logger.error(f"启动Playwright失败: {e}")
            raise
        
        # 尝试使用系统安装的Chrome浏览器
        try:
            self._debug_print("尝试使用系统Chrome浏览器...")
            self.browser = self.playwright.chromium.launch(
                channel="chrome",
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            logger.info("使用系统Chrome浏览器")
            self._debug_print("[OK] 成功使用系统Chrome浏览器")
        except Exception as e:
            logger.warning(f"使用系统Chrome失败: {e}，尝试使用chromium")
            self._debug_print(f"[!] 系统Chrome不可用: {e}")
            self._debug_print("尝试使用Playwright自带的Chromium...")
            try:
                self.browser = self.playwright.chromium.launch(
                    headless=headless,
                    args=['--disable-blink-features=AutomationControlled']
                )
                logger.info("使用Playwright Chromium")
                self._debug_print("[OK] 成功使用Playwright Chromium")
            except Exception as e2:
                logger.error(f"启动Chromium失败: {e2}")
                self._debug_print(f"[X] 无法启动浏览器: {e2}")
                raise
        
        # 创建上下文并设置Cookie
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 添加Cookie
        cookies = self._parse_cookies()
        if cookies:
            self.context.add_cookies(cookies)
            logger.info(f"已添加 {len(cookies)} 个cookie")
        
        self.page = self.context.new_page()
        
        # 注入脚本隐藏自动化特征
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        # 初始化子模块
        self._init_handlers()
    
    def _close_browser(self):
        """关闭浏览器"""
        try:
            if self.context:
                try:
                    self.context.close()
                except Exception as e:
                    logger.warning(f"关闭上下文失败: {e}")
        except Exception as e:
            logger.warning(f"关闭上下文时出错: {e}")
        
        try:
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.warning(f"关闭浏览器失败: {e}")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
        
        try:
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.warning(f"停止Playwright失败: {e}")
        except Exception as e:
            logger.warning(f"停止Playwright时出错: {e}")
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.title_handler = None
        self.publish_settings_handler = None
        self.content_filler = None
    
    def check_login(self) -> bool:
        """
        检查登录状态
        
        Returns:
            是否已登录
        """
        try:
            self._init_browser(headless=True)
            
            self._debug_print("正在访问知乎首页...")
            self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=60000)
            self._debug_print(f"[OK] 成功访问知乎首页: {self.page.url}")
            
            self._debug_print("等待页面加载完成...")
            self.page.wait_for_load_state('networkidle', timeout=60000)
            self._debug_print("[OK] 页面加载完成")
            
            self._debug_screenshot("debug_login_check.png")
            
            self._debug_print("检查登录状态...")
            user_elements = self.page.query_selector_all('.AppHeader-profileEntry, .UserName, [data-za-detail-view-id="5412"]')
            is_logged_in = len(user_elements) > 0
            
            if is_logged_in:
                logger.info("登录检查通过")
                self._debug_print("[OK] 知乎登录状态正常")
            else:
                logger.warning("登录检查失败 - 未找到用户元素")
                self._debug_print("[X] 知乎登录状态异常")
            
            self._debug_print(f"页面标题: {self.page.title()}")
            
            return is_logged_in
            
        except Exception as e:
            logger.error(f"检查登录状态时出错: {e}")
            self._debug_print(f"[X] 测试登录状态失败: {e}")
            self._debug_screenshot("debug_login_error.png")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self._close_browser()
    
    def _fill_editor(self, title: str, content: str, file_path: str = None):
        """
        填充编辑器内容
        
        流程：
        1. 编辑题目
        2. 编辑发布设置（创作声明、专栏选择、话题添加）
        3. 填充正文
        4. 检测字数
        5. 测试发布按钮状态
        
        Args:
            title: 文章标题
            content: 文章内容（Markdown格式）
            file_path: 文件路径（用于导入文档模式）
        """
        logger.info("正在填充编辑器内容...")
        self._debug_print("正在填充编辑器内容...")
        
        # 等待编辑器加载
        self._debug_print("等待编辑器加载...")
        self.page.wait_for_selector('textarea[placeholder*="标题"], .WriteIndex-titleInput textarea', timeout=30000)
        time.sleep(2)
        self._debug_print("[OK] 编辑器已加载")
        
        self._debug_screenshot("debug_editor_initial.png")
        
        # 1. 编辑题目
        if self.title_handler:
            processed_title = self.title_handler.set_title(title)
        else:
            # 备用方案：直接在主模块处理
            self._debug_print("\n1. 编辑题目...")
            if len(title) > 100:
                title = title[:97] + "..."
            title_input = self.page.query_selector('textarea[placeholder*="标题"], .WriteIndex-titleInput textarea')
            if title_input:
                title_input.fill("")
                time.sleep(0.5)
                title_input.fill(title)
                time.sleep(0.5)
            processed_title = title
        
        # 2. 编辑发布设置
        if self.publish_settings_handler:
            self.publish_settings_handler.configure_publish_settings(self.config.column_name)
        
        # 3. 填充正文
        content_fill_mode = getattr(self.config, 'content_fill_mode', 'copy_paste')
        if self.content_filler:
            self.content_filler.fill_content(content, file_path, content_fill_mode)
        
        logger.info("内容填充成功")
        self._debug_print("[OK] 文章内容填充完成")
    
    def _select_column(self, column_name: str) -> bool:
        """
        选择专栏（向后兼容方法）
        
        Args:
            column_name: 专栏名称
            
        Returns:
            是否选择成功
        """
        if self.publish_settings_handler:
            return self.publish_settings_handler._select_column(column_name)
        return False
    
    def _publish_article(self, as_draft: bool = False) -> Optional[str]:
        """
        发布文章
        
        Args:
            as_draft: 是否保存为草稿
            
        Returns:
            文章URL，失败返回None
        """
        logger.info("正在发布文章...")
        self._debug_print("正在发布文章...")
        
        try:
            if as_draft:
                return self._publish_as_draft()
            else:
                return self._publish_directly()
        except Exception as e:
            logger.error(f"发布文章时出错: {e}")
            self._debug_print(f"[X] 发布文章时出错: {e}")
            return None
    
    def _publish_as_draft(self) -> Optional[str]:
        """发布为草稿"""
        self._debug_print("[!] 知乎草稿会自动保存，正在等待自动保存完成...")
        
        initial_url = self.page.url
        self._debug_print(f"初始URL: {initial_url}")
        
        if '/draft/' in initial_url or '/p/' in initial_url:
            self._debug_print(f"[OK] 草稿自动保存成功! 文章URL: {initial_url}")
            return initial_url
        
        for i in range(6):
            time.sleep(5)
            current_url = self.page.url
            self._debug_print(f"当前URL: {current_url}")
            
            if '/draft/' in current_url or '/p/' in current_url:
                self._debug_print(f"[OK] 草稿自动保存成功! 文章URL: {current_url}")
                return current_url
            elif current_url != initial_url:
                self._debug_print(f"[OK] 草稿自动保存成功! 文章URL: {current_url}")
                return current_url
        
        article_url = self.page.url
        self._debug_print(f"[!] 自动保存超时，但返回当前URL: {article_url}")
        return article_url
    
    def _publish_directly(self) -> Optional[str]:
        """直接发布文章"""
        time.sleep(2)
        
        self._debug_print("等待页面完全加载...")
        time.sleep(2)
        
        self._debug_screenshot("debug_before_publish.png")
        
        self._debug_print(f"当前页面URL: {self.page.url}")
        
        # 查找发布按钮
        publish_button = self._find_publish_button()
        
        if not publish_button:
            self._debug_print("[X] 未找到发布按钮")
            return None
        
        # 检查内容长度
        self._check_content_length()
        
        # 等待按钮激活
        if not self._wait_for_button_active(publish_button):
            self._debug_print("[!] 发布按钮未激活，尝试强制点击")
        
        # 多次尝试点击发布按钮
        max_click_attempts = 3
        for attempt in range(max_click_attempts):
            self._debug_print(f"\n尝试点击发布按钮 ({attempt + 1}/{max_click_attempts})...")
            
            # 点击发布按钮
            if not self._click_publish_button(publish_button):
                return None
            
            # 等待一下看是否有弹窗或页面变化
            time.sleep(2)
            
            # 检查是否有弹窗出现
            modal_handled = self._handle_publish_modal()
            if modal_handled:
                self._debug_print("[OK] 处理了发布弹窗")
                time.sleep(3)
            
            # 检查URL是否变化
            current_url = self.page.url
            if '/p/' in current_url and '/edit' not in current_url:
                logger.info(f"文章已发布: {current_url}")
                self._debug_print(f"[OK] 发布成功! 文章URL: {current_url}")
                return current_url
            
            # 检查是否有新窗口/标签页打开
            pages = self.page.context.pages
            if len(pages) > 1:
                self._debug_print("[OK] 检测到新页面打开")
                # 切换到新页面
                new_page = pages[-1]
                new_url = new_page.url
                if '/p/' in new_url:
                    logger.info(f"文章已在新标签页发布: {new_url}")
                    self._debug_print(f"[OK] 发布成功! 新页面URL: {new_url}")
                    return new_url
            
            # 如果仍在编辑页面，重新查找发布按钮
            publish_button = self._find_publish_button()
            if not publish_button:
                self._debug_print("[OK] 发布按钮消失，可能已发布成功")
                return self.page.url
        
        # 等待页面跳转
        return self._wait_for_publish_completion()
    
    def _find_publish_button(self):
        """查找发布按钮"""
        self._debug_print("寻找发布按钮...")
        
        publish_button_selectors = [
            'button:has-text("发布")',
            '.WriteIndex-publishButton',
            'button[class*="publish"]',
            '//button[contains(text(), "发布")]'
        ]
        
        for selector in publish_button_selectors:
            try:
                self._debug_print(f"尝试选择器: {selector}")
                elem = self.page.query_selector(selector)
                if elem and elem.is_visible():
                    self._debug_print(f"[OK] 找到发布按钮: {selector}")
                    return elem
            except Exception as e:
                self._debug_print(f"选择器 {selector} 失败: {e}")
                continue
        
        return None
    
    def _check_content_length(self):
        """检查内容长度 - 从状态栏读取字数"""
        self._debug_print("检查内容长度...")
        try:
            # 从状态栏读取字数 - 与content_filler.py中的实现一致
            word_count_selectors = [
                '.WriteIndex-statusBar span:has-text("字数")',
                '.WriteIndex-statusBar span:nth-child(1)',
                '.WriteIndex-statusBar',
                '[class*="statusBar"] span:has-text("字数")',
                '[class*="status"] span:has-text("字数")',
                'span:has-text("字数")',
                'div:has-text("字数")'
            ]
            
            word_count = 0
            for selector in word_count_selectors:
                try:
                    self._debug_print(f"尝试选择器: {selector}")
                    status_elem = self.page.query_selector(selector)
                    if status_elem:
                        text = status_elem.text_content()
                        self._debug_print(f"状态栏文本: {text}")
                        # 提取字数 - 格式为 "字数：8862" 或 "字数:8862"
                        match = re.search(r'字数[：:](\d+)', text)
                        if match:
                            word_count = int(match.group(1))
                            self._debug_print(f"从状态栏读取到字数: {word_count}")
                            break
                except Exception as e:
                    self._debug_print(f"选择器 {selector} 失败: {e}")
                    continue
            
            if word_count == 0:
                # 如果无法从状态栏读取，尝试从编辑器内容计算
                self._debug_print("[!] 无法从状态栏读取字数，尝试从编辑器内容计算...")
                content_editor = self.page.query_selector('.DraftEditor-root .public-DraftEditor-content')
                if content_editor:
                    content_text = content_editor.text_content()
                    word_count = len(content_text.strip())
                    self._debug_print(f"从编辑器内容计算字数: {word_count}")
            
            self._debug_print(f"当前正文内容长度: {word_count} 字符")
            
            if word_count < 8:
                self._debug_print("[!] 正文内容长度不足8个字符，尝试添加额外内容")
                self.page.keyboard.press('End')
                time.sleep(0.5)
                self.page.keyboard.type("\n\n*注：本文由自动生成工具发布*")
                self._debug_print("[OK] 已添加额外内容")
                time.sleep(1)
        except Exception as e:
            self._debug_print(f"检查内容长度时出错: {e}")
    
    def _is_button_active(self, btn) -> bool:
        """检查按钮是否激活"""
        try:
            is_disabled = btn.is_disabled() or btn.get_attribute('disabled') is not None
            if is_disabled:
                return False
            
            computed_style = self.page.evaluate('(elem) => window.getComputedStyle(elem)', btn)
            background_color = computed_style.get('background-color', '')
            opacity = computed_style.get('opacity', '1')
            class_name = btn.get_attribute('class') or ''
            
            disabled_classes = ['disabled', 'Disabled', 'btn-disabled', 'is-disabled']
            for cls in disabled_classes:
                if cls in class_name:
                    return False
            
            if (is_disabled is False and 
                opacity == '1' and 
                '999' not in background_color.lower() and
                'gray' not in background_color.lower() and
                'grey' not in background_color.lower()):
                return True
            
            return not is_disabled
        except Exception as e:
            self._debug_print(f"检查按钮状态时出错: {e}")
            return not (btn.is_disabled() or btn.get_attribute('disabled') is not None)
    
    def _wait_for_button_active(self, publish_button, max_wait_time: int = 30) -> bool:
        """等待按钮激活"""
        self._debug_print(f"等待发布按钮激活（最大等待{max_wait_time}秒）...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            is_active = self._is_button_active(publish_button)
            self._debug_print(f"  按钮激活状态: {is_active}")
            
            if is_active:
                self._debug_print("[OK] 发布按钮已激活")
                return True
            
            try:
                content_editor = self.page.query_selector('.DraftEditor-root .public-DraftEditor-content')
                if content_editor:
                    content_editor.click()
                    self._debug_print("  尝试点击编辑器区域，触发状态更新")
            except Exception as e:
                self._debug_print(f"  点击编辑器区域时出错: {e}")
            
            time.sleep(1)
        
        return False
    
    def _click_publish_button(self, publish_button) -> bool:
        """点击发布按钮"""
        click_success = False
        
        # 方式1: 普通点击（最高优先级）
        self._debug_print("尝试方式1: 普通点击...")
        try:
            publish_button.click()
            click_success = True
            self._debug_print("[OK] 普通点击成功")
        except Exception as e:
            self._debug_print(f"[!] 普通点击失败: {e}")
        
        # 方式2: force_click
        if not click_success:
            self._debug_print("尝试方式2: force_click强制点击...")
            try:
                publish_button.click(force=True)
                click_success = True
                self._debug_print("[OK] force_click成功")
            except Exception as e:
                self._debug_print(f"[!] force_click失败: {e}")
        
        # 方式3: JavaScript点击
        if not click_success:
            self._debug_print("尝试方式3: JavaScript点击...")
            try:
                self.page.evaluate('(elem) => elem.click()', publish_button)
                click_success = True
                self._debug_print("[OK] JavaScript点击成功")
            except Exception as e:
                self._debug_print(f"[!] JavaScript点击失败: {e}")
        
        if click_success:
            logger.info("已点击发布按钮")
            self._debug_print("[OK] 正在发布文章...")
            time.sleep(1)
            self._debug_screenshot("debug_after_click.png")
            time.sleep(2)
            self._debug_screenshot("debug_after_wait.png")
        
        return click_success
    
    def _handle_publish_modal(self) -> bool:
        """处理发布弹窗
        
        Returns:
            是否处理了弹窗
        """
        self._debug_print("检查是否有弹窗出现...")
        
        modal_selectors = [
            '.Modal-wrapper',
            '.Modal-inner',
            '[class*="modal"]',
            '[class*="dialog"]',
            '[role="dialog"]',
            '.Modal'
        ]
        
        for selector in modal_selectors:
            try:
                modal = self.page.query_selector(selector)
                if modal and modal.is_visible():
                    self._debug_print(f"[OK] 发现弹窗: {selector}")
                    
                    confirm_selectors = [
                        'button:has-text("确认")',
                        'button:has-text("确定")',
                        'button:has-text("发布")'
                    ]
                    
                    for conf_selector in confirm_selectors:
                        try:
                            confirm_btn = modal.query_selector(conf_selector)
                            if confirm_btn and confirm_btn.is_visible():
                                self._debug_print(f"[OK] 找到确认按钮: {conf_selector}")
                                confirm_btn.click()
                                self._debug_print("[OK] 已点击确认按钮")
                                time.sleep(3)
                                return True
                        except:
                            continue
                    break
            except:
                continue
        
        self._debug_print("[!] 未发现弹窗，可能直接发布了")
        return False
    
    def _wait_for_publish_completion(self, max_attempts: int = 3) -> Optional[str]:
        """等待发布完成"""
        self._debug_print("等待页面跳转到文章详情页...")
        
        for i in range(max_attempts):
            current_url = self.page.url
            self._debug_print(f"尝试 {i+1}/{max_attempts} - 当前URL: {current_url}")
            
            if '/p/' in current_url and '/edit' not in current_url:
                logger.info(f"文章已发布: {current_url}")
                self._debug_print(f"[OK] 发布成功! 文章URL: {current_url}")
                return current_url
            
            # 如果仍在编辑页面，可能发布按钮没有反应，尝试再次点击
            if '/edit' in current_url:
                self._debug_print("[!] 仍在编辑页面，尝试再次点击发布按钮...")
                publish_button = self._find_publish_button()
                if publish_button:
                    try:
                        publish_button.click()
                        self._debug_print("[OK] 再次点击发布按钮")
                        time.sleep(3)
                    except Exception as e:
                        self._debug_print(f"[!] 再次点击失败: {e}")
            
            time.sleep(5)
        
        self._debug_print(f"[X] 发布超时：{max_attempts}次尝试后仍未获取到发布后的URL")
        return None
    
    def publish(
        self,
        summary: PaperSummary,
        paper: ArxivPaper,
        as_draft: Optional[bool] = None,
        headless: bool = True
    ) -> Optional[str]:
        """
        发布文章到知乎
        
        Args:
            summary: 论文总结
            paper: 论文信息
            as_draft: 是否保存为草稿
            headless: 是否无头模式
            
        Returns:
            知乎文章URL，失败返回None
        """
        if not self.config.enabled:
            logger.info("知乎发布器已禁用")
            return None
        
        if not self.cookie:
            logger.error("知乎cookie未配置")
            return None
        
        as_draft = as_draft if as_draft is not None else self.config.draft_first
        
        try:
            self._init_browser(headless=headless)
            
            logger.info("正在打开知乎编辑器...")
            self.page.goto(self.EDITOR_URL, wait_until='networkidle', timeout=60000)
            time.sleep(3)
            
            title = paper.title
            markdown_content = summary.to_markdown() if hasattr(summary, 'to_markdown') else str(summary)
            
            self._fill_editor(title, markdown_content)
            
            article_url = self._publish_article(as_draft)
            
            if article_url:
                logger.info(f"文章发布成功: {article_url}")
                self._debug_print(f"[OK] 文章发布成功! 链接: {article_url}")
                
                # 更新brief.json中的发布状态
                self._debug_print("更新brief.json中的发布状态...")
                success = self.storage.update_zhihu_publish_status(
                    paper.arxiv_id,
                    True,
                    article_url
                )
                if success:
                    self._debug_print("[OK] 发布状态更新成功")
                else:
                    self._debug_print("[!] 发布状态更新失败")
            else:
                logger.warning("文章发布失败 - 未返回URL")
                self._debug_print("[X] 文章发布失败")
            
            return article_url
            
        except Exception as e:
            logger.error(f"发布到知乎时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self._close_browser()
    
    def publish_from_file(
        self,
        file_path: str,
        paper: ArxivPaper,
        as_draft: Optional[bool] = None,
        headless: bool = True
    ) -> Optional[str]:
        """
        从Markdown文件发布文章到知乎
        
        Args:
            file_path: Markdown文件路径
            paper: 论文信息
            as_draft: 是否保存为草稿
            headless: 是否无头模式
            
        Returns:
            知乎文章URL，失败返回None
        """
        if not self.config.enabled:
            logger.info("Zhihu publisher is disabled")
            return None
        
        if not self.cookie:
            logger.error("Zhihu cookie is not configured")
            return None
        
        as_draft = as_draft if as_draft is not None else self.config.draft_first
        
        try:
            self._debug_print(f"正在读取Markdown文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            self._debug_print(f"[OK] 成功读取Markdown文件，内容长度: {len(markdown_content)} 字符")
            
            self._debug_print("正在初始化浏览器...")
            self._init_browser(headless=headless)
            self._debug_print("[OK] 浏览器初始化完成")
            
            logger.info("Opening Zhihu editor...")
            self._debug_print("正在打开知乎编辑器...")
            try:
                self.page.goto(self.EDITOR_URL, wait_until='domcontentloaded', timeout=60000)
                self._debug_print(f"[OK] 成功打开知乎编辑器: {self.EDITOR_URL}")
                
                self._debug_screenshot("debug_initial_page.png")
                
                self._debug_print("等待页面元素加载...")
                self.page.wait_for_load_state('networkidle', timeout=60000)
                self._debug_print("[OK] 页面元素加载完成")
            except Exception as e:
                logger.error(f"Failed to open editor: {e}")
                self._debug_print(f"[X] 打开知乎编辑器失败: {e}")
                self._debug_screenshot("debug_open_error.png")
                raise
            
            time.sleep(2)
            
            title = paper.title
            self._debug_print(f"准备填充编辑器，标题: {title[:50]}...")
            
            try:
                self._fill_editor(title, markdown_content, file_path)
                self._debug_print("[OK] 编辑器填充完成")
            except Exception as e:
                logger.error(f"Failed to fill editor: {e}")
                self._debug_print(f"[X] 填充编辑器失败: {e}")
                self._debug_screenshot("debug_fill_error.png")
                raise
            
            try:
                self._debug_print("正在发布文章...")
                article_url = self._publish_article(as_draft)
                
                if article_url:
                    logger.info(f"Article published successfully: {article_url}")
                    self._debug_print(f"[OK] 文章发布成功! 链接: {article_url}")
                    
                    # 更新brief.json中的发布状态
                    self._debug_print("更新brief.json中的发布状态...")
                    success = self.storage.update_zhihu_publish_status(
                        paper.arxiv_id,
                        True,
                        article_url
                    )
                    if success:
                        self._debug_print("[OK] 发布状态更新成功")
                    else:
                        self._debug_print("[!] 发布状态更新失败")
                else:
                    logger.warning("Article publish failed - no URL returned")
                    self._debug_print("[X] 文章发布失败")
            except Exception as e:
                logger.error(f"Failed to publish article: {e}")
                self._debug_print(f"[X] 发布文章失败: {e}")
                self._debug_screenshot("debug_publish_error.png")
                raise
            
            return article_url
            
        except Exception as e:
            logger.error(f"Error publishing to Zhihu: {e}")
            self._debug_print(f"[X] 发布失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self._close_browser()
