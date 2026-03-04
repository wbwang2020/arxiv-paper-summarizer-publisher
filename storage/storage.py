import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple

from config import StorageConfig
from models import ArxivPaper, PaperSummary
from utils import get_logger, sanitize_filename

logger = get_logger()


class PaperStorage:
    """论文存储管理器 - 支持年-月文件夹结构和简报功能"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_dir = Path(config.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建根索引文件
        self.index_file = self.base_dir / "index.json"
        self._init_index()
    
    def _init_index(self):
        """初始化根索引文件"""
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict:
        """加载根索引"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_index(self, index: Dict):
        """保存根索引"""
        # 处理datetime对象
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2, default=serialize_datetime)
    
    def _get_year_month_folder(self, date: datetime) -> str:
        """获取年-月文件夹名称 (YYYY-MM)"""
        return date.strftime("%Y-%m")
    
    def _get_storage_path(self, paper: ArxivPaper) -> Path:
        """获取存储路径 (年-月格式)"""
        year_month = self._get_year_month_folder(paper.published_date)
        dir_path = self.base_dir / year_month
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def _get_brief_file_path(self, dir_path: Path) -> Path:
        """获取简报文件路径"""
        return dir_path / "brief.json"
    
    def _load_brief(self, dir_path: Path) -> Dict:
        """加载文件夹简报"""
        brief_file = self._get_brief_file_path(dir_path)
        try:
            if brief_file.exists():
                with open(brief_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"从 {brief_file} 加载简报时出错: {e}")
        return {"papers": {}}
    
    def _save_brief(self, dir_path: Path, brief: Dict):
        """保存文件夹简报"""
        brief_file = self._get_brief_file_path(dir_path)
        try:
            # 处理datetime对象
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            with open(brief_file, "w", encoding="utf-8") as f:
                json.dump(brief, f, ensure_ascii=False, indent=2, default=serialize_datetime)
            logger.debug(f"简报已保存到 {brief_file}")
        except Exception as e:
            logger.error(f"保存简报到 {brief_file} 时出错: {e}")
    
    def _generate_filename(self, paper: ArxivPaper, extension: str = "md") -> str:
        """生成文件名"""
        date_str = paper.published_date.strftime("%Y%m%d")
        arxiv_id = paper.arxiv_id.replace("/", "_")
        title = sanitize_filename(paper.title, max_length=50)
        
        filename = self.config.filename_template.format(
            date=date_str,
            arxiv_id=arxiv_id,
            title=title
        )
        
        # 添加扩展名
        if not filename.endswith(f".{extension}"):
            filename += f".{extension}"
        
        return sanitize_filename(filename, max_length=150)
    
    def _get_recent_year_month_folders(self, count: int = 2) -> List[Path]:
        """
        获取最近N个年-月文件夹
        
        Args:
            count: 获取的文件夹数量
            
        Returns:
            文件夹路径列表（按时间倒序）
        """
        folders = []
        
        # 扫描base_dir下的所有年-月文件夹
        for item in self.base_dir.iterdir():
            if item.is_dir():
                # 检查文件夹名是否符合 YYYY-MM 格式
                folder_name = item.name
                if re.match(r'^\d{4}-\d{2}$', folder_name):
                    try:
                        # 解析年月
                        year, month = map(int, folder_name.split('-'))
                        folder_date = datetime(year, month, 1)
                        folders.append((folder_date, item))
                    except (ValueError, Exception):
                        continue
        
        # 按日期倒序排序
        folders.sort(key=lambda x: x[0], reverse=True)
        
        # 返回最近N个
        return [folder[1] for folder in folders[:count]]
    
    def _get_all_arxiv_ids_in_folders(self, folders: List[Path]) -> Set[str]:
        """
        从指定文件夹的简报中获取所有arxiv_id
        
        Args:
            folders: 文件夹路径列表
            
        Returns:
            arxiv_id集合
        """
        arxiv_ids = set()
        
        for folder in folders:
            brief = self._load_brief(folder)
            papers = brief.get("papers", {})
            arxiv_ids.update(papers.keys())
        
        return arxiv_ids
    
    def is_paper_summarized_recently(self, arxiv_id: str, months: int = 2) -> bool:
        """
        检查论文是否在最近N个月内已被总结
        
        Args:
            arxiv_id: arXiv ID
            months: 检查的月数（默认2个月）
            
        Returns:
            是否已总结
        """
        recent_folders = self._get_recent_year_month_folders(months)
        recent_ids = self._get_all_arxiv_ids_in_folders(recent_folders)
        
        return arxiv_id in recent_ids
    
    def get_paper_summary_info(self, arxiv_id: str, months: int = 2) -> Optional[Dict]:
        """
        获取论文的总结信息（如果存在）
        
        Args:
            arxiv_id: arXiv ID
            months: 搜索的月数
            
        Returns:
            论文信息字典，未找到返回None
        """
        recent_folders = self._get_recent_year_month_folders(months)
        
        for folder in recent_folders:
            brief = self._load_brief(folder)
            papers = brief.get("papers", {})
            
            if arxiv_id in papers:
                info = papers[arxiv_id].copy()
                info["folder"] = folder.name
                return info
        
        return None
    
    def save_summary(
        self,
        summary: PaperSummary,
        paper: ArxivPaper,
        format: str = "markdown"
    ) -> str:
        """
        保存论文总结
        
        Args:
            summary: 论文总结
            paper: 论文信息
            format: 存储格式 (markdown, json)
            
        Returns:
            保存的文件路径
        """
        dir_path = self._get_storage_path(paper)
        
        if format == "markdown":
            filename = self._generate_filename(paper, "md")
            file_path = dir_path / filename
            content = summary.to_markdown(include_metadata=self.config.include_metadata)
        elif format == "json":
            filename = self._generate_filename(paper, "json")
            file_path = dir_path / filename
            # 处理datetime对象
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            content = json.dumps(summary.model_dump(), ensure_ascii=False, indent=2, default=serialize_datetime)
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 更新根索引
        index = self._load_index()
        index[paper.arxiv_id] = {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": paper.authors,
            "author_affiliations": paper.author_affiliations if hasattr(paper, 'author_affiliations') else [],
            "published_date": paper.published_date.isoformat(),
            "primary_category": paper.primary_category,
            "file_path": str(file_path),
            "saved_at": datetime.now().isoformat(),
        }
        self._save_index(index)
        
        # 更新文件夹简报
        brief = self._load_brief(dir_path)
        if "papers" not in brief:
            brief["papers"] = {}
        
        brief["papers"][paper.arxiv_id] = {
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": paper.authors,
            "author_affiliations": paper.author_affiliations if hasattr(paper, 'author_affiliations') else [],
            "published_date": paper.published_date.isoformat(),
            "primary_category": paper.primary_category,
            "file_path": str(file_path),
            "saved_at": datetime.now().isoformat(),
            "summary_date": summary.summary_date.isoformat() if hasattr(summary, 'summary_date') else datetime.now().isoformat(),
            "zhihu_published": False,  # 默认未发布
            "zhihu_article_url": None,
            "zhihu_published_at": None,
        }
        
        # 更新简报元数据
        brief["meta"] = {
            "folder": dir_path.name,
            "updated_at": datetime.now().isoformat(),
            "total_papers": len(brief["papers"])
        }
        
        self._save_brief(dir_path, brief)
        
        logger.info(f"总结已保存到 {file_path}")
        return str(file_path)
    
    def load_summary(self, arxiv_id: str) -> Optional[PaperSummary]:
        """
        加载已保存的总结
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            论文总结，未找到返回None
        """
        # 首先检查根索引
        index = self._load_index()
        
        if arxiv_id not in index:
            # 尝试在最近文件夹的简报中查找
            info = self.get_paper_summary_info(arxiv_id)
            if not info:
                return None
            file_path = info.get("file_path")
        else:
            file_path = index[arxiv_id].get("file_path")
        
        if not file_path or not os.path.exists(file_path):
            return None
        
        try:
            if file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return PaperSummary(**data)
            else:
                # Markdown格式需要重新解析，这里返回简化版本
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 从索引获取基本信息
                info = index.get(arxiv_id, {})
                if not info:
                    # 从简报获取
                    info = self.get_paper_summary_info(arxiv_id) or {}
                
                return PaperSummary(
                    arxiv_id=arxiv_id,
                    title=info.get("title", ""),
                    authors=info.get("authors", []),
                    published_year=datetime.fromisoformat(info["published_date"]).year if info.get("published_date") else datetime.now().year,
                    venue="arXiv"
                )
                
        except Exception as e:
            logger.error(f"加载 {arxiv_id} 的总结时出错: {e}")
            return None
    
    def exists(self, arxiv_id: str) -> bool:
        """
        检查论文是否已处理（全局检查）
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            是否已存在
        """
        index = self._load_index()
        
        if arxiv_id not in index:
            return False
        
        file_path = index[arxiv_id].get("file_path")
        return file_path and os.path.exists(file_path)
    
    def exists_in_recent_months(self, arxiv_id: str, months: int = 2) -> bool:
        """
        检查论文是否在最近N个月内已处理
        
        Args:
            arxiv_id: arXiv ID
            months: 检查的月数
            
        Returns:
            是否已存在
        """
        return self.is_paper_summarized_recently(arxiv_id, months)
    
    def list_summaries(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        列出已保存的总结
        
        Args:
            date_from: 起始日期
            date_to: 结束日期
            category: 分类过滤
            
        Returns:
            总结信息列表
        """
        index = self._load_index()
        results = []
        
        for arxiv_id, info in index.items():
            # 日期过滤
            if date_from or date_to:
                published = datetime.fromisoformat(info["published_date"])
                # 移除时区信息，使其成为offset-naive
                if hasattr(published, 'tzinfo') and published.tzinfo is not None:
                    published = published.replace(tzinfo=None)
                if date_from and published < date_from:
                    continue
                if date_to and published > date_to:
                    continue
            
            # 分类过滤
            if category and info.get("primary_category") != category:
                continue
            
            results.append(info)
        
        # 按日期排序
        results.sort(key=lambda x: x["published_date"], reverse=True)
        
        return results
    
    def list_recent_summaries(self, months: int = 2) -> List[Dict]:
        """
        列出最近N个月的总结
        
        Args:
            months: 月数
            
        Returns:
            总结信息列表
        """
        recent_folders = self._get_recent_year_month_folders(months)
        results = []
        
        for folder in recent_folders:
            brief = self._load_brief(folder)
            papers = brief.get("papers", {})
            for arxiv_id, info in papers.items():
                info_copy = info.copy()
                info_copy["folder"] = folder.name
                results.append(info_copy)
        
        # 按日期排序
        results.sort(key=lambda x: x.get("published_date", ""), reverse=True)
        
        return results
    
    def delete_summary(self, arxiv_id: str) -> bool:
        """
        删除已保存的总结
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            是否成功
        """
        index = self._load_index()
        
        if arxiv_id not in index:
            # 尝试从简报中查找
            info = self.get_paper_summary_info(arxiv_id)
            if not info:
                return False
            folder_name = info.get("folder")
            if folder_name:
                folder_path = self.base_dir / folder_name
                brief = self._load_brief(folder_path)
                if arxiv_id in brief.get("papers", {}):
                    del brief["papers"][arxiv_id]
                    brief["meta"]["total_papers"] = len(brief["papers"])
                    brief["meta"]["updated_at"] = datetime.now().isoformat()
                    self._save_brief(folder_path, brief)
            return True
        
        file_path = index[arxiv_id].get("file_path")
        
        try:
            # 删除文件
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            
            # 从文件夹简报中删除
            folder_name = Path(file_path).parent.name if file_path else None
            if folder_name:
                folder_path = self.base_dir / folder_name
                if folder_path.exists():
                    brief = self._load_brief(folder_path)
                    if arxiv_id in brief.get("papers", {}):
                        del brief["papers"][arxiv_id]
                        if "meta" in brief:
                            brief["meta"]["total_papers"] = len(brief["papers"])
                            brief["meta"]["updated_at"] = datetime.now().isoformat()
                        self._save_brief(folder_path, brief)
            
            # 从根索引中删除
            del index[arxiv_id]
            self._save_index(index)
            
            logger.info(f"已删除 {arxiv_id} 的总结")
            return True
            
        except Exception as e:
            logger.error(f"删除 {arxiv_id} 的总结时出错: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        index = self._load_index()
        
        categories = {}
        years = {}
        
        for info in index.values():
            cat = info.get("primary_category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            
            year = datetime.fromisoformat(info["published_date"]).year
            years[year] = years.get(year, 0) + 1
        
        # 获取文件夹统计
        folder_stats = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and re.match(r'^\d{4}-\d{2}$', item.name):
                brief = self._load_brief(item)
                total = len(brief.get("papers", {}))
                folder_stats.append({
                    "folder": item.name,
                    "total_papers": total
                })
        
        folder_stats.sort(key=lambda x: x["folder"], reverse=True)
        
        return {
            "total_papers": len(index),
            "by_category": categories,
            "by_year": years,
            "by_folder": folder_stats
        }
    
    def get_folder_brief(self, folder_name: str) -> Optional[Dict]:
        """
        获取指定文件夹的简报
        
        Args:
            folder_name: 文件夹名称 (YYYY-MM)
            
        Returns:
            简报内容，不存在返回None
        """
        folder_path = self.base_dir / folder_name
        if not folder_path.exists():
            return None
        
        return self._load_brief(folder_path)
    
    def update_zhihu_publish_status(
        self,
        arxiv_id: str,
        published: bool,
        article_url: Optional[str] = None
    ) -> bool:
        """
        更新知乎发布状态
        
        Args:
            arxiv_id: arXiv ID
            published: 是否已发布
            article_url: 知乎文章URL
            
        Returns:
            是否更新成功
        """
        try:
            # 查找论文所在的文件夹
            info = self.get_paper_summary_info(arxiv_id, months=12)
            if not info:
                logger.warning(f"无法更新发布状态: 未找到论文 {arxiv_id}")
                return False
            
            folder_name = info.get("folder")
            if not folder_name:
                logger.warning(f"无法更新发布状态: {arxiv_id} 的文件夹信息缺失")
                return False
            
            folder_path = self.base_dir / folder_name
            brief = self._load_brief(folder_path)
            
            if arxiv_id not in brief.get("papers", {}):
                logger.warning(f"无法更新发布状态: {arxiv_id} 不在简报中")
                return False
            
            # 更新发布状态
            brief["papers"][arxiv_id]["zhihu_published"] = published
            brief["papers"][arxiv_id]["zhihu_article_url"] = article_url
            brief["papers"][arxiv_id]["zhihu_published_at"] = datetime.now().isoformat() if published else None
            
            # 更新简报元数据
            brief["meta"]["updated_at"] = datetime.now().isoformat()
            
            self._save_brief(folder_path, brief)
            
            status = "已发布" if published else "未发布"
            logger.info(f"已更新 {arxiv_id} 的知乎发布状态: {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新 {arxiv_id} 的发布状态时出错: {e}")
            return False
    
    def is_zhihu_published(self, arxiv_id: str, months: int = 2) -> bool:
        """
        检查论文是否已发布到知乎
        
        Args:
            arxiv_id: arXiv ID
            months: 搜索最近N个月的文件夹
            
        Returns:
            是否已发布
        """
        info = self.get_paper_summary_info(arxiv_id, months=months)
        if not info:
            return False
        
        return info.get("zhihu_published", False)
