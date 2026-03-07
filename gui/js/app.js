/**
 * ArXiv文献自动总结系统 - GUI前端逻辑
 */

// API基础URL
const API_BASE = 'http://127.0.0.1:5000/api';

// 全局变量
let currentProcess = null;
let currentConfig = null;
let currentPapers = [];
let selectedPaper = null;
let currentSections = [];
let editingSectionIndex = -1;
let isProcessing = false;
let currentServerId = null;

// 心跳机制变量
let heartbeatInterval = null;
let lastHeartbeatTime = 0;
const HEARTBEAT_INTERVAL = 2000; // 心跳间隔2秒
const HEARTBEAT_TIMEOUT = 5000;  // 心跳超时5秒

// 从localStorage恢复处理状态
function restoreProcessingState() {
    const savedState = localStorage.getItem('isProcessing');
    if (savedState === 'true') {
        isProcessing = true;
    }
}

// 保存处理状态到localStorage
function saveProcessingState(processing) {
    localStorage.setItem('isProcessing', processing);
}

// 更新配置控件的禁用状态
function updateConfigControlsState(disabled) {
    const configSection = document.getElementById('config');
    if (!configSection) return;
    
    // 禁用/启用所有配置输入控件
    const inputs = configSection.querySelectorAll('input, select, textarea, button');
    inputs.forEach(input => {
        // 保存按钮除外
        if (input.type === 'submit' || input.textContent === '保存配置') {
            return;
        }
        input.disabled = disabled;
    });
    
    // 添加/移除禁用样式
    if (disabled) {
        configSection.classList.add('config-disabled');
    } else {
        configSection.classList.remove('config-disabled');
    }
}

// 检查服务器是否重启，如果是则清除输出缓存
async function checkServerRestart() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        const serverId = data.server_id;
        
        const lastServerId = localStorage.getItem('serverId');
        
        if (lastServerId && lastServerId !== serverId) {
            console.log('检测到服务器重启，清除输出缓存和处理状态');
            localStorage.removeItem('outputCache');
            localStorage.removeItem('isProcessing'); // 清除处理状态
            isProcessing = false;
        }
        
        localStorage.setItem('serverId', serverId);
        currentServerId = serverId;
    } catch (error) {
        console.error('检查服务器状态失败:', error);
    }
}

// 保存运行控制状态
function saveControlState() {
    const runMode = document.querySelector('input[name="runMode"]:checked')?.value || '--run-once';
    const verboseMode = document.getElementById('verboseMode')?.checked || false;
    localStorage.setItem('runMode', runMode);
    localStorage.setItem('verboseMode', verboseMode);
}

// 加载运行控制状态
function loadControlState() {
    const runMode = localStorage.getItem('runMode') || '--run-once';
    const verboseMode = localStorage.getItem('verboseMode') === 'true';
    
    const runModeRadio = document.querySelector(`input[name="runMode"][value="${runMode}"]`);
    if (runModeRadio) {
        runModeRadio.checked = true;
    }
    
    const verboseCheckbox = document.getElementById('verboseMode');
    if (verboseCheckbox) {
        verboseCheckbox.checked = verboseMode;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', async function() {
    await checkServerRestart(); // 先检查服务器是否重启
    restoreProcessingState(); // 恢复处理状态
    
    initTabs();
    initConfigTabs();
    initAIConfigTabs();
    loadConfig();
    loadPapers();
    loadStats();
    loadOperations();
    loadControlState(); // 加载运行控制状态
    loadOutputCache(); // 加载缓存的输出内容
    
    // 恢复配置控件的禁用状态
    updateConfigControlsState(isProcessing);
    
    // 初始化系统状态显示
    updateSystemStatus();
    
    // 初始化连接状态为断开（等待首次检查）
    updateConnectionStatus(false);
    
    // 温度滑块事件
    const temperatureSlider = document.getElementById('temperature');
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', function() {
            document.getElementById('temperatureValue').textContent = this.value;
        });
    }
    
    // 运行控制状态变化监听
    const runModeRadios = document.querySelectorAll('input[name="runMode"]');
    runModeRadios.forEach(radio => {
        radio.addEventListener('change', saveControlState);
    });
    
    const verboseCheckbox = document.getElementById('verboseMode');
    if (verboseCheckbox) {
        verboseCheckbox.addEventListener('change', saveControlState);
    }
    
    // 启动心跳机制
    startHeartbeat();
    
    // 页面可见性变化时处理心跳
    document.addEventListener('visibilitychange', handleVisibilityChange);
});

// ==================== 心跳机制 ====================

function startHeartbeat() {
    // 启动心跳检测
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
    
    // 立即执行一次
    doHeartbeat();
    
    // 定期执行心跳
    heartbeatInterval = setInterval(doHeartbeat, HEARTBEAT_INTERVAL);
}

function stopHeartbeat() {
    // 停止心跳检测
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

async function doHeartbeat() {
    // 执行心跳检测
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000); // 3秒超时
        
        const response = await fetch(`${API_BASE}/status`, {
            signal: controller.signal,
            cache: 'no-cache' // 禁用缓存
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const data = await response.json();
            lastHeartbeatTime = Date.now();
            
            // 更新连接状态为正常
            updateConnectionStatus(true);
            
            // 检查处理状态变化
            if (data.is_processing !== isProcessing) {
                isProcessing = data.is_processing;
                saveProcessingState(isProcessing);
                updateProcessingUI();
            }
            
            // 恢复缓冲的输出
            if (data.is_processing && data.output_buffer && data.output_buffer.length > 0) {
                const outputArea = document.getElementById('outputArea');
                if (outputArea && outputArea.children.length === 0) {
                    data.output_buffer.forEach(lineText => {
                        if (lineText.trim() !== '') {
                            const line = document.createElement('div');
                            line.textContent = lineText;
                            outputArea.appendChild(line);
                        }
                    });
                    outputArea.scrollTop = outputArea.scrollHeight;
                }
            }
        } else {
            // 响应不正常，标记为断开
            handleHeartbeatFailure();
        }
    } catch (error) {
        // 如果是请求被中止（AbortError），不处理
        if (error.name === 'AbortError') {
            console.log('心跳请求被中止');
            return;
        }
        // 其他请求失败，标记为断开
        handleHeartbeatFailure();
    }
}

function handleHeartbeatFailure() {
    // 处理心跳失败
    const now = Date.now();
    const timeSinceLastHeartbeat = now - lastHeartbeatTime;
    
    // 如果超过超时时间没有成功的心跳，标记为断开
    if (timeSinceLastHeartbeat > HEARTBEAT_TIMEOUT) {
        updateConnectionStatus(false);
    }
}

function handleVisibilityChange() {
    // 处理页面可见性变化
    if (document.hidden) {
        // 页面隐藏时，记录日志
        console.log('页面隐藏');
    } else {
        // 页面显示时，检查是否需要立即更新状态
        console.log('页面显示，检查连接状态');
        const now = Date.now();
        const timeSinceLastHeartbeat = now - lastHeartbeatTime;
        // 如果超过心跳间隔没有更新，立即执行一次心跳
        if (timeSinceLastHeartbeat > HEARTBEAT_INTERVAL) {
            doHeartbeat();
        }
    }
}

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
            
            // 如果切换到输出配置标签，加载输出配置
            if (configId === 'output') {
                loadOutputConfig();
            }
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

function loadOutputCache() {
    const outputArea = document.getElementById('outputArea');
    const cachedOutput = localStorage.getItem('outputCache');
    
    if (cachedOutput) {
        outputArea.innerHTML = '';
        const lines = cachedOutput.split('\n');
        lines.forEach(lineText => {
            if (lineText.trim() !== '') {
                const line = document.createElement('div');
                line.textContent = lineText;
                outputArea.appendChild(line);
            }
        });
        outputArea.scrollTop = outputArea.scrollHeight;
    }
}

async function startExecution() {
    const outputArea = document.getElementById('outputArea');
    const runMode = document.querySelector('input[name="runMode"]:checked').value;
    const verbose = document.getElementById('verboseMode').checked;
    
    // 检查是否已在处理中
    if (isProcessing) {
        showAlert('已有任务在运行中，请等待完成后再启动新任务', 'error');
        return;
    }
    
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
    
    // 清空输出区域和缓存
    outputArea.innerHTML = '';
    localStorage.removeItem('outputCache');
    
    try {
        const response = await fetch(`${API_BASE}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ args: args })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '请求失败');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let outputContent = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value, { stream: true });
            // 按行分割文本
            const lines = text.split('\n');
            
            lines.forEach(lineText => {
                if (lineText.trim() !== '') {
                    const line = document.createElement('div');
                    line.textContent = lineText;
                    outputArea.appendChild(line);
                    outputContent += lineText + '\n';
                }
            });
            
            // 保存到缓存
            localStorage.setItem('outputCache', outputContent);
            
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

async function stopExecution() {
    try {
        const response = await fetch(`${API_BASE}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showAlert('处理已停止', 'success');
        } else {
            const error = await response.json();
            showAlert('停止失败：' + error.error, 'error');
        }
    } catch (error) {
        showAlert('停止处理失败：' + error.message, 'error');
    }
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
        console.log('开始加载配置...');
        const response = await fetch(`${API_BASE}/config`);
        console.log('配置请求状态:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }
        currentConfig = await response.json();
        console.log('配置加载成功:', currentConfig);
        
        // 填充表单
        fillConfigForm(currentConfig);
        
    } catch (error) {
        console.error('加载配置失败：', error);
        showAlert('加载配置失败: ' + error.message, 'error');
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
        console.log('开始加载论文列表...');
        const response = await fetch(`${API_BASE}/papers`);
        console.log('论文列表请求状态:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }
        currentPapers = await response.json();
        console.log('论文列表加载成功:', currentPapers.length, '篇论文');
        
        renderPapersTable(currentPapers);
        updatePaperStats(currentPapers);
        
    } catch (error) {
        console.error('加载论文列表失败：', error);
        showAlert('加载论文列表失败: ' + error.message, 'error');
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

// 更新系统状态显示
function updateSystemStatus() {
    console.log('更新系统状态:', isProcessing ? '正在处理任务...' : '系统就绪');
    const statusElement = document.getElementById('systemStatus');
    if (!statusElement) {
        console.error('找不到systemStatus元素');
        return;
    }
    if (isProcessing) {
        statusElement.textContent = '正在处理任务...';
        statusElement.className = 'processing';
    } else {
        statusElement.textContent = '系统就绪';
        statusElement.className = 'ready';
    }
}

// 更新连接状态显示
function updateConnectionStatus(connected) {
    console.log('更新连接状态:', connected ? '后台连接正常' : '后台连接断开');
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (!lastUpdateElement) {
        console.error('找不到lastUpdate元素');
        return;
    }
    if (connected) {
        lastUpdateElement.textContent = '后台连接正常 | 最后更新：' + new Date().toLocaleString();
        lastUpdateElement.className = 'connected';
    } else {
        lastUpdateElement.textContent = '后台连接断开';
        lastUpdateElement.className = 'disconnected';
    }
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

// ==================== 处理状态管理 ====================

function updateProcessingUI() {
    const startButton = document.querySelector('button[onclick="startExecution()"]');
    const stopButton = document.createElement('button');
    stopButton.textContent = '停止处理';
    stopButton.className = 'btn-secondary';
    stopButton.onclick = stopExecution;
    
    const buttonContainer = startButton.parentElement;
    
    if (isProcessing) {
        startButton.disabled = true;
        startButton.textContent = '处理中...';
        
        // 禁用配置控件
        updateConfigControlsState(true);
        
        // 更新系统状态
        updateSystemStatus();
        
        // 检查是否已存在停止按钮
        if (!document.querySelector('button[onclick="stopExecution()"]')) {
            buttonContainer.appendChild(stopButton);
        }
    } else {
        startButton.disabled = false;
        startButton.textContent = '开始执行';
        
        // 启用配置控件
        updateConfigControlsState(false);
        
        // 更新系统状态
        updateSystemStatus();
        
        // 移除停止按钮
        const existingStopButton = document.querySelector('button[onclick="stopExecution()"]');
        if (existingStopButton) {
            existingStopButton.remove();
        }
    }
}

async function stopExecution() {
    try {
        const response = await fetch(`${API_BASE}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            showAlert('处理已停止', 'success');
        } else {
            const error = await response.json();
            showAlert('停止失败：' + error.error, 'error');
        }
    } catch (error) {
        showAlert('停止处理失败：' + error.message, 'error');
    }
}

// ==================== 输出配置管理 ====================

async function loadOutputConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/output`);
        const outputConfig = await response.json();
        renderOutputConfig(outputConfig);
    } catch (error) {
        console.error('加载输出配置失败：', error);
        showAlert('加载输出配置失败', 'error');
    }
}

function renderOutputConfig(config) {
    const modulesContainer = document.getElementById('outputModules');
    modulesContainer.innerHTML = '';
    
    const modules = {
        'main': '主模块',
        'core': '核心系统',
        'scanner': '论文扫描器',
        'summarizer': 'AI总结器',
        'storage': '存储管理',
        'publisher': '知乎发布器',
        'scheduler': '任务调度器'
    };
    
    for (const [moduleId, moduleName] of Object.entries(modules)) {
        const moduleConfig = config.modules?.[moduleId] || {
            debug: false,
            log_level: 'INFO',
            enable_debug: false
        };
        
        const moduleDiv = document.createElement('div');
        moduleDiv.className = 'output-module';
        moduleDiv.innerHTML = `
            <h3>${moduleName}</h3>
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="${moduleId}-debug" ${moduleConfig.debug ? 'checked' : ''}>
                    <span>调试模式</span>
                </label>
            </div>
            <div class="form-group">
                <label for="${moduleId}-log-level">日志级别：</label>
                <select id="${moduleId}-log-level">
                    <option value="DEBUG" ${moduleConfig.log_level === 'DEBUG' ? 'selected' : ''}>DEBUG</option>
                    <option value="INFO" ${moduleConfig.log_level === 'INFO' ? 'selected' : ''}>INFO</option>
                    <option value="WARNING" ${moduleConfig.log_level === 'WARNING' ? 'selected' : ''}>WARNING</option>
                    <option value="ERROR" ${moduleConfig.log_level === 'ERROR' ? 'selected' : ''}>ERROR</option>
                    <option value="CRITICAL" ${moduleConfig.log_level === 'CRITICAL' ? 'selected' : ''}>CRITICAL</option>
                </select>
            </div>
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="${moduleId}-enable-debug" ${moduleConfig.enable_debug ? 'checked' : ''}>
                    <span>启用调试输出</span>
                </label>
            </div>
        `;
        
        modulesContainer.appendChild(moduleDiv);
    }
}

async function saveOutputConfig() {
    try {
        const modules = {
            'main': '主模块',
            'core': '核心系统',
            'scanner': '论文扫描器',
            'summarizer': 'AI总结器',
            'storage': '存储管理',
            'publisher': '知乎发布器',
            'scheduler': '任务调度器'
        };
        
        const modulesConfig = {};
        for (const moduleId of Object.keys(modules)) {
            modulesConfig[moduleId] = {
                debug: document.getElementById(`${moduleId}-debug`).checked,
                log_level: document.getElementById(`${moduleId}-log-level`).value,
                enable_debug: document.getElementById(`${moduleId}-enable-debug`).checked
            };
        }
        
        const outputConfig = {
            modules: modulesConfig
        };
        
        const response = await fetch(`${API_BASE}/config/output`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(outputConfig)
        });
        
        if (response.ok) {
            showAlert('输出配置保存成功', 'success');
        } else {
            throw new Error('保存失败');
        }
        
    } catch (error) {
        showAlert('保存输出配置失败：' + error.message, 'error');
    }
}

// 输出配置现在作为配置管理的子标签，在切换到该标签时自动加载
