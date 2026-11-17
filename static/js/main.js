/**
 * VizScript Hub - 前端交互逻辑
 */

// ============================================================
// 全局状态
// ============================================================
const state = {
    scripts: [],
    currentFilter: 'all',
    uploadedFile: null,
    currentScriptId: null,
    currentScriptContent: null,
    aiModifiedContent: null,
    pollTimer: null,
    workspaceModal: null,
    addScriptModal: null,
    diffModal: null,
    isLocalhost: ['127.0.0.1', 'localhost', '::1'].includes(window.location.hostname),
    // 工作区执行状态
    workspace: {
        scriptId: null,
        uploadedFile: null,
        taskId: null,
        outputUrl: null,
        taskMeta: null,
        currentScript: null,
        // 分页
        totalRows: 0,
        currentPage: 0,
        pageSize: 25,
        sortColumn: null,
        sortDirection: 'asc',
        // 筛选
        filterStack: [],
        filterLogic: 'and',
        filteredRowCount: null,
        filteredFileName: null,
        // 列操作
        selectedColumns: [],
        columnRenames: {},
        // 搜索
        searchKeyword: '',
        // @PARAM 参数
        parsedParams: [],
        paramValues: {}
    },
    // AI 模型选择
    selectedAIModel: 'mimo-v2.5',
    availableModels: []
};

// ============================================================
// 初始化
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // 先加载数据（不依赖 Bootstrap），避免某个外部库加载失败导致整页卡在“加载中”
    loadScripts();
    loadProjectHistory();
    loadSuggestionCount();
    loadColorLibrary();
    loadAIModels();
    setupKeyboard();

    // 弹窗依赖 Bootstrap；缺失时降级提示，不影响上面数据加载
    initBootstrapModals();
});

function initBootstrapModals() {
    if (typeof window.bootstrap === 'undefined') {
        console.warn('[Script Hub] Bootstrap 未加载，弹窗功能不可用。请确认 static/vendor 目录下资源齐全。');
        state.workspaceModal = null;
        state.addScriptModal = null;
        state.diffModal = null;
        state.manualEditModal = null;
        state.suggestionsModal = null;
        return;
    }
    state.workspaceModal = new bootstrap.Modal(document.getElementById('scriptWorkspaceModal'));
    state.addScriptModal = new bootstrap.Modal(document.getElementById('addScriptModal'));
    state.diffModal = new bootstrap.Modal(document.getElementById('diffModal'));
    state.manualEditModal = new bootstrap.Modal(document.getElementById('manualEditModal'));
    state.suggestionsModal = new bootstrap.Modal(document.getElementById('suggestionsModal'));
}

// ============================================================
// 1. 脚本列表加载与过滤
// ============================================================

async function loadScripts(filter = 'all') {
    try {
        let url;
        if (filter === 'all') {
            url = '/api/scripts';
        } else if (filter === 'data_process') {
            url = '/api/scripts?category=data_process';
        } else if (filter === 'modified') {
            url = '/api/scripts?modified=true';
        } else {
            url = `/api/scripts?language=${filter}`;
        }
        const res = await fetch(url);
        const data = await res.json();

        state.scripts = data.scripts;
        updateScriptCounts();
        // 重新应用搜索关键字
        const kw = state.workspace.searchKeyword || document.getElementById('searchInput').value.toLowerCase().trim();
        if (kw) {
            state.workspace.searchKeyword = kw;
            const filtered = state.scripts.filter(s =>
                s.name.toLowerCase().includes(kw) ||
                s.description.toLowerCase().includes(kw) ||
                s.id.toLowerCase().includes(kw)
            );
            renderScriptCards(filtered);
        } else {
            renderScriptCards(state.scripts);
        }
    } catch (err) {
        showToast('加载脚本失败: ' + err.message, 'danger');
    }
}

function updateScriptCounts() {
    fetch('/api/scripts').then(r => r.json()).then(data => {
        const all = data.scripts;
        document.getElementById('countAll').textContent = all.length;
        document.getElementById('countR').textContent = all.filter(s => s.language === 'R').length;
        document.getElementById('countPy').textContent = all.filter(s => s.language === 'Python').length;
        document.getElementById('countDP').textContent = all.filter(s => s.category === 'data_process').length;
        document.getElementById('countModified').textContent = all.filter(s => s.based_on).length;
    });
    // 更新上传文件计数
    fetch('/api/uploads').then(r => r.json()).then(data => {
        document.getElementById('uploadCount').textContent = data.items ? data.items.length : 0;
    }).catch(() => {});
    // 刷新历史项目列表
    loadProjectHistory();
}

function renderScriptCards(scripts) {
    const grid = document.getElementById('scriptGrid');

    if (scripts.length === 0) {
        grid.innerHTML = `
            <div class="text-center text-muted py-5" style="grid-column: 1 / -1;">
                <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                <p class="mt-3">暂无匹配的脚本</p>
            </div>`;
        return;
    }

    grid.innerHTML = scripts.map(s => {
        const isDP = s.category === 'data_process';
        const langClass = isDP ? 'dp-lang' : (s.language === 'R' ? 'r-lang' : 'py-lang');
        const langIcon = isDP ? 'bi-gear-fill' : (s.language === 'R' ? 'bi-r-circle-fill' : 'bi-p-circle-fill');
        const langLabel = isDP ? '数据处理' : s.language;
        const thumbSrc = s.thumbnail ? `/${s.thumbnail}` : null;
        const basedOnTag = s.based_on
            ? `<span class="modified-tag" title="基于 ${s.based_on} 修改"><i class="bi bi-pencil-square"></i> 修改版</span>`
            : '';
        const fmtLabel = s.data_format === 'wide' ? '宽数据' : s.data_format === 'long' ? '长数据' : '';
        const fmtTag = fmtLabel
            ? `<span class="data-format-tag ${s.data_format === 'wide' ? 'fmt-wide' : 'fmt-long'}" title="数据格式: ${fmtLabel}">${fmtLabel}</span>`
            : '';

        return `
        <div class="script-card" onclick="openScriptWorkspace('${s.id}')">
            ${basedOnTag}
            ${fmtTag}
            <span class="lang-badge ${langClass}">
                <i class="${langIcon}"></i> ${langLabel}
            </span>
            <div class="card-thumb">
                ${thumbSrc
                    ? `<img src="${thumbSrc}?t=${Date.now()}" alt="${s.name}" onerror="this.parentElement.innerHTML='<i class=\\'bi bi-file-earmark-code\\'></i>'">`
                    : `<i class="bi bi-file-earmark-code"></i>`}
            </div>
            <h6>${escapeHtml(s.name)}</h6>
            <p>${escapeHtml(s.description || '暂无描述')}</p>
            <div class="card-actions" onclick="event.stopPropagation()">
                <button class="btn btn-gradient btn-sm" onclick="openScriptWorkspace('${s.id}')"
                        title="打开工作区">
                    <i class="bi bi-play-fill"></i> 运行
                </button>
                <button class="btn btn-outline-info btn-sm" onclick="loadScriptToAIById('${s.id}')"
                        title="发送到 AI">
                    <i class="bi bi-robot"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

function filterScripts(language, el) {
    state.currentFilter = language;

    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    if (el) el.classList.add('active');

    const titles = {
        'all': '全部脚本',
        'R': 'R 脚本',
        'Python': 'Python 脚本',
        'data_process': '数据处理',
        'modified': '修改脚本'
    };
    document.getElementById('sectionTitle').textContent = titles[language] || '全部脚本';

    loadScripts(language);
}

function searchScripts() {
    const keyword = document.getElementById('searchInput').value.toLowerCase();
    state.workspace.searchKeyword = keyword;
    const filtered = state.scripts.filter(s =>
        s.name.toLowerCase().includes(keyword) ||
        s.description.toLowerCase().includes(keyword) ||
        s.id.toLowerCase().includes(keyword)
    );
    renderScriptCards(filtered);
}

async function reloadScripts() {
    await fetch('/api/scripts/reload');
    await loadScripts(state.currentFilter);
    showToast('脚本列表已刷新', 'success');
}

// ============================================================
// 2. 脚本执行工作区
// ============================================================

async function openScriptWorkspace(scriptId) {
    state.workspace.scriptId = scriptId;
    state.currentScriptId = scriptId;

    // 重置工作区状态
    state.workspace.uploadedFile = null;
    state.workspace.projectFolder = null;  // 历史项目重分析时使用
    state.workspace.taskId = null;
    state.workspace.outputUrl = null;
    state.workspace.taskMeta = null;
    state.workspace.selectedColumns = [];
    state.workspace.columnRenames = {};
    state.workspace.filterStack = [];
    state.workspace.filterLogic = 'and';
    state.workspace.filteredRowCount = null;
    state.workspace.filteredFileName = null;
    state.workspace.totalRows = 0;
    state.workspace.currentPage = 0;
    state.workspace.sortColumn = null;
    state.workspace.sortDirection = 'asc';
    state.workspace.currentScript = null;
    state.workspace.parsedParams = [];
    state.workspace.paramValues = {};
    if (state.pollTimer) {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
    }

    // 重置工作区 UI
    document.getElementById('workspacePreview').style.display = 'none';
    document.getElementById('workspaceFileInput').value = '';
    document.getElementById('workspaceResultSection').style.display = 'none';
    document.getElementById('workspaceLogSection').style.display = 'none';
    document.getElementById('workspaceResult').innerHTML = '';
    document.getElementById('workspaceLogContent').textContent = '';
    document.getElementById('workspaceRunBtn').disabled = true;
    document.getElementById('aiAnalysisPanel').style.display = 'none';
    document.getElementById('aiAnalysisContent').innerHTML = '';

    try {
        const res = await fetch(`/api/scripts/${scriptId}`);
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
            return;
        }

        const script = data.script;
        state.currentScriptContent = data.content;
        state.workspace.parsedParams = data.parsed_params || [];

        // 填充工作区头部
        document.getElementById('workspaceScriptName').textContent = script.name;

        // 填充脚本信息
        const langBadgeClass = script.language === 'R' ? 'r-lang' : 'py-lang';
        const fmt = script.data_format;
        const fmtDisplay = fmt === 'wide' ? '宽数据' : fmt === 'long' ? '长数据' : '-';
        document.getElementById('workspaceScriptInfo').innerHTML = `
            <p><strong>ID:</strong> ${script.id}
               <span class="lang-badge ${langBadgeClass} ms-2">${script.language}</span></p>
            <p><strong>描述:</strong><br>${(script.description || '-').replace(/\n/g, '<br>')}</p>
            ${script.data_requirements ? '<p><strong>数据要求:</strong><br>' + script.data_requirements.replace(/\n/g, '<br>') + '</p>' : ''}
            <p><strong>输入格式:</strong> ${script.input_format || 'csv'}
               &nbsp;|&nbsp; <strong>数据格式:</strong>
               <span class="data-format-tag-inline ${fmt === 'wide' ? 'fmt-wide' : fmt === 'long' ? 'fmt-long' : ''}">${fmtDisplay}</span>
               &nbsp;|&nbsp; <strong>文件:</strong> ${script.path}</p>`;

        // 填充脚本代码
        document.getElementById('workspaceScriptCode').textContent =
            data.content || '(脚本文件为空)';

        // 显示/隐藏示例数据按钮
        state.workspace.currentScript = script;

        const sampleBtn = document.getElementById('workspaceSampleBtn');
        if (script.sample_data) {
            sampleBtn.style.display = 'inline-block';
            sampleBtn.title = `加载示例数据: ${script.sample_data}`;
        } else {
            sampleBtn.style.display = 'none';
        }

        // 删除按钮权限控制：localhost 可删所有，内网仅可删修改版脚本（数据处理除外）
        const delBtn = document.querySelector('#scriptWorkspaceModal .btn-outline-danger');
        if (delBtn) {
            const isModified = !!script.based_on && script.category !== 'data_process';
            const canDelete = state.isLocalhost || isModified;
            delBtn.style.display = canDelete ? '' : 'none';
        }

        // 设置上传区域
        setupWorkspaceUpload();

        state.workspaceModal.show();
    } catch (err) {
        showToast('加载脚本失败: ' + err.message, 'danger');
    }
}

// 工作区上传事件是否已绑定（只需绑定一次）
let _workspaceUploadBound = false;

function setupWorkspaceUpload() {
    if (_workspaceUploadBound) return;
    _workspaceUploadBound = true;

    const dropZone = document.getElementById('workspaceDropZone');
    if (!dropZone) return;

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleWorkspaceFile(files[0]);
        }
    });

    // 文件选择按钮
    const fileInput = document.getElementById('workspaceFileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleWorkspaceFile(file);
        });
    }

    // "选择文件" 按钮
    const selectBtn = document.getElementById('workspaceSelectFileBtn');
    if (selectBtn) {
        selectBtn.addEventListener('click', () => {
            const fi = document.getElementById('workspaceFileInput');
            if (fi) fi.click();
        });
    }

    // 点击上传区（非按钮区域）打开文件选择器
    dropZone.addEventListener('click', (e) => {
        if (e.target.closest && e.target.closest('button')) return;
        const fi = document.getElementById('workspaceFileInput');
        if (fi) fi.click();
    });
}

async function handleWorkspaceFile(file) {
    const allowedExts = ['csv', 'xlsx', 'xls', 'txt'];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        showToast(`不支持的文件格式: .${ext}`, 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
            return;
        }

        state.workspace.uploadedFile = data.filename;
        state.uploadedFile = data.filename;
        // 初始化列
        state.workspace.selectedColumns = [...(data.columns || [])];
        state.workspace.columnRenames = {};
        state.workspace.filterStack = [];
        state.workspace.filterLogic = 'and';
        state.workspace.filteredRowCount = null;
        state.workspace.filteredFileName = null;
        state.workspace.totalRows = data.total_rows || 0;
        state.workspace.currentPage = 0;
        state.workspace.sortColumn = null;
        state.workspace.sortDirection = 'asc';
        // 清除筛选器缓存
        if (typeof _columnStats !== 'undefined') _columnStats = null;
        if (typeof _columnValuesFetching !== 'undefined') _columnValuesFetching = {};

        // 显示预览区
        document.getElementById('workspacePreview').style.display = 'block';
        document.getElementById('filterBuilderPanel').style.display = 'none';
        document.getElementById('appliedFilters').style.display = 'none';
        document.getElementById('filterResultSummary').style.display = 'none';
        if (document.getElementById('commitFilterBtn')) {
            const btn = document.getElementById('commitFilterBtn');
            btn.className = 'btn btn-sm btn-success';
            btn.innerHTML = '<i class="bi bi-check-circle"></i> 保留此筛选结果用于分析';
            btn.disabled = false;
        }

        // 更新信息栏
        document.getElementById('workspacePreviewInfo').innerHTML =
            `共 ${data.total_rows} 行，${data.total_columns} 列
             <span class="ms-2">
                 <span class="dropdown d-inline-block">
                     <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button"
                             data-bs-toggle="dropdown" data-bs-auto-close="outside" aria-expanded="false" title="列筛选">
                         <i class="bi bi-funnel"></i>
                         <span id="selectedColCount">${data.columns.length}/${data.columns.length}</span>
                     </button>
                     <div class="dropdown-menu dropdown-menu-end p-2" style="max-height:400px; overflow-y:auto; min-width:220px;" onclick="event.stopPropagation()">
                         <h6 class="dropdown-header px-1">批量操作</h6>
                         <div class="d-flex gap-1 px-1 mb-2">
                             <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="selectAllColumns()">全选</button>
                             <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="deselectAllColumns()">取消</button>
                             <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="invertColumnSelection()">反选</button>
                         </div>
                     </div>
                 </span>
             </span>
             <a id="previewDownloadLink" class="btn btn-sm btn-outline-secondary ms-2"
                href="javascript:void(0)" onclick="downloadWithRenames()"
                title="下载数据文件">
                 <i class="bi bi-download"></i> 下载
             </a>`;

        // 渲染分页表格
        renderPreviewTable();

        document.getElementById('workspaceRunBtn').disabled = false;
        showToast('文件上传成功', 'success');
    } catch (err) {
        showToast('上传失败: ' + err.message, 'danger');
    }
}

function clearWorkspaceUpload() {
    state.workspace.uploadedFile = null;
    state.workspace.projectFolder = null;
    state.workspace.filterStack = [];
    state.workspace.filteredFileName = null;
    state.workspace.filteredRowCount = null;
    state.workspace.selectedColumns = [];
    state.workspace.columnRenames = {};
    state.workspace.totalRows = 0;
    state.workspace.currentPage = 0;
    state.workspace.sortColumn = null;
    state.workspace.sortDirection = 'asc';
    document.getElementById('workspacePreview').style.display = 'none';
    document.getElementById('filterBuilderPanel').style.display = 'none';
    document.getElementById('workspaceFileInput').value = '';
    document.getElementById('workspaceRunBtn').disabled = true;
    if (typeof _columnStats !== 'undefined') _columnStats = null;
    if (typeof _columnValuesFetching !== 'undefined') _columnValuesFetching = {};
}

async function downloadWithRenames() {
    const fname = state.workspace.filteredFileName || state.workspace.uploadedFile;
    if (!fname) {
        showToast('没有可下载的文件', 'warning');
        return;
    }

    // 如果已有 filteredFileName（来自应用勾选/筛选提交），说明列选择和重命名已导出，直接下载
    if (state.workspace.filteredFileName) {
        const a = document.createElement('a');
        a.href = `/uploads/${state.workspace.filteredFileName}`;
        a.download = state.workspace.filteredFileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        return;
    }

    // 有重命名但未提交（没有 filteredFileName），调用导出接口
    const renames = state.workspace.columnRenames;
    const hasRenames = Object.keys(renames || {}).length > 0;
    if (hasRenames) {
        try {
            const res = await fetch(`/api/data/${encodeURIComponent(fname)}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ column_renames: renames })
            });
            const data = await res.json();
            if (data.error) {
                showToast('导出失败: ' + data.error, 'danger');
                return;
            }
            const a = document.createElement('a');
            a.href = `/uploads/${data.filtered_filename}`;
            a.download = data.filtered_filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (err) {
            showToast('下载失败: ' + err.message, 'danger');
        }
        return;
    }

    // 无任何处理，直接下载原文件
    const a = document.createElement('a');
    a.href = `/uploads/${fname}`;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function updateDownloadLink() {
    const link = document.getElementById('previewDownloadLink');
    if (!link) return;
    const target = state.workspace.filteredFileName || state.workspace.uploadedFile;
    if (target) {
        link.title = state.workspace.filteredFileName ? '下载筛选后数据' : '下载数据文件';
    }
}


async function loadSampleData() {
    if (!state.workspace.scriptId) return;

    try {
        const res = await fetch(`/api/scripts/${state.workspace.scriptId}`);
        const data = await res.json();
        const sampleFile = data.script.sample_data;

        if (!sampleFile) {
            showToast('此脚本没有配置示例数据', 'warning');
            return;
        }

        // 从 sample_data 目录加载文件并上传
        const fileRes = await fetch(`/sample_data/${sampleFile}`);
        if (!fileRes.ok) {
            showToast('示例数据文件不存在', 'danger');
            return;
        }

        const blob = await fileRes.blob();
        const file = new File([blob], sampleFile, { type: 'text/csv' });

        // 复用上传逻辑
        await handleWorkspaceFile(file);
        showToast('示例数据已加载', 'success');
    } catch (err) {
        showToast('加载示例数据失败: ' + err.message, 'danger');
    }
}

async function runScriptFromWorkspace() {
    const scriptId = state.workspace.scriptId;
    const uploadedFile = state.workspace.uploadedFile;

    if (!scriptId) {
        showToast('请先选择一个脚本', 'warning');
        return;
    }
    if (!uploadedFile) {
        showToast('请先上传数据文件', 'warning');
        return;
    }

    // 显示加载状态
    const resultSection = document.getElementById('workspaceResultSection');
    const resultDiv = document.getElementById('workspaceResult');
    resultSection.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="result-loading">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">正在准备数据...</p>
            <span class="status-badge status-running">
                <i class="bi bi-arrow-repeat"></i> 准备中
            </span>
        </div>`;

    // 如果有未提交的筛选条件，先自动导出筛选数据
    const hasUncommittedFilters = (state.workspace.filterStack || []).length > 0;
    if (hasUncommittedFilters && !state.workspace.filteredFileName) {
        try {
            await commitFilteredData();
        } catch (e) {
            // commitFilteredData 内部已提示错误，仍然继续执行（回退到原始数据）
        }
    }

    resultDiv.innerHTML = `
        <div class="result-loading">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">正在执行脚本...</p>
            <span class="status-badge status-running">
                <i class="bi bi-arrow-repeat"></i> 执行中
            </span>
        </div>`;

    try {
        const formData = new FormData();
        if (state.workspace.filteredFileName) {
            formData.append('use_filtered', state.workspace.filteredFileName);
            // 筛选文件已包含列选择和重命名的结果，无需重复发送
        } else {
            formData.append('use_uploaded', uploadedFile);
            // 列选择和重命名仅在未使用筛选文件时生效
            if (state.workspace.selectedColumns && state.workspace.selectedColumns.length > 0) {
                formData.append('columns', JSON.stringify(state.workspace.selectedColumns));
            }
            if (state.workspace.columnRenames && Object.keys(state.workspace.columnRenames).length > 0) {
                formData.append('column_renames', JSON.stringify(state.workspace.columnRenames));
            }
        }

        const res = await fetch(`/api/run/${scriptId}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.error) {
            throw new Error(data.error);
        }

        state.workspace.taskId = data.task_id;
        pollWorkspaceTaskStatus(data.task_id);

    } catch (err) {
        resultDiv.innerHTML = `
            <div class="text-center text-danger py-4">
                <i class="bi bi-exclamation-triangle-fill" style="font-size: 2rem;"></i>
                <p class="mt-2">${escapeHtml(err.message)}</p>
            </div>`;
        showToast('执行失败: ' + err.message, 'danger');
    }
}

// ============================================================
// @PARAM 参数控件 + 重绘
// ============================================================

function buildParamControls() {
    const params = state.workspace.parsedParams || [];
    if (params.length === 0) return '';

    let html = `
        <div class="param-controls mt-3 p-3" style="border:1px solid var(--border); border-radius:8px; background:var(--bg-card);">
            <h6 class="mb-3"><i class="bi bi-sliders"></i> 参数调整</h6>
            <div class="param-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:12px;">`;

    for (const p of params) {
        const val = state.workspace.paramValues[p.name] !== undefined
            ? state.workspace.paramValues[p.name] : p.default;
        const escapedVal = escapeHtml(String(val));
        const escapedName = escapeHtml(p.name);
        const escapedLabel = escapeHtml(p.label || p.name);

        if (p.type === 'bool') {
            const checked = val === true || val === 'true' ? 'checked' : '';
            html += `
                <label class="d-flex align-items-center gap-2" style="cursor:pointer; font-size:0.85rem;">
                    <input type="checkbox" class="param-input" data-param="${escapedName}" ${checked}>
                    <span>${escapedLabel}</span>
                </label>`;
        } else if (p.type === 'int') {
            html += `
                <div style="font-size:0.85rem;">
                    <label style="font-weight:500; margin-bottom:2px;">${escapedLabel}</label>
                    <input type="number" step="1" class="form-control form-control-sm param-input"
                           data-param="${escapedName}" value="${escapedVal}">
                </div>`;
        } else if (p.type === 'float') {
            html += `
                <div style="font-size:0.85rem;">
                    <label style="font-weight:500; margin-bottom:2px;">${escapedLabel}</label>
                    <input type="number" step="any" class="form-control form-control-sm param-input"
                           data-param="${escapedName}" value="${escapedVal}">
                </div>`;
        } else {
            html += `
                <div style="font-size:0.85rem;">
                    <label style="font-weight:500; margin-bottom:2px;">${escapedLabel}</label>
                    <input type="text" class="form-control form-control-sm param-input"
                           data-param="${escapedName}" value="${escapedVal}">
                </div>`;
        }
    }

    html += `</div>
        <button class="btn btn-gradient btn-sm mt-3" onclick="submitReplot()">
            <i class="bi bi-arrow-repeat"></i> 重绘
        </button>
    </div>`;

    return html;
}

async function submitReplot() {
    const scriptId = state.workspace.scriptId;
    const uploadedFile = state.workspace.uploadedFile;
    const projectFolder = state.workspace.projectFolder;

    if (!scriptId) {
        showToast('请先选择一个脚本', 'warning');
        return;
    }
    if (!uploadedFile && !projectFolder) {
        showToast('请先上传数据文件', 'warning');
        return;
    }

    // 收集参数值
    const paramInputs = document.querySelectorAll('.param-input');
    const params = {};
    paramInputs.forEach(el => {
        const name = el.dataset.param;
        if (el.type === 'checkbox') {
            params[name] = el.checked;
        } else if (el.type === 'number') {
            params[name] = parseFloat(el.value) || 0;
        } else {
            params[name] = el.value;
        }
    });
    state.workspace.paramValues = params;

    // 显示重绘中
    const resultDiv = document.getElementById('workspaceResult');
    const imgTag = resultDiv.querySelector('img');
    if (imgTag) {
        imgTag.style.opacity = '0.4';
    }
    if (!document.getElementById('replot-loading')) {
        const loadBadge = document.createElement('div');
        loadBadge.className = 'text-center py-2';
        loadBadge.id = 'replot-loading';
        loadBadge.innerHTML = '<span class="status-badge status-running"><i class="bi bi-arrow-repeat"></i> 重绘中...</span>';
        resultDiv.appendChild(loadBadge);
    }
    const btn = resultDiv.querySelector('.btn-gradient[onclick*="submitReplot"]');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split"></i> 重绘中...'; }

    try {
        const formData = new FormData();
        if (state.workspace.filteredFileName) {
            formData.append('use_filtered', state.workspace.filteredFileName);
        } else if (projectFolder) {
            formData.append('use_project_data', projectFolder);
        } else {
            formData.append('use_uploaded', uploadedFile);
        }
        formData.append('parameters', JSON.stringify(params));

        const res = await fetch(`/api/run/${scriptId}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        state.workspace.taskId = data.task_id;
        pollReplotStatus(data.task_id);
    } catch (err) {
        showToast('重绘失败: ' + err.message, 'danger');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 重绘'; }
        const lb = document.getElementById('replot-loading');
        if (lb) lb.remove();
        if (imgTag) imgTag.style.opacity = '1';
    }
}

function pollReplotStatus(taskId) {
    if (state.pollTimer) clearInterval(state.pollTimer);

    const resultDiv = document.getElementById('workspaceResult');
    const logSection = document.getElementById('workspaceLogSection');
    const logContent = document.getElementById('workspaceLogContent');
    let pollCount = 0;
    const maxPolls = 120;

    state.pollTimer = setInterval(async () => {
        pollCount++;
        if (pollCount > maxPolls) {
            clearInterval(state.pollTimer);
            showToast('重绘超时', 'danger');
            const lb = document.getElementById('replot-loading');
            if (lb) lb.remove();
            const btn = resultDiv.querySelector('.btn-gradient');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 重绘'; }
            const img = resultDiv.querySelector('img');
            if (img) img.style.opacity = '1';
            return;
        }

        try {
            const res = await fetch(`/api/status/${taskId}`);
            const data = await res.json();

            if (data.status === 'success') {
                clearInterval(state.pollTimer);
                state.workspace.outputUrl = data.result.output_url;
                state.workspace.taskMeta = data;
                state.workspace.projectFolder = data.folder_name || '';

                const imgUrl = data.result.output_url + '?t=' + Date.now();
                const img = resultDiv.querySelector('img');
                if (img) {
                    img.src = imgUrl;
                    img.style.opacity = '1';
                }

                const folderName = data.folder_name || '';
                const downloadBtns = renderDownloadButtons(data, folderName, data.result.output_url);
                const btnContainer = resultDiv.querySelector('.d-flex.justify-content-center.gap-2');
                if (btnContainer) {
                    btnContainer.outerHTML = `<p class="mt-2 d-flex justify-content-center gap-2 flex-wrap">${downloadBtns}
                        <button class="btn btn-sm btn-outline-info" onclick="analyzeResultImage('${escapeHtml(folderName)}')" title="AI 分析">
                            <i class="bi bi-robot"></i> AI 分析
                        </button></p>`;
                }

                logSection.style.display = 'block';
                logContent.textContent = data.result.stdout || '(无输出)';
                if (data.result.stderr) {
                    logContent.textContent += '\n\n[stderr]\n' + data.result.stderr;
                }

                const rb = resultDiv.querySelector('.btn-gradient');
                if (rb) { rb.disabled = false; rb.innerHTML = '<i class="bi bi-arrow-repeat"></i> 重绘'; }
                const lb = document.getElementById('replot-loading');
                if (lb) lb.remove();

                showToast('重绘成功', 'success');

            } else if (data.status === 'failed') {
                clearInterval(state.pollTimer);
                showToast('重绘失败: ' + (data.result?.error || 'unknown'), 'danger');
                const lb = document.getElementById('replot-loading');
                if (lb) lb.remove();
                const btn = resultDiv.querySelector('.btn-gradient');
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> 重绘'; }
                const img = resultDiv.querySelector('img');
                if (img) img.style.opacity = '1';
            }
        } catch (err) {
            clearInterval(state.pollTimer);
            showToast('重绘状态查询失败', 'danger');
        }
    }, 3000);
}

function pollWorkspaceTaskStatus(taskId) {
    if (state.pollTimer) clearInterval(state.pollTimer);

    const resultSection = document.getElementById('workspaceResultSection');
    const resultDiv = document.getElementById('workspaceResult');
    const logSection = document.getElementById('workspaceLogSection');
    const logContent = document.getElementById('workspaceLogContent');

    let pollCount = 0;
    const maxPolls = 120;

    state.pollTimer = setInterval(async () => {
        pollCount++;
        if (pollCount > maxPolls) {
            clearInterval(state.pollTimer);
            resultDiv.innerHTML = `
                <div class="text-center text-danger py-3">
                    <i class="bi bi-clock-fill"></i>
                    <p class="mt-2">任务执行超时</p>
                </div>`;
            return;
        }

        try {
            const res = await fetch(`/api/status/${taskId}`);
            const data = await res.json();

            if (data.status === 'success') {
                clearInterval(state.pollTimer);

                state.workspace.outputUrl = data.result.output_url;
                state.workspace.taskMeta = data;
                state.workspace.projectFolder = data.folder_name || '';

                const folderName = data.folder_name || '';
                const csvPreview = data.result.csv_preview;

                if (csvPreview) {
                    // 数据处理结果：显示 CSV 预览 + 下载
                    const csvUrl = data.result.csv_download || data.result.output_url;
                    resultDiv.innerHTML = `
                        <div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <small class="text-muted">
                                    <i class="bi bi-table"></i> 转换结果: ${csvPreview.shape[0]} 行 x ${csvPreview.shape[1]} 列
                                </small>
                                <a class="btn btn-sm btn-gradient" href="${csvUrl}" download>
                                    <i class="bi bi-download"></i> 下载 CSV
                                </a>
                            </div>
                            <div class="table-responsive" style="max-height: 300px;">
                                <table class="table table-sm table-bordered mb-0">
                                    <thead class="table-light">
                                        <tr>${csvPreview.columns.map(c => `<th>${escapeHtml(String(c))}</th>`).join('')}</tr>
                                    </thead>
                                    <tbody>
                                        ${csvPreview.rows.map(row =>
                                            '<tr>' + row.map(cell =>
                                                `<td>${escapeHtml(cell == null ? '' : String(cell))}</td>`
                                            ).join('') + '</tr>'
                                        ).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>`;
                } else {
                    // 可视化结果：显示图片
                    const imgUrl = data.result.output_url + '?t=' + Date.now();
                    const downloadBtns = renderDownloadButtons(data, folderName, data.result.output_url);

                    // 构建参数控件
                    const paramsHtml = buildParamControls();

                    resultDiv.innerHTML = `
                        <div class="text-center">
                            <img src="${imgUrl}" alt="执行结果"
                                 onclick="showImageOverlay('${escapeHtml(imgUrl)}')"
                                 style="cursor:zoom-in; max-width:100%; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                            <p class="mt-2 d-flex justify-content-center gap-2 flex-wrap">
                                ${downloadBtns}
                                <button class="btn btn-sm btn-outline-info"
                                        onclick="analyzeResultImage('${escapeHtml(folderName)}')"
                                        title="提交图表给 AI 分析">
                                    <i class="bi bi-robot"></i> AI 分析
                                </button>
                            </p>
                        </div>
                        ${paramsHtml}`;
                }

                logSection.style.display = 'block';
                logContent.textContent = data.result.stdout || '(无输出)';
                if (data.result.stderr) {
                    logContent.textContent += '\n\n[stderr]\n' + data.result.stderr;
                }

                showToast('脚本执行成功', 'success');
                appendHistoryLog(data);
                setTimeout(() => loadScripts(state.currentFilter), 1000);

            } else if (data.status === 'failed') {
                clearInterval(state.pollTimer);

                state.workspace.taskMeta = data;
                resultDiv.innerHTML = `
                    <div class="text-center text-danger py-4">
                        <i class="bi bi-x-circle-fill" style="font-size: 2rem;"></i>
                        <p class="mt-2">${escapeHtml(data.result?.error || '执行失败')}</p>
                    </div>`;

                logSection.style.display = 'block';
                logContent.textContent = (data.result?.stdout || '') +
                    '\n\n[stderr]\n' + (data.result?.stderr || '');

                showToast('脚本执行失败', 'danger');
                appendHistoryLog(data);

            } else if (data.status === 'running') {
                const elapsed = pollCount * 5;
                const badge = resultDiv.querySelector('.status-badge');
                if (badge) {
                    badge.innerHTML = `<i class="bi bi-arrow-repeat"></i> 执行中 (${elapsed}s)`;
                }
            }
        } catch (err) {
            clearInterval(state.pollTimer);
            showToast('状态查询失败: ' + err.message, 'danger');
        }
    }, 5000);
}

// ============================================================
// 2.5 AI 图像分析
// ============================================================

async function analyzeResultImage(folderName) {
    const panel = document.getElementById('aiAnalysisPanel');
    const content = document.getElementById('aiAnalysisContent');
    panel.style.display = 'block';
    content.innerHTML = `
        <div class="text-center text-muted py-3">
            <div class="spinner-border spinner-border-sm" role="status"></div>
            <p class="mt-2 mb-0">AI 正在分析图表图片...</p>
        </div>`;

    panel.scrollIntoView({ behavior: 'smooth' });

    try {
        const res = await fetch('/api/ai/analyze-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_name: folderName,
                model: (document.getElementById('aiAnalysisModelSelect')?.value) || 'mimo-v2.5'
            })
        });
        const data = await res.json();

        if (data.error) {
            throw new Error(data.error);
        }

        renderAIAnalysis(data.interpretation, data.suggestions, data.model_used);
    } catch (err) {
        content.innerHTML = `
            <div class="text-danger">
                <i class="bi bi-exclamation-triangle-fill"></i> 分析失败: ${escapeHtml(err.message)}
            </div>`;
    }
}


// ============================================================
// 3. 图片详情遮罩层
// ============================================================

function showImageOverlay(imgUrl) {
    const overlay = document.getElementById('imageOverlay');
    const overlayImg = document.getElementById('overlayImage');
    const metaDiv = document.getElementById('overlayMeta');
    const downloadBtn = document.getElementById('overlayDownloadBtn');

    overlayImg.src = imgUrl;
    downloadBtn.href = imgUrl;

    const meta = state.workspace.taskMeta;
    const folderName = meta ? meta.folder_name : '';
    const pdfBtn = document.getElementById('overlayDownloadPdfBtn');
    const jpgBtn = document.getElementById('overlayDownloadJpgBtn');
    if (pdfBtn && folderName) updateOverlayDownloadLinks(folderName, meta);
    if (meta) {
        const startedAt = meta.started_at
            ? new Date(meta.started_at).toLocaleString('zh-CN') : '-';
        const finishedAt = meta.finished_at
            ? new Date(meta.finished_at).toLocaleString('zh-CN') : '-';

        metaDiv.innerHTML = `
            <div class="meta-item">
                <span class="meta-label">脚本名称</span>
                <span class="meta-value">${escapeHtml(meta.script_name || '-')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">脚本语言</span>
                <span class="meta-value">${escapeHtml(meta.script_language || '-')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">脚本描述</span>
                <span class="meta-value">${escapeHtml(meta.script_description || '-')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">数据文件</span>
                <span class="meta-value">${escapeHtml(meta.data_filename || '-')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">工作目录</span>
                <span class="meta-value">${escapeHtml(meta.folder_name || '-')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">开始时间</span>
                <span class="meta-value">${startedAt}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">完成时间</span>
                <span class="meta-value">${finishedAt}</span>
            </div>
        `;
    } else {
        metaDiv.innerHTML = '<p class="text-muted">暂无元数据</p>';
    }

    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeImageOverlay() {
    document.getElementById('imageOverlay').style.display = 'none';
    document.body.style.overflow = '';
}

// ============================================================
// 4. 执行历史日志
// ============================================================

function appendHistoryLog(data) {
    const logPanel = document.getElementById('logPanel');
    const logContent = document.getElementById('logContent');

    logPanel.style.display = 'block';
    const time = new Date().toLocaleTimeString('zh-CN');
    const icon = data.status === 'success'
        ? '<i class="bi bi-check-circle-fill text-success"></i>'
        : '<i class="bi bi-x-circle-fill text-danger"></i>';
    const scriptName = data.script_name || data.script_id || '-';

    // 清除占位文本
    const placeholder = logContent.querySelector('.text-muted');
    if (placeholder) logContent.innerHTML = '';

    const entry = document.createElement('div');
    entry.className = 'history-entry';
    entry.style.cssText = 'padding:4px 0;border-bottom:1px solid #333;font-size:0.78rem;';
    entry.innerHTML = `${icon} [${time}] ${escapeHtml(scriptName)} - ${data.status === 'success' ? '成功' : '失败'}`;
    logContent.insertBefore(entry, logContent.firstChild);

    // 最多保留 20 条
    while (logContent.children.length > 20) {
        logContent.removeChild(logContent.lastChild);
    }
}

function toggleLogPanel() {
    const content = document.getElementById('logContent');
    const icon = document.getElementById('logToggleIcon');
    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.className = 'bi bi-chevron-up';
    } else {
        content.style.display = 'none';
        icon.className = 'bi bi-chevron-down';
    }
}

// ============================================================
// 4b. 历史项目
// ============================================================

async function loadProjectHistory() {
    try {
        const res = await fetch('/api/projects');
        const data = await res.json();
        renderProjectHistory(data.projects || []);
    } catch (err) {
        document.getElementById('projectHistoryList').innerHTML =
            '<small class="text-muted">加载失败</small>';
    }
}

function renderProjectHistory(projects) {
    const container = document.getElementById('projectHistoryList');

    if (projects.length === 0) {
        container.innerHTML = '<small class="text-muted">暂无历史项目</small>';
        return;
    }

    container.innerHTML = projects.slice(0, 15).map(p => {
        const dotClass = p.status === 'success' ? 'success' : 'failed';
        const time = p.finished_at
            ? new Date(p.finished_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
            : '';
        const name = p.script_name || p.folder_name;

        return `
        <div class="project-history-item" onclick="viewProject('${escapeHtml(p.folder_name)}')" title="${escapeHtml(p.script_description || '')}">
            <span class="project-dot ${dotClass}"></span>
            <span class="project-name">${escapeHtml(name)}</span>
            <span class="project-time">${time}</span>
            <span class="project-delete" onclick="deleteProject('${escapeHtml(p.folder_name)}', event)" title="删除此项目">
                <i class="bi bi-x-lg"></i>
            </span>
        </div>`;
    }).join('');

    if (projects.length > 15) {
        container.innerHTML +=
            `<small class="text-muted">...及其他 ${projects.length - 15} 个项目</small>`;
    }
}

async function viewProject(folderName) {
    try {
        const res = await fetch(`/api/projects/${folderName}`);
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
            return;
        }

        const meta = data.metadata || {};
        // 合并顶层 pdf_url / jpg_url 到 meta 中
        if (data.pdf_url) meta.pdf_url = data.pdf_url;
        if (data.jpg_url) meta.jpg_url = data.jpg_url;

        state.workspace.taskMeta = meta;
        state.workspace.uploadedFile = null;
        state.workspace.taskId = meta.task_id || null;
        state.workspace.outputUrl = meta.output_url || '';

        if (state.pollTimer) {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }

        // 打开工作区模态框并显示结果
        const scriptId = meta.script_id;
        if (scriptId) {
            await openScriptWorkspace(scriptId);
        }

        // 在 openScriptWorkspace 之后设置，避免被其重置逻辑覆盖
        state.workspace.projectFolder = folderName;

        // 如果有结果图片，直接显示
        if (meta.output_url) {
            const imgUrl = meta.output_url + '?t=' + Date.now();
            const downloadBtns = renderDownloadButtons(meta, folderName, meta.output_url);

            // 构建参数控件（使用 API 返回的 parsed_params）
            if (data.parsed_params && data.parsed_params.length > 0) {
                state.workspace.parsedParams = data.parsed_params;
                // 如果有保存的 user_params，用它们覆盖默认值
                if (meta.user_params && typeof meta.user_params === 'object') {
                    state.workspace.paramValues = { ...meta.user_params };
                }
            }
            const paramsHtml = buildParamControls();

            document.getElementById('workspaceResultSection').style.display = 'block';
            document.getElementById('workspaceResult').innerHTML = `
                <div class="text-center">
                    <img src="${imgUrl}" alt="执行结果"
                         onclick="showImageOverlay('${escapeHtml(imgUrl)}')"
                         style="cursor:zoom-in; max-width:100%; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                    <p class="mt-2 d-flex justify-content-center gap-2 flex-wrap">
                        ${downloadBtns}
                        <button class="btn btn-sm btn-outline-info"
                                onclick="analyzeResultImage('${escapeHtml(folderName)}')"
                                title="提交图表给 AI 分析">
                            <i class="bi bi-robot"></i> AI 分析
                        </button>
                    </p>
                </div>
                ${paramsHtml}`;
            // 构建完整执行日志
            const successStdout = meta.stdout || '';
            const successStderr = meta.stderr || '';
            let successLog = `项目: ${folderName}\n状态: ${meta.status || '未知'}\n创建时间: ${meta.created_at || '-'}\n完成时间: ${meta.finished_at || '-'}`;
            if (successStdout) successLog += `\n\n[stdout]\n${successStdout}`;
            if (successStderr) successLog += `\n\n[stderr]\n${successStderr}`;
            document.getElementById('workspaceLogSection').style.display = 'block';
            document.getElementById('workspaceLogContent').textContent = successLog;
        } else if (meta.status === 'failed') {
            // 显示失败信息 + 参数控件（允许重试）
            document.getElementById('workspaceResultSection').style.display = 'block';
            const errorMsg = meta.error || '未知错误';
            const stdout = meta.stdout || '';
            const stderr = meta.stderr || '';
            const paramsHtml = buildParamControls();
            document.getElementById('workspaceResult').innerHTML = `
                <div class="alert alert-danger mb-2">
                    <strong><i class="bi bi-exclamation-triangle-fill"></i> 执行失败</strong>
                    <p class="mb-0 mt-1">${escapeHtml(errorMsg)}</p>
                </div>
                ${stderr ? `<div class="card card-body bg-dark text-light p-2 mb-2" style="font-size:0.75rem; max-height:200px; overflow-y:auto;">
                    <strong class="text-danger">stderr:</strong>
                    <pre class="mb-0 text-light" style="white-space:pre-wrap;">${escapeHtml(stderr)}</pre>
                </div>` : ''}
                ${stdout ? `<div class="card card-body bg-dark text-light p-2" style="font-size:0.75rem; max-height:150px; overflow-y:auto;">
                    <strong class="text-info">stdout:</strong>
                    <pre class="mb-0 text-light" style="white-space:pre-wrap;">${escapeHtml(stdout)}</pre>
                </div>` : ''}
                ${paramsHtml}`;
            let failLog = `项目: ${folderName}\n状态: 失败\n创建时间: ${meta.created_at || '-'}\n完成时间: ${meta.finished_at || '-'}\n错误: ${errorMsg}`;
            if (stdout) failLog += `\n\n[stdout]\n${stdout}`;
            if (stderr) failLog += `\n\n[stderr]\n${stderr}`;
            document.getElementById('workspaceLogSection').style.display = 'block';
            document.getElementById('workspaceLogContent').textContent = failLog;
        }

        // 自动加载已保存的 AI 分析
        if (data.ai_analysis) {
            renderAIAnalysis(data.ai_analysis.interpretation, data.ai_analysis.suggestions);
        }

        // 更新图片遮罩层的下载按钮
        updateOverlayDownloadLinks(folderName, meta);

    } catch (err) {
        showToast('加载项目失败: ' + err.message, 'danger');
    }
}

function renderAIAnalysis(interpretation, suggestions, modelName) {
    const panel = document.getElementById('aiAnalysisPanel');
    const content = document.getElementById('aiAnalysisContent');
    panel.style.display = 'block';
    const interp = interpretation || '(无解读内容)';
    const sugg = suggestions || '(无改进建议)';
    const modelTag = modelName ? `<div class="text-end mb-1" style="font-size:0.7rem;color:var(--text-muted);">分析模型: ${escapeHtml(modelName)}</div>` : '';
    content.innerHTML = `
        ${modelTag}
        <ul class="nav nav-tabs nav-fill mb-2" style="font-size:0.8rem;">
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="#aiTabInterpret">📊 结果解读</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#aiTabSuggest">💡 改进建议</a>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane fade show active" id="aiTabInterpret">
                <div style="white-space:pre-wrap;">${escapeHtml(interp)}</div>
            </div>
            <div class="tab-pane fade" id="aiTabSuggest">
                <div style="white-space:pre-wrap;">${escapeHtml(sugg)}</div>
            </div>
        </div>`;
}

async function deleteProject(folderName, event) {
    event.stopPropagation();
    if (!confirm(`确定要删除项目「${folderName}」吗？`)) return;

    try {
        const res = await fetch(`/api/projects/${folderName}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast('项目已删除', 'success');
            loadProjectHistory();
        }
    } catch (err) {
        showToast('删除失败: ' + err.message, 'danger');
    }
}

async function clearAllProjects() {
    if (!confirm('确定要清除全部历史项目吗？此操作不可撤销。')) return;

    try {
        const res = await fetch('/api/projects', { method: 'DELETE' });
        const data = await res.json();
        showToast(data.message, 'success');
        loadProjectHistory();
    } catch (err) {
        showToast('清除失败: ' + err.message, 'danger');
    }
}

function getDownloadUrls(data, folderName) {
    // 优先使用脚本直接生成的 PDF/JPG，回退到 on-the-fly 转换
    const pdfUrl = data.result?.pdf_url || data.pdf_url
        || (folderName ? `/api/convert/${encodeURIComponent(folderName)}/pdf` : '');
    const jpgUrl = data.result?.jpg_url || data.jpg_url
        || (folderName ? `/api/convert/${encodeURIComponent(folderName)}/jpg` : '');
    return { pdfUrl, jpgUrl };
}

function renderDownloadButtons(data, folderName, pngUrl) {
    const { pdfUrl, jpgUrl } = getDownloadUrls(data, folderName);
    return `
        <a href="${pngUrl || '#'}" target="_blank"
           class="btn btn-sm btn-outline-primary" download>
            <i class="bi bi-download"></i> PNG
        </a>
        <a href="${pdfUrl}" target="_blank"
           class="btn btn-sm btn-outline-info" download>
            <i class="bi bi-file-pdf"></i> PDF
        </a>
        <a href="${jpgUrl}" target="_blank"
           class="btn btn-sm btn-outline-success" download>
            <i class="bi bi-file-image"></i> JPG
        </a>`;
}

function updateOverlayDownloadLinks(folderName, data) {
    const pdfBtn = document.getElementById('overlayDownloadPdfBtn');
    const jpgBtn = document.getElementById('overlayDownloadJpgBtn');
    const { pdfUrl, jpgUrl } = getDownloadUrls(data || state.workspace.taskMeta || {}, folderName);
    if (pdfBtn) pdfBtn.href = pdfUrl;
    if (jpgBtn) jpgBtn.href = jpgUrl;
}

// ============================================================
// 5. AI 对话界面
// ============================================================

function loadScriptToAI() {
    state.workspaceModal.hide();
    if (state.currentScriptId && state.currentScriptContent) {
        loadScriptToAIById(state.currentScriptId);
    }
}

function loadWorkspaceScriptToAI() {
    state.workspaceModal.hide();
    if (state.currentScriptId && state.currentScriptContent) {
        loadScriptToAIById(state.currentScriptId);
    }
}

async function loadScriptToAIById(scriptId) {
    try {
        const res = await fetch(`/api/scripts/${scriptId}`);
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
            return;
        }

        state.currentScriptId = scriptId;
        state.currentScriptContent = data.content;

        document.getElementById('aiScriptInfo').style.display = 'block';
        document.getElementById('aiCurrentScript').textContent = data.script.name;
        document.getElementById('aiInput').focus();

        addAIMessage('bot', `已加载脚本「${data.script.name}」(${data.script.language})。请告诉我你想如何修改它。`);

        if (window.innerWidth <= 992) {
            document.getElementById('aiPanel').classList.add('mobile-open');
        }
    } catch (err) {
        showToast('加载脚本到 AI 失败: ' + err.message, 'danger');
    }
}

async function sendAIMessage() {
    const input = document.getElementById('aiInput');
    const userRequest = input.value.trim();

    if (!userRequest) return;
    if (!state.currentScriptContent) {
        showToast('请先在左侧选择一个脚本', 'warning');
        return;
    }

    addAIMessage('user', userRequest);
    input.value = '';

    const thinkingId = addAIMessage('bot', '<i>正在分析您的需求...</i>');

    try {
        const res = await fetch('/api/ai/modify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                script_content: state.currentScriptContent,
                user_request: userRequest,
                language: 'Python',
                model: state.selectedAIModel
            })
        });
        const data = await res.json();

        removeAIMessage(thinkingId);

        if (data.error) {
            addAIMessage('bot', `❌ ${data.error}${data.hint ? '<br><small>' + data.hint + '</small>' : ''}`);
        } else {
            state.aiModifiedContent = data.modified_script;
            addAIMessage('bot',
                `✅ ${data.explanation}<br><br>
                 <button class="btn btn-sm btn-outline-primary" onclick="showDiff()">
                     <i class="bi bi-file-diff"></i> 查看代码对比
                 </button>
                 <button class="btn btn-sm btn-gradient ms-2" onclick="applyAIModification()">
                     <i class="bi bi-check-lg"></i> 应用修改
                 </button>`);
        }
    } catch (err) {
        removeAIMessage(thinkingId);
        addAIMessage('bot', `❌ 请求失败: ${err.message}`);
    }
}

function addAIMessage(role, html) {
    const container = document.getElementById('aiMessages');
    const id = 'msg_' + Date.now();
    const avatarIcon = role === 'user' ? 'bi-person-fill' : 'bi-robot';
    const roleClass = role === 'user' ? 'ai-user' : 'ai-bot';

    const div = document.createElement('div');
    div.className = `ai-message ${roleClass}`;
    div.id = id;
    div.innerHTML = `
        <div class="ai-avatar"><i class="${avatarIcon}"></i></div>
        <div class="ai-bubble">${html}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    return id;
}

function removeAIMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function clearAIChat() {
    document.getElementById('aiMessages').innerHTML = `
        <div class="ai-message ai-bot">
            <div class="ai-avatar"><i class="bi bi-robot"></i></div>
            <div class="ai-bubble">
                你好！我是 AI 脚本助手。<br>
                我可以帮你修改可视化脚本。<br>
                请先在左侧选择一个脚本，我会读取其内容，然后你可以告诉我如何修改。
            </div>
        </div>`;
    state.currentScriptContent = null;
    state.aiModifiedContent = null;
    document.getElementById('aiScriptInfo').style.display = 'none';
}

function showDiff() {
    if (!state.aiModifiedContent) return;

    const diffContent = document.getElementById('diffContent');
    const original = state.currentScriptContent || '';
    const modified = state.aiModifiedContent || '';

    const origLines = original.split('\n');
    const modLines = modified.split('\n');
    const maxLen = Math.max(origLines.length, modLines.length);

    let html = '<table class="table table-sm table-bordered diff-table"><tbody>';
    for (let i = 0; i < maxLen; i++) {
        const orig = i < origLines.length ? origLines[i] : '';
        const mod = i < modLines.length ? modLines[i] : '';
        const isDiff = orig !== mod;

        html += '<tr>';
        html += `<td class="diff-lineno" style="width:40px;text-align:right;color:#999;">${i + 1}</td>`;
        html += `<td class="${isDiff ? 'diff_sub' : ''}" style="width:48%;font-family:monospace;font-size:0.8rem;white-space:pre-wrap;">${escapeHtml(orig)}</td>`;
        html += `<td class="diff-lineno" style="width:40px;text-align:right;color:#999;">${i + 1}</td>`;
        html += `<td class="${isDiff ? 'diff_add' : ''}" style="width:48%;font-family:monospace;font-size:0.8rem;white-space:pre-wrap;">${escapeHtml(mod)}</td>`;
        html += '</tr>';
    }
    html += '</tbody></table>';

    diffContent.innerHTML = html;
    state.diffModal.show();
}

async function applyAIModification() {
    if (!state.aiModifiedContent || !state.currentScriptId) {
        showToast('没有可应用的修改', 'warning');
        return;
    }

    // 提示用户输入新脚本 ID 和名称
    const newId = prompt('请输入新脚本 ID:', state.currentScriptId + '_v2');
    if (!newId) return;
    const newName = prompt('请输入新脚本名称:', '');
    if (!newName) return;

    try {
        const res = await fetch(`/api/scripts/${state.currentScriptId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: state.aiModifiedContent,
                source: 'ai',
                new_id: newId.trim(),
                new_name: newName.trim()
            })
        });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast(`已保存为新脚本: ${newName}`, 'success');
            state.currentScriptContent = state.aiModifiedContent;
            state.aiModifiedContent = null;
            state.diffModal.hide();
            addAIMessage('bot', '✅ AI 修改已保存为新脚本。');
            loadScripts(state.currentFilter);
        }
    } catch (err) {
        showToast('保存失败: ' + err.message, 'danger');
    }
}

// ============================================================
// 6. 脚本管理 (添加/删除)
// ============================================================

function showAddScriptModal() {
    document.getElementById('addScriptForm').reset();
    // 类型切换
    document.getElementById('addScriptLanguageCol').style.display = '';
    document.getElementById('addScriptLanguage').required = true;
    // 清除之前的验证状态
    document.querySelectorAll('#addScriptForm .is-invalid').forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll('#addScriptForm .dup-feedback').forEach(el => el.remove());
    state.addScriptModal.show();
    // 延迟绑定验证，确保 DOM 已渲染
    setTimeout(() => setupAddScriptValidation(), 100);
}

function onAddScriptCategoryChange() {
    const cat = document.getElementById('addScriptCategory').value;
    const langCol = document.getElementById('addScriptLanguageCol');
    const langSelect = document.getElementById('addScriptLanguage');
    if (cat === 'data_process') {
        langCol.style.display = 'none';
        langSelect.value = 'Python';
        langSelect.required = false;
    } else {
        langCol.style.display = '';
        langSelect.required = true;
    }
}

function setupAddScriptValidation() {
    const idInput = document.querySelector('#addScriptForm [name="id"]');
    const nameInput = document.querySelector('#addScriptForm [name="name"]');
    if (!idInput || !nameInput) return;

    const checkDuplicate = (input, fieldName) => {
        const value = input.value.trim();
        if (!value) return;
        const exists = state.scripts.some(s =>
            (fieldName === 'id' && s.id === value) ||
            (fieldName === 'name' && s.name === value)
        );
        // 移除旧反馈
        input.classList.remove('is-invalid', 'is-valid');
        const oldFb = input.parentElement.querySelector('.dup-feedback');
        if (oldFb) oldFb.remove();

        if (exists) {
            input.classList.add('is-invalid');
            const fb = document.createElement('div');
            fb.className = 'invalid-feedback dup-feedback';
            fb.textContent = fieldName === 'id' ? '此 ID 已存在' : '此名称已存在';
            input.parentElement.appendChild(fb);
        } else {
            input.classList.add('is-valid');
        }
    };

    idInput.addEventListener('input', () => checkDuplicate(idInput, 'id'));
    nameInput.addEventListener('input', () => checkDuplicate(nameInput, 'name'));
}

function detectDataFormat(fileInput) {
    const file = fileInput.files[0];
    if (!file) return;
    const select = document.getElementById('dataFormatSelect');
    // 只对 CSV/TXT 自动检测
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        const text = e.target.result;
        const firstLine = text.split('\n')[0];
        const colCount = (firstLine.match(/,/g) || []).length + 1;
        // 列数 > 5 判定为宽数据，否则为长数据
        const detected = colCount > 5 ? 'wide' : 'long';
        select.value = detected;
        const label = detected === 'wide' ? '宽数据' : '长数据';
        // 刷新 select 的选中显示
        select.dispatchEvent(new Event('change'));
    };
    reader.readAsText(file);
}

async function submitAddScript() {
    const form = document.getElementById('addScriptForm');
    const formData = new FormData(form);

    const id = formData.get('id');
    const name = formData.get('name');
    const scriptFile = formData.get('script_file');

    if (!id || !name) {
        showToast('请填写脚本 ID 和名称', 'warning');
        return;
    }
    if (!scriptFile || !scriptFile.name) {
        showToast('请上传脚本文件', 'warning');
        return;
    }

    try {
        const res = await fetch('/api/scripts/add', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            showToast('脚本添加成功', 'success');
            state.addScriptModal.hide();
            loadScripts(state.currentFilter);
        } else {
            showToast(data.error || '添加失败', 'danger');
        }
    } catch (err) {
        showToast('添加失败: ' + err.message, 'danger');
    }
}

async function deleteScriptFromWorkspace() {
    if (!state.currentScriptId) return;

    if (!confirm('确定要删除此脚本吗？此操作不可撤销。')) return;

    try {
        const delRes = await fetch(`/api/scripts/${state.currentScriptId}`, { method: 'DELETE' });
        const data = await delRes.json();
        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast('脚本已删除', 'success');
            state.workspaceModal.hide();
            loadScripts(state.currentFilter);
        }
    } catch (err) {
        showToast('删除失败: ' + err.message, 'danger');
    }
}

// ============================================================
// 6b. 手动修改脚本
// ============================================================

function openManualEdit() {
    if (!state.currentScriptId || !state.currentScriptContent) {
        showToast('请先选择一个脚本', 'warning');
        return;
    }
    document.getElementById('manualEditScriptName').textContent =
        state.currentScriptId;
    document.getElementById('manualEditContent').value =
        state.currentScriptContent;
    // 预填新脚本 ID 和名称
    const newIdInput = document.getElementById('manualEditNewId');
    const newNameInput = document.getElementById('manualEditNewName');
    if (newIdInput) newIdInput.value = state.currentScriptId + '_v2';
    if (newNameInput) newNameInput.value = '';
    state.manualEditModal.show();
}

async function saveManualEdit() {
    const newContent = document.getElementById('manualEditContent').value;
    if (!newContent.trim()) {
        showToast('脚本内容不能为空', 'warning');
        return;
    }

    const newId = document.getElementById('manualEditNewId').value.trim();
    const newName = document.getElementById('manualEditNewName').value.trim();
    if (!newId) {
        showToast('请输入新脚本 ID', 'warning');
        return;
    }
    if (!newName) {
        showToast('请输入新脚本名称', 'warning');
        return;
    }

    try {
        const res = await fetch(`/api/scripts/${state.currentScriptId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: newContent,
                source: 'manual',
                new_id: newId,
                new_name: newName
            })
        });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast(`已保存为新脚本: ${newName}`, 'success');
            state.currentScriptContent = newContent;
            state.manualEditModal.hide();
            setTimeout(() => loadScripts(state.currentFilter), 500);
        }
    } catch (err) {
        showToast('保存失败: ' + err.message, 'danger');
    }
}

// ============================================================
// 7. 快捷运行（兼容旧入口）
// ============================================================

function quickRun(scriptId) {
    openScriptWorkspace(scriptId);
}

function runScriptFromDetail() {
    openScriptWorkspace(state.currentScriptId);
}

// ============================================================
// 8. 建议模块
// ============================================================

async function showSuggestionsModal() {
    // 填充脚本选择下拉
    const select = document.getElementById('suggestScriptSelect');
    select.innerHTML = '<option value="">-- 通用建议（不指定脚本） --</option>' +
        state.scripts.map(s => `<option value="${s.id}">${escapeHtml(s.name)} (${s.language})</option>`).join('');

    // 加载历史建议
    await loadSuggestions();

    // 初始化 AI 推荐 Tab
    setupAIRecommendTab();
    document.getElementById('aiRecPreview').style.display = 'none';
    document.getElementById('aiRecResult').style.display = 'none';
    state._aiRecFile = null;
    state._aiRecModified = null;
    state._aiRecSelectedColumns = [];
    state._aiRecColumnRenames = {};
    state._aiRecColumnValues = {};
    state._aiRecColumnValueFilters = {};
    state._aiRecPreviewRows = [];
    state._aiRecPreviewColumns = [];
    document.getElementById('aiRecSubmitBtn').disabled = true;

    state.suggestionsModal.show();
}

async function loadSuggestionCount() {
    try {
        const res = await fetch('/api/suggestions');
        const data = await res.json();
        document.getElementById('countSuggestions').textContent = data.total || 0;
    } catch (err) { /* ignore */ }
}

async function loadSuggestions() {
    try {
        const res = await fetch('/api/suggestions');
        const data = await res.json();
        renderSuggestions(data.suggestions || []);
    } catch (err) {
        document.getElementById('suggestionsList').innerHTML =
            '<small class="text-muted">加载失败</small>';
    }
}

function renderSuggestions(suggestions) {
    const container = document.getElementById('suggestionsList');
    if (suggestions.length === 0) {
        container.innerHTML = '<small class="text-muted">暂无建议记录</small>';
        return;
    }
    container.innerHTML = suggestions.map(s => {
        const time = new Date(s.created_at).toLocaleString('zh-CN');
        const scriptLabel = s.script_name
            ? `<div class="suggestion-script"><i class="bi bi-file-code"></i> ${escapeHtml(s.script_name)}</div>`
            : '';
        return `
        <div class="suggestion-item">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    ${scriptLabel}
                    <div class="mt-1">${escapeHtml(s.content)}</div>
                    <div class="suggestion-meta mt-1">${time}</div>
                </div>
                <button class="btn btn-sm text-danger p-0 ms-2" title="删除"
                        onclick="deleteSuggestion('${s.id}')">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        </div>`;
    }).join('');
}

async function submitSuggestion() {
    const scriptSelect = document.getElementById('suggestScriptSelect');
    const content = document.getElementById('suggestContent').value.trim();

    if (!content) {
        showToast('请输入建议内容', 'warning');
        return;
    }

    const scriptId = scriptSelect.value;
    const scriptOption = scriptSelect.selectedOptions[0];
    const scriptName = scriptId ? scriptOption.text.replace(/\s*\(.*\)\s*$/, '') : '';

    try {
        const res = await fetch('/api/suggestions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                script_id: scriptId,
                script_name: scriptName,
                content: content
            })
        });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast('建议已提交', 'success');
            document.getElementById('suggestContent').value = '';
            await loadSuggestions();
            await loadSuggestionCount();
        }
    } catch (err) {
        showToast('提交失败: ' + err.message, 'danger');
    }
}

async function submitLogSuggestion() {
    const meta = state.workspace.taskMeta || {};
    const scriptId = meta.script_id || state.workspace.scriptId || '';
    const scriptName = meta.script_name || '';
    const logEl = document.getElementById('workspaceLogContent');
    const logText = logEl ? logEl.textContent : '';

    let content = '【执行报错】\n';
    if (meta.result && meta.result.error) {
        content += '错误信息: ' + meta.result.error + '\n\n';
    }
    content += '脚本: ' + (scriptName || scriptId) + ' (' + scriptId + ')\n\n';
    content += '--- 执行日志 ---\n' + (logText || '(空)');

    await showSuggestionsModal();
    const select = document.getElementById('suggestScriptSelect');
    if (scriptId) {
        for (const opt of select.options) {
            if (opt.value === scriptId) {
                opt.selected = true;
                break;
            }
        }
    }
    document.getElementById('suggestContent').value = content;
}

async function deleteSuggestion(id) {
    try {
        await fetch(`/api/suggestions/${id}`, { method: 'DELETE' });
        showToast('建议已删除', 'success');
        await loadSuggestions();
        await loadSuggestionCount();
    } catch (err) {
        showToast('删除失败: ' + err.message, 'danger');
    }
}

// ---- 脚本推荐 ----

// 初始化推荐 Tab 的子标签页及 AI 推荐区域
let _aiRecUploadBound = false;

function setupAIRecommendTab() {
    // 填充脚本选择下拉
    const select = document.getElementById('aiRecScriptSelect');
    if (select && state.scripts.length > 0) {
        select.innerHTML = '<option value="">-- 请选择脚本 --</option>' +
            state.scripts.filter(s => s.category !== 'data_process').map(s =>
                `<option value="${s.id}">${escapeHtml(s.name)} (${s.language})</option>`
            ).join('');
    }
    // 绑定上传事件（只绑定一次）
    if (_aiRecUploadBound) return;
    _aiRecUploadBound = true;

    const dropZone = document.getElementById('aiRecDropZone');
    const fileInput = document.getElementById('aiRecFileInput');
    const selectBtn = document.getElementById('aiRecSelectFileBtn');

    if (!dropZone) return;

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleAIRecommendFile(e.dataTransfer.files[0]);
        }
    });
    dropZone.addEventListener('click', (e) => {
        if (e.target.closest && e.target.closest('button')) return;
        if (fileInput) fileInput.click();
    });
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handleAIRecommendFile(e.target.files[0]);
        });
    }
    if (selectBtn) {
        selectBtn.addEventListener('click', () => {
            if (fileInput) fileInput.click();
        });
    }
}

async function handleAIRecommendFile(file) {
    const allowedExts = ['csv', 'xlsx', 'xls', 'txt'];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        showToast(`不支持的文件格式: .${ext}`, 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'danger'); return; }

        state._aiRecFile = data.filename;
        state._aiRecSelectedColumns = [...(data.columns || [])];
        state._aiRecColumnRenames = {};
        state._aiRecColumnValueFilters = {};
        // 使用新格式：读取前50行作为预览
        const previewRes = await fetch('/api/data/' + encodeURIComponent(data.filename) + '/rows?page=0&page_size=50');
        const previewData = await previewRes.json();
        state._aiRecPreviewRows = previewData.rows || [];
        state._aiRecPreviewColumns = previewData.columns || data.columns || [];
        state._aiRecPreview = { columns: state._aiRecPreviewColumns, rows: state._aiRecPreviewRows, shape: [state._aiRecPreviewRows.length, state._aiRecPreviewColumns.length] };

        // 显示预览（带列选择、重命名和下拉筛选）
        document.getElementById('aiRecPreview').style.display = 'block';
        const thead = document.querySelector('#aiRecPreviewTable thead');
        const tbody = document.querySelector('#aiRecPreviewTable tbody');
        const preview = state._aiRecPreview;
        if (preview && preview.columns && !preview.error) {
            thead.innerHTML = '<tr>' + preview.columns.map((c, i) =>
                `<th style="user-select:none;">
                    <input type="checkbox" checked style="cursor:pointer; margin-right:4px;" data-col="${escapeHtml(String(c))}"
                           onclick="event.preventDefault(); this.checked=!this.checked; toggleAIRecColumnCb(this)">
                    <span class="col-name-text" data-original="${escapeHtml(String(c))}">${escapeHtml(String(c))}</span>
                </th>`).join('') + '</tr>';
            tbody.innerHTML = preview.rows.map(row =>
                '<tr>' + row.map(cell =>
                    `<td>${escapeHtml(cell == null ? '' : String(cell))}</td>`).join('') + '</tr>'
            ).join('');
            document.getElementById('aiRecPreviewInfo').innerHTML =
                `显示前 ${preview.shape[0]} 行，共 ${preview.columns.length} 列
                 <span class="ms-2">
                     <span class="dropdown d-inline-block">
                         <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button"
                                 data-bs-toggle="dropdown" data-bs-auto-close="outside" aria-expanded="false" title="列筛选">
                             <i class="bi bi-funnel"></i>
                             <span id="aiRecSelectedColCount">${preview.columns.length}/${preview.columns.length}</span>
                         </button>
                         <div class="dropdown-menu dropdown-menu-end p-2" style="max-height:400px; overflow-y:auto; min-width:280px;" id="aiRecFilterDropdown" onclick="event.stopPropagation()"
                             <h6 class="dropdown-header px-1">批量操作</h6>
                             <div class="d-flex gap-1 px-1 mb-2">
                                 <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="selectAllAIRecColumns()">全选</button>
                                 <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="deselectAllAIRecColumns()">取消</button>
                                 <button class="btn btn-sm btn-outline-secondary flex-grow-1" onclick="invertAIRecColumns()">反选</button>
                             </div>
                             <div class="dropdown-divider"></div>
                             <h6 class="dropdown-header px-1">按值筛选列 <small class="text-muted" id="aiRecDropdownColCount"></small></h6>
                             <div id="aiRecDropdownCols"></div>
                         </div>
                     </span>
                 </span>`;
        }
        // 拉取完整数据的唯一值用于筛选
        fetchColumnValues('aiRec', state._aiRecFile);
        updateAIRecommendSubmitBtn();
        showToast('文件上传成功', 'success');
    } catch (err) {
        showToast('上传失败: ' + err.message, 'danger');
    }
}

function selectAllAIRecColumns() {
    syncAIRecAllCheckboxes(true);
}

function deselectAllAIRecColumns() {
    syncAIRecAllCheckboxes(false);
}

function invertAIRecColumns() {
    const cbs = document.querySelectorAll('#aiRecPreviewTable thead input[type="checkbox"]');
    const newSelected = [];
    cbs.forEach(cb => {
        cb.checked = !cb.checked;
        if (cb.checked) newSelected.push(cb.dataset.col);
    });
    state._aiRecSelectedColumns = newSelected;
    document.querySelectorAll('#aiRecDropdownCols input[type="checkbox"]').forEach(dcb => {
        dcb.checked = newSelected.includes(dcb.dataset.col);
    });
    updateAIRecColCountBadge();
}

function syncAIRecAllCheckboxes(checked) {
    const cbs = document.querySelectorAll('#aiRecPreviewTable thead input[type="checkbox"]');
    const allCols = [];
    cbs.forEach(cb => { cb.checked = checked; allCols.push(cb.dataset.col); });
    state._aiRecSelectedColumns = checked ? allCols : [];
    document.querySelectorAll('#aiRecDropdownCols input[type="checkbox"]').forEach(dcb => {
        dcb.checked = checked;
    });
    updateAIRecColCountBadge();
}

function toggleAIRecColumnCb(cb) {
    const colName = cb.dataset.col;
    if (cb.checked) {
        if (!state._aiRecSelectedColumns.includes(colName)) {
            state._aiRecSelectedColumns.push(colName);
        }
    } else {
        state._aiRecSelectedColumns = state._aiRecSelectedColumns.filter(c => c !== colName);
    }
    updateAIRecColCountBadge();
}

function updateAIRecColCountBadge() {
    const total = document.querySelectorAll('#aiRecPreviewTable thead input[type="checkbox"]').length || 1;
    const sel = state._aiRecSelectedColumns.length;
    const badge = document.getElementById('aiRecSelectedColCount');
    if (badge) badge.textContent = `${sel}/${total}`;
    const dropdownTitle = document.getElementById('aiRecDropdownColCount');
    if (dropdownTitle) dropdownTitle.textContent = `(${sel}/${total})`;
}

function updateAIRecommendSubmitBtn() {
    const btn = document.getElementById('aiRecSubmitBtn');
    const scriptId = document.getElementById('aiRecScriptSelect')?.value || '';
    btn.disabled = !(scriptId && state._aiRecFile);
}

// ============================================================
// AI Recommend 列值筛选（保留原有下拉筛选逻辑）
// ============================================================

async function fetchColumnValues(scope, filename) {
    try {
        const res = await fetch('/api/column-values/' + encodeURIComponent(filename));
        const data = await res.json();
        if (data.error) return;
        if (scope === 'aiRec') {
            state._aiRecColumnValues = data.column_values || {};
            state._aiRecTotalRows = data.total_rows || 0;
            state._aiRecColumnValueFilters = {};
        }
        const columns = state._aiRecPreviewColumns;
        renderDropdownCols(scope, columns || data.columns);
    } catch (err) { /* 静默失败 */ }
}

function renderDropdownCols(scope, columns) {
    const containerId = scope === 'aiRec' ? 'aiRecDropdownCols' : 'workspaceDropdownCols';
    const container = document.getElementById(containerId);
    if (!container) return;
    const colValues = scope === 'aiRec' ? (state._aiRecColumnValues || {}) : {};
    const colValFilters = scope === 'aiRec' ? (state._aiRecColumnValueFilters || {}) : {};
    const store = scope === 'aiRec' ? state : null;
    if (!store) return;

    container.innerHTML = columns.map(c => {
        const displayName = state._aiRecColumnRenames[c] || c;
        const colChecked = state._aiRecSelectedColumns.includes(c) || state._aiRecSelectedColumns.includes(displayName) ? 'checked' : '';
        const vinfo = colValues[c];
        const vals = vinfo ? vinfo.values : [];
        const totalUnique = vinfo ? vinfo.total_unique : 0;
        const truncated = vinfo ? vinfo.truncated : false;
        const selectedVals = colValFilters[c];

        let valsHtml = '';
        if (vals && vals.length > 0) {
            const showVals = vals.slice(0, 50);
            valsHtml = '<div class="ms-3 mt-1" style="max-height:120px; overflow-y:auto; font-size:0.75rem;">' +
                showVals.map(v => {
                    const vStr = v == null ? '(空)' : String(v);
                    const vEsc = escapeHtml(vStr);
                    const vChecked = !selectedVals || (selectedVals.has && selectedVals.has(vStr)) ? 'checked' : '';
                    return '<label class="d-flex align-items-center gap-1 mb-1" style="cursor:pointer;">' +
                        '<input type="checkbox" ' + vChecked + ' data-scope="' + scope + '" data-col="' + escapeHtml(c) + '" data-val="' + vEsc + '" onchange="toggleColumnValue(this)">' +
                        '<span>' + (vStr.length > 28 ? vStr.slice(0, 28) + '...' : vStr) + '</span></label>';
                }).join('');
            if (truncated || vals.length > 50) {
                valsHtml += '<small class="text-muted">显示50/' + totalUnique + '个值' + (truncated ? ' (已截断)' : '') + '</small>';
            }
            valsHtml += '</div>';
        }

        return '<div class="dropdown-item-text py-1">' +
            '<div class="d-flex justify-content-between align-items-center">' +
            '<label class="d-flex align-items-center gap-1 mb-0" style="cursor:pointer;">' +
            '<input type="checkbox" ' + colChecked + ' data-scope="' + scope + '" data-col="' + escapeHtml(c) + '" onchange="toggleColumnFromDropdown(this)">' +
            '<span class="fw-bold" style="font-size:0.8rem;">' + escapeHtml(displayName) + '</span></label>' +
            '<small class="text-muted">' + (selectedVals && selectedVals.size ? selectedVals.size + '/' + vals.length : '') + '</small></div>' +
            valsHtml + '</div>';
    }).join('');

    if (scope === 'aiRec') updateAIRecColCountBadge();
}

function toggleColumnValue(cb) {
    const scope = cb.dataset.scope;
    const colName = cb.dataset.col;
    const val = cb.dataset.val;
    const filters = state._aiRecColumnValueFilters;
    if (!filters[colName]) {
        const colVals = (state._aiRecColumnValues || {})[colName];
        if (colVals && colVals.values) {
            filters[colName] = new Set(colVals.values.map(v => String(v == null ? '(空)' : v)));
        } else {
            filters[colName] = new Set();
        }
    }
    const filterSet = filters[colName];
    if (cb.checked) { filterSet.add(val); }
    else { filterSet.delete(val); }
    const allVals = (state._aiRecColumnValues || {})[colName];
    if (allVals && allVals.values && filterSet.size >= allVals.values.length) {
        delete filters[colName];
    }
    applyColumnValueFilters(scope);
    renderDropdownCols(scope, state._aiRecPreviewColumns);
}

function applyColumnValueFilters(scope) {
    if (scope !== 'aiRec') return;
    const rows = state._aiRecPreviewRows;
    const columns = state._aiRecPreviewColumns;
    const valFilters = state._aiRecColumnValueFilters || {};
    if (!rows || !columns) return;
    const tbody = document.querySelector('#aiRecPreviewTable tbody');
    if (!tbody) return;
    const activeCols = Object.keys(valFilters).filter(k => valFilters[k] && valFilters[k].size > 0);
    if (activeCols.length === 0) {
        tbody.innerHTML = rows.map(row =>
            '<tr>' + row.map(cell =>
                '<td>' + escapeHtml(cell == null ? '' : String(cell)) + '</td>').join('') + '</tr>'
        ).join('');
        return;
    }
    const filteredRows = rows.filter(row => {
        return activeCols.every(colName => {
            const colIdx = columns.indexOf(colName);
            if (colIdx === -1) return true;
            const cellVal = String(row[colIdx] == null ? '(空)' : row[colIdx]);
            const filterSet = valFilters[colName];
            return filterSet && filterSet.has(cellVal);
        });
    });
    tbody.innerHTML = filteredRows.length > 0
        ? filteredRows.map(row =>
            '<tr>' + row.map(cell =>
                '<td>' + escapeHtml(cell == null ? '' : String(cell)) + '</td>').join('') + '</tr>'
        ).join('')
        : '<tr><td colspan="' + columns.length + '" class="text-center text-muted">无匹配数据</td></tr>';
}

function toggleColumnFromDropdown(cb) {
    const scope = cb.dataset.scope;
    const colName = cb.dataset.col;
    if (cb.checked) {
        if (!state._aiRecSelectedColumns.includes(colName)) {
            state._aiRecSelectedColumns.push(colName);
        }
    } else {
        state._aiRecSelectedColumns = state._aiRecSelectedColumns.filter(c => c !== colName);
    }
    const thCb = document.querySelector('#aiRecPreviewTable thead input[data-col="' + escapeHtml(colName) + '"]');
    if (thCb) thCb.checked = cb.checked;
    updateAIRecColCountBadge();
}

// 监听脚本选择变化
document.addEventListener('DOMContentLoaded', () => {
    const scriptSelect = document.getElementById('aiRecScriptSelect');
    if (scriptSelect) {
        scriptSelect.addEventListener('change', updateAIRecommendSubmitBtn);
    }
});

async function submitAIRecommend() {
    const scriptId = document.getElementById('aiRecScriptSelect')?.value || '';
    if (!scriptId) { showToast('请选择脚本', 'warning'); return; }
    if (!state._aiRecFile) { showToast('请上传数据文件', 'warning'); return; }

    const btn = document.getElementById('aiRecSubmitBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> AI 分析中...';

    try {
        const formData = new FormData();
        formData.append('script_id', scriptId);
        formData.append('use_uploaded', state._aiRecFile);
        formData.append('model', state.selectedAIModel);
        if (state._aiRecSelectedColumns && state._aiRecSelectedColumns.length > 0) {
            formData.append('columns', JSON.stringify(state._aiRecSelectedColumns));
        }
        if (state._aiRecColumnRenames && Object.keys(state._aiRecColumnRenames).length > 0) {
            formData.append('column_renames', JSON.stringify(state._aiRecColumnRenames));
        }

        const res = await fetch('/api/ai/recommend', { method: 'POST', body: formData });
        const data = await res.json();

        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-robot"></i> AI 分析并修改脚本';

        if (data.error) {
            showToast(data.error, 'danger');
            return;
        }

        state._aiRecModified = data.modified_script;
        state._aiRecDiffHtml = data.diff_html;
        state._aiRecScriptId = scriptId;

        document.getElementById('aiRecResult').style.display = 'block';
        document.getElementById('aiRecExplanation').innerHTML =
            '<i class="bi bi-check-circle-fill text-success me-1"></i>' +
            escapeHtml(data.explanation || 'AI 已根据数据列名完成脚本适配。');

    } catch (err) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-robot"></i> AI 分析并修改脚本';
        showToast('AI 推荐失败: ' + err.message, 'danger');
    }
}

function showAIRecommendDiff() {
    if (!state._aiRecModified || !state._aiRecScriptId) return;

    const diffContent = document.getElementById('diffContent');
    // 获取原始脚本内容
    const originalScript = state.scripts.find(s => s.id === state._aiRecScriptId);
    // simple line-by-line diff
    fetch(`/api/scripts/${state._aiRecScriptId}`).then(r => r.json()).then(scriptData => {
        const orig = scriptData.content || '';
        const mod = state._aiRecModified || '';
        const origLines = orig.split('\n');
        const modLines = mod.split('\n');
        const maxLen = Math.max(origLines.length, modLines.length);
        let html = '<table class="table table-sm table-bordered diff-table"><tbody>';
        for (let i = 0; i < maxLen; i++) {
            const ol = i < origLines.length ? origLines[i] : '';
            const ml = i < modLines.length ? modLines[i] : '';
            const isDiff = ol !== ml;
            html += '<tr>';
            html += `<td class="diff-lineno" style="width:40px;text-align:right;color:#999;">${i + 1}</td>`;
            html += `<td class="${isDiff ? 'diff_sub' : ''}" style="width:48%;font-family:monospace;font-size:0.8rem;white-space:pre-wrap;">${escapeHtml(ol)}</td>`;
            html += `<td class="diff-lineno" style="width:40px;text-align:right;color:#999;">${i + 1}</td>`;
            html += `<td class="${isDiff ? 'diff_add' : ''}" style="width:48%;font-family:monospace;font-size:0.8rem;white-space:pre-wrap;">${escapeHtml(ml)}</td>`;
            html += '</tr>';
        }
        html += '</tbody></table>';
        diffContent.innerHTML = html;
        state.diffModal.show();
    });
}

async function applyAIRecommend() {
    if (!state._aiRecModified || !state._aiRecScriptId) {
        showToast('没有可应用的修改', 'warning');
        return;
    }

    const newId = prompt('请输入新脚本 ID:', state._aiRecScriptId + '_ai');
    if (!newId) return;
    const newName = prompt('请输入新脚本名称:', '');
    if (!newName) return;

    try {
        const res = await fetch(`/api/scripts/${state._aiRecScriptId}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: state._aiRecModified,
                source: 'ai',
                new_id: newId.trim(),
                new_name: newName.trim()
            })
        });
        const data = await res.json();
        if (data.error) {
            showToast(data.error, 'danger');
        } else {
            showToast(`已保存为新脚本: ${newName}`, 'success');
            state._aiRecModified = null;
            document.getElementById('aiRecResult').style.display = 'none';
            state.diffModal.hide();
            setTimeout(() => loadScripts(state.currentFilter), 500);
        }
    } catch (err) {
        showToast('保存失败: ' + err.message, 'danger');
    }
}


// ============================================================
// 面板切换
// ============================================================

function toggleAIPanel() {
    const panel = document.getElementById('aiPanel');
    const icon = document.getElementById('aiToggleIcon');

    if (panel.classList.contains('collapsed')) {
        panel.classList.remove('collapsed');
        icon.className = 'bi bi-chevron-right';
    } else {
        panel.classList.add('collapsed');
        icon.className = 'bi bi-chevron-left';
    }
}

// ============================================================
// AI 模型切换
// ============================================================

async function loadAIModels() {
    try {
        // 图片分析 → 只加载小米（Mimo），隐藏 DeepSeek
        const analysisRes = await fetch('/api/ai/models?scope=image-analysis');
        const analysisData = await analysisRes.json();
        const analysisSel = document.getElementById('aiAnalysisModelSelect');
        if (analysisSel) {
            analysisSel.innerHTML = analysisData.models.map(m =>
                `<option value="${m.id}" ${m.default ? 'selected' : ''}>${m.label}${m.available ? '' : ' (未配置)'}</option>`
            ).join('');
        }

        // 脚本修改/推荐等功能 → 只加载 DeepSeek，隐藏小米
        const modifyRes = await fetch('/api/ai/models?scope=script-modify');
        const modifyData = await modifyRes.json();
        state.availableModels = modifyData.models || [];

        const selects = ['aiModelSelect', 'aiRecModelSelect'];
        selects.forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            const currentVal = sel.value;
            sel.innerHTML = modifyData.models.map(m =>
                `<option value="${m.id}" ${m.default ? 'selected' : ''}>${m.label}${m.available ? '' : ' (未配置)'}</option>`
            ).join('');
            // 恢复之前的选中值
            if (currentVal && modifyData.models.some(m => m.id === currentVal)) {
                sel.value = currentVal;
            }
        });
        // 同步 state
        const primarySel = document.getElementById('aiModelSelect');
        if (primarySel) state.selectedAIModel = primarySel.value;
    } catch (err) {
        console.warn('加载 AI 模型列表失败', err);
    }
}

function setAIModel(modelId) {
    state.selectedAIModel = modelId;
    // 同步非图片分析的模型下拉框
    ['aiModelSelect', 'aiRecModelSelect'].forEach(id => {
        const sel = document.getElementById(id);
        if (sel && sel.value !== modelId) sel.value = modelId;
    });
}

// ============================================================
// 工具函数
// ============================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const colors = {
        success: '#16a34a',
        danger: '#dc2626',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        background: ${colors[type] || colors.info};
        color: white;
        padding: 0.75rem 1.25rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        animation: fadeIn 0.3s ease;
        max-width: 400px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setupKeyboard() {
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            const aiInput = document.getElementById('aiInput');
            if (document.activeElement === aiInput) {
                sendAIMessage();
            }
        }
        if (e.key === 'Escape') {
            const overlay = document.getElementById('imageOverlay');
            if (overlay && overlay.style.display !== 'none') {
                closeImageOverlay();
                return;
            }
            if (document.getElementById('aiPanel').classList.contains('mobile-open')) {
                document.getElementById('aiPanel').classList.remove('mobile-open');
            }
        }
    });
}


// ============================================================
// 全局颜色库
// ============================================================

async function loadColorLibrary() {
    try {
        const res = await fetch('/api/colors');
        const data = await res.json();
        renderColorLibrary(data);
    } catch (err) {
        document.getElementById('colorLibrary').innerHTML =
            '<small class="text-danger">加载失败</small>';
    }
}

function renderColorLibrary(data) {
    const container = document.getElementById('colorLibrary');
    const activeSeries = data.active_series || 'npg';
    const series = data.series || {};
    const customs = data.custom || [];

    let html = '';

    // 内置系列
    for (const [key, s] of Object.entries(series)) {
        const isActive = key === activeSeries;
        const swatches = (s.colors || []).map(c =>
            `<span class="color-swatch ${isActive ? 'active' : ''}"
                  style="background:${c};" title="${c}"></span>`
        ).join('');

        html += `
            <div class="color-series ${isActive ? 'color-series-active' : ''}"
                 onclick="setActiveColorSeries('${escapeHtml(key)}')"
                 style="cursor:pointer; padding:4px 6px; border-radius:6px; margin-bottom:4px; ${isActive ? 'background:rgba(99,102,241,0.08); border:1px solid var(--primary);' : 'border:1px solid transparent;'}">
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <span style="font-size:0.7rem; font-weight:600; ${isActive ? 'color:var(--primary);' : ''}">
                        ${isActive ? '● ' : ''}${escapeHtml(s.name)}
                    </span>
                </div>
                <div style="display:flex; gap:2px; margin-top:2px;">${swatches}</div>
            </div>`;
    }

    // 自定义系列
    if (customs.length > 0) {
        html += '<div class="dropdown-divider my-1"></div>';
        html += '<small class="text-muted" style="font-size:0.65rem;">自定义配色</small>';
        for (const c of customs) {
            const isActive = activeSeries === 'custom' && customs.indexOf(c) === customs.length - 1;
            const swatches = (c.colors || []).map(cl =>
                `<span class="color-swatch ${isActive ? 'active' : ''}"
                      style="background:${cl};" title="${cl}"></span>`
            ).join('');
            html += `
                <div class="color-series ${isActive ? 'color-series-active' : ''}"
                     style="cursor:pointer; padding:4px 6px; border-radius:6px; margin-bottom:4px; ${isActive ? 'background:rgba(99,102,241,0.08); border:1px solid var(--primary);' : 'border:1px solid transparent;'}">
                    <div style="display:flex; align-items:center; justify-content:space-between;">
                        <span style="font-size:0.7rem; font-weight:600; ${isActive ? 'color:var(--primary);' : ''}"
                              onclick="event.stopPropagation(); setActiveColorSeries('custom')">
                            ${isActive ? '● ' : ''}${escapeHtml(c.name)}
                        </span>
                        <button class="btn btn-sm p-0" style="font-size:0.6rem; color:#dc2626;"
                                onclick="event.stopPropagation(); deleteCustomColor('${escapeHtml(c.id)}')"
                                title="删除"><i class="bi bi-x-lg"></i></button>
                    </div>
                    <div style="display:flex; gap:2px; margin-top:2px;">${swatches}</div>
                </div>`;
        }
    }

    // 添加自定义颜色按钮
    html += `
        <button class="btn btn-sm btn-outline-secondary w-100 mt-2" style="font-size:0.7rem;"
                onclick="showAddCustomColor()">
            <i class="bi bi-plus-lg"></i> 自定义配色
        </button>`;

    container.innerHTML = html;
}

async function setActiveColorSeries(seriesId) {
    try {
        const res = await fetch('/api/colors/active', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ series_id: seriesId })
        });
        const data = await res.json();
        if (data.error) {
            showToast(data.error, 'warning');
            return;
        }
        loadColorLibrary();
        showToast('颜色系列已切换，下次运行脚本生效', 'success');
    } catch (err) {
        showToast('切换失败: ' + err.message, 'danger');
    }
}

function showAddCustomColor() {
    const name = prompt('请输入自定义配色名称:', '我的配色');
    if (!name) return;
    const hexInput = prompt('请输入颜色列表（用逗号分隔，如 #E64B35,#4DBBD5,#00A087）:',
        '#E64B35,#4DBBD5,#00A087,#3C5488,#F39B7F,#8491B4,#91D1C2,#DC0000');
    if (!hexInput) return;
    const colors = hexInput.split(',').map(s => s.trim()).filter(s => /^#[0-9a-fA-F]{6}$/.test(s));
    if (colors.length < 2) {
        showToast('至少需要2个有效的十六进制颜色 (#RRGGBB)', 'warning');
        return;
    }

    fetch('/api/colors/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, colors: colors })
    }).then(r => r.json()).then(data => {
        if (data.error) { showToast(data.error, 'danger'); return; }
        loadColorLibrary();
        showToast('自定义配色已保存', 'success');
    }).catch(err => showToast('保存失败: ' + err.message, 'danger'));
}

async function deleteCustomColor(customId) {
    if (!confirm('确定要删除这个自定义配色吗？')) return;
    try {
        const res = await fetch(`/api/colors/custom/${customId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.error) { showToast(data.error, 'danger'); return; }
        loadColorLibrary();
        showToast('已删除', 'success');
    } catch (err) {
        showToast('删除失败: ' + err.message, 'danger');
    }
}

