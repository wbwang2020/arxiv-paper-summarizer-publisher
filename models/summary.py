from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class FigureTableInfo(BaseModel):
    """图表信息"""
    number: str = Field(..., description="编号")
    title: str = Field(..., description="标题")
    description: str = Field(default="", description="内容概述")


class ReferenceInfo(BaseModel):
    """参考文献信息"""
    authors: str = Field(default="", description="作者")
    year: str = Field(default="", description="年份")
    title: str = Field(default="", description="标题")
    journal: str = Field(default="", description="期刊/会议")
    volume_issue: str = Field(default="", description="卷期")
    pages: str = Field(default="", description="页码")


class PaperSummary(BaseModel):
    """论文详细总结"""
    
    # 基本信息（必须包含：作者、作者单位、发表年份、论文标题、期刊/会议名称）
    arxiv_id: str = Field(..., description="arXiv ID")
    title: str = Field(..., description="论文标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    author_affiliations: List[str] = Field(default_factory=list, description="作者单位列表")
    published_year: int = Field(..., description="发表年份")
    venue: str = Field(default="arXiv", description="期刊/会议名称")
    doi: Optional[str] = Field(None, description="DOI（如果有）")
    
    # AI总结内容
    motivation: str = Field(default="", description="研究动机")
    core_hypothesis: str = Field(default="", description="核心假设")
    research_design: str = Field(default="", description="研究设计")
    data_source: str = Field(default="", description="数据来源")
    methods: str = Field(default="", description="方法与技术")
    analysis_process: str = Field(default="", description="分析流程")
    data_analysis: str = Field(default="", description="数据分析方法")
    core_findings: str = Field(default="", description="核心发现")
    experimental_results: str = Field(default="", description="实验结果")
    supporting_results: str = Field(default="", description="辅助结果")
    conclusions: str = Field(default="", description="结论")
    contributions: str = Field(default="", description="贡献")
    relevance: str = Field(default="", description="与研究主题关联")
    highlights: str = Field(default="", description="亮点")
    figures_tables: List[FigureTableInfo] = Field(default_factory=list, description="图表信息")
    evaluation: str = Field(default="", description="评价")
    questions: str = Field(default="", description="疑问")
    inspiration: str = Field(default="", description="启发")
    references: List[ReferenceInfo] = Field(default_factory=list, description="参考文献")
    
    # 元数据
    summary_date: datetime = Field(default_factory=datetime.now, description="总结日期")
    ai_model: str = Field(default="", description="使用的AI模型")
    processing_time: float = Field(default=0.0, description="处理耗时(秒)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def to_markdown(self, include_metadata: bool = False) -> str:
        """转换为Markdown格式
        
        Args:
            include_metadata: 是否包含元数据
        """
        lines = []
        
        # 标题
        lines.append(f"# {self.title}")
        lines.append("")
        
        # 基本信息（包含：作者、作者单位、发表年份、论文标题、期刊/会议名称）
        lines.append("## 1. 基本信息")
        lines.append(f"- **论文标题**: {self.title}")
        lines.append(f"- **作者**: {', '.join(self.authors)}")
        
        # 作者单位
        if self.author_affiliations:
            lines.append(f"- **作者单位**: {', '.join(self.author_affiliations)}")
        
        lines.append(f"- **发表年份**: {self.published_year}")
        lines.append(f"- **期刊/会议**: {self.venue}")
        lines.append(f"- **arXiv ID**: {self.arxiv_id}")
        
        # DOI（如果有）
        if self.doi:
            lines.append(f"- **DOI**: {self.doi}")
        
        lines.append("")
        
        # 研究动机
        if self.motivation:
            lines.append("## 2. 研究动机")
            lines.append(self.motivation)
            lines.append("")
        
        # 核心假设
        if self.core_hypothesis:
            lines.append("## 3. 核心假设")
            lines.append(self.core_hypothesis)
            lines.append("")
        
        # 研究设计
        if self.research_design:
            lines.append("## 4. 研究设计")
            lines.append(self.research_design)
            lines.append("")
        
        # 数据来源
        if self.data_source:
            lines.append("## 5. 数据/样本来源")
            lines.append(self.data_source)
            lines.append("")
        
        # 方法与技术
        if self.methods:
            lines.append("## 6. 方法与技术")
            lines.append(self.methods)
            lines.append("")
        
        # 分析流程
        if self.analysis_process:
            lines.append("## 7. 分析流程")
            lines.append(self.analysis_process)
            lines.append("")
        
        # 数据分析
        if self.data_analysis:
            lines.append("## 8. 数据分析")
            lines.append(self.data_analysis)
            lines.append("")
        
        # 核心发现
        if self.core_findings:
            lines.append("## 9. 核心发现")
            lines.append(self.core_findings)
            lines.append("")
        
        # 实验结果
        if self.experimental_results:
            lines.append("## 10. 实验结果")
            lines.append(self.experimental_results)
            lines.append("")
        
        # 辅助结果
        if self.supporting_results:
            lines.append("## 11. 辅助结果")
            lines.append(self.supporting_results)
            lines.append("")
        
        # 结论
        if self.conclusions:
            lines.append("## 12. 结论")
            lines.append(self.conclusions)
            lines.append("")
        
        # 贡献
        if self.contributions:
            lines.append("## 13. 贡献")
            lines.append(self.contributions)
            lines.append("")
        
        # 关联性
        if self.relevance:
            lines.append("## 14. 与研究主题的关联")
            lines.append(self.relevance)
            lines.append("")
        
        # 亮点
        if self.highlights:
            lines.append("## 15. 亮点")
            lines.append(self.highlights)
            lines.append("")
        
        # 图表
        if self.figures_tables:
            lines.append("## 16. 图表信息")
            for ft in self.figures_tables:
                lines.append(f"- **{ft.number}**: {ft.title}")
                if ft.description:
                    lines.append(f"  - {ft.description}")
            lines.append("")
        
        # 评价
        if self.evaluation:
            lines.append("## 17. 评价")
            lines.append(self.evaluation)
            lines.append("")
        
        # 疑问
        if self.questions:
            lines.append("## 18. 疑问")
            lines.append(self.questions)
            lines.append("")
        
        # 启发
        if self.inspiration:
            lines.append("## 19. 启发")
            lines.append(self.inspiration)
            lines.append("")
        
        # 参考文献
        if self.references:
            lines.append("## 20. 参考文献")
            for i, ref in enumerate(self.references, 1):
                ref_str = f"{i}. "
                if ref.authors:
                    ref_str += f"{ref.authors}, "
                if ref.year:
                    ref_str += f"{ref.year}. "
                if ref.title:
                    ref_str += f"\"{ref.title}\". "
                if ref.journal:
                    ref_str += f"{ref.journal}"
                if ref.volume_issue:
                    ref_str += f", {ref.volume_issue}"
                if ref.pages:
                    ref_str += f", {ref.pages}"
                lines.append(ref_str)
            lines.append("")
        
        # 元数据
        if include_metadata:
            lines.append("---")
            lines.append(f"*总结生成时间: {self.summary_date.strftime('%Y-%m-%d %H:%M:%S')}*")
            lines.append(f"*AI模型: {self.ai_model}*")
            lines.append(f"*处理耗时: {self.processing_time:.2f}秒*")
        
        return "\n".join(lines)
