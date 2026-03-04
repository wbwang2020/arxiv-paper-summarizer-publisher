import os
from typing import List, Optional
from pydantic import BaseModel, Field
import yaml


class ArxivConfig(BaseModel):
    """arXiv配置"""
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    categories: List[str] = Field(default_factory=list, description="分类列表")
    days_back: int = Field(default=7, description="扫描最近N天的论文")
    max_results: int = Field(default=50, description="每次最大获取数量")
    sort_by: str = Field(default="submittedDate", description="排序方式")
    sort_order: str = Field(default="descending", description="排序顺序")


class SummarySectionConfig(BaseModel):
    """章节配置定义"""
    section_number: str = Field(description="章节编号（对应提示词模板中的 ## N. 格式）")
    field_name: str = Field(description="映射到PaperSummary对象的字段名")
    description: str = Field(description="章节描述")
    field_type: str = Field(default="string", description="字段类型: string, list")


class AIConfig(BaseModel):
    """AI配置"""
    provider: str = Field(default="deepseek", description="AI提供商")
    api_key: str = Field(default="", description="API密钥")
    api_url: str = Field(default="https://api.deepseek.com/v1/chat/completions", description="API地址")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=8000, description="最大token数")
    max_input_tokens: int = Field(default=131072, description="最大输入token数 (128k)")
    timeout: int = Field(default=120, description="超时时间(秒)")
    system_prompt: str = Field(default="", description="系统提示词（从config.yaml读取）")
    prompt_template: str = Field(default="", description="提示词模板（从config.yaml读取）")
    summary_sections: List[SummarySectionConfig] = Field(default_factory=list, description="章节定义列表")
    
    def get_api_key(self) -> str:
        """获取API密钥（支持环境变量）"""
        if self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            return os.getenv(env_var, "")
        return self.api_key


class StorageConfig(BaseModel):
    """存储配置"""
    base_dir: str = Field(default="./papers", description="本地存储根目录")
    format: str = Field(default="markdown", description="存储格式")
    filename_template: str = Field(default="{date}_{arxiv_id}_{title}", description="文件名模板")
    organize_by: str = Field(default="date", description="组织方式: date/category")
    include_metadata: bool = Field(default=False, description="是否包含元数据")


class ZhihuConfig(BaseModel):
    """知乎配置"""
    enabled: bool = Field(default=True, description="是否启用")
    cookie: str = Field(default="", description="Cookie")
    # 支持两种方式：1) 直接指定column_id 2) 通过username+column_name搜索
    column_id: Optional[str] = Field(None, description="专栏ID（直接指定）")
    username: Optional[str] = Field(None, description="知乎用户名/ID（用于搜索专栏）")
    column_name: Optional[str] = Field(None, description="专栏名称（用于搜索）")
    create_column_if_not_exists: bool = Field(default=True, description="专栏不存在时是否自动创建")
    draft_first: bool = Field(default=True, description="先保存为草稿")
    auto_publish: bool = Field(default=False, description="是否自动发布")
    content_fill_mode: str = Field(default="copy_paste", description="正文填充模式: copy_paste（拷贝粘贴）, import_document（导入文档）")
    debug: bool = Field(default=True, description="调试模式: true（调试模式）, false（执行模式）")
    
    def get_cookie(self) -> str:
        """获取Cookie（支持环境变量）"""
        if self.cookie.startswith("${") and self.cookie.endswith("}"):
            env_var = self.cookie[2:-1]
            return os.getenv(env_var, "")
        return self.cookie


class SchedulerConfig(BaseModel):
    """调度器配置"""
    enabled: bool = Field(default=True, description="是否启用")
    cron: str = Field(default="0 9 * * *", description="Cron表达式")
    timezone: str = Field(default="Asia/Shanghai", description="时区")


class Config(BaseModel):
    """主配置类"""
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    zhihu: ZhihuConfig = Field(default_factory=ZhihuConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从YAML文件加载配置"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            arxiv=ArxivConfig(
                keywords=os.getenv("ARXIV_KEYWORDS", "").split(",") if os.getenv("ARXIV_KEYWORDS") else [],
                categories=os.getenv("ARXIV_CATEGORIES", "cs.LG,cs.AI").split(","),
                days_back=int(os.getenv("ARXIV_DAYS_BACK", "7")),
                max_results=int(os.getenv("ARXIV_MAX_RESULTS", "50")),
            ),
            ai=AIConfig(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                api_url=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            ),
            storage=StorageConfig(
                base_dir=os.getenv("STORAGE_BASE_DIR", "./papers"),
                include_metadata=os.getenv("STORAGE_INCLUDE_METADATA", "false").lower() == "true",
            ),
            zhihu=ZhihuConfig(
                enabled=os.getenv("ZHIHU_ENABLED", "true").lower() == "true",
                cookie=os.getenv("ZHIHU_COOKIE", ""),
                column_id=os.getenv("ZHIHU_COLUMN_ID", None),
                column_name=os.getenv("ZHIHU_COLUMN_NAME", None),
                create_column_if_not_exists=os.getenv("ZHIHU_CREATE_COLUMN", "false").lower() == "true",
            ),
        )
    
    def to_yaml(self, path: str):
        """保存配置到YAML文件"""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, allow_unicode=True, default_flow_style=False)
