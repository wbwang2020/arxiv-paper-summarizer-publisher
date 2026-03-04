# ArXiv 文献自动总结系统 - 工程设计文档

## 1. 项目概述

### 1.1 项目目标
构建一个自动化文献总结系统，能够：
- 定时扫描arXiv.org指定关键词的预印本论文
- 使用AI工具（DeepSeek）进行详细总结
- 本地缓存Markdown格式总结
- 自动发布到知乎（支持进度显示）

### 1.2 技术栈
- **语言**: Python 3.10+
- **核心库**: 
  - `arxiv` - arXiv API客户端
  - `requests` - HTTP请求
  - `schedule` - 定时任务
  - `pydantic` - 数据验证
  - `markdown` - Markdown处理
  - `pdfplumber` / `PyMuPDF` - PDF文本提取

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        ArXiv Survey System                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Scanner   │  │   Summarizer│  │   Storage   │  │ Publisher│ │
│  │   Module    │→ │   Module    │→ │   Module    │→ │  Module  │ │
│  │  (arXiv API)│  │  (DeepSeek) │  │  (Markdown) │  │ (Zhihu)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│         ↑                                              ↑         │
│         └──────────────────────────────────────────────┘         │
│                         Scheduler Module                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 模块设计

### 3.1 配置模块 (config/)

#### 3.1.1 配置文件结构
```yaml
# config.yaml
arxiv:
  keywords: ["你的关键词"]         # 搜索关键词
  categories: ["cs.LG", "cs.AI"]  # arXiv分类
  days_back: 7                    # 扫描最近N天的论文
  max_results: 50                 # 每次最大获取数量
  sort_by: "submittedDate"        # 排序方式
  sort_order: "descending"        # 排序顺序

ai:
  provider: "deepseek"            # AI提供商
  api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
  api_url: "https://api.deepseek.com/v1/chat/completions"
  model: "deepseek-chat"
  temperature: 0.7
  max_tokens: 8000                # 输出token长度
  max_input_tokens: 131072        # 输入上下文长度(128k)
  timeout: 300                    # 超时时间(秒)
  # 提示词配置 - 从config.yaml读取，不在代码中硬编码
  system_prompt: |
    你是一个专业的学术论文分析助手...
  prompt_template: |
    请对以下论文进行详细分析...（支持 {title}, {authors}, {year}, {arxiv_id}, {abstract}, {content} 占位符）
  # 章节定义 - 用于解析AI响应
  summary_sections:
    - section_number: "2"
      field_name: "motivation"
      description: "研究动机"
    - section_number: "3"
      field_name: "core_hypothesis"
      description: "核心假设"
    # ... 其他章节定义

storage:
  base_dir: "./papers"            # 本地存储根目录
  format: "markdown"              # 存储格式
  filename_template: "{date}_{arxiv_id}_{title}"
  organize_by: "date"             # 按日期/分类组织
  include_metadata: false          # 是否包含元数据

zhihu:
  enabled: true                   # 是否启用知乎发布
  cookie: "${ZHIHU_COOKIE}"       # 从环境变量读取
  column_id: "562976376331236864" # 知乎专栏ID
  column_name: "世界模型-arxiv预印本总结" # 专栏名称（用于搜索）
  draft_first: true               # 先保存为草稿
  auto_publish: false             # 是否自动发布
  content_fill_mode: "copy_paste" # 正文填充模式: copy_paste（拷贝粘贴）, import_document（导入文档）
  debug: true                     # 调试模式: true（调试模式）, false（执行模式）

scheduler:
  enabled: true
  cron: "0 9 * * *"               # 每天上午9点执行
  timezone: "Asia/Shanghai"
```

#### 3.1.2 配置类定义
```python
class ArxivConfig(BaseModel):
    """arXiv配置"""
    keywords: List[str]
    categories: List[str]
    days_back: int = 7
    max_results: int = 50
    sort_by: str = "submittedDate"
    sort_order: str = "descending"

class AIConfig(BaseModel):
    """AI配置 - 提示词从config.yaml读取，不再硬编码"""
    provider: str = "deepseek"
    api_key: str = Field(default="", description="API密钥")
    api_url: str = Field(default="https://api.deepseek.com/v1/chat/completions", description="API地址")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=8000, description="最大输出token数")
    max_input_tokens: int = Field(default=131072, description="最大输入token数 (128k)")
    timeout: int = Field(default=300, description="超时时间(秒)")
    # 提示词配置 - 从config.yaml读取，不在代码中硬编码
    system_prompt: str = Field(default="", description="系统提示词（从config.yaml读取）")
    prompt_template: str = Field(default="", description="提示词模板（从config.yaml读取）")
    # 章节定义 - 用于解析AI响应
    summary_sections: List[Dict] = Field(default_factory=list, description="章节定义列表")

class SummarySectionConfig(BaseModel):
    """章节配置定义"""
    section_number: str = Field(description="章节编号（对应提示词模板中的 ## N. 格式）")
    field_name: str = Field(description="映射到PaperSummary对象的字段名")
    description: str = Field(description="章节描述")
    field_type: str = Field(default="string", description="字段类型: string, list")

class StorageConfig(BaseModel):
    """存储配置"""
    base_dir: str = "./papers"
    format: str = "markdown"
    filename_template: str = "{date}_{arxiv_id}_{title}"
    organize_by: str = "date"
    include_metadata: bool = False

class ZhihuConfig(BaseModel):
    """知乎配置"""
    enabled: bool = True
    cookie: str = Field(default="", description="Cookie字符串")
    # 专栏配置（两种方式，优先级: column_id > column_name）
    column_id: Optional[str] = None      # 直接指定专栏ID
    column_name: Optional[str] = None    # 通过专栏名称搜索
    create_column_if_not_exists: bool = False  # 专栏不存在时自动创建
    draft_first: bool = True
    auto_publish: bool = False
    content_fill_mode: str = Field(default="copy_paste", description="正文填充模式: copy_paste（拷贝粘贴）, import_document（导入文档）")
    debug: bool = Field(default=True, description="调试模式: true（调试模式）, false（执行模式）")
    
    def get_cookie(self) -> str:
        """获取Cookie（支持环境变量语法）"""
        if self.cookie.startswith("${") and self.cookie.endswith("}"):
            env_var = self.cookie[2:-1]
            return os.getenv(env_var, "")
        return self.cookie

class SchedulerConfig(BaseModel):
    """调度配置"""
    enabled: bool = True
    cron: str = "0 9 * * *"
    timezone: str = "Asia/Shanghai"

class Config(BaseModel):
    """系统总配置"""
    arxiv: ArxivConfig
    ai: AIConfig
    storage: StorageConfig
    zhihu: ZhihuConfig
    scheduler: SchedulerConfig
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从YAML文件加载配置"""
        pass
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        pass
```

---

### 3.2 数据模型模块 (models/)

#### 3.2.1 论文信息模型
```python
class ArxivPaper(BaseModel):
    """arXiv论文基本信息"""
    arxiv_id: str                  # arXiv ID (如: 2401.12345)
    title: str                     # 论文标题
    authors: List[str]             # 作者列表
    author_affiliations: List[str] # 作者单位列表
    abstract: str                  # 摘要
    categories: List[str]          # 分类
    published_date: datetime       # 发布日期
    updated_date: datetime         # 更新日期
    pdf_url: str                   # PDF下载链接
    abs_url: str                   # 摘要页面链接
    primary_category: str          # 主要分类
    venue: Optional[str]           # 期刊/会议名称（如果有）
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### 3.2.2 论文总结模型
```python
class PaperSummary(BaseModel):
    """论文详细总结"""
    # 基本信息（必须包含：作者、作者单位、发表年份、论文标题、期刊/会议名称）
    arxiv_id: str
    title: str
    authors: List[str]
    author_affiliations: List[str] # 作者单位列表
    published_year: int
    venue: str                     # 期刊/会议（预印本则为arXiv）
    doi: Optional[str]             # DOI（如果有）
    
    # AI总结内容（20个维度）
    motivation: str                # 研究动机
    core_hypothesis: str           # 核心假设
    research_design: str           # 研究设计
    data_source: str               # 数据来源
    methods: str                   # 方法与技术
    analysis_process: str          # 分析流程
    data_analysis: str             # 数据分析方法
    core_findings: str             # 核心发现
    experimental_results: str      # 实验结果
    supporting_results: str        # 辅助结果
    conclusions: str               # 结论
    contributions: str             # 贡献
    relevance: str                 # 与研究主题关联
    highlights: str                # 亮点
    figures_tables: List[Dict]     # 图表信息
    evaluation: str                # 评价
    questions: str                 # 疑问
    inspiration: str               # 启发
    references: List[Dict]         # 参考文献
    
    # 元数据
    summary_date: datetime         # 总结日期
    ai_model: str                  # 使用的AI模型
    processing_time: float         # 处理耗时
    
    def to_markdown(self, include_metadata: bool = False) -> str:
        """转换为Markdown格式
        
        Args:
            include_metadata: 是否包含元数据
        """
        pass
```

#### 3.2.3 任务状态模型
```python
class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    SCANNING = "scanning"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    SUMMARIZING = "summarizing"
    STORING = "storing"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"            # 已处理过，跳过

class PaperTask(BaseModel):
    """论文处理任务"""
    task_id: str                   # 任务ID (UUID)
    arxiv_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    retry_count: int = 0
    paper: Optional[ArxivPaper] = None
    summary: Optional[PaperSummary] = None
    local_path: Optional[str] = None
    zhihu_url: Optional[str] = None
    
    def update_status(self, status: TaskStatus, error: str = None):
        """更新任务状态"""
        pass
    
    def is_successful(self) -> bool:
        """检查任务是否成功"""
        return self.status == TaskStatus.COMPLETED
```

---

### 3.3 arXiv扫描模块 (scanner/)

#### 3.3.1 接口定义
```python
class ArxivScanner:
    """arXiv论文扫描器"""
    
    def __init__(self, config: ArxivConfig):
        """初始化扫描器"""
        pass
    
    def search_papers(
        self,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_results: int = 50
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
        pass
    
    def search_recent_papers(self, days: int = None) -> List[ArxivPaper]:
        """搜索最近N天的论文"""
        pass
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[ArxivPaper]:
        """通过ID获取论文信息"""
        pass
    
    def download_pdf(self, paper: ArxivPaper, save_path: str) -> bool:
        """下载PDF文件"""
        pass
```

#### 3.3.2 PDF文本提取器
```python
class PDFExtractor:
    """PDF文本提取器"""
    
    def extract_text(self, pdf_path: str, max_chars: int = 150000) -> str:
        """
        从PDF提取文本
        
        Args:
            pdf_path: PDF文件路径
            max_chars: 最大字符数限制
            
        Returns:
            提取的文本内容
        """
        pass
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """使用pdfplumber提取"""
        pass
    
    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """使用PyMuPDF提取"""
        pass
```

---

### 3.4 AI总结模块 (summarizer/)

#### 3.4.1 提示词配置
提示词从 `config.yaml` 文件中读取，不再硬编码在代码中。这种设计允许用户自定义提示词而无需修改源代码。

**配置说明：**
- `system_prompt`: 系统提示词，定义AI助手的角色和任务
- `prompt_template`: 提示词模板，包含论文分析的结构化格式
- `summary_sections`: 章节定义，定义如何从AI响应中提取各个章节内容

**模板占位符：**
- `{title}` - 论文标题
- `{authors}` - 作者列表
- `{year}` - 发表年份
- `{arxiv_id}` - arXiv ID
- `{abstract}` - 论文摘要
- `{content}` - 论文全文内容

**章节定义配置：**
章节定义允许灵活配置如何从AI响应中提取各个部分的内容。每个章节包含：
- `section_number`: 章节编号（对应提示词模板中的 `## N.` 格式）
- `field_name`: 映射到 `PaperSummary` 对象的字段名
- `description`: 章节描述

**配置示例：**
```yaml
# config.yaml 中的 AI 提示词配置
ai:
  # 系统提示词
  system_prompt: |
    你是一个专业的学术论文分析助手，擅长深度解析计算机科学和人工智能领域的学术论文。
    你的任务是阅读论文并生成结构化的详细综述，帮助研究人员快速理解论文的核心内容。
    请确保分析全面、准确、客观，并突出论文的创新点和潜在价值。
  
  # 提示词模板
  prompt_template: |
    请对以下论文进行详细分析，并按照指定格式生成综述。

    【论文基本信息】
    - 标题：{title}
    - 作者：{authors}
    - 发表年份：{year}
    - arXiv ID：{arxiv_id}

    【论文摘要】
    {abstract}

    【论文全文】
    {content}

    请按照以下结构生成详细综述...

  # 章节定义 - 用于解析AI响应
  summary_sections:
    - section_number: "2"
      field_name: "motivation"
      description: "研究动机"
    - section_number: "3"
      field_name: "core_hypothesis"
      description: "核心假设"
    - section_number: "4"
      field_name: "research_design"
      description: "研究设计"
    - section_number: "5"
      field_name: "data_source"
      description: "数据/样本来源"
    - section_number: "6"
      field_name: "methods"
      description: "方法与技术"
    - section_number: "7"
      field_name: "analysis_process"
      description: "分析流程"
    - section_number: "8"
      field_name: "data_analysis"
      description: "数据分析"
    - section_number: "9"
      field_name: "core_findings"
      description: "核心发现"
    - section_number: "10"
      field_name: "experimental_results"
      description: "实验结果"
    - section_number: "11"
      field_name: "supporting_results"
      description: "辅助结果"
    - section_number: "12"
      field_name: "conclusions"
      description: "结论"
    - section_number: "13"
      field_name: "contributions"
      description: "贡献"
    - section_number: "14"
      field_name: "relevance"
      description: "与研究主题的关联"
    - section_number: "15"
      field_name: "highlights"
      description: "亮点"
    - section_number: "16"
      field_name: "figures_tables"
      description: "图表信息"
      field_type: "list"  # 特殊类型：列表
    - section_number: "17"
      field_name: "evaluation"
      description: "评价"
    - section_number: "18"
      field_name: "questions"
      description: "疑问"
    - section_number: "19"
      field_name: "inspiration"
      description: "启发"
    - section_number: "20"
      field_name: "references"
      description: "参考文献"
      field_type: "list"  # 特殊类型：列表
```

**设计优势：**
1. **可维护性** - 提示词和章节定义集中管理在配置文件中，便于修改和版本控制
2. **灵活性** - 用户可以根据需要自定义提示词和章节映射，无需修改代码
3. **可读性** - 使用YAML block scalar syntax (`|`) 格式，多行文本更易阅读
4. **可测试性** - 提示词和章节定义变更可以独立测试，不影响代码逻辑
5. **可扩展性** - 支持添加新章节或修改现有章节结构，只需修改配置文件

#### 3.4.2 总结器接口
```python
class PaperSummarizer:
    """论文AI总结器"""
    
    def __init__(self, config: AIConfig):
        """初始化总结器"""
        self.config = config
        self.api_key = config.get_api_key()
        self.system_prompt = config.system_prompt
        self.prompt_template = config.prompt_template
        self.section_mappings = self._build_section_mappings()
        
        if not self.api_key:
            logger.warning("AI API密钥未配置")
    
    def _build_section_mappings(self) -> dict:
        """
        根据配置构建章节映射
        
        Returns:
            章节编号到字段名的映射字典
        """
        mappings = {}
        if hasattr(self.config, 'summary_sections') and self.config.summary_sections:
            for section in self.config.summary_sections:
                mappings[section['section_number']] = {
                    'field_name': section['field_name'],
                    'description': section['description'],
                    'field_type': section.get('field_type', 'string')
                }
        return mappings
    
    def summarize(
        self,
        paper: ArxivPaper,
        content: str,
        max_retries: int = 3
    ) -> PaperSummary:
        """
        对论文进行AI总结
        
        Args:
            paper: 论文信息
            content: 论文全文内容
            max_retries: 最大重试次数
            
        Returns:
            论文总结对象
        """
        start_time = time.time()
        
        # 构建提示词
        prompt = self._build_prompt(paper, content)
        
        # 调用API
        response_text = self._call_api_with_retry(prompt, max_retries)
        
        # 解析响应（使用配置的章节映射）
        summary = self._parse_response(response_text, paper)
        
        # 设置元数据
        summary.ai_model = self.config.model
        summary.processing_time = time.time() - start_time
        
        logger.info(f"总结论文 {paper.arxiv_id} 完成，耗时 {summary.processing_time:.2f}秒")
        
        return summary
    
    def _build_prompt(self, paper: ArxivPaper, content: str) -> str:
        """构建提示词（自动处理token限制）"""
        pass
    
    def _call_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        pass
    
    def _parse_response(self, response: str, paper: ArxivPaper) -> PaperSummary:
        """
        解析API响应为结构化数据（使用配置的章节映射）
        
        Args:
            response: AI API返回的文本
            paper: 论文信息
            
        Returns:
            结构化的PaperSummary对象
        """
        # 创建基础Summary对象
        summary = PaperSummary(
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors,
            author_affiliations=paper.author_affiliations if hasattr(paper, 'author_affiliations') else [],
            published_year=paper.published_date.year,
            venue=paper.venue if hasattr(paper, 'venue') and paper.venue else "arXiv"
        )
        
        # 提取各个章节
        sections = self._extract_sections(response)
        
        # 使用配置的章节映射填充字段
        for section_num, section_content in sections.items():
            if section_num in self.section_mappings:
                mapping = self.section_mappings[section_num]
                field_name = mapping['field_name']
                field_type = mapping['field_type']
                
                # 根据字段类型进行特殊处理
                if field_type == 'list':
                    if field_name == 'figures_tables':
                        setattr(summary, field_name, self._parse_figures_tables(section_content))
                    elif field_name == 'references':
                        setattr(summary, field_name, self._parse_references(section_content))
                else:
                    setattr(summary, field_name, section_content)
        
        # 解析基本信息部分，提取作者单位等
        basic_info = sections.get("1", "")
        affiliations = self._extract_affiliations(basic_info)
        if affiliations:
            summary.author_affiliations = affiliations
        
        doi = self._extract_doi(basic_info)
        if doi:
            summary.doi = doi
        
        return summary
    
    def _extract_sections(self, text: str) -> dict:
        """
        提取各个章节内容
        
        Args:
            text: AI响应文本
            
        Returns:
            章节编号到内容的映射
        """
        sections = {}
        
        # 匹配 ## 数字. 标题 格式的章节
        pattern = r'##\s*(\d+)\.\s*([^\n]*)\n(.*?)(?=##\s*\d+\.|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for num, title, content in matches:
            sections[num] = content.strip()
        
        return sections
    
    def _parse_figures_tables(self, text: str) -> list:
        """解析图表信息"""
        pass
    
    def _parse_references(self, text: str) -> list:
        """解析参考文献"""
        pass
    
    def _extract_affiliations(self, text: str) -> list:
        """从基本信息中提取作者单位"""
        pass
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """从基本信息中提取DOI"""
        pass
```

#### 3.4.3 章节配置设计原理

**设计目标：**
将章节定义从代码中分离出来，使其可以通过配置文件灵活管理，实现以下目标：
1. **灵活性** - 用户可以自定义章节结构，无需修改代码
2. **可维护性** - 章节定义集中管理，便于版本控制
3. **可扩展性** - 支持添加新章节或修改现有章节结构
4. **类型安全** - 支持不同字段类型的解析（string, list）

**工作流程：**
```
┌─────────────────────────────────────────────────────────────┐
│ 1. 用户在 config.yaml 中定义章节配置                  │
│    - section_number: 章节编号                        │
│    - field_name: 映射到 PaperSummary 的字段名          │
│    - field_type: 字段类型 (string/list)                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PaperSummarizer 初始化时构建章节映射                │
│    - 读取 config.summary_sections                       │
│    - 构建 section_number -> field_name 的映射字典        │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 解析AI响应时使用映射字典                          │
│    - 提取章节内容: _extract_sections()                │
│    - 遍历章节映射，填充对应的字段                     │
│    - 根据 field_type 调用相应的解析方法                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 返回结构化的 PaperSummary 对象                     │
└─────────────────────────────────────────────────────────────┘
```

**字段类型支持：**
- `string`: 普通文本字段，直接赋值
- `list`: 列表字段，调用专门的解析方法
  - `figures_tables`: 调用 `_parse_figures_tables()`
  - `references`: 调用 `_parse_references()`

**扩展示例：**
如果需要添加新的章节，只需在 `config.yaml` 中添加配置：

```yaml
summary_sections:
  - section_number: "21"
    field_name: "future_work"
    description: "未来工作"
    field_type: "string"
```

然后在 `PaperSummary` 类中添加对应的字段定义即可。

---

### 3.5 存储模块 (storage/)

#### 3.5.1 接口定义
```python
class PaperStorage:
    """论文存储管理器 - 支持年-月文件夹结构和简报功能"""
    
    def __init__(self, config: StorageConfig):
        """初始化存储"""
        pass
    
    def save_summary(
        self,
        summary: PaperSummary,
        paper: ArxivPaper,
        format: str = "markdown"
    ) -> str:
        """
        保存论文总结（自动更新年-月文件夹和简报）
        
        Args:
            summary: 论文总结
            paper: 论文信息
            format: 存储格式
            
        Returns:
            保存的文件路径
        """
        pass
    
    def load_summary(self, arxiv_id: str) -> Optional[PaperSummary]:
        """加载已保存的总结"""
        pass
    
    def exists(self, arxiv_id: str) -> bool:
        """检查论文是否已处理（全局检查）"""
        pass
    
    def exists_in_recent_months(self, arxiv_id: str, months: int = 2) -> bool:
        """
        检查论文是否在最近N个月内已处理
        
        Args:
            arxiv_id: arXiv ID
            months: 检查的月数
            
        Returns:
            是否已存在
        """
        pass
    
    def get_paper_summary_info(self, arxiv_id: str, months: int = 2) -> Optional[Dict]:
        """
        获取论文的总结信息（如果存在）
        
        Args:
            arxiv_id: arXiv ID
            months: 搜索的月数
            
        Returns:
            论文信息字典，未找到返回None
        """
        pass
    
    def list_summaries(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """列出已保存的总结"""
        pass
    
    def list_recent_summaries(self, months: int = 2) -> List[Dict]:
        """
        列出最近N个月的总结
        
        Args:
            months: 月数
            
        Returns:
            总结信息列表
        """
        pass
    
    def get_folder_brief(self, folder_name: str) -> Optional[Dict]:
        """
        获取指定文件夹的简报
        
        Args:
            folder_name: 文件夹名称 (YYYY-MM)
            
        Returns:
            简报内容，不存在返回None
        """
        pass
    
    def get_stats(self) -> Dict:
        """获取存储统计信息（包含按文件夹统计）"""
        pass
    
    def _generate_filename(self, paper: ArxivPaper) -> str:
        """生成文件名"""
        pass
    
    def _get_year_month_folder(self, date: datetime) -> str:
        """获取年-月文件夹名称 (YYYY-MM)"""
        pass
    
    def _get_recent_year_month_folders(self, count: int = 2) -> List[Path]:
        """获取最近N个年-月文件夹"""
        pass
    
    def _load_brief(self, dir_path: Path) -> Dict:
        """加载文件夹简报"""
        pass
    
    def _save_brief(self, dir_path: Path, brief: Dict):
        """保存文件夹简报"""
        pass
```

#### 3.5.2 文件组织结构
```
papers/
├── 2026-02/                      # 年-月格式文件夹
│   ├── brief.json                # 该月简报（以arxiv_id为主键）
│   ├── 20260225_2602.22260v1_Code_World_Models_for_Parameter_Control_in_Evoluti.md
│   ├── 20260225_2602.22452v1_CWM__Contrastive_World_Models_for_Action_Feasibili.md
│   └── ...
├── 2026-03/                      # 最新月份
│   ├── brief.json
│   └── ...
├── index.json                    # 全局索引文件
└── pdf/                          # PDF缓存（可选）
    └── 2026-02/
        └── 2602.22260v1.pdf
```

#### 3.5.3 简报文件格式 (brief.json)
```json
{
  "papers": {
    "2602.22260v1": {
      "arxiv_id": "2602.22260v1",
      "title": "论文标题",
      "authors": ["作者A", "作者B"],
      "author_affiliations": ["MIT", "Stanford"],
      "published_date": "2026-02-25T00:00:00",
      "primary_category": "cs.LG",
      "file_path": "papers/2026-02/20260225_2602.22260v1_Paper_Title.md",
      "saved_at": "2026-03-02T19:20:24.626951",
      "summary_date": "2026-03-02T19:20:24.626951",
      "zhihu_published": true,
      "zhihu_article_url": "https://zhuanlan.zhihu.com/p/xxxxxx",
      "zhihu_published_at": "2026-03-02T20:30:00"
    }
  },
  "meta": {
    "folder": "2026-02",
    "updated_at": "2026-03-02T19:20:24.626951",
    "total_papers": 1
  }
}
```

**新增字段说明**:
- `author_affiliations`: 作者单位列表
- `zhihu_published`: 是否已发布到知乎
- `zhihu_article_url`: 知乎文章URL
- `zhihu_published_at`: 知乎发布时间

#### 3.5.4 最近月份检查机制
系统运行时自动检测最近两个"年-月"文件夹，避免重复处理：
1. 扫描 `papers/` 目录下所有 `YYYY-MM` 格式的文件夹
2. 按时间倒序排序，取最近N个（默认2个）
3. 从这些文件夹的 `brief.json` 中读取所有已处理的 `arxiv_id`
4. 如果待处理论文已存在，则跳过并显示所在文件夹信息

```python
# 检查是否在最近两个月内已处理
if storage.exists_in_recent_months(arxiv_id, months=2):
    info = storage.get_paper_summary_info(arxiv_id, months=2)
    print(f"跳过已总结的论文: {arxiv_id} (位于 {info['folder']} 文件夹)")
    continue
```

#### 3.5.5 知乎发布状态管理
系统通过 `brief.json` 跟踪每篇论文的知乎发布状态：

**自动检测已发布论文**:
```python
# 检查论文是否已发布到知乎
if storage.is_zhihu_published(arxiv_id, months=2):
    info = storage.get_paper_summary_info(arxiv_id, months=2)
    print(f"跳过已发布的论文: {arxiv_id}")
    print(f"知乎文章链接: {info.get('zhihu_article_url')}")
else:
    # 发布到知乎
    article_url = publisher.publish(summary, paper)
    # 更新发布状态
    storage.update_zhihu_publish_status(
        arxiv_id,
        published=True,
        article_url=article_url
    )
```

**发布状态字段**:
- `zhihu_published`: bool - 是否已发布
- `zhihu_article_url`: str - 知乎文章URL
- `zhihu_published_at`: str - ISO格式发布时间

**发布状态更新机制**:
- 文章发布成功后自动更新brief.json中的发布状态
- 支持通过PaperStorage类的update_zhihu_publish_status方法更新状态
- 确保数据一致性和可靠性

---

### 3.6 知乎发布模块 (publisher/)

#### 3.6.1 接口定义
```python
class ZhihuPublisher:
    """知乎文章发布器"""
    
    BASE_URL = "https://www.zhihu.com"
    API_URL = "https://www.zhihu.com/api/v4"
    
    def __init__(self, config: ZhihuConfig):
        """初始化发布器"""
        pass
    
    def publish(
        self,
        summary: PaperSummary,
        paper: ArxivPaper,
        as_draft: Optional[bool] = None
    ) -> Optional[str]:
        """
        发布文章到知乎
        
        专栏选择优先级:
        1. 如果配置了column_id，直接使用
        2. 如果配置了column_name，搜索并匹配专栏
        3. 如果配置了create_column_if_not_exists且专栏不存在，自动创建
        
        Args:
            summary: 论文总结
            paper: 论文信息
            as_draft: 是否保存为草稿（默认使用配置）
            
        Returns:
            知乎文章URL，失败返回None
        """
        pass
    
    def check_login(self) -> bool:
        """检查登录状态"""
        pass
    
    def get_user_info(self) -> Optional[Dict]:
        """获取当前登录用户信息"""
        pass
    
    def get_columns(self) -> list:
        """获取用户的专栏列表（通过搜索API）"""
        pass
    
    def search_columns(self, query: str, limit: int = 10) -> list:
        """搜索专栏"""
        pass
    
    def search_columns_by_author(self, author_name: str) -> list:
        """搜索特定作者的专栏"""
        pass
    
    def find_column_by_name(self, column_name: str) -> Optional[Dict]:
        """
        通过专栏名称搜索专栏
        
        优先搜索当前用户的专栏，如果找不到则搜索所有专栏
        支持精确匹配和部分匹配
        """
        pass
    
    def get_or_create_column(self, column_name: str, description: str = "") -> Optional[str]:
        """获取或创建专栏"""
        pass
    
    def create_column(self, title: str, description: str = "") -> Optional[str]:
        """创建知乎专栏"""
        pass
    
    def _get_target_column_id(self) -> Optional[str]:
        """获取目标专栏ID（根据配置优先级）"""
        pass
    
    def _markdown_to_zhihu_html(self, markdown_content: str) -> str:
        """将Markdown转换为知乎HTML格式"""
        pass
    
    def _add_to_column(self, article_id: str, column_id: str) -> bool:
        """将文章添加到专栏"""
        pass

#### 3.6.2 知乎发布配置说明
**专栏配置方式**（优先级从高到低）：

1. **直接指定column_id**（最优先）
   ```yaml
   zhihu:
     column_id: "c_2011870444341454378"
   ```

2. **通过column_name搜索**（支持部分匹配）
   ```yaml
   zhihu:
     column_name: "世界模型-arxiv预印本总结"
     create_column_if_not_exists: false  # 可选：自动创建
   ```

3. **自动创建专栏**
   ```yaml
   zhihu:
     column_name: "我的新专栏"
     create_column_if_not_exists: true
   ```

**注意**: 知乎API端点可能会变更或限制访问。当前提供两种发布方案：

#### 方案1: API发布 (ZhihuPublisher)
- ✅ 支持Cookie登录验证
- ✅ 支持专栏名称搜索
- ⚠️ 文章发布API可能返回404（知乎已限制）
- 💡 适合：API测试和专栏管理

#### 方案2: Playwright自动化 (ZhihuPlaywrightPublisher) - 推荐
使用浏览器自动化技术，模拟人工操作：
- ✅ 支持Cookie登录验证
- ✅ 支持文章发布到指定专栏
- ✅ 支持保存为草稿或直接发布
- ✅ 支持Markdown格式自动转换
- ✅ 支持超时处理机制（最多3次尝试）
- ✅ 支持内容长度检查（确保不少于8个字符）
- ✅ 支持发布按钮激活状态检查
- ✅ 支持Markdown解析对话框处理
- ✅ 支持下拉菜单操作优化
- ✅ 支持详细截图功能（便于调试）
- ⚠️ 需要安装浏览器（Chromium）
- ⚠️ 运行时会打开浏览器窗口（可配置无头模式）
- 💡 适合：生产环境实际发布

**使用Playwright方案**:
```python
from publisher import ZhihuPlaywrightPublisher

publisher = ZhihuPlaywrightPublisher(config.zhihu)
article_url = publisher.publish_from_file(
    file_path="path/to/summary.md",
    paper=arxiv_paper,
    as_draft=True,  # 保存为草稿
    headless=False  # 显示浏览器窗口（调试用）
)
```

**文件上传模式**:
- 通过`content_fill_mode: "import_document"`配置启用
- 直接使用set_input_files方法设置文件，避免点击不可见元素导致的超时问题
- 自动检测文档导入状态，等待导入完成
- 支持Markdown文件的直接导入

**安装依赖**:
```bash
pip install playwright markdown
python -m playwright install chromium
```

#### 3.6.3 模块重构设计

**知乎发布模块结构**:
```
publisher/
├── __init__.py
├── zhihu.py                      # 知乎API发布器
├── zhihu_playwright.py           # 知乎Playwright发布器（主入口）
└── zhihu_modules/                # 子模块目录
    ├── __init__.py
    ├── title_settings.py         # 题目设置模块
    ├── publish_settings.py       # 发布设置模块
    └── content_filler.py         # 文章主体填充模块
```

**子模块职责**:

1. **title_settings.py** - 题目设置模块
   - `TitleSettingsHandler` 类
   - 处理标题填写、长度验证（最大100字）、截断等功能
   - 验证标题是否正确填写

2. **publish_settings.py** - 发布设置模块
   - `PublishSettingsHandler` 类
   - 处理创作声明选择（"包含AI辅助创作"）
   - 专栏选择（通过"专栏收录"->"发布到专栏"流程）
   - 话题添加
   - 创作声明未找到时使用键盘操作选择

3. **content_filler.py** - 文章主体填充模块
   - `ContentFiller` 类
   - 支持两种填充模式：
     - `copy_paste`: 拷贝粘贴方式（默认）
     - `import_document`: 导入文档方式
   - 字数检测（通过状态栏验证内容是否有效粘贴）
   - Markdown解析对话框处理
   - 文件上传模式优化：直接使用set_input_files方法设置文件，避免点击不可见元素导致的超时问题
   - 文档导入状态检测和等待

**主模块与子模块交互**:
```python
class ZhihuPlaywrightPublisher:
    def __init__(self, config: ZhihuConfig):
        # ... 初始化代码 ...
        self.title_handler: Optional[TitleSettingsHandler] = None
        self.publish_settings_handler: Optional[PublishSettingsHandler] = None
        self.content_filler: Optional[ContentFiller] = None
    
    def _init_handlers(self):
        """初始化子模块处理器"""
        if self.page:
            self.title_handler = TitleSettingsHandler(
                self.page, self._debug_print, self._debug_screenshot
            )
            self.publish_settings_handler = PublishSettingsHandler(
                self.page, self._debug_print, self._debug_screenshot
            )
            self.content_filler = ContentFiller(
                self.page, self._debug_print, self._debug_screenshot
            )
    
    def _fill_editor(self, title: str, content: str, file_path: str = None):
        """填充编辑器内容"""
        # 1. 编辑题目
        if self.title_handler:
            self.title_handler.set_title(title)
        
        # 2. 编辑发布设置
        if self.publish_settings_handler:
            self.publish_settings_handler.configure_publish_settings(
                self.config.column_name
            )
        
        # 3. 填充正文
        content_fill_mode = getattr(self.config, 'content_fill_mode', 'copy_paste')
        if self.content_filler:
            self.content_filler.fill_content(content, file_path, content_fill_mode)
```

#### 3.6.4 发布流程优化

**编辑器填充流程**:
1. 等待编辑器加载
2. 编辑题目（先执行，避免被清除）
3. 编辑发布设置（创作声明、专栏选择、话题添加）
4. 填充正文（拷贝粘贴或导入文档）
   - 导入文档方式：直接使用set_input_files方法设置文件，避免点击不可见元素导致的超时问题
   - 检测'文档导入中'对话框，等待导入完成
5. 检测字数（验证内容是否有效粘贴）
6. 测试发布按钮状态

**超时处理机制**:
- 发布后最多尝试3次获取文章URL
- 每次尝试间隔5秒
- 超时后强制退出发布流程

**内容长度检查**:
- 确保正文内容不少于8个字符
- 内容不足时自动添加额外内容

**发布按钮激活状态检查**:
- 点击前检查按钮是否激活
- 通过检测按钮的色彩和CSS属性判断激活状态
- 实现最大30秒的等待机制
- 每1秒检查一次按钮状态
- 尝试点击编辑器区域触发状态更新
- 激活状态异常时尝试刷新

**Markdown解析对话框处理**:
- 自动检测并点击"确认并解析"按钮
- 确保内容正确解析

**下拉菜单操作优化**:
- 增加等待时间确保下拉菜单完全展开
- 等待选择操作完成

**创作声明选择优化**:
- 尝试使用正则表达式查找"包含AI辅助创作"选项
- 未找到时使用键盘操作（4次ArrowDown）选择
- 简化查找逻辑，减少对对话框的依赖

**详细截图功能**:
- 编辑器初始状态
- 标题填写后
- 内容填充后
- 专栏选择后
- 发布前（标题、正文、发布设置）
- 发布后

#### 3.6.5 调试模式支持

**配置参数**:
```yaml
zhihu:
  # 调试模式: true（调试模式，输出详细日志和生成截图）, false（执行模式，简洁输出）
  debug: true
```

**调试模式特性**:
- `debug: true`: 输出详细日志，生成调试截图
- `debug: false`: 简洁输出，不生成截图（生产环境）

**调试方法**:
```python
def _debug_print(self, message: str):
    """调试模式下输出信息"""
    if self.debug:
        print(message)

def _debug_screenshot(self, path: str):
    """调试模式下保存截图"""
    if self.debug and self.page:
        try:
            self.page.screenshot(path=path)
            print(f"📸 已保存截图: {path}")
        except Exception as e:
            print(f"⚠️ 截图失败: {e}")
```

---

### 3.7 调度模块 (scheduler/)

#### 3.7.1 接口定义
```python
class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config: SchedulerConfig):
        """初始化调度器"""
        pass
    
    def schedule_daily_task(
        self,
        hour: int,
        minute: int,
        task_func: Callable
    ):
        """设置每日定时任务"""
        pass
    
    def schedule_cron_task(
        self,
        cron_expr: str,
        task_func: Callable
    ):
        """使用Cron表达式设置任务"""
        pass
    
    def start(self):
        """启动调度器"""
        pass
    
    def stop(self):
        """停止调度器"""
        pass
```

---

### 3.8 主控制器 (core/)

#### 3.8.1 接口定义
```python
class ArxivSurveySystem:
    """文献总结系统主控制器"""
    
    def __init__(self, config_path: str):
        """
        初始化系统
        
        Args:
            config_path: 配置文件路径
        """
        pass
    
    def run_once(self) -> ProcessingResult:
        """
        执行一次完整的扫描-总结-发布流程
        
        Returns:
            处理结果（成功数、失败数、跳过数）
        """
        pass
    
    def run_continuous(self):
        """持续运行，按配置定时执行"""
        pass
    
    def process_single_paper(self, arxiv_id: str) -> PaperTask:
        """处理单篇论文"""
        pass
    
    def _process_paper(self, paper: ArxivPaper) -> PaperTask:
        """处理单篇论文的内部方法"""
        pass
```

---

### 3.9 进度显示模块 (utils/progress.py)

#### 3.9.1 批量进度显示
```python
class BatchProgress:
    """批量处理进度显示"""
    
    def __init__(self, total: int, title: str = "Processing"):
        self.total = total
        self.current = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
    
    def start_paper(self, arxiv_id: str, title: str):
        """开始处理新论文"""
        pass
    
    def finish_paper(self, success: bool = True, skipped: bool = False):
        """完成论文处理"""
        pass
    
    def finish(self):
        """完成所有处理"""
        pass
```

#### 3.9.2 单篇论文进度
```python
class PaperProgress:
    """论文处理进度显示"""
    
    STEPS = [
        ("📥", "下载PDF"),
        ("📄", "提取文本"),
        ("🤖", "AI总结"),
        ("💾", "保存本地"),
        ("📤", "发布知乎"),
    ]
    
    def __init__(self, arxiv_id: str, total_steps: int = 5):
        self.arxiv_id = arxiv_id
        self.total_steps = total_steps
        self.current_step = 0
        self.step_start_time = time.time()
    
    def start_step(self, step_num: int, step_name: str):
        """开始一个新步骤"""
        pass
    
    def finish_step(self, success: bool = True, message: str = ""):
        """完成当前步骤"""
        pass
```

### 3.10 GUI模块 (gui/)

#### 3.10.1 设计原则
- **轻量化**: 单页应用，无复杂框架
- **直接调用**: 通过API直接调用现有main.py接口
- **配置编辑**: 基于现有config.yaml进行编辑
- **数据显示**: 基于现存brief.json进行论文信息显示
- **单实例约束**: 同一时间只能运行一个GUI服务器实例

#### 3.10.2 后端设计 (server.py)
```python
class FlaskBackend:
    """Flask后端服务器"""
    
    def check_single_instance(port=5000):
        """检查是否只有一个实例在运行"""
        # 通过socket绑定检查端口占用
        pass
    
    @app.route('/api/run', methods=['POST'])
    def run_main():
        """执行main.py命令"""
        # 接收前端参数，调用main.py
        pass
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def config():
        """获取/更新配置"""
        pass
    
    @app.route('/api/papers', methods=['GET'])
    def list_papers():
        """获取论文列表"""
        pass
    
    @app.route('/api/paper/<arxiv_id>', methods=['GET'])
    def get_paper(arxiv_id):
        """获取单篇论文详情"""
        pass
```

#### 3.10.3 前端设计 (index.html + app.js)
- **配置区域**: 编辑config.yaml的各项配置
- **执行区域**: 选择执行模式（扫描/总结/发布/完整流程）
- **论文列表**: 显示已处理的论文列表
- **日志输出**: 实时显示执行日志
- **单实例提示**: 检测到多实例时显示警告

#### 3.10.4 API接口列表
| 接口 | 方法 | 说明 |
|------|------|------|
| / | GET | 返回index.html主页 |
| /api/run | POST | 执行main.py命令 |
| /api/config | GET/POST | 获取/更新配置 |
| /api/papers | GET | 获取论文列表 |
| /api/paper/<id> | GET | 获取论文详情 |

#### 3.10.5 单实例约束实现
```python
def check_single_instance(port=5000):
    """检查是否只有一个实例在运行"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except socket.error:
        return False

# 启动时检查
if not check_single_instance(port=5000):
    print("错误：GUI服务器已经在运行（端口5000被占用）")
    sys.exit(1)
```

---

## 4. API 详细设计

### 4.1 模块间API

```python
# scanner/api.py
class IArxivScanner(ABC):
    @abstractmethod
    def search(self, query: SearchQuery) -> List[ArxivPaper]: ...
    
    @abstractmethod
    def download(self, paper: ArxivPaper) -> bytes: ...

# summarizer/api.py
class IPaperSummarizer(ABC):
    @abstractmethod
    def summarize(self, paper: ArxivPaper, content: str) -> PaperSummary: ...

# storage/api.py
class IPaperStorage(ABC):
    @abstractmethod
    def save(self, summary: PaperSummary) -> str: ...
    
    @abstractmethod
    def load(self, arxiv_id: str) -> Optional[PaperSummary]: ...
    
    @abstractmethod
    def exists(self, arxiv_id: str) -> bool: ...

# publisher/api.py
class IArticlePublisher(ABC):
    @abstractmethod
    def publish(self, summary: PaperSummary) -> Optional[str]: ...
```

### 4.2 外部API集成

#### 4.2.1 DeepSeek API
```python
POST https://api.deepseek.com/v1/chat/completions

Request:
{
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是一个专业的学术论文分析助手..."},
        {"role": "user", "content": "<论文内容>"}
    ],
    "temperature": 0.7,
    "max_tokens": 8000
}

Response:
{
    "choices": [{
        "message": {"content": "<总结内容>"}
    }]
}
```

#### 4.2.2 arXiv API
```python
import arxiv

# 搜索论文
search = arxiv.Search(
    query='(cat:cs.LG OR cat:cs.AI) AND (all:"你的关键词")',
    max_results=50,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

# 获取结果
for result in client.results(search):
    print(result.title)
```

---

## 5. 错误处理与日志

### 5.1 异常体系
```python
class ArxivSurveyError(Exception):
    """基础异常"""
    pass

class ConfigError(ArxivSurveyError):
    """配置错误"""
    pass

class ScannerError(ArxivSurveyError):
    """扫描错误"""
    pass

class SummarizerError(ArxivSurveyError):
    """总结错误"""
    pass

class StorageError(ArxivSurveyError):
    """存储错误"""
    pass

class PublisherError(ArxivSurveyError):
    """发布错误"""
    pass
```

### 5.2 日志配置
```python
logging_config = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/arxiv_survey.log",
            "level": "DEBUG"
        }
    },
    "loggers": {
        "arxiv_survey": {
            "level": "DEBUG",
            "handlers": ["console", "file"]
        }
    }
}
```

---

## 6. 项目结构

```
arxiv-survey/
├── config/
│   ├── __init__.py
│   ├── config.py                 # 配置类定义
│   └── config.yaml               # 配置文件模板
├── models/
│   ├── __init__.py
│   ├── paper.py                  # 论文数据模型
│   ├── summary.py                # 总结数据模型
│   └── task.py                   # 任务数据模型
├── scanner/
│   ├── __init__.py
│   ├── scanner.py                # arXiv扫描器
│   └── pdf_extractor.py          # PDF文本提取
├── summarizer/
│   ├── __init__.py
│   ├── summarizer.py             # AI总结器
│   ├── prompt.py                 # 提示词模板
│   └── parser.py                 # 响应解析器
├── storage/
│   ├── __init__.py
│   ├── storage.py                # 存储管理器
│   └── markdown_formatter.py     # Markdown格式化
├── publisher/
│   ├── __init__.py
│   ├── zhihu.py                  # 知乎发布器（API方案）
│   ├── zhihu_playwright.py       # 知乎发布器（Playwright方案）
│   └── zhihu_modules/            # 子模块目录
│       ├── __init__.py
│       ├── title_settings.py     # 题目设置模块
│       ├── publish_settings.py   # 发布设置模块
│       └── content_filler.py     # 文章主体填充模块
├── scheduler/
│   ├── __init__.py
│   └── scheduler.py              # 任务调度器
├── core/
│   ├── __init__.py
│   └── system.py                 # 系统主控制器
├── utils/
│   ├── __init__.py
│   ├── logger.py                 # 日志工具
│   ├── helpers.py                # 辅助函数
│   └── progress.py               # 进度显示工具
├── gui/                          # GUI模块（新增）
│   ├── server.py                 # Flask后端服务器
│   ├── index.html                # 前端主页面
│   ├── css/
│   │   └── style.css             # 样式文件
│   └── js/
│       └── app.js                # 前端功能模块
├── tests/
│   └── ...
├── logs/                         # 日志目录
├── papers/                       # 论文存储目录
├── temp/                         # 临时文件目录
├── main.py                       # 主入口
├── requirements.txt              # 依赖
├── DESIGN.md                     # 本设计文档
└── README.md                     # 项目说明文档
```

---

## 7. 使用示例

### 7.1 配置文件示例
```yaml
arxiv:
  keywords:
    - "你的关键词"
  categories:
    - "cs.LG"
    - "cs.AI"
  days_back: 7
  max_results: 50

ai:
  provider: "deepseek"
  api_key: "${DEEPSEEK_API_KEY}"
  api_url: "https://api.deepseek.com/v1/chat/completions"
  model: "deepseek-chat"
  max_tokens: 8000
  max_input_tokens: 131072  # 128k上下文

storage:
  base_dir: "./papers"
  organize_by: "date"

zhihu:
  enabled: true
  cookie: "${ZHIHU_COOKIE}"
  column_id: "562976376331236864"
  draft_first: true

scheduler:
  enabled: true
  cron: "0 9 * * *"
```

### 7.2 代码使用示例
```python
from core.system import ArxivSurveySystem

# 初始化系统
system = ArxivSurveySystem("config/config.yaml")

# 单次执行
result = system.run_once()
print(f"成功: {result.success}, 失败: {result.failed}")

# 持续运行（定时任务）
# system.run_continuous()

# 处理单篇论文
task = system.process_single_paper("2401.12345")
if task.is_successful():
    print(f"本地路径: {task.local_path}")
    print(f"知乎链接: {task.zhihu_url}")
```

### 7.3 命令行使用
```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DEEPSEEK_API_KEY="your_api_key"
export ZHIHU_COOKIE="your_cookie"
export ZHIHU_ENABLED="true"

# 单次执行
python main.py --run-once

# 持续运行
python main.py --daemon

# 处理单篇论文
python main.py --paper 2401.12345

# 查看已处理论文
python main.py --list

# 查看统计信息
python main.py --stats
```

---

## 8. 安全与隐私

1. **API密钥管理**: 所有敏感信息通过环境变量注入，不硬编码
2. **Cookie安全**: 知乎Cookie仅用于个人账号，不共享
3. **Rate Limiting**: arXiv API和DeepSeek API都有请求频率限制
4. **数据本地存储**: 论文内容仅本地存储，不上传到第三方
5. **环境变量覆盖**: 支持通过环境变量覆盖配置文件设置

---

## 9. 扩展性设计

1. **多AI提供商支持**: 通过配置可切换OpenAI、Claude等
2. **多平台发布**: 可扩展支持微信公众号、掘金等平台
3. **插件系统**: 支持自定义处理器和格式化器
4. **Web界面**: 已实现轻量级Web GUI（Flask + HTML/JS）
5. **进度显示**: 支持命令行进度条和状态显示

---

## 10. 已知问题与解决方案

### 10.1 知乎发布API限制
**问题**: 知乎文章发布API返回404错误
**原因**: 知乎可能已关闭或限制公开API访问
**解决方案**: 
- 系统仍会尝试自动发布
- 如果失败，可手动复制生成的Markdown文件内容到知乎
- Markdown文件保存在 `papers/YYYY/MM/` 目录下

### 10.2 PDF文本提取
**问题**: 某些PDF格式特殊，文本提取可能不完整
**解决方案**: 
- 使用多种PDF提取库（pdfplumber、PyMuPDF）
- 自动选择最佳提取结果

### 10.3 长论文处理
**问题**: 超长论文可能超出AI模型上下文限制
**解决方案**: 
- 智能截断内容，保留关键部分
- 基于token数动态计算可处理内容长度

---

## 11. 更新日志

### v1.5.0 (2026-03-04)
- ✅ 章节配置外部化实现 - 将章节定义从代码移到 `config.yaml`
- ✅ 支持灵活的章节映射配置
- ✅ 新增 `SummarySectionConfig` 配置类
- ✅ 新增 `summary_sections` 配置字段
- ✅ 更新 `PaperSummarizer` 实现，支持动态章节解析
- ✅ 支持不同字段类型的解析（string, list）
- ✅ 提高系统灵活性和可扩展性
- ✅ 添加 `_build_section_mappings()` 方法构建章节映射
- ✅ 重构 `_parse_response()` 方法使用配置的章节映射
- ✅ 验证章节配置加载和映射功能正常工作

### v1.4.0 (2026-03-04)
- ✅ 提示词配置外部化 - 从代码硬编码改为从 `config.yaml` 读取
- ✅ 支持自定义系统提示词 (`system_prompt`)
- ✅ 支持自定义提示词模板 (`prompt_template`)
- ✅ 使用YAML block scalar syntax (`|`) 提高多行文本可读性
- ✅ 移除 `summarizer/prompt.py` 文件，简化代码结构
- ✅ 更新DESIGN文档，反映新的提示词配置设计

### v1.3.0 (2026-03-04)
- ✅ 实现轻量级Web GUI界面
- ✅ 支持配置文件在线编辑
- ✅ 支持论文列表查看
- ✅ 支持实时日志输出
- ✅ 支持单实例运行约束
- ✅ 所有日志信息中文化

### v1.2.0 (2026-03-03)
- ✅ 实现Playwright浏览器自动化发布方案
- ✅ 支持超时处理机制（最多3次尝试获取文章URL）
- ✅ 支持内容长度检查（确保不少于8个字符）
- ✅ 支持发布按钮激活状态检查
- ✅ 支持Markdown解析对话框处理
- ✅ 支持下拉菜单操作优化
- ✅ 支持详细截图功能（便于调试）
- ✅ 优化专栏选择逻辑，通过"专栏收录"->"发布到专栏"路径
- ✅ 实现标题长度检查和截断功能（确保不超过100字）
- ✅ 支持从现有Markdown文件直接发布

### v1.1.0 (2026-03-02)
- ✅ 实现年-月文件夹结构存储 (YYYY-MM)
- ✅ 实现每个文件夹JSON格式简报 (brief.json)
- ✅ 实现最近两个月智能跳过机制
- ✅ 新增 `exists_in_recent_months()` API
- ✅ 新增 `list_recent_summaries()` API
- ✅ 新增 `get_folder_brief()` API
- ✅ 优化统计功能，支持按文件夹统计

### v1.0.0 (2026-03-02)
- ✅ 实现arXiv论文自动扫描
- ✅ 实现DeepSeek AI总结（20维度分析）
- ✅ 实现Markdown本地存储
- ✅ 实现知乎发布功能（API限制）
- ✅ 实现进度显示功能
- ✅ 实现环境变量配置覆盖
- ✅ 支持128k上下文长度
