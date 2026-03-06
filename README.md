# ArXiv 文献自动总结-发布系统（发布到知乎）

一个自动化文献总结系统，能够定时扫描arXiv.org指定关键词的预印本论文，使用DeepSeek AI进行详细总结，并将结果保存为Markdown格式，支持自动发布到知乎。

## 功能特性

- **自动扫描**: 定时扫描arXiv指定关键词和分类的最新论文
- **AI总结**: 使用DeepSeek API生成详细的结构化论文综述（20个维度）
- **本地缓存**: 以Markdown格式保存总结到本地，支持年-月文件夹结构
- **简报管理**: 每个月份文件夹自动生成JSON格式简报，以arxiv_id为主键
- **智能跳过**: 自动检测最近两个月份文件夹，避免重复处理已总结论文
- **自动发布**: 支持Playwright浏览器自动化发布到知乎专栏（支持草稿模式和直接发布）
- **定时任务**: 支持Cron表达式配置定时执行
- **进度显示**: 直观的进度条显示处理状态
- **环境配置**: 支持环境变量覆盖配置文件
- **长上下文**: 支持128k上下文长度处理长论文
- **Web GUI**: 轻量级Web界面，支持配置编辑、论文列表查看和实时日志输出
- **单实例约束**: GUI服务器同一时间只能运行一个实例
- **统一输出处理**: 集中管理各模块的输出，支持不同级别日志输出控制
- **模块化输出配置**: 为每个模块提供独立的输出配置，支持从配置文件和GUI界面进行管理

## 快速开始

### 1. 环境要求

- Python 3.10+
- DeepSeek API Key
- 知乎Cookie（如需发布到知乎）

### 2. 安装

```bash
# 克隆仓库
git clone <repository-url>
cd arxiv-survey

# 创建虚拟环境（推荐）
conda create -n survey python=3.10
conda activate survey

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

#### 方式一：使用环境变量（推荐）

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY="your_api_key"
$env:ZHIHU_COOKIE="your_cookie_string"
$env:ZHIHU_ENABLED="true"

# Linux/Mac
export DEEPSEEK_API_KEY="your_api_key"
export ZHIHU_COOKIE="your_cookie_string"
export ZHIHU_ENABLED="true"
```

#### 方式二：使用配置文件

复制 `config/config.yaml` 并修改：

```yaml
arxiv:
  keywords:
    - "你的关键词"            # 搜索关键词
  categories:
    - "cs.LG"
    - "cs.AI"
  days_back: 7                # 扫描最近7天
  max_results: 50

ai:
  provider: "deepseek"
  api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
  model: "deepseek-chat"
  max_tokens: 8000            # 输出长度
  max_input_tokens: 131072    # 128k上下文
  temperature: 0.7
  timeout: 300
  system_prompt: |
    你是一个专业的学术论文分析助手，擅长对计算机科学领域的论文进行深入分析和总结。
  prompt_template: |
    请对以下论文进行详细分析，按照以下结构输出：
    
    ## 1. 基本信息
    论文标题、作者、作者单位、发表年份、期刊/会议名称、DOI
    
    ## 2. 研究动机
    ...
  summary_sections:
    - section_number: "2"
      field_name: "motivation"
      description: "研究动机"
      field_type: "string"
    - section_number: "3"
      field_name: "core_hypothesis"
      description: "核心假设"
      field_type: "string"
    - section_number: "16"
      field_name: "figures_tables"
      description: "图表信息"
      field_type: "list"
    - section_number: "20"
      field_name: "references"
      description: "参考文献"
      field_type: "list"

zhihu:
  enabled: true
  cookie: "${ZHIHU_COOKIE}"   # 从环境变量读取
  column_id: "your_column_id"
  draft_first: true
```

### 4. 运行

```bash
# 单次执行
python main.py --run-once

# 持续运行（定时任务）
python main.py --daemon

# 处理单篇论文
python main.py --paper 2401.12345

# 查看已处理论文
python main.py --list

# 查看统计信息
python main.py --stats

# 启动Web GUI
python gui/server.py
```

启动GUI后，访问 http://localhost:5000 即可使用Web界面。

## 项目结构

```
arxiv-survey/
├── config/                    # 配置模块
│   ├── config.py
│   └── config.yaml
├── models/                    # 数据模型
│   ├── paper.py
│   ├── summary.py
│   └── task.py
├── scanner/                   # arXiv扫描
│   ├── scanner.py
│   └── pdf_extractor.py
├── summarizer/                # AI总结
│   ├── summarizer.py
│   ├── prompt.py
│   └── parser.py
├── storage/                   # 本地存储
│   ├── storage.py
│   └── markdown_formatter.py
├── publisher/                 # 知乎发布
│   ├── zhihu.py                  # 知乎发布器（API方案）
│   ├── zhihu_playwright.py       # 知乎发布器（Playwright方案，主入口）
│   ├── format_converter.py
│   └── zhihu_modules/            # 知乎发布子模块
│       ├── __init__.py
│       ├── title_settings.py     # 题目设置模块
│       ├── publish_settings.py   # 发布设置模块
│       └── content_filler.py     # 文章主体填充模块
├── scheduler/                 # 定时任务
│   └── scheduler.py
├── core/                      # 系统核心
│   └── system.py
├── utils/                     # 工具函数
│   ├── logger.py
│   ├── helpers.py
│   └── progress.py
├── gui/                       # Web GUI模块
│   ├── server.py              # Flask后端服务器
│   ├── index.html             # 前端主页面
│   ├── css/
│   │   └── style.css          # 样式文件
│   └── js/
│       └── app.js             # 前端功能模块
├── main.py                    # 主入口
├── requirements.txt
├── DESIGN.md                  # 设计文档
└── README.md                  # 本文件
```

## 详细配置说明

### arXiv配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| keywords | list | - | 搜索关键词列表 |
| categories | list | ["cs.LG", "cs.AI"] | arXiv分类列表 |
| days_back | int | 7 | 扫描最近N天的论文 |
| max_results | int | 50 | 每次最大获取数量 |
| sort_by | string | "submittedDate" | 排序方式 |

### AI配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| provider | string | "deepseek" | AI提供商（deepseek/openai/claude） |
| api_key | string | - | API密钥 |
| api_url | string | "https://api.deepseek.com/v1/chat/completions" | API地址 |
| model | string | "deepseek-chat" | 模型名称 |
| max_tokens | int | 8000 | 最大输出token数 |
| max_input_tokens | int | 131072 | 最大输入token数（128k） |
| temperature | float | 0.7 | 温度参数 |
| timeout | int | 300 | 请求超时时间（秒） |
| system_prompt | string | - | 系统提示词（多行文本） |
| prompt_template | string | - | 提示词模板（多行文本，支持占位符） |
| summary_sections | list | [] | 章节定义列表 |

#### 章节定义配置

`summary_sections` 配置项用于定义AI响应的章节结构，每个章节包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| section_number | string | 章节编号（对应提示词模板中的 ## N. 格式） |
| field_name | string | 映射到PaperSummary对象的字段名 |
| description | string | 章节描述 |
| field_type | string | 字段类型：string（文本）或 list（列表） |

**示例配置**：
```yaml
summary_sections:
  - section_number: "2"
    field_name: "motivation"
    description: "研究动机"
    field_type: "string"
  - section_number: "16"
    field_name: "figures_tables"
    description: "图表信息"
    field_type: "list"
  - section_number: "20"
    field_name: "references"
    description: "参考文献"
    field_type: "list"
```

**默认章节列表**（共19个章节）：
1. motivation - 研究动机
2. core_hypothesis - 核心假设
3. research_design - 研究设计
4. data_source - 数据/样本来源
5. methods - 方法与技术
6. analysis_process - 分析流程
7. data_analysis - 数据分析
8. core_findings - 核心发现
9. experimental_results - 实验结果
10. supporting_results - 辅助结果
11. conclusions - 结论
12. contributions - 贡献
13. relevance - 与研究主题的关联
14. highlights - 亮点
15. figures_tables - 图表信息（列表类型）
16. evaluation - 评价
17. questions - 疑问
18. inspiration - 启发
19. references - 参考文献（列表类型）

### 存储配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| base_dir | string | "./papers" | 本地存储根目录 |
| format | string | "markdown" | 存储格式 |
| filename_template | string | "{date}_{arxiv_id}_{title}" | 文件名模板 |
| organize_by | string | "date" | 组织方式：date（按日期）或 category（按分类） |
| include_metadata | bool | false | 是否在Markdown文件中包含元数据 |

### 知乎配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| enabled | bool | true | 是否启用知乎发布 |
| cookie | string | - | 知乎Cookie字符串 |
| column_id | string | - | 知乎专栏ID（直接指定） |
| column_name | string | - | 专栏名称（自动搜索） |
| create_column_if_not_exists | bool | false | 专栏不存在时自动创建 |
| draft_first | bool | true | 是否先保存为草稿 |
| content_fill_mode | string | "copy_paste" | 正文填充模式：copy_paste（拷贝粘贴）或 import_document（导入文档） |
| debug | bool | true | 调试模式：true输出详细日志和截图，false简洁输出（生产环境） |

#### 专栏配置方式（二选一）

**方式1：直接指定专栏ID**（优先级最高）
```yaml
zhihu:
  column_id: "c_2011870444341454378"
```

**方式2：通过专栏名称搜索**（支持部分匹配）
```yaml
zhihu:
  column_name: "世界模型-arxiv预印本总结"
  create_column_if_not_exists: false  # 可选：自动创建
```

系统会优先搜索当前用户的专栏，如果找不到则搜索所有专栏。支持精确匹配和部分匹配。

#### 如何获取知乎Cookie

1. 登录知乎网页版
2. 打开浏览器开发者工具（F12）
3. 切换到 Application/Storage 标签
4. 找到 Cookies > https://www.zhihu.com
5. 复制以下字段的值：
   - `_xsrf`
   - `z_c0`
   - `d_c0`
   - `SESSIONID`
6. 格式：`key1=value1; key2=value2; ...`

### 输出配置

系统采用统一的输出处理机制，为每个模块提供独立的输出配置，支持不同级别日志输出控制。

#### 配置示例

```yaml
output:
  modules:
    main: 
      debug: false
      log_level: INFO
      enable_debug: false
    core: 
      debug: false
      log_level: INFO
      enable_debug: false
    scanner: 
      debug: false
      log_level: INFO
      enable_debug: false
    summarizer: 
      debug: false
      log_level: INFO
      enable_debug: false
    storage: 
      debug: false
      log_level: INFO
      enable_debug: false
    publisher: 
      debug: true
      log_level: INFO
      enable_debug: true
    scheduler: 
      debug: false
      log_level: INFO
      enable_debug: false
```

#### 模块输出配置参数

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| debug | bool | false | 是否开启调试模式 |
| log_level | string | "INFO" | 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL |
| enable_debug | bool | false | 是否启用调试输出 |

#### 支持的模块

- **main**: 主模块
- **core**: 核心系统模块
- **scanner**: 论文扫描器
- **summarizer**: AI总结器
- **storage**: 存储管理
- **publisher**: 知乎发布器
- **scheduler**: 任务调度器

## AI总结维度

系统会对每篇论文进行多维度详细分析，章节结构完全可配置。

### 默认章节结构（20个维度）

1. **基本信息**（必须包含：论文标题、作者、作者单位、发表年份、期刊/会议名称、DOI）
2. 研究动机
3. 核心假设
4. 研究设计
5. 数据来源
6. 方法与技术
7. 分析流程
8. 数据分析方法
9. 核心发现
10. 实验结果
11. 辅助结果
12. 结论
13. 贡献
14. 关联性
15. 亮点
16. 图表信息
17. 评价
18. 疑问
19. 启发
20. 参考文献

### 自定义章节结构

章节结构可以通过配置文件或GUI界面进行自定义：

**配置文件方式**（`config/config.yaml`）：
```yaml
ai:
  summary_sections:
    - section_number: "2"
      field_name: "motivation"
      description: "研究动机"
      field_type: "string"
    - section_number: "3"
      field_name: "core_hypothesis"
      description: "核心假设"
      field_type: "string"
    # 添加更多章节...
```

**GUI方式**：
1. 启动GUI：`python gui/server.py`
2. 访问 http://localhost:5000
3. 进入"配置管理" → "AI配置" → "章节定义"标签页
4. 可视化添加、编辑、删除章节定义
5. 支持调整章节顺序（上移/下移）
6. 保存配置

### 字段类型说明

- **string（文本）**：适用于单段文本内容，如研究动机、核心假设等
- **list（列表）**：适用于多条项目列表，如图表信息、参考文献等

### 章节配置特性

- ✅ 完全外部化：章节定义从代码移到配置文件
- ✅ 灵活映射：支持自定义章节编号到字段名的映射
- ✅ 类型支持：支持文本和列表两种字段类型
- ✅ 可视化管理：通过GUI界面进行增删改查
- ✅ 向后兼容：不配置时使用默认章节结构

## 存储格式

总结文件以Markdown格式保存，采用年-月文件夹结构：

```
papers/
├── 2026-02/                      # 年-月格式文件夹
│   ├── brief.json                # 该月简报（以arxiv_id为主键）
│   ├── 20260225_2602.22260v1_Paper_Title.md
│   └── ...
├── 2026-03/                      # 最新月份
│   ├── brief.json
│   └── ...
├── index.json                    # 全局索引文件
└── pdf/                          # PDF缓存
    └── 2026-02/
        └── 2602.22260v1.pdf
```

### 元数据配置

系统支持配置是否在Markdown文件中包含元数据（如总结生成时间、AI模型、处理耗时等）：

```yaml
storage:
  # 是否包含元数据
  include_metadata: false  # 默认关闭
```

- `include_metadata: false`：不包含元数据（默认）
- `include_metadata: true`：在Markdown文件末尾添加元数据信息

### 简报文件格式 (brief.json)

每个年-月文件夹下自动生成JSON格式简报，以arxiv_id为主键：

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
      "saved_at": "2026-03-02T19:20:24",
      "summary_date": "2026-03-02T19:20:24",
      "zhihu_published": true,
      "zhihu_article_url": "https://zhuanlan.zhihu.com/p/xxxxxx",
      "zhihu_published_at": "2026-03-02T20:30:00"
    }
  },
  "meta": {
    "folder": "2026-02",
    "updated_at": "2026-03-02T19:20:24",
    "total_papers": 1
  }
}
```

**字段说明**:
- `author_affiliations`: 作者单位列表
- `zhihu_published`: 是否已发布到知乎
- `zhihu_article_url`: 知乎文章URL
- `zhihu_published_at`: 知乎发布时间

### 智能跳过机制

系统运行时自动检测最近两个"年-月"文件夹：

**1. 跳过已总结的论文**:
```
⏭️  跳过已总结的论文: 2602.22260v1 (位于 2026-02 文件夹)
```

**2. 跳过已发布的论文**:
```
⏭️  跳过知乎发布（已于 2026-03-02T20:30:00 发布）
   文章链接: https://zhuanlan.zhihu.com/p/xxxxxx
```

系统会自动跟踪每篇论文的知乎发布状态，避免重复发布。

## 定时任务配置

使用Cron表达式配置定时任务：

```yaml
scheduler:
  enabled: true
  cron: "0 9 * * *"           # 每天上午9点
  timezone: "Asia/Shanghai"
```

常用Cron表达式：
- `0 9 * * *` - 每天上午9点
- `0 */6 * * *` - 每6小时
- `0 9 * * 1` - 每周一上午9点

## 进度显示

系统提供直观的进度显示：

```
📊 批量处理进度: 3/5 [60%] | 成功: 2 | 失败: 0 | 跳过: 1 | 耗时: 125.3s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 正在处理: 2602.22452v1 - 示例论文标题
   [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━] 100%

   ✅ 1. 下载PDF        (2.3s)
   ✅ 2. 提取文本       (1.8s)
   ✅ 3. AI总结         (45.2s)
   ✅ 4. 保存本地       (0.1s)
   ⏭️  5. 发布知乎      (跳过)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 环境变量说明

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| DEEPSEEK_API_KEY | DeepSeek API密钥 | sk-xxx... |
| ZHIHU_COOKIE | 知乎Cookie字符串 | _xsrf=xxx; z_c0=xxx; ... |
| ZHIHU_ENABLED | 是否启用知乎发布 | true/false |
| ZHIHU_COLUMN_ID | 知乎专栏ID（直接指定） | c_2011870444341454378 |
| ZHIHU_COLUMN_NAME | 知乎专栏名称（自动搜索） | 世界模型-arxiv预印本总结 |
| ZHIHU_CREATE_COLUMN | 专栏不存在时自动创建 | true/false |
| STORAGE_INCLUDE_METADATA | 是否在Markdown文件中包含元数据 | true/false |

环境变量优先级高于配置文件。

## 知乎发布详细说明

### 发布流程

知乎发布模块采用模块化设计，将发布流程拆分为三个独立子模块：

1. **题目设置模块** (`title_settings.py`)
   - 自动检查标题长度（知乎限制100字）
   - 超长标题自动截断并添加省略号
   - 验证标题是否正确填写

2. **发布设置模块** (`publish_settings.py`)
   - 自动选择创作声明为"包含AI辅助创作"
   - 通过"专栏收录"->"发布到专栏"路径选择专栏
   - 自动添加文章话题

3. **文章主体填充模块** (`content_filler.py`)
   - 支持两种填充模式：
     - **拷贝粘贴模式** (`copy_paste`): 将Markdown内容直接粘贴到编辑器
     - **导入文档模式** (`import_document`): 通过知乎"导入文档"功能上传文件
   - 自动检测字数，验证内容是否有效粘贴
   - 处理Markdown解析对话框

### 正文填充模式配置

```yaml
zhihu:
  # 正文填充模式
  content_fill_mode: "copy_paste"    # 或 "import_document"
```

**拷贝粘贴模式** (`copy_paste`):
- 将Markdown内容直接粘贴到知乎编辑器
- 自动处理格式转换
- 适合：大多数场景，简单快速

**导入文档模式** (`import_document`):
- 通过知乎编辑器的"导入"->"导入文档"功能上传
- 支持MD/DOC格式文件
- 自动触发系统文件对话框并输入文件路径
- 适合：大文件或需要保留原始格式的场景

### 调试模式配置

```yaml
zhihu:
  # 调试模式
  debug: true    # true: 调试模式（详细日志+截图）, false: 执行模式（简洁输出）
```

**调试模式** (`debug: true`):
- 输出详细的操作日志
- 自动生成调试截图（如 `debug_editor_initial.png`, `debug_title_filled.png` 等）
- 适合：开发调试、问题排查

**执行模式** (`debug: false`):
- 简洁输出，仅显示关键信息
- 不生成调试截图
- 适合：生产环境定时任务

### 发布流程优化特性

- ✅ **智能标题处理**: 自动检查并截断超长标题（>100字）
- ✅ **发布按钮激活检测**: 通过色彩和CSS属性检测按钮状态，最大等待30秒
- ✅ **内容长度检查**: 确保正文不少于8个字符，不足时自动补充
- ✅ **Markdown解析处理**: 自动点击"确认并解析"按钮
- ✅ **超时处理**: 最多尝试3次获取文章URL，超时后安全退出
- ✅ **详细截图**: 关键节点自动截图，便于调试和问题定位

## 常见问题

### 1. 知乎发布失败

**问题**: 知乎API返回404错误

**原因**: 知乎已关闭或限制公开API访问

**解决方案**: 
- **推荐方案**: 使用 Playwright 自动化发布（已集成）
  ```bash
  # 安装依赖
  pip install playwright markdown
  python -m playwright install chromium
  
  # 使用 Playwright 发布
  python test_playwright_publish.py
  ```
- **备选方案**: 手动复制生成的Markdown文件内容到知乎
- Markdown文件保存在 `papers/YYYY-MM/` 目录下

**两种发布方案对比**:

| 方案 | 类型 | 优点 | 缺点 | 推荐场景 |
|------|------|------|------|----------|
| API发布 | HTTP请求 | 快速、无界面 | 知乎已限制 | 测试、专栏管理 |
| Playwright | 浏览器自动化 | 稳定可靠、功能完整 | 需要安装浏览器 | 生产环境 |

### 2. Playwright 相关问题

**问题**: 运行时出现 "Sandbox Error: hit restricted"

**原因**: Playwright 浏览器沙箱限制

**解决方案**: 
- 忽略此错误，不影响发布功能
- 或在启动浏览器时添加 `--no-sandbox` 参数

**问题**: 发布按钮为灰色，无法点击

**原因**: 标题长度超过100字或正文内容不足8个字符

**解决方案**: 
- 系统会自动检查标题长度并截断
- 系统会自动检查内容长度并添加额外内容

**问题**: 发布后URL仍为编辑器链接

**原因**: 发布过程中页面未正确跳转

**解决方案**: 
- 系统已实现超时处理机制，最多尝试3次获取文章URL
- 若仍失败，可手动从浏览器复制发布后的文章URL

### 3. PDF文本提取不完整

**问题**: 某些PDF格式特殊，文本提取可能不完整

**解决方案**: 
- 系统使用多种PDF提取库（pdfplumber、PyMuPDF）
- 自动选择最佳提取结果

### 4. 长论文处理超时

**问题**: 超长论文可能超出AI模型上下文限制

**解决方案**: 
- 系统会智能截断内容，保留关键部分
- 基于token数动态计算可处理内容长度

### 5. 环境变量不生效

**问题**: 设置环境变量后配置未更新

**解决方案**: 
- 确保环境变量名正确（区分大小写）
- 重启终端或IDE
- 检查配置文件是否使用了 `${VAR}` 语法

## GUI使用说明

### 启动GUI服务器

```bash
# 在anaconda环境中启动
python gui/server.py
```

### GUI功能

1. **配置编辑**: 在线编辑config.yaml的各项配置
   - arXiv配置：关键词、分类、扫描天数、结果数等
   - AI配置：分为三个标签页
     - **基本设置**：提供商、API密钥、模型、温度、token数、超时等
     - **提示词设置**：系统提示词和提示词模板（多行编辑）
     - **章节定义**：可视化编辑章节定义（增删改查、排序）
   - 存储配置：目录、格式、文件名模板等
   - 知乎配置：Cookie、专栏、发布模式等
   - 输出配置：可视化配置各模块的输出参数（调试模式、日志级别、调试输出）
2. **执行控制**: 选择执行模式（仅扫描/仅总结/仅发布/完整流程）
3. **论文列表**: 查看已处理的论文列表和状态
4. **实时日志**: 显示执行过程中的实时日志输出
5. **章节定义管理**: 可视化表格管理章节定义
   - 添加新章节
   - 编辑现有章节
   - 删除选中章节
   - 上移/下移调整顺序
   - 支持文本和列表两种字段类型
6. **输出配置管理**: 可视化配置各模块的输出参数
   - 为每个模块单独设置调试模式
   - 为每个模块单独设置日志级别
   - 为每个模块单独设置是否启用调试输出
7. **单实例约束**: 同一时间只能运行一个GUI实例

### 单实例约束

系统通过端口占用检查确保同一时间只能运行一个GUI服务器实例：
- 如果端口5000已被占用，新实例会显示错误并退出
- 错误提示：`错误：GUI服务器已经在运行（端口5000被占用）`

## 开发计划

- [x] 基础扫描和总结功能
- [x] Markdown本地存储
- [x] 知乎发布功能
- [x] 进度显示
- [x] 环境变量配置
- [x] 128k上下文支持
- [x] 浏览器自动化发布（Playwright）
- [x] Web管理界面（GUI）
- [x] 单实例约束
- [x] 日志中文化
- [ ] 多AI提供商支持
- [ ] 多平台发布（微信公众号、掘金等）

## 技术栈

- **语言**: Python 3.10+
- **核心库**:
  - `arxiv` - arXiv API客户端
  - `requests` - HTTP请求
  - `schedule` - 定时任务
  - `pydantic` - 数据验证
  - `markdown` - Markdown处理
  - `pdfplumber` / `PyMuPDF` - PDF文本提取
  - `playwright` - 浏览器自动化（用于知乎发布）

## 许可证

MIT License

## 贡献

本项目不保证响应Issue和Pull Request。

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)
