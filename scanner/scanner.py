from datetime import datetime, timedelta
from typing import List, Optional
import time

import arxiv
import requests

from config import ArxivConfig
from models import ArxivPaper
from utils import get_logger

logger = get_logger()


class ArxivScanner:
    """arXiv论文扫描器"""
    
    def __init__(self, config: ArxivConfig):
        self.config = config
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=3
        )
    
    def _build_query(self, keywords: Optional[List[str]] = None, 
                     categories: Optional[List[str]] = None) -> str:
        """构建arXiv查询字符串"""
        query_parts = []
        
        # 添加分类条件
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({cat_query})")
        elif self.config.categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in self.config.categories])
            query_parts.append(f"({cat_query})")
        
        # 添加关键词条件
        search_keywords = keywords or self.config.keywords
        if search_keywords:
            # 在标题和摘要中搜索关键词
            kw_query = " OR ".join([f'all:"{kw}"' for kw in search_keywords])
            query_parts.append(f"({kw_query})")
        
        return " AND ".join(query_parts) if query_parts else ""
    
    def _get_sort_criterion(self) -> arxiv.SortCriterion:
        """获取排序标准"""
        sort_map = {
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "relevance": arxiv.SortCriterion.Relevance,
        }
        return sort_map.get(self.config.sort_by, arxiv.SortCriterion.SubmittedDate)
    
    def _get_sort_order(self) -> arxiv.SortOrder:
        """获取排序顺序"""
        order_map = {
            "ascending": arxiv.SortOrder.Ascending,
            "descending": arxiv.SortOrder.Descending,
        }
        return order_map.get(self.config.sort_order, arxiv.SortOrder.Descending)
    
    def _result_to_paper(self, result: arxiv.Result) -> ArxivPaper:
        """将arXiv结果转换为论文对象"""
        # 提取作者信息
        authors = []
        author_affiliations = []
        
        for author in result.authors:
            author_str = str(author)
            authors.append(author_str)
            # 尝试从作者字符串中提取单位（通常格式：Name (Affiliation)）
            if '(' in author_str and ')' in author_str:
                aff_start = author_str.find('(')
                aff_end = author_str.find(')')
                if aff_start > 0 and aff_end > aff_start:
                    affiliation = author_str[aff_start+1:aff_end].strip()
                    if affiliation and affiliation not in author_affiliations:
                        author_affiliations.append(affiliation)
        
        return ArxivPaper(
            arxiv_id=result.entry_id.split("/")[-1],
            title=result.title,
            authors=authors,
            author_affiliations=author_affiliations,
            abstract=result.summary,
            categories=result.categories,
            published_date=result.published,
            updated_date=result.updated,
            pdf_url=result.pdf_url,
            abs_url=result.entry_id,
            primary_category=result.primary_category
        )
    
    def search_papers(
        self,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_results: Optional[int] = None
    ) -> List[ArxivPaper]:
        """
        搜索arXiv论文
        
        Args:
            keywords: 关键词列表（OR关系）
            categories: 分类列表
            date_from: 起始日期
            date_to: 结束日期
            max_results: 最大结果数
            
        Returns:
            论文列表
        """
        query = self._build_query(keywords, categories)
        max_results = max_results or self.config.max_results
        
        logger.info(f"使用查询语句搜索arXiv: {query}")
        logger.info(f"最大结果数: {max_results}")
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=self._get_sort_criterion(),
            sort_order=self._get_sort_order()
        )
        
        papers = []
        try:
            for result in self.client.results(search):
                paper = self._result_to_paper(result)
                
                # 日期过滤
                if date_from:
                    # 确保日期比较是在相同的时区处理
                    if hasattr(paper.published_date, 'tzinfo') and paper.published_date.tzinfo is not None:
                        # 转换为naive datetime进行比较
                        if paper.published_date.replace(tzinfo=None) < date_from:
                            continue
                    else:
                        if paper.published_date < date_from:
                            continue
                if date_to:
                    if hasattr(paper.published_date, 'tzinfo') and paper.published_date.tzinfo is not None:
                        if paper.published_date.replace(tzinfo=None) > date_to:
                            continue
                    else:
                        if paper.published_date > date_to:
                            continue
                
                papers.append(paper)
                logger.debug(f"找到论文: {paper.arxiv_id} - {paper.title[:50]}...")
                
        except Exception as e:
            logger.error(f"搜索arXiv时出错: {e}")
            raise
        
        logger.info(f"找到 {len(papers)} 篇论文")
        return papers
    
    def search_recent_papers(self, days: Optional[int] = None) -> List[ArxivPaper]:
        """
        搜索最近N天的论文
        
        Args:
            days: 天数（默认使用配置）
            
        Returns:
            论文列表
        """
        days = days or self.config.days_back
        date_from = datetime.now() - timedelta(days=days)
        
        logger.info(f"搜索最近 {days} 天的论文 (自 {date_from.date()} 起)")
        
        return self.search_papers(date_from=date_from)
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """
        通过ID获取论文信息
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            论文对象，未找到返回None
        """
        # 清理ID（移除版本号）
        clean_id = arxiv_id.split("v")[0]
        
        search = arxiv.Search(id_list=[clean_id])
        
        try:
            results = list(self.client.results(search))
            if results:
                return self._result_to_paper(results[0])
        except Exception as e:
            logger.error(f"获取论文 {arxiv_id} 时出错: {e}")
        
        return None
    
    def download_pdf(self, paper: ArxivPaper, save_path: str, 
                     timeout: int = 60) -> bool:
        """
        下载PDF文件
        
        Args:
            paper: 论文对象
            save_path: 保存路径
            timeout: 超时时间
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"正在下载 {paper.arxiv_id} 的PDF")
            
            response = requests.get(paper.pdf_url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"PDF已保存到 {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载PDF时出错: {e}")
            return False
