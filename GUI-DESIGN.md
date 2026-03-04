# ArXiv 文献自动总结-发布系统 - 轻量级GUI设计文档

## 1. 项目概述

### 1.1 设计目标
- 轻量级单页应用，直接调用现有main.py接口
- 基于现有config.yaml进行配置编辑
- 基于现存brief.json进行论文信息显示
- 无需额外后端服务，纯前端实现

### 1.2 技术栈
- **前端**：原生HTML + CSS + JavaScript
- **后端调用**：Python subprocess调用main.py
- **配置存储**：直接读写config.yaml
- **数据展示**：读取brief.json文件

## 2. 界面架构

### 2.1 整体布局
```
+--------------------------------------------------+
|  ArXiv文献自动总结系统                [刷新状态]  |
+--------------------------------------------------+
|  [运行控制]  [配置管理]  [论文列表]  [系统状态]   |
+--------------------------------------------------+
|                                                  |
|              主内容区域                          |
|                                                  |
+--------------------------------------------------+
|  状态栏: 系统就绪 | 最后更新: 2026-03-04 18:30   |
+--------------------------------------------------+
```

### 2.2 页面结构
单页应用，通过Tab切换不同功能区域：
1. **运行控制**：执行各种运行模式
2. **配置管理**：编辑config.yaml
3. **论文列表**：显示brief.json中的论文信息
4. **系统状态**：显示系统状态和日志

## 3. 功能模块设计

### 3.1 运行控制模块

#### 界面元素
```
+--------------------------------------------------+
|  运行控制                                         |
+--------------------------------------------------+
|                                                  |
|  运行模式:                                        |
|  (•) 完整流程: 扫描+总结+发布                    |
|  ( ) 仅扫描: 扫描和总结论文                      |
|  ( ) 仅发布: 发布已总结的论文                    |
|  ( ) 处理单篇论文                                |
|      输入arXiv ID: [________________]            |
|                                                  |
|  高级选项:                                        |
|  [ ] 显示详细日志 (-v)                           |
|                                                  |
|  [开始执行]  [停止执行]                          |
|                                                  |
+--------------------------------------------------+
|  执行输出:                                        |
|  +----------------------------------------------+|
|  | 18:30:00 - 开始执行完整流程...               ||
|  | 18:30:01 - 扫描arXiv论文...                  ||
|  | ...                                          ||
|  +----------------------------------------------+|
+--------------------------------------------------+
```

#### 交互逻辑
- 选择运行模式，点击"开始执行"
- 调用Python subprocess执行: `python main.py --run-once`
- 实时显示命令输出到文本区域
- 支持停止执行（终止子进程）

### 3.2 配置管理模块

#### 界面元素
```
+--------------------------------------------------+
|  配置管理                                         |
+--------------------------------------------------+
|  [arXiv配置] [AI配置] [存储配置] [知乎配置]       |
+--------------------------------------------------+
|                                                  |
|  arXiv配置:                                       |
|  +----------------------------------------------+|
|  | 搜索关键词:                                   ||
|  | [World Model                    ] [+][-]     ||
|  |                                              ||
|  | arXiv分类:                                    ||
|  | [x] cs.LG  (机器学习)                        ||
|  | [x] cs.AI  (人工智能)                        ||
|  |                                              ||
|  | 扫描最近N天: [14              ] 天           ||
|  | 最大结果数:  [10              ] 篇           ||
|  | 排序方式:    [提交日期 ▼]                    ||
|  +----------------------------------------------+|
|                                                  |
|  [保存配置]  [重置配置]  [导出配置]              |
|                                                  |
+--------------------------------------------------+
```

#### 配置分类

**arXiv配置**
- 搜索关键词（支持多关键词，可添加/删除）
- arXiv分类（复选框选择）
- 扫描天数（数字输入）
- 最大结果数（数字输入）
- 排序方式（下拉选择）

**AI配置**
- 提供商选择（deepseek/openai/claude）
- API密钥输入（密码框，支持环境变量语法）
- API地址输入
- 模型名称输入
- 温度参数（滑块 0.0-1.0）
- 最大token数（数字输入）
- 最大输入token数（数字输入，默认131072）
- 超时时间（数字输入）
- 系统提示词（多行文本框，支持YAML block scalar语法）
- 提示词模板（多行文本框，支持占位符）
- 章节定义（表格形式，可添加/删除/编辑）

**存储配置**
- 存储目录输入
- 存储格式选择（markdown/json）
- 文件名模板输入
- 组织方式选择（date/category/flat）

**知乎配置**
- 启用知乎发布（开关）
- Cookie输入（密码框，长文本）
- 专栏名称输入
- 正文填充模式选择（copy_paste/import_document）
- 调试模式开关

#### AI配置详细界面
```
+--------------------------------------------------+
|  AI配置                                           |
+--------------------------------------------------+
|  [基本设置] [提示词设置] [章节定义]               |
+--------------------------------------------------+
|                                                  |
|  基本设置:                                        |
|  +----------------------------------------------+|
|  | 提供商:    [deepseek ▼]                      ||
|  | API密钥:   [********************]            ||
|  | API地址:   [https://api.deepseek.com/...]    ||
|  | 模型名称:  [deepseek-chat        ]            ||
|  | 温度:      [====●====] 0.7                   ||
|  | 最大token: [8000               ]             ||
|  | 输入token: [131072             ]             ||
|  | 超时时间:  [300                ] 秒          ||
|  +----------------------------------------------+|
|                                                  |
|  提示词设置:                                      |
|  +----------------------------------------------+|
|  | 系统提示词:                                   ||
|  | +--------------------------------------------+||
|  | | 你是一个专业的学术论文分析助手...          |||
|  | |                                            |||
|  | +--------------------------------------------+||
|  |                                              ||
|  | 提示词模板:                                   ||
|  | +--------------------------------------------+||
|  | | 请对以下论文进行详细分析...                |||
|  | | 标题：{title}                              |||
|  | | 作者：{authors}                            |||
|  | | ...                                        |||
|  | +--------------------------------------------+||
|  +----------------------------------------------+|
|                                                  |
|  章节定义:                                        |
|  +----------------------------------------------+|
|  | 编号 | 字段名            | 描述       | 类型 ||
|  |------|-------------------|------------|------||
|  | 2    | motivation        | 研究动机   | 文本 ||
|  | 3    | core_hypothesis   | 核心假设   | 文本 ||
|  | 4    | research_design   | 研究设计   | 文本 ||
|  | ...  | ...               | ...        | ...  ||
|  | 16   | figures_tables    | 图表信息   | 列表 ||
|  | 20   | references        | 参考文献   | 列表 ||
|  +----------------------------------------------+|
|  [添加章节] [删除选中] [上移] [下移]             |
|                                                  |
+--------------------------------------------------+
```

#### 章节定义编辑弹窗
```
+--------------------------------------------------+
|  编辑章节                              [X]       |
+--------------------------------------------------+
|                                                  |
|  章节编号:   [2        ]                         |
|  字段名:     [motivation          ]              |
|  描述:       [研究动机            ]              |
|  字段类型:   (•) 文本  ( ) 列表                  |
|                                                  |
|  [取消]  [保存]                                  |
+--------------------------------------------------+
```

#### 交互逻辑
- 读取现有config.yaml，填充到表单
- 修改配置后点击"保存配置"
- 直接写入config.yaml文件
- 支持导出配置为文件下载
- 提示词支持多行编辑，使用YAML block scalar语法（|）
- 章节定义支持增删改查，可调整顺序
- 字段类型支持文本（string）和列表（list）两种

### 3.3 论文列表模块

#### 界面元素
```
+--------------------------------------------------+
|  论文列表                                         |
+--------------------------------------------------+
|  筛选: [全部 ▼]  搜索: [________________]        |
|  时间范围: [最近7天 ▼]  [刷新列表]               |
+--------------------------------------------------+
|                                                  |
|  共 7 篇论文                                      |
|                                                  |
|  +----------------------------------------------+|
|  | 状态 | 标题                    | 日期 | 操作||
|  |------|-------------------------|------|-----||
|  |  ✅  | Discrete World Models...|03-02 |查看||
|  |  ✅  | Scaling Tasks, Not S... |03-02 |查看||
|  |  ⏳  | Chain of World: Worl... |03-03 |发布||
|  |  ⏳  | Contextual Latent Wo... |03-03 |发布||
|  +----------------------------------------------+|
|                                                  |
|  [<] 1 / 1 [>]                                   |
|                                                  |
+--------------------------------------------------+
```

#### 状态标识
- ✅ 已发布（zhihu_published=true且有URL）
- ⏳ 未发布（zhihu_published=false或URL为空）
- ❌ 发布失败（可记录失败状态）

#### 交互逻辑
- 读取所有brief.json文件，汇总论文信息
- 支持按状态、日期筛选
- 支持标题搜索
- 点击"查看"显示论文详情（弹窗或展开）
- 点击"发布"调用main.py --publish处理单篇论文

#### 论文详情弹窗
```
+--------------------------------------------------+
|  论文详情                              [X]       |
+--------------------------------------------------+
|  arXiv ID: 2603.03195v1                          |
|  标题: Chain of World: World Model Thinking...   |
|  作者: Fuxiang Yang, Donglin Di, ...             |
|  分类: cs.CV                                     |
|  发布日期: 2026-03-03                            |
|                                                  |
|  发布状态: 未发布                                |
|  [发布到知乎]  [查看Markdown]  [重新总结]        |
+--------------------------------------------------+
```

### 3.4 系统状态模块

#### 界面元素
```
+--------------------------------------------------+
|  系统状态                                         |
+--------------------------------------------------+
|                                                  |
|  系统概览:                                        |
|  +--------------+ +--------------+ +------------+|
|  | 总论文数     | | 已发布       | | 待发布     ||
|  |     7        | |     2        | |     5      ||
|  +--------------+ +--------------+ +------------+|
|                                                  |
|  知乎状态: [● 已登录]  专栏: 世界模型-arxiv...    |
|  [检查登录状态]  [刷新专栏列表]                   |
|                                                  |
|  最近操作:                                        |
|  +----------------------------------------------+|
|  | 时间       | 操作         | 状态   | 结果   ||
|  |------------|--------------|--------|--------||
|  | 18:30:00   | 完整流程     | 完成   | 成功   ||
|  | 18:00:00   | 仅发布       | 完成   | 成功   ||
|  +----------------------------------------------+|
|                                                  |
|  系统日志 (最近50行):                             |
|  +----------------------------------------------+|
|  | 18:30:05 - INFO - 扫描完成，找到3篇新论文    ||
|  | 18:30:10 - INFO - 开始总结论文...            ||
|  | ...                                          ||
|  +----------------------------------------------+|
|                                                  |
+--------------------------------------------------+
```

#### 交互逻辑
- 实时读取brief.json统计论文数量
- 调用main.py --check-zhihu检查登录状态
- 显示最近操作历史（可存储在本地localStorage）
- 显示系统日志（可读取日志文件或捕获输出）

## 4. 技术实现方案

### 4.1 文件结构
```
gui/
├── index.html          # 主页面
├── css/
│   └── style.css       # 样式文件
├── js/
│   ├── app.js          # 主应用逻辑
│   ├── config.js       # 配置管理
│   ├── papers.js       # 论文列表管理
│   └── api.js          # 后端接口调用
└── server.py           # 简单的HTTP服务器（可选）
```

### 4.2 核心功能实现

#### 调用main.py
```javascript
// 使用WebSocket或Server-Sent Events实时获取输出
async function runMain(args) {
    const response = await fetch('/api/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({args: args})
    });
    
    // 实时读取输出流
    const reader = response.body.getReader();
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        appendOutput(new TextDecoder().decode(value));
    }
}
```

#### 读取/写入config.yaml
```javascript
// 读取配置
async function loadConfig() {
    const response = await fetch('/api/config');
    return await response.json();
}

// 保存配置
async function saveConfig(config) {
    await fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(config)
    });
}

// 保存AI配置（包含章节定义）
async function saveAIConfig(aiConfig) {
    await fetch('/api/config/ai', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(aiConfig)
    });
}

// 更新章节定义
async function updateSummarySections(sections) {
    await fetch('/api/config/ai/sections', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({summary_sections: sections})
    });
}
```

#### 读取brief.json
```javascript
// 获取所有论文
async function getPapers() {
    const response = await fetch('/api/papers');
    return await response.json();
}
```

### 4.3 简易后端（server.py）
使用Python Flask提供简单的API接口：

```python
from flask import Flask, request, jsonify
import subprocess
import yaml
import json
from pathlib import Path

app = Flask(__name__)

@app.route('/api/run', methods=['POST'])
def run_main():
    args = request.json.get('args', [])
    process = subprocess.Popen(
        ['python', 'main.py'] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    def generate():
        for line in process.stdout:
            yield line
    
    return Response(generate(), mimetype='text/plain')

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        config = request.json
        with open('config/config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return {'status': 'ok'}

@app.route('/api/config/ai', methods=['GET', 'POST'])
def ai_config():
    """AI配置管理（包含提示词和章节定义）"""
    if request.method == 'GET':
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('ai', {})
    else:
        ai_config = request.json
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        config['ai'] = ai_config
        with open('config/config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return {'status': 'ok'}

@app.route('/api/config/ai/sections', methods=['GET', 'POST'])
def summary_sections():
    """章节定义管理"""
    if request.method == 'GET':
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('ai', {}).get('summary_sections', [])
    else:
        sections = request.json.get('summary_sections', [])
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if 'ai' not in config:
            config['ai'] = {}
        config['ai']['summary_sections'] = sections
        with open('config/config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return {'status': 'ok'}

@app.route('/api/papers', methods=['GET'])
def get_papers():
    papers = []
    papers_dir = Path('papers')
    for folder in papers_dir.iterdir():
        if folder.is_dir():
            brief_file = folder / 'brief.json'
            if brief_file.exists():
                with open(brief_file, 'r') as f:
                    brief = json.load(f)
                    papers.extend(brief.get('papers', {}).values())
    return papers

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

## 5. 样式设计

### 5.1 颜色方案
- 主色调：蓝色 (#1890ff)
- 成功色：绿色 (#52c41a)
- 警告色：橙色 (#faad14)
- 错误色：红色 (#f5222d)
- 背景色：浅灰 (#f0f2f5)
- 文字色：深灰 (#333333)

### 5.2 组件样式
- 按钮：圆角矩形，悬停效果
- 输入框：边框样式，聚焦高亮
- 表格：斑马纹，悬停高亮
- 卡片：阴影效果，圆角

### 5.3 响应式断点
- 桌面端：> 1024px
- 平板端：768px - 1024px
- 移动端：< 768px（简化布局）

## 6. 部署方案

### 6.1 启动方式
```bash
# 方式1: 直接打开HTML文件（功能受限，无法调用Python）
open gui/index.html

# 方式2: 启动简易后端
python gui/server.py
# 然后访问 http://localhost:5000

# 方式3: 集成到main.py
python main.py --gui
# 自动启动Web界面
```

### 6.2 依赖
- Python: flask, pyyaml
- 前端: 无依赖（原生JS）或使用CDN引入轻量级框架

## 7. 开发计划

### 第一阶段：基础功能
1. 搭建基础HTML结构和样式
2. 实现运行控制模块（调用main.py）
3. 实现配置管理模块（读写config.yaml）
4. **实现AI配置模块（支持提示词和章节定义编辑）**

### 第二阶段：数据展示
1. 实现论文列表模块（读取brief.json）
2. 实现系统状态模块
3. 添加筛选和搜索功能

### 第三阶段：优化完善
1. 添加响应式适配
2. 优化用户体验（加载状态、错误提示等）
3. 添加操作历史记录
4. **添加章节定义可视化编辑功能**

## 8. 注意事项

1. **安全性**：Cookie和API密钥等敏感信息需要加密存储
2. **并发**：避免同时执行多个main.py实例
3. **错误处理**：完善错误提示和用户反馈
4. **兼容性**：确保在不同浏览器上正常工作
5. **性能**：论文数量多时考虑分页加载

## 9. 配置版本更新说明

### v1.5.0 配置更新（2026-03-04）

#### 新增配置项
1. **AI配置**
   - `system_prompt`: 系统提示词（多行文本）
   - `prompt_template`: 提示词模板（多行文本，支持占位符）
   - `summary_sections`: 章节定义列表（数组）
   - `max_input_tokens`: 最大输入token数（默认131072）

#### 章节定义结构
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
```

#### GUI适配
- AI配置页面分为三个标签页：基本设置、提示词设置、章节定义
- 提示词编辑支持多行文本，使用YAML block scalar语法
- 章节定义支持表格形式展示，可添加/删除/编辑/排序
- 字段类型支持文本（string）和列表（list）两种

#### 向后兼容
- 旧版本配置文件仍然兼容
- 新增配置项有默认值，不强制要求配置
- 章节定义为空时，summarizer使用默认行为

## 10. 总结

## 11. 单实例约束设计

### 11.1 设计目标
确保同一时间只能运行一个GUI服务器实例，防止多网页连接导致的冲突问题。

### 11.2 实现方案

#### 后端实现（server.py）
```python
import socket

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
if __name__ == '__main__':
    if not check_single_instance(port=5000):
        print("错误：GUI服务器已经在运行（端口5000被占用）")
        print("请关闭已运行的实例后再启动")
        sys.exit(1)
    
    # 正常启动服务器
    app.run(debug=True, host='0.0.0.0', port=5000)
```

#### 错误提示
当检测到已有实例运行时，显示以下错误信息：
```
错误：GUI服务器已经在运行（端口5000被占用）
请关闭已运行的实例后再启动
```

### 11.3 工作原理
1. 启动时尝试绑定到本地端口5000
2. 如果绑定成功，说明没有其他实例在运行，继续启动
3. 如果绑定失败（端口被占用），说明已有实例在运行，退出程序
4. 前端页面正常显示，无需额外处理

### 11.4 注意事项
- 单实例约束仅限制GUI服务器实例数量，不影响main.py的命令行执行
- 如果端口5000被其他程序占用，GUI服务器将无法启动
- 异常退出时端口可能未及时释放，需要等待或手动释放

---

## 12. 日志中文化

### 12.1 设计目标
将所有英文日志信息替换为中文，提高系统可维护性和易用性。

### 12.2 实现范围
已中文化的模块包括：
- scanner/scanner.py - 扫描器模块
- scanner/pdf_extractor.py - PDF提取器模块
- core/system.py - 系统核心模块
- storage/storage.py - 存储管理模块
- publisher/zhihu_playwright.py - 知乎发布器模块
- publisher/zhihu.py - 知乎API模块
- summarizer/summarizer.py - AI总结器模块
- scheduler/scheduler.py - 任务调度器模块
- main.py - 主程序
- gui/server.py - GUI服务器

### 12.3 示例
**修改前：**
```python
logger.info("Found 10 papers")
logger.error("Failed to publish article")
```

**修改后：**
```python
logger.info("找到 10 篇论文")
logger.error("发布文章失败")
```

---

## 总结

本轻量级GUI设计方案直接利用现有的main.py接口和配置文件，无需复杂后端架构。通过简单的HTTP服务器提供API接口，前端使用原生技术实现，降低了开发和维护成本。界面简洁直观，满足基本的功能需求，适合个人或小型团队使用。

主要特性：
- ✅ 轻量级单页应用
- ✅ 配置文件在线编辑
- ✅ 论文列表实时查看
- ✅ 实时日志输出
- ✅ 单实例运行约束
- ✅ 全中文日志输出