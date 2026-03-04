from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ArxivPaper(BaseModel):
    """arXiv论文基本信息"""
    
    arxiv_id: str = Field(..., description="arXiv ID (如: 2401.12345)")
    title: str = Field(..., description="论文标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    author_affiliations: List[str] = Field(default_factory=list, description="作者单位列表")
    abstract: str = Field(default="", description="摘要")
    categories: List[str] = Field(default_factory=list, description="分类列表")
    published_date: datetime = Field(..., description="发布日期")
    updated_date: Optional[datetime] = Field(None, description="更新日期")
    pdf_url: str = Field(..., description="PDF下载链接")
    abs_url: str = Field(..., description="摘要页面链接")
    primary_category: str = Field(..., description="主要分类")
    venue: Optional[str] = Field(None, description="期刊/会议名称（如果有）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def __str__(self) -> str:
        return f"[{self.arxiv_id}] {self.title}"
    
    def get_short_id(self) -> str:
        """获取短ID（去除版本号）"""
        return self.arxiv_id.split("v")[0]
    
    def get_authors_text(self, max_authors: int = 3) -> str:
        """获取作者文本表示"""
        if len(self.authors) <= max_authors:
            return ", ".join(self.authors)
        return ", ".join(self.authors[:max_authors]) + f" et al. ({len(self.authors)} authors)"
