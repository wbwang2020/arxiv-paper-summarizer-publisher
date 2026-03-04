from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .paper import ArxivPaper
from .summary import PaperSummary


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    SCANNING = "scanning"
    DOWNLOADING = "downloading"
    SUMMARIZING = "summarizing"
    STORING = "storing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PaperTask(BaseModel):
    """论文处理任务"""
    
    task_id: str = Field(..., description="任务ID (UUID)")
    arxiv_id: str = Field(..., description="arXiv ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(default=0, description="重试次数")
    paper: Optional[ArxivPaper] = Field(None, description="论文信息")
    summary: Optional[PaperSummary] = Field(None, description="论文总结")
    local_path: Optional[str] = Field(None, description="本地文件路径")
    zhihu_url: Optional[str] = Field(None, description="知乎文章URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def update_status(self, status: TaskStatus, error_message: Optional[str] = None):
        """更新任务状态"""
        self.status = status
        self.updated_at = datetime.now()
        if error_message:
            self.error_message = error_message
    
    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        self.updated_at = datetime.now()
    
    def is_successful(self) -> bool:
        """检查任务是否成功完成"""
        return self.status == TaskStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.status == TaskStatus.FAILED
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """检查是否可以重试"""
        return self.retry_count < max_retries and (self.status == TaskStatus.FAILED or self.status == TaskStatus.PENDING)
