import json
import re
import time
from typing import Optional, Dict, Union
from urllib.parse import urlencode

import requests

from config import ZhihuConfig
from models import PaperSummary, ArxivPaper
from utils import get_logger

logger = get_logger()


class ZhihuPublisher:
    """知乎文章发布器"""
    
    BASE_URL = "https://www.zhihu.com"
    API_URL = "https://www.zhihu.com/api/v4"
    
    def __init__(self, config: ZhihuConfig):
        self.config = config
        self.cookie = config.get_cookie()
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        
        if self.cookie:
            self.session.headers["Cookie"] = self.cookie
    
    def _extract_xsrf(self) -> Optional[str]:
        """从Cookie中提取XSRF token"""
        if not self.cookie:
            return None
        
        match = re.search(r'_xsrf=([^;]+)', self.cookie)
        if match:
            return match.group(1)
        return None
    
    def _get_xsrf_from_page(self) -> Optional[str]:
        """从页面HTML中提取XSRF token"""
        try:
            response = self.session.get(f"{self.BASE_URL}/", timeout=10)
            match = re.search(r'"xsrf":"([^"]+)"', response.text)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"从页面获取XSRF失败: {e}")
        return None
    
    def _markdown_to_zhihu_html(self, markdown: str) -> str:
        """
        将Markdown转换为知乎HTML格式
        
        Args:
            markdown: Markdown内容
            
        Returns:
            知乎HTML格式内容
        """
        content = markdown
        
        # 处理标题
        content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        
        # 处理粗体和斜体
        content = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', content)
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        
        # 处理代码块
        content = re.sub(
            r'```(\w+)?\n(.*?)```',
            r'<pre><code>\2</code></pre>',
            content,
            flags=re.DOTALL
        )
        # 确保代码块被正确转换
        content = content.replace('```', '<pre><code>').replace('```', '</code></pre>')
        
        # 处理行内代码
        content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
        
        # 处理水平分割线
        content = re.sub(r'^\s*---\s*$', r'<hr>', content, flags=re.MULTILINE)
        # 处理被包裹在p标签中的水平分割线
        content = re.sub(r'<p>\s*---\s*</p>', r'<hr>', content)
        
        # 处理列表
        # 无序列表
        lines = content.split('\n')
        result_lines = []
        in_ul = False
        in_ol = False
        
        for line in lines:
            ul_match = re.match(r'^(\s*)[-*] (.+)$', line)
            ol_match = re.match(r'^(\s*)\d+[.\)] (.+)$', line)
            
            if ul_match:
                if not in_ul:
                    result_lines.append('<ul>')
                    in_ul = True
                result_lines.append(f'<li>{ul_match.group(2)}</li>')
            elif ol_match:
                if not in_ol:
                    result_lines.append('<ol>')
                    in_ol = True
                result_lines.append(f'<li>{ol_match.group(2)}</li>')
            else:
                if in_ul:
                    result_lines.append('</ul>')
                    in_ul = False
                if in_ol:
                    result_lines.append('</ol>')
                    in_ol = False
                result_lines.append(line)
        
        if in_ul:
            result_lines.append('</ul>')
        if in_ol:
            result_lines.append('</ol>')
        
        content = '\n'.join(result_lines)
        
        # 处理链接
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', content)
        
        # 处理段落（空行分隔）
        paragraphs = content.split('\n\n')
        new_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            new_paragraphs.append(p)
        content = '\n\n'.join(new_paragraphs)
        
        # 处理分隔线
        content = re.sub(r'^---+$', '<hr>', content, flags=re.MULTILINE)
        
        return content
    
    def publish(
        self,
        summary: Union[PaperSummary, str],
        paper: ArxivPaper,
        as_draft: Optional[bool] = None
    ) -> Optional[str]:
        """
        发布文章到知乎
        
        Args:
            summary: 论文总结（PaperSummary对象或字符串）
            paper: 论文信息
            as_draft: 是否保存为草稿（默认使用配置）
            
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
            # 准备内容（使用论文原名作为标题）
            title = paper.title
            
            # 处理summary参数
            if isinstance(summary, PaperSummary):
                markdown_content = summary.to_markdown()
            else:
                markdown_content = summary
                
            html_content = self._markdown_to_zhihu_html(markdown_content)
            
            # 构建请求数据
            data = {
                "title": title,
                "content": html_content,
                "comment_permission": "all",  # 允许所有人评论
                "can_reward": False,
            }
            
            if as_draft:
                data["status"] = "draft"
            else:
                data["status"] = "publish"
            
            # 获取XSRF token
            xsrf = self._extract_xsrf() or self._get_xsrf_from_page()
            if xsrf:
                self.session.headers["x-xsrftoken"] = xsrf
            
            # 创建文章
            url = f"{self.API_URL}/articles"
            
            logger.info(f"正在发布文章到知乎: {title[:50]}...")
            logger.info(f"API URL: {url}")
            logger.info(f"请求数据键: {list(data.keys())}")
            
            response = self.session.post(
                url,
                json=data,
                timeout=30
            )
            
            logger.info(f"响应状态: {response.status_code}")
            logger.info(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                article_id = result.get("id")
                article_url = f"{self.BASE_URL}/p/{article_id}"
                
                logger.info(f"文章发布成功: {article_url}")
                
                # 处理专栏投稿
                column_id = self._get_target_column_id()
                if column_id and article_id:
                    self._add_to_column(article_id, column_id)
                
                return article_url
            else:
                logger.error(f"发布文章失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"发布到知乎时出错: {e}")
            return None
    
    def _get_target_column_id(self) -> Optional[str]:
        """
        获取目标专栏ID
        
        优先级：
        1. 直接配置的 column_id
        2. 通过 column_name 搜索
        3. 自动创建（如果配置了 create_column_if_not_exists）
        
        Returns:
            专栏ID，未找到返回None
        """
        # 1. 优先使用直接配置的 column_id
        if self.config.column_id:
            logger.info(f"使用配置的column_id: {self.config.column_id}")
            return self.config.column_id
        
        # 2. 如果配置了 column_name，尝试搜索
        if self.config.column_name:
            logger.info(f"按名称搜索专栏: {self.config.column_name}")
            
            # 先尝试查找现有专栏
            column = self.find_column_by_name(self.config.column_name)
            
            if column:
                logger.info(f"找到专栏: {column['title']} (ID: {column['id']})")
                return column["id"]
            
            # 如果配置了自动创建，则创建新专栏
            if self.config.create_column_if_not_exists:
                logger.info(f"创建新专栏: {self.config.column_name}")
                description = f"自动创建的专栏: {self.config.column_name}"
                return self.create_column(self.config.column_name, description)
            
            logger.warning(f"未找到专栏: {self.config.column_name}")
        
        logger.info("未配置专栏，文章将不发布到专栏")
        return None
    
    def _add_to_column(self, article_id: str, column_id: str) -> bool:
        """
        将文章添加到专栏
        
        Args:
            article_id: 文章ID
            column_id: 专栏ID
            
        Returns:
            是否成功
        """
        try:
            url = f"{self.API_URL}/columns/{column_id}/articles"
            data = {"id": article_id}
            
            response = self.session.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"文章已添加到专栏 {column_id}")
                return True
            else:
                logger.warning(f"添加文章到专栏失败: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"添加文章到专栏时出错: {e}")
            return False
    
    def check_login(self) -> bool:
        """
        检查登录状态
        
        Returns:
            是否已登录
        """
        if not self.cookie:
            return False
        
        try:
            # 尝试获取用户信息
            url = f"{self.API_URL}/me"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"已登录为: {data.get('name', 'Unknown')}")
                return True
            else:
                logger.warning(f"未登录: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"检查登录状态时出错: {e}")
            return False
    
    def get_columns(self) -> list:
        """
        获取用户的专栏列表
        
        注意：知乎API已变更，此方法现在通过搜索获取用户的专栏
        
        Returns:
            专栏列表
        """
        if not self.cookie:
            return []
        
        # 获取用户信息
        user_info = self.get_user_info()
        if not user_info:
            logger.warning("无法获取用户信息，无法获取专栏")
            return []
        
        # 使用搜索API获取用户的专栏
        return self.search_columns_by_author(user_info.get("name", ""))
    
    def search_columns(self, query: str, limit: int = 10) -> list:
        """
        搜索专栏
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            专栏列表
        """
        if not self.cookie:
            return []
        
        try:
            url = f"{self.API_URL}/search_v3"
            params = {
                "t": "column",
                "q": query,
                "offset": 0,
                "limit": limit
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                search_results = data.get("data", [])
                
                columns = []
                for result in search_results:
                    if result.get("type") == "search_result":
                        obj = result.get("object", {})
                        columns.append({
                            "id": obj.get("id"),
                            "title": obj.get("title"),
                            "description": obj.get("description"),
                            "url": obj.get("url"),
                            "author": obj.get("author", {}).get("name") if obj.get("author") else None,
                        })
                
                return columns
            else:
                logger.warning(f"搜索专栏失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"搜索专栏时出错: {e}")
            return []
    
    def search_columns_by_author(self, author_name: str) -> list:
        """
        搜索特定作者的专栏
        
        Args:
            author_name: 作者名称
            
        Returns:
            专栏列表
        """
        columns = self.search_columns(author_name, limit=20)
        
        # 过滤出该作者的专栏
        author_columns = [
            col for col in columns 
            if col.get("author") == author_name
        ]
        
        return author_columns
    
    def find_column_by_name(self, column_name: str) -> Optional[Dict]:
        """
        通过专栏名称搜索专栏
        
        优先搜索当前用户的专栏，如果找不到则搜索所有专栏
        
        Args:
            column_name: 专栏名称（支持部分匹配）
            
        Returns:
            专栏信息字典，未找到返回None
        """
        if not self.cookie or not column_name:
            return None
        
        logger.info(f"搜索专栏: {column_name}")
        
        # 获取当前用户信息
        user_info = self.get_user_info()
        current_user = user_info.get("name") if user_info else None
        
        # 使用搜索API搜索专栏
        all_columns = self.search_columns(column_name, limit=20)
        
        if not all_columns:
            logger.warning(f"未找到专栏: {column_name}")
            return None
        
        # 首先尝试在当前用户的专栏中匹配
        if current_user:
            user_columns = [col for col in all_columns if col.get("author") == current_user]
            
            # 精确匹配
            for col in user_columns:
                if col.get("title") == column_name:
                    logger.info(f"在用户专栏中找到精确匹配: {col['title']} (ID: {col['id']})")
                    return col
            
            # 部分匹配
            column_name_lower = column_name.lower()
            for col in user_columns:
                if column_name_lower in col.get("title", "").lower():
                    logger.info(f"在用户专栏中找到部分匹配: {col['title']} (ID: {col['id']})")
                    return col
        
        # 如果在用户专栏中找不到，尝试在所有结果中匹配
        for col in all_columns:
            if col.get("title") == column_name:
                logger.info(f"找到精确匹配: {col['title']} (ID: {col['id']}, 作者: {col.get('author')})")
                return col
        
        # 部分匹配
        column_name_lower = column_name.lower()
        for col in all_columns:
            if column_name_lower in col.get("title", "").lower():
                logger.info(f"找到部分匹配: {col['title']} (ID: {col['id']}, 作者: {col.get('author')})")
                return col
        
        logger.warning(f"未找到专栏: {column_name}")
        return None
    
    def get_or_create_column(self, column_name: str, description: str = "") -> Optional[str]:
        """
        获取或创建专栏
        
        Args:
            column_name: 专栏名称
            description: 专栏描述（创建时使用）
            
        Returns:
            专栏ID，失败返回None
        """
        # 先尝试查找现有专栏
        column = self.find_column_by_name(column_name)
        
        if column:
            logger.info(f"使用现有专栏: {column['title']} (ID: {column['id']})")
            return column["id"]
        
        # 如果配置了自动创建，则创建新专栏
        if self.config.create_column_if_not_exists:
            logger.info(f"未找到专栏，创建新专栏: {column_name}")
            return self.create_column(column_name, description)
        
        logger.warning(f"未找到专栏且禁用自动创建: {column_name}")
        return None
    
    def get_user_info(self) -> Optional[Dict]:
        """
        获取当前登录用户信息
        
        Returns:
            用户信息字典，未登录返回None
        """
        if not self.cookie:
            return None
        
        try:
            url = f"{self.API_URL}/me"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "url_token": data.get("url_token"),
                    "headline": data.get("headline"),
                    "avatar_url": data.get("avatar_url"),
                }
            else:
                logger.warning(f"获取用户信息失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息时出错: {e}")
            return None
    
    def create_column(self, title: str, description: str = "") -> Optional[str]:
        """
        创建知乎专栏
        
        Args:
            title: 专栏标题
            description: 专栏描述
            
        Returns:
            专栏ID，失败返回None
        """
        if not self.cookie:
            logger.error("未设置cookie，无法创建专栏")
            return None
        
        try:
            url = f"{self.API_URL}/columns"
            
            data = {
                "title": title,
                "description": description,
            }
            
            response = self.session.post(url, json=data, timeout=10)
            
            if response.status_code == 201:
                result = response.json()
                column_id = result.get("id")
                logger.info(f"专栏创建成功: {title} (ID: {column_id})")
                return column_id
            else:
                logger.warning(f"创建专栏失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"创建专栏时出错: {e}")
            return None
