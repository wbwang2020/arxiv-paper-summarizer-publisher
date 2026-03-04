/**
 * ArXiv文献自动总结系统 - GUI前端逻辑
 */

// API基础URL
const API_BASE = 'http://localhost:5000/api';

// 全局变量
let currentProcess = null;
let currentConfig = null;
let currentPapers = [];
let selectedPaper = null;
let currentSections = [];
let editingSectionIndex = -1;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initConfigTabs();
    initAIConfigTabs();
    loadConfig();
    loadPapers();
    loadStats();
    loadOperations();
    
    // 温度滑块事件
    const temperatureSlider = document.getElementById('temperature');
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', function() {
            document.getElementById('temperatureValue').textContent = this.value;
        });
    }
});

// ==================== 标签切换 ====================

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // 更新按钮状态
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 更新内容显示
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabId) {
                    content.classList.add('active');
                }
            });
        });
    });
}

function initConfigTabs() {
    const configTabs = document.querySelectorAll('.config-tab');
    const configContents = document.querySelectorAll('.config-content');
    
    configTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const configId = tab.dataset.config;
            
            // 更新标签状态
            configTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 更新内容显示
            configContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `config-${configId}`) {
                    content.classList.add('active');
                }
            });
        });
    });
}

function initAIConfigTabs() {
    const aiConfigTabs = document.querySelectorAll('.ai-config-tab');
    const aiConfigContents = document.querySelectorAll('.ai-config-content');
    
    aiConfigTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const configId = tab.dataset.aiConfig;
            
            // 更新标签状态
            aiConfigTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // 更新内容显示
            aiConfigContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `ai-config-${configId}`) {
                    content.classList.add('active');
                }
            });
        });
    });
}

// ==================== 运行控制 ====================

async function startExecution() {
    const outputArea = document.getElementById('outputArea');
    const runMode = document.querySelector('input[name="runMode"]:checked').value;
    const verbose = document.getElementById('verboseMode').checked;
    
    // 构建参数
    let args = [runMode];
    
    if (runMode === '--paper') {
        const paperId = document.getElementById('paperId').value.trim();
        if (!paperId) {
            showAlert('请输入arXiv ID', 'error');
            return;
        }
        args.push(paperId);
    }
    
    if (verbose) {
        args.push('-v');
    }
    
    // 清空输出区域
    outputArea.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ args: args })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            // 按行分割文本
            const lines = text.split('\n');
            
            lines.forEach(lineText => {
                if (lineText.trim() !== '') {
                    const line = document.createElement('div');
                    line.textContent = lineText;
                    outputArea.appendChild(line);
                }
            });
            
            outputArea.scrollTop = outputArea.scrollHeight;
        }
        
        // 记录操作
        addOperation(getModeName(runMode), '完成');
        
        // 刷新数据
        setTimeout(() => {
            loadPapers();
            loadStats();
        }, 1000);
        
    } catch (error) {
        showAlert('执行失败：' + error.message, 'error');
        addOperation(getModeName(runMode), '失败');
    }
}

function stopExecution() {
    showAlert('停止功能需要在后端实现进程管理', 'warning');
}

function getModeName(mode) {
    const modeNames = {
        '--run-once': '完整流程',
        '--scan': '仅扫描',
        '--publish': '仅发布',
        '--paper': '处理单篇论文'
    };
    return modeNames[mode] || mode;
}

// ==================== 配置管理 ====================

async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        currentConfig = await response.json();
        
        // 填充表单
        fillConfigForm(currentConfig);
        
    } catch (error) {
        console.error('加载配置失败：', error);
        showAlert('加载配置失败', 'error');
    }
}

function fillConfigForm(config) {
    // arXiv配置
    if (config.arxiv) {
        // 关键词
        const keywordsList = document.getElementById('keywordsList');
        keywordsList.innerHTML = '';
        if (config.arxiv.keywords) {
            config.arxiv.keywords.forEach(keyword => {
                addKeywordTag(keyword);
            });
        }
        
        // 分类
        if (config.arxiv.categories) {
            config.arxiv.categories.forEach(cat => {
                const checkbox = document.getElementById(`cat-${cat.replace('.', '')}`);
                if (checkbox) checkbox.checked = true;
            });
        }
        
        document.getElementById('daysBack').value = config.arxiv.days_back || 14;
        document.getElementById('maxResults').value = config.arxiv.max_results || 10;
        document.getElementById('sortBy').value = config.arxiv.sort_by || 'submittedDate';
    }
    
    // AI配置
    if (config.ai) {
        document.getElementById('aiProvider').value = config.ai.provider || 'deepseek';
        document.getElementById('aiApiKey').value = config.ai.api_key || '';
        document.getElementById('aiApiUrl').value = config.ai.api_url || '';
        document.getElementById('aiModel').value = config.ai.model || '';
        document.getElementById('temperature').value = config.ai.temperature || 0.7;
        document.getElementById('temperatureValue').textContent = config.ai.temperature || 0.7;
        document.getElementById('maxTokens').value = config.ai.max_tokens || 8000;
        document.getElementById('maxInputTokens').value = config.ai.max_input_tokens || 131072;
        document.getElementById('aiTimeout').value = config.ai.timeout || 300;
        document.getElementById('systemPrompt').value = config.ai.system_prompt || '';
        document.getElementById('promptTemplate').value = config.ai.prompt_template || '';
        
        // 加载章节定义
        if (config.ai.summary_sections && Array.isArray(config.ai.summary_sections)) {
            currentSections = config.ai.summary_sections;
            renderSectionsTable();
        }
    }
    
    // 存储配置
    if (config.storage) {
        document.getElementById('storageDir').value = config.storage.base_dir || './papers';
        document.getElementById('storageFormat').value = config.storage.format || 'markdown';
        document.getElementById('filenameTemplate').value = config.storage.filename_template || '{date}_{arxiv_id}_{title}';
        document.getElementById('organizeBy').value = config.storage.organize_by || 'date';
    }
    
    // 知乎配置
    if (config.zhihu) {
        document.getElementById('zhihuEnabled').checked = config.zhihu.enabled || false;
        document.getElementById('zhihuCookie').value = config.zhihu.cookie || '';
        document.getElementById('zhihuColumn').value = config.zhihu.column_name || '';
        document.getElementById('contentFillMode').value = config.zhihu.content_fill_mode || 'import_document';
        document.getElementById('zhihuDebug').checked = config.zhihu.debug || false;
    }
}

function addKeywordTag(keyword) {
    const keywordsList = document.getElementById('keywordsList');
    const tag = document.createElement('span');
    tag.className = 'keyword-tag';
    tag.innerHTML = `
        ${keyword}
        <span class="remove" onclick="removeKeyword(this)">&times;</span>
    `;
    keywordsList.appendChild(tag);
}

function addKeyword() {
    const keyword = prompt('请输入关键词：');
    if (keyword && keyword.trim()) {
        addKeywordTag(keyword.trim());
    }
}

function removeKeyword(element) {
    element.parentElement.remove();
}

async function saveConfig() {
    try {
        const config = collectConfigFromForm();
        
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showAlert('配置保存成功', 'success');
            currentConfig = config;
        } else {
            throw new Error('保存失败');
        }
        
    } catch (error) {
        showAlert('保存配置失败：' + error.message, 'error');
    }
}

function collectConfigFromForm() {
    // 收集关键词
    const keywords = [];
    document.querySelectorAll('.keyword-tag').forEach(tag => {
        const text = tag.textContent.replace('×', '').trim();
        if (text) keywords.push(text);
    });
    
    // 收集分类
    const categories = [];
    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(cb => {
        categories.push(cb.value);
    });
    
    return {
        arxiv: {
            keywords: keywords,
            categories: categories,
            days_back: parseInt(document.getElementById('daysBack').value),
            max_results: parseInt(document.getElementById('maxResults').value),
            sort_by: document.getElementById('sortBy').value,
            sort_order: 'descending'
        },
        ai: {
            provider: document.getElementById('aiProvider').value,
            api_key: document.getElementById('aiApiKey').value,
            api_url: document.getElementById('aiApiUrl').value,
            model: document.getElementById('aiModel').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            max_input_tokens: parseInt(document.getElementById('maxInputTokens').value),
            timeout: parseInt(document.getElementById('aiTimeout').value),
            system_prompt: document.getElementById('systemPrompt').value,
            prompt_template: document.getElementById('promptTemplate').value,
            summary_sections: currentSections
        },
        storage: {
            base_dir: document.getElementById('storageDir').value,
            format: document.getElementById('storageFormat').value,
            filename_template: document.getElementById('filenameTemplate').value,
            organize_by: document.getElementById('organizeBy').value,
            include_metadata: false
        },
        zhihu: {
            enabled: document.getElementById('zhihuEnabled').checked,
            cookie: document.getElementById('zhihuCookie').value,
            column_name: document.getElementById('zhihuColumn').value,
            create_column_if_not_exists: false,
            draft_first: false,
            auto_publish: true,
            content_fill_mode: document.getElementById('contentFillMode').value,
            debug: document.getElementById('zhihuDebug').checked
        },
        scheduler: currentConfig?.scheduler || {
            enabled: true,
            cron: '0 9 * * *',
            timezone: 'Asia/Shanghai'
        }
    };
}

function resetConfig() {
    if (confirm('确定要重置配置吗？所有修改将丢失。')) {
        loadConfig();
    }
}

function exportConfig() {
    const config = collectConfigFromForm();
    const yamlContent = objectToYaml(config);
    
    const blob = new Blob([yamlContent], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'config.yaml';
    a.click();
    URL.revokeObjectURL(url);
}

function objectToYaml(obj, indent = 0) {
    let yaml = '';
    const spaces = '  '.repeat(indent);
    
    for (const [key, value] of Object.entries(obj)) {
        if (value === null || value === undefined) {
            yaml += `${spaces}${key}: null\n`;
        } else if (Array.isArray(value)) {
            yaml += `${spaces}${key}:\n`;
            value.forEach(item => {
                yaml += `${spaces}  - "${item}"\n`;
            });
        } else if (typeof value === 'object') {
            yaml += `${spaces}${key}:\n`;
            yaml += objectToYaml(value, indent + 1);
        } else if (typeof value === 'boolean') {
            yaml += `${spaces}${key}: ${value}\n`;
        } else if (typeof value === 'number') {
            yaml += `${spaces}${key}: ${value}\n`;
        } else {
            yaml += `${spaces}${key}: "${value}"\n`;
        }
    }
    
    return yaml;
}

// ==================== 论文列表 ====================

async function loadPapers() {
    try {
        const response = await fetch(`${API_BASE}/papers`);
        currentPapers = await response.json();
        
        renderPapersTable(currentPapers);
        updatePaperStats(currentPapers);
        
    } catch (error) {
        console.error('加载论文列表失败：', error);
        showAlert('加载论文列表失败', 'error');
    }
}

function renderPapersTable(papers) {
    const tbody = document.getElementById('papersTableBody');
    tbody.innerHTML = '';
    
    if (papers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">暂无论文</td></tr>';
        return;
    }
    
    papers.forEach(paper => {
        const isPublished = paper.zhihu_published && paper.zhihu_article_url;
        const statusIcon = isPublished ? '✅' : '⏳';
        const statusClass = isPublished ? 'published' : 'unpublished';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="status ${statusClass}">${statusIcon}</td>
            <td>${paper.arxiv_id}</td>
            <td title="${paper.title}">${truncateText(paper.title, 40)}</td>
            <td>${paper.primary_category || '-'}</td>
            <td>${formatDate(paper.published_date)}</td>
            <td class="actions">
                <button class="btn-small" onclick="viewPaper('${paper.arxiv_id}')">查看</button>
                ${!isPublished ? `<button class="btn-small" onclick="publishSinglePaper('${paper.arxiv_id}')">发布</button>` : ''}
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updatePaperStats(papers) {
    const total = papers.length;
    const published = papers.filter(p => p.zhihu_published && p.zhihu_article_url).length;
    const unpublished = total - published;
    
    document.getElementById('totalPapers').textContent = total;
    document.getElementById('publishedCount').textContent = published;
    document.getElementById('unpublishedCount').textContent = unpublished;
}

function filterPapers() {
    const filter = document.getElementById('paperFilter').value;
    let filtered = currentPapers;
    
    if (filter === 'published') {
        filtered = currentPapers.filter(p => p.zhihu_published && p.zhihu_article_url);
    } else if (filter === 'unpublished') {
        filtered = currentPapers.filter(p => !p.zhihu_published || !p.zhihu_article_url);
    }
    
    renderPapersTable(filtered);
}

function searchPapers() {
    const searchTerm = document.getElementById('paperSearch').value.toLowerCase();
    
    if (!searchTerm) {
        renderPapersTable(currentPapers);
        return;
    }
    
    const filtered = currentPapers.filter(paper => 
        paper.title.toLowerCase().includes(searchTerm) ||
        paper.arxiv_id.toLowerCase().includes(searchTerm)
    );
    
    renderPapersTable(filtered);
}

function viewPaper(arxivId) {
    selectedPaper = currentPapers.find(p => p.arxiv_id === arxivId);
    if (!selectedPaper) return;
    
    const modalBody = document.getElementById('paperModalBody');
    const isPublished = selectedPaper.zhihu_published && selectedPaper.zhihu_article_url;
    
    modalBody.innerHTML = `
        <p><strong>arXiv ID：</strong>${selectedPaper.arxiv_id}</p>
        <p><strong>标题：</strong>${selectedPaper.title}</p>
        <p><strong>作者：</strong>${selectedPaper.authors ? selectedPaper.authors.join(', ') : '-'}</p>
        <p><strong>分类：</strong>${selectedPaper.primary_category || '-'}</p>
        <p><strong>发布日期：</strong>${formatDate(selectedPaper.published_date)}</p>
        <p><strong>保存日期：</strong>${formatDate(selectedPaper.saved_at)}</p>
        <p><strong>发布状态：</strong>${isPublished ? '已发布' : '未发布'}</p>
        ${isPublished ? `<p><strong>知乎链接：</strong><a href="${selectedPaper.zhihu_article_url}" target="_blank">${selectedPaper.zhihu_article_url}</a></p>` : ''}
    `;
    
    const publishBtn = document.getElementById('publishBtn');
    publishBtn.style.display = isPublished ? 'none' : 'inline-block';
    
    document.getElementById('paperModal').classList.add('show');
}

function closeModal() {
    document.getElementById('paperModal').classList.remove('show');
    selectedPaper = null;
}

async function publishPaper() {
    if (!selectedPaper) return;
    
    closeModal();
    
    // 切换到运行控制标签
    document.querySelector('[data-tab="control"]').click();
    
    // 设置单篇论文模式
    document.querySelector('input[value="--paper"]').checked = true;
    document.getElementById('paperId').value = selectedPaper.arxiv_id;
    
    // 开始执行
    await startExecution();
}

function publishSinglePaper(arxivId) {
    selectedPaper = currentPapers.find(p => p.arxiv_id === arxivId);
    if (selectedPaper) {
        publishPaper();
    }
}

// ==================== 系统状态 ====================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('statTotal').textContent = stats.total;
        document.getElementById('statPublished').textContent = stats.published;
        document.getElementById('statUnpublished').textContent = stats.unpublished;
        
    } catch (error) {
        console.error('加载统计信息失败：', error);
    }
}

async function checkZhihuLogin() {
    const statusDiv = document.getElementById('zhihuStatus');
    statusDiv.innerHTML = '<span class="loading"></span> 检查中...';
    
    try {
        const response = await fetch(`${API_BASE}/check-zhihu`);
        const result = await response.json();
        
        if (result.logged_in) {
            statusDiv.innerHTML = '<span class="status-dot green"></span> 已登录';
        } else {
            statusDiv.innerHTML = '<span class="status-dot red"></span> 未登录';
        }
        
    } catch (error) {
        statusDiv.innerHTML = '<span class="status-dot red"></span> 检查失败';
    }
}

function loadOperations() {
    const operations = JSON.parse(localStorage.getItem('operations') || '[]');
    renderOperationsTable(operations);
}

function addOperation(operation, status) {
    const operations = JSON.parse(localStorage.getItem('operations') || '[]');
    
    operations.unshift({
        time: new Date().toLocaleString(),
        operation: operation,
        status: status
    });
    
    // 只保留最近20条
    if (operations.length > 20) {
        operations.pop();
    }
    
    localStorage.setItem('operations', JSON.stringify(operations));
    renderOperationsTable(operations);
}

function renderOperationsTable(operations) {
    const tbody = document.getElementById('operationsTableBody');
    tbody.innerHTML = '';
    
    if (operations.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">暂无操作记录</td></tr>';
        return;
    }
    
    operations.forEach(op => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${op.time}</td>
            <td>${op.operation}</td>
            <td>${op.status}</td>
        `;
        tbody.appendChild(row);
    });
}

function refreshStatus() {
    loadStats();
    loadPapers();
    updateLastUpdateTime();
    showAlert('状态已刷新', 'success');
}

function updateLastUpdateTime() {
    document.getElementById('lastUpdate').textContent = 
        '最后更新：' + new Date().toLocaleString();
}

// ==================== 章节定义管理 ====================

function renderSectionsTable() {
    const tbody = document.getElementById('sectionsTableBody');
    tbody.innerHTML = '';
    
    if (currentSections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px;">暂无章节定义</td></tr>';
        return;
    }
    
    currentSections.forEach((section, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${section.section_number || ''}</td>
            <td>${section.field_name || ''}</td>
            <td>${section.description || ''}</td>
            <td>${section.field_type === 'list' ? '列表' : '文本'}</td>
            <td class="actions">
                <input type="checkbox" class="section-checkbox" data-index="${index}">
                <button class="btn-small" onclick="editSection(${index})">编辑</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function addSection() {
    editingSectionIndex = -1;
    document.getElementById('sectionNumber').value = '';
    document.getElementById('fieldName').value = '';
    document.getElementById('fieldDescription').value = '';
    document.querySelector('input[name="fieldType"][value="string"]').checked = true;
    document.getElementById('sectionModal').classList.add('show');
}

function editSection(index) {
    editingSectionIndex = index;
    const section = currentSections[index];
    
    document.getElementById('sectionNumber').value = section.section_number || '';
    document.getElementById('fieldName').value = section.field_name || '';
    document.getElementById('fieldDescription').value = section.description || '';
    
    const fieldType = section.field_type || 'string';
    document.querySelector(`input[name="fieldType"][value="${fieldType}"]`).checked = true;
    
    document.getElementById('sectionModal').classList.add('show');
}

function saveSection() {
    const section = {
        section_number: document.getElementById('sectionNumber').value.trim(),
        field_name: document.getElementById('fieldName').value.trim(),
        description: document.getElementById('fieldDescription').value.trim(),
        field_type: document.querySelector('input[name="fieldType"]:checked').value
    };
    
    if (!section.section_number || !section.field_name) {
        showAlert('请填写章节编号和字段名', 'error');
        return;
    }
    
    if (editingSectionIndex >= 0) {
        currentSections[editingSectionIndex] = section;
    } else {
        currentSections.push(section);
    }
    
    renderSectionsTable();
    closeSectionModal();
}

function closeSectionModal() {
    document.getElementById('sectionModal').classList.remove('show');
    editingSectionIndex = -1;
}

function deleteSelectedSections() {
    const checkboxes = document.querySelectorAll('.section-checkbox:checked');
    if (checkboxes.length === 0) {
        showAlert('请选择要删除的章节', 'warning');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${checkboxes.length} 个章节吗？`)) {
        return;
    }
    
    const indicesToDelete = Array.from(checkboxes).map(cb => parseInt(cb.dataset.index)).sort((a, b) => b - a);
    indicesToDelete.forEach(index => {
        currentSections.splice(index, 1);
    });
    
    renderSectionsTable();
}

function moveSectionUp() {
    const checkboxes = document.querySelectorAll('.section-checkbox:checked');
    if (checkboxes.length !== 1) {
        showAlert('请选择一个章节进行移动', 'warning');
        return;
    }
    
    const index = parseInt(checkboxes[0].dataset.index);
    if (index === 0) {
        showAlert('已经是第一个章节了', 'warning');
        return;
    }
    
    const temp = currentSections[index];
    currentSections[index] = currentSections[index - 1];
    currentSections[index - 1] = temp;
    
    renderSectionsTable();
}

function moveSectionDown() {
    const checkboxes = document.querySelectorAll('.section-checkbox:checked');
    if (checkboxes.length !== 1) {
        showAlert('请选择一个章节进行移动', 'warning');
        return;
    }
    
    const index = parseInt(checkboxes[0].dataset.index);
    if (index === currentSections.length - 1) {
        showAlert('已经是最后一个章节了', 'warning');
        return;
    }
    
    const temp = currentSections[index];
    currentSections[index] = currentSections[index + 1];
    currentSections[index + 1] = temp;
    
    renderSectionsTable();
}

// ==================== 工具函数 ====================

function truncateText(text, maxLength) {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN');
    } catch {
        return dateString;
    }
}

function showAlert(message, type = 'info') {
    // 创建提示元素
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // 插入到页面顶部
    const container = document.querySelector('.container');
    container.insertBefore(alert, container.firstChild);
    
    // 3秒后自动移除
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// 点击弹窗外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('paperModal');
    if (event.target === modal) {
        closeModal();
    }
}
