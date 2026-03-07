# ArXiv 文献自动总结-发布系统（知乎/飞书）

一个自动化文献总结系统，能够定时扫描arXiv.org指定关键词的预印本论文，使用DeepSeek AI进行详细总结，并将结果保存为Markdown格式，支持自动发布到知乎和飞书。

## 功能特性

- **自动扫描**: 定时扫描arXiv指定关键词和分类的最新论文
- **AI总结**: 使用DeepSeek API生成详细的结构化论文综述（20个维度）
- **本地缓存**: 以Markdown格式保存总结到本地，支持年-月文件夹结构
- **简报管理**: 每个月份文件夹自动生成JSON格式简报，以arxiv_id为主键
- **智能跳过**: 自动检测最近两个月份文件夹，避免重复处理已总结论文
- **多平台发布**: 支持自动发布到知乎（已完成），飞书（开发中）
- **定时任务**: 支持Cron表达式配置定时执行
- **Web GUI**: 轻量级Web界面，支持配置编辑、论文列表查看和实时日志输出

## 快速开始

### 1. 环境要求

- Python 3.10+
- DeepSeek API Key
- 知乎Cookie（如需发布到知乎）
- 飞书应用ID和密钥（如需发布到飞书）

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
$env:FEISHU_ENABLED="false"
$env:FEISHU_APP_ID="your_app_id"
$env:FEISHU_APP_SECRET="your_app_secret"

# Linux/Mac
export DEEPSEEK_API_KEY="your_api_key"
export ZHIHU_COOKIE="your_cookie_string"
export ZHIHU_ENABLED="true"
export FEISHU_ENABLED="false"
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

#### 方式二：使用配置文件

复制 `config/config.yaml` 并修改关键配置：

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

zhihu:
  enabled: true
  cookie: "${ZHIHU_COOKIE}"   # 从环境变量读取
  column_id: "your_column_id"
  draft_first: true

feishu:
  enabled: false
  app_id: "${FEISHU_APP_ID}"   # 从环境变量读取
  app_secret: "${FEISHU_APP_SECRET}"   # 从环境变量读取
  folder_token: "${FEISHU_FOLDER_TOKEN}"   # 从环境变量读取（可选）
  notify: true
  notify_user_ids: []
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
├── scanner/                   # arXiv扫描
├── summarizer/                # AI总结
├── storage/                   # 本地存储
├── publisher/                 # 发布模块
│   ├── zhihu.py                  # 知乎发布器（API方案）
│   ├── zhihu_playwright.py       # 知乎发布器（Playwright方案，主入口）
│   ├── feishu.py                 # 飞书发布器
├── scheduler/                 # 定时任务
├── core/                      # 系统核心
├── utils/                     # 工具函数
├── gui/                       # Web GUI模块
├── main.py                    # 主入口
├── requirements.txt
├── DESIGN.md                  # 设计文档
└── README.md                  # 本文件
```

## 关键配置说明

### 核心配置项

| 配置项 | 说明 |
|--------|------|
| DEEPSEEK_API_KEY | DeepSeek API密钥 |
| ZHIHU_COOKIE | 知乎Cookie字符串 |
| ZHIHU_ENABLED | 是否启用知乎发布 |
| FEISHU_ENABLED | 是否启用飞书发布 |
| FEISHU_APP_ID | 飞书应用ID |
| FEISHU_APP_SECRET | 飞书应用密钥 |
| FEISHU_FOLDER_TOKEN | 飞书目标文件夹Token（可选） |

环境变量优先级高于配置文件。

### 如何获取知乎Cookie

1. 登录知乎网页版
2. 打开浏览器开发者工具（F12）
3. 切换到 Application/Storage 标签
4. 找到 Cookies > https://www.zhihu.com
5. 复制 `_xsrf`、`z_c0`、`d_c0`、`SESSIONID` 字段的值
6. 格式：`key1=value1; key2=value2; ...`

## 常见问题

### 1. 知乎发布失败

**原因**: 知乎已关闭或限制公开API访问

**解决方案**: 使用 Playwright 自动化发布（已集成）

### 2. 环境变量不生效

**解决方案**:
- 确保环境变量名正确（区分大小写）
- 重启终端或IDE
- 检查配置文件是否使用了 `${VAR}` 语法

### 3. PDF文本提取不完整

**解决方案**: 系统使用多种PDF提取库，自动选择最佳提取结果

### 4. 长论文处理超时

**解决方案**: 系统会智能截断内容，保留关键部分

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

## TODO

- [ ] 完成飞书发布功能的开发
- [ ] 设计并实现微信公众号发布功能

## 许可证

MIT License

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)