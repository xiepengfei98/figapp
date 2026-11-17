/**
 * 多维度筛选构建器
 * 依赖：main.js 中的 state, escapeHtml(), showToast()
 *        preview-table.js 中的 renderPreviewTable()
 */

let _filterIdCounter = 0;
let _columnStats = null;       // 缓存列统计信息
let _columnValuesFetching = {}; // 防重复请求

// ============================================================
// 筛选面板显示/隐藏
// ============================================================

function toggleFilterPanel() {
    const panel = document.getElementById('filterBuilderPanel');
    if (!panel) return;
    const show = panel.style.display === 'none';
    panel.style.display = show ? 'block' : 'none';
    if (show) {
        ensureColumnStats().then(() => renderPendingFilters());
        renderAppliedChips();
    }
}

// ============================================================
// 列统计信息（驱动运算符选择）
// ============================================================

async function ensureColumnStats() {
    if (_columnStats) return _columnStats;
    const fname = state.workspace.uploadedFile;
    if (!fname) return null;
    try {
        const res = await fetch(`/api/data/${encodeURIComponent(fname)}/stats`);
        const data = await res.json();
        if (data.error) return null;
        _columnStats = data.columns || {};
        return _columnStats;
    } catch (err) {
        return null;
    }
}

function isNumericCol(col) {
    if (!_columnStats || !_columnStats[col]) return false;
    const d = _columnStats[col];
    return d.dtype && (d.dtype.includes('int') || d.dtype.includes('float'));
}

// ============================================================
// 待应用筛选行
// ============================================================

function addFilterRow(col, op, val) {
    const id = ++_filterIdCounter;
    const row = document.createElement('div');
    row.className = 'filter-row d-flex align-items-center gap-2 mb-2';
    row.id = `filterRow-${id}`;
    row.dataset.filterId = id;

    // 列选择（值用原始列名，显示用重命名后的名称）
    const colSelect = document.createElement('select');
    colSelect.className = 'form-select form-select-sm';
    colSelect.style.width = '150px';
    const renames = state.workspace.columnRenames || {};
    colSelect.innerHTML = '<option value="">-- 选择列 --</option>' +
        state.workspace.selectedColumns.map(c => {
            const label = renames[c] || c;
            return `<option value="${escapeHtml(String(c))}"${c === col ? ' selected' : ''}>${escapeHtml(String(label))}</option>`;
        }).join('');
    colSelect.onchange = function() { onFilterColumnChange(this); };

    // 运算符
    const opSelect = document.createElement('select');
    opSelect.className = 'form-select form-select-sm';
    opSelect.style.width = '130px';
    opSelect.onchange = function() { onFilterOperatorChange(this); };

    // 值输入区
    const valueContainer = document.createElement('div');
    valueContainer.className = 'filter-value-area d-flex gap-1';
    valueContainer.style.flex = '1';

    // 移除按钮
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-sm btn-outline-danger';
    removeBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
    removeBtn.title = '移除此条件';
    removeBtn.onclick = function() { removeFilterRow(id); };

    row.appendChild(colSelect);
    row.appendChild(opSelect);
    row.appendChild(valueContainer);
    row.appendChild(removeBtn);

    document.getElementById('pendingFilters').appendChild(row);

    // 初始化运算符
    if (col) updateOperatorOptions(colSelect);

    // 初始化值输入
    if (op) {
        opSelect.value = op;
        updateValueInput(row, colSelect.value, op, val);
    }

    return id;
}

function removeFilterRow(id) {
    const row = document.getElementById(`filterRow-${id}`);
    if (row) row.remove();
}

function onFilterColumnChange(select) {
    updateOperatorOptions(select);
    const row = select.closest('.filter-row');
    if (row) updateValueInput(row, select.value, null, null);
}

function onFilterOperatorChange(opSelect) {
    const row = opSelect.closest('.filter-row');
    if (!row) return;
    const colSelect = row.querySelector('select:first-child');
    updateValueInput(row, colSelect.value, opSelect.value, null);
}

function updateOperatorOptions(colSelect) {
    const col = colSelect.value;
    const row = colSelect.closest('.filter-row');
    const opSelect = row.querySelector('select:nth-child(2)');

    const numericOps = [
        ['eq', '等于'], ['neq', '不等于'],
        ['gt', '大于'], ['gte', '大于等于'],
        ['lt', '小于'], ['lte', '小于等于'],
        ['between', '介于'], ['in', '在列表中'], ['not_in', '不在列表中'],
        ['is_null', '为空'], ['is_not_null', '非空']
    ];
    const textOps = [
        ['eq', '等于'], ['neq', '不等于'],
        ['contains', '包含'], ['not_contains', '不包含'],
        ['starts_with', '开头是'], ['ends_with', '结尾是'],
        ['in', '在列表中'], ['not_in', '不在列表中'],
        ['is_null', '为空'], ['is_not_null', '非空'],
        ['is_empty', '为空字符串']
    ];

    const ops = isNumericCol(col) ? numericOps : textOps;
    opSelect.innerHTML = ops.map(([v, label]) =>
        `<option value="${v}">${label}</option>`).join('');
}

async function updateValueInput(row, col, op, presetVal) {
    const container = row.querySelector('.filter-value-area');
    if (!container) return;

    container.innerHTML = '';

    if (!col || !op) return;

    if (op === 'is_null' || op === 'is_not_null' || op === 'is_empty') {
        container.innerHTML = '<span class="text-muted small mt-1">N/A</span>';
        return;
    }

    if (op === 'between') {
        const lo = document.createElement('input');
        lo.type = 'number'; lo.className = 'form-control form-control-sm';
        lo.placeholder = '最小值'; lo.style.width = '90px';
        const hi = document.createElement('input');
        hi.type = 'number'; hi.className = 'form-control form-control-sm';
        hi.placeholder = '最大值'; hi.style.width = '90px';
        if (presetVal && Array.isArray(presetVal) && presetVal.length >= 2) {
            lo.value = presetVal[0]; hi.value = presetVal[1];
        }
        container.appendChild(lo);
        container.appendChild(hi);
        return;
    }

    if (op === 'in' || op === 'not_in') {
        container.style.flexWrap = 'wrap';
        container.style.maxHeight = '150px';
        container.style.overflowY = 'auto';
        const vals = await fetchColumnValuesForCol(col);
        if (vals && vals.length > 0) {
            const presetSet = presetVal && Array.isArray(presetVal) ? new Set(presetVal.map(String)) : null;
            vals.forEach(v => {
                const vStr = v == null ? '(空)' : String(v);
                const lbl = document.createElement('label');
                lbl.className = 'd-flex align-items-center gap-1 me-2 mb-1';
                lbl.style.fontSize = '0.75rem';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = escapeHtml(vStr);
                cb.dataset.realVal = v == null ? '' : String(v);
                if (presetSet && presetSet.has(v == null ? '' : String(v))) cb.checked = true;
                lbl.appendChild(cb);
                lbl.appendChild(document.createTextNode(vStr.length > 25 ? vStr.slice(0, 25) + '...' : vStr));
                container.appendChild(lbl);
            });
        } else {
            container.innerHTML = '<span class="text-muted small mt-1">无可选值</span>';
        }
        return;
    }

    // 默认：文本或数字输入
    const input = document.createElement('input');
    input.type = (op === 'gt' || op === 'gte' || op === 'lt' || op === 'lte') ? 'number' : 'text';
    input.className = 'form-control form-control-sm';
    input.placeholder = '输入值...';
    input.style.flex = '1';
    if (presetVal !== null && presetVal !== undefined && !Array.isArray(presetVal)) {
        input.value = presetVal;
    }
    container.appendChild(input);
}

async function fetchColumnValuesForCol(col) {
    if (_columnValuesFetching[col]) return null;
    _columnValuesFetching[col] = true;
    try {
        const fname = state.workspace.filteredFileName || state.workspace.uploadedFile;
        let url = `/api/column-values/${encodeURIComponent(fname)}`;
        if (state.workspace.filteredFileName) {
            url += `?filtered_filename=${encodeURIComponent(state.workspace.filteredFileName)}`;
        }
        const res = await fetch(url);
        const data = await res.json();
        if (data.error) return null;
        const info = data.column_values && data.column_values[col];
        return info ? info.values : [];
    } catch (err) {
        return null;
    } finally {
        delete _columnValuesFetching[col];
    }
}

function renderPendingFilters() {
    const container = document.getElementById('pendingFilters');
    if (!container) return;
    // 保留已存在的筛选行，只清除容器初始内容
    if (container.children.length === 0) {
        // 如果还有已应用的筛选，自动填充到待应用区方便编辑
        const applied = state.workspace.filterStack || [];
        if (applied.length > 0) {
            applied.forEach(f => {
                addFilterRow(f.column, f.operator, f.value);
            });
        }
    }
}

// ============================================================
// 应用筛选
// ============================================================

async function applyFilters() {
    const fname = state.workspace.uploadedFile;
    if (!fname) return;

    // 收集待应用区的筛选条件
    const pendingFilters = collectPendingFilters();

    // 合并已应用的筛选（如果存在）—— 新筛选叠加在旧筛选之上
    const allFilters = [...(state.workspace.filterStack || []), ...pendingFilters];

    const logic = state.workspace.filterLogic || 'and';

    if (allFilters.length === 0) {
        // 无筛选条件，恢复全量数据
        state.workspace.filterStack = [];
        state.workspace.filteredRowCount = null;
        state.workspace.currentPage = 0;
        document.getElementById('pendingFilters').innerHTML = '';
        renderAppliedChips();
        renderPreviewTable();
        return;
    }

    try {
        const res = await fetch(`/api/data/${encodeURIComponent(fname)}/filter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filters: allFilters,
                logic: logic,
                page: 0,
                page_size: state.workspace.pageSize
            })
        });
        const data = await res.json();
        if (data.error) {
            showToast('筛选失败: ' + data.error, 'danger');
            return;
        }

        // 更新状态
        state.workspace.filterStack = allFilters;
        state.workspace.filteredRowCount = data.filtered_count;
        state.workspace.currentPage = 0;

        // 清空待应用区
        document.getElementById('pendingFilters').innerHTML = '';

        // 渲染已应用 chips + 表格
        renderAppliedChips();
        renderTableWithData(data);
        updateFilterSummary(data.filtered_count, data.total_count);

    } catch (err) {
        showToast('筛选请求失败: ' + err.message, 'danger');
    }
}

function collectPendingFilters() {
    const filters = [];
    document.querySelectorAll('#pendingFilters .filter-row').forEach(row => {
        const selects = row.querySelectorAll('select');
        const col = selects[0].value;
        const op = selects[1].value;
        if (!col || !op) return;

        let value = null;
        if (op === 'is_null' || op === 'is_not_null' || op === 'is_empty') {
            value = null;
        } else if (op === 'between') {
            const inputs = row.querySelectorAll('input[type="number"]');
            if (inputs.length >= 2 && inputs[0].value !== '' && inputs[1].value !== '') {
                value = [parseFloat(inputs[0].value), parseFloat(inputs[1].value)];
            } else return;
        } else if (op === 'in' || op === 'not_in') {
            const cbs = row.querySelectorAll('input[type="checkbox"]:checked');
            if (cbs.length === 0) return;
            value = Array.from(cbs).map(cb => cb.dataset.realVal);
        } else {
            const input = row.querySelector('.filter-value-area input[type="text"], .filter-value-area input[type="number"]');
            if (!input || input.value === '') return;
            const colType = isNumericCol(col) || op === 'gt' || op === 'gte' || op === 'lt' || op === 'lte';
            value = colType && !isNaN(parseFloat(input.value)) ? parseFloat(input.value) : input.value;
        }

        filters.push({ column: col, operator: op, value: value });
    });
    return filters;
}

function renderTableWithData(data) {
    const columns = data.columns;
    renderTableHeader(columns);
    const tbody = document.querySelector('#workspacePreviewTable tbody');
    if (!data.rows || data.rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${columns.length}" class="text-center text-muted py-3">
            <i class="bi bi-inbox"></i> 无匹配数据，请调整筛选条件</td></tr>`;
    } else {
        tbody.innerHTML = data.rows.map(row =>
            '<tr>' + row.map(cell =>
                `<td>${escapeHtml(cell == null ? '' : String(cell))}</td>`).join('') + '</tr>'
        ).join('');
    }
    renderPagination(data.filtered_count, 0, state.workspace.pageSize);
}

function updateFilterSummary(filtered, total) {
    const el = document.getElementById('filterResultSummary');
    if (!el) return;
    const pct = total > 0 ? Math.round(filtered / total * 100) : 0;
    el.innerHTML = `<i class="bi bi-funnel-fill"></i> 筛选结果：<strong>${filtered}</strong> / ${total} 行 (${pct}%)`;
    el.style.display = '';
}

// ============================================================
// 已应用筛选 Chips
// ============================================================

function renderAppliedChips() {
    const container = document.getElementById('appliedFilterChips');
    const section = document.getElementById('appliedFilters');
    const stack = state.workspace.filterStack || [];

    if (!container || !section) return;

    if (stack.length === 0) {
        section.style.display = 'none';
        container.innerHTML = '';
        document.getElementById('filterResultSummary').style.display = 'none';
        document.getElementById('commitFilterBtn').style.display = 'none';
        return;
    }

    section.style.display = 'block';
    document.getElementById('commitFilterBtn').style.display = '';

    const renames = state.workspace.columnRenames || {};
    container.innerHTML = stack.map((f, i) => {
        const displayCol = renames[f.column] || f.column;
        const label = `${displayCol} ${operatorLabel(f.operator)} ${formatFilterValue(f.value)}`;
        return `<span class="filter-chip badge bg-primary-subtle text-primary-emphasis border border-primary-subtle me-1 mb-1"
                     style="cursor:default; font-size:0.8rem;">
            ${escapeHtml(label)}
            <i class="bi bi-x-circle-fill ms-1" style="cursor:pointer; opacity:0.7;"
               onclick="removeAppliedFilter(${i})" title="移除此筛选条件"></i>
        </span>`;
    }).join('');
}

function removeAppliedFilter(index) {
    const stack = state.workspace.filterStack || [];
    stack.splice(index, 1);
    state.workspace.filterStack = stack;
    // 重新应用剩余筛选
    reapplyAllFilters();
}

function clearAllFilters() {
    state.workspace.filterStack = [];
    state.workspace.filteredRowCount = null;
    state.workspace.filteredFileName = null;
    state.workspace.currentPage = 0;
    _columnStats = null;
    _columnValuesFetching = {};
    if (typeof updateDownloadLink === 'function') updateDownloadLink();
    document.getElementById('pendingFilters').innerHTML = '';
    renderAppliedChips();
    document.getElementById('filterResultSummary').style.display = 'none';
    renderPreviewTable();
}

async function reapplyAllFilters() {
    const fname = state.workspace.uploadedFile;
    const stack = state.workspace.filterStack || [];
    const logic = state.workspace.filterLogic || 'and';

    if (stack.length === 0) {
        clearAllFilters();
        return;
    }

    try {
        const res = await fetch(`/api/data/${encodeURIComponent(fname)}/filter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filters: stack,
                logic: logic,
                page: 0,
                page_size: state.workspace.pageSize
            })
        });
        const data = await res.json();
        if (data.error) {
            showToast('重新筛选失败: ' + data.error, 'danger');
            return;
        }
        state.workspace.filteredRowCount = data.filtered_count;
        state.workspace.currentPage = 0;
        renderAppliedChips();
        renderTableWithData(data);
        updateFilterSummary(data.filtered_count, data.total_count);
    } catch (err) {
        showToast('请求失败: ' + err.message, 'danger');
    }
}

// ============================================================
// 逻辑切换
// ============================================================

function toggleFilterLogic() {
    const current = state.workspace.filterLogic || 'and';
    state.workspace.filterLogic = current === 'and' ? 'or' : 'and';
    const badge = document.getElementById('filterLogicBadge');
    const btn = document.getElementById('toggleFilterLogicBtn');
    if (badge) badge.textContent = state.workspace.filterLogic.toUpperCase();
    if (btn) btn.textContent = `切换 ${state.workspace.filterLogic === 'and' ? 'OR' : 'AND'}`;
    // 如果有已应用的筛选，重新计算
    if ((state.workspace.filterStack || []).length > 0) {
        reapplyAllFilters();
    }
}

// ============================================================
// 提交筛选数据
// ============================================================

async function commitFilteredData() {
    const fname = state.workspace.uploadedFile;
    const stack = state.workspace.filterStack || [];

    if (!fname) return;

    try {
        const res = await fetch(`/api/data/${encodeURIComponent(fname)}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filters: stack,
                logic: state.workspace.filterLogic || 'and',
                columns: state.workspace.selectedColumns,
                column_renames: state.workspace.columnRenames
            })
        });
        const data = await res.json();
        if (data.error) {
            showToast('导出失败: ' + data.error, 'danger');
            return;
        }

        state.workspace.filteredFileName = data.filtered_filename;
        state.workspace.filteredRowCount = data.filtered_rows;
        showToast(`筛选数据已保留：${data.filtered_rows} 行, ${data.filtered_columns.length} 列`, 'success');

        // 更新下载链接指向筛选后数据
        if (typeof updateDownloadLink === 'function') updateDownloadLink();

        // 更新提交按钮状态
        const btn = document.getElementById('commitFilterBtn');
        if (btn) {
            btn.className = 'btn btn-sm btn-success';
            btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> 已保留筛选结果 ✓';
            btn.disabled = true;
        }
    } catch (err) {
        showToast('导出请求失败: ' + err.message, 'danger');
    }
}

// 列选择变更时，如已有筛选结果则允许重新确认
function onColumnSelectionChanged() {
    if (state.workspace.filteredFileName) {
        const btn = document.getElementById('commitFilterBtn');
        if (btn) {
            btn.className = 'btn btn-sm btn-gradient';
            btn.innerHTML = '<i class="bi bi-check-circle"></i> 列已变更，点击重新保留';
            btn.disabled = false;
        }
    }
}

// ============================================================
// 工具函数
// ============================================================

function operatorLabel(op) {
    const map = {
        eq: '=', neq: '≠', gt: '>', gte: '≥', lt: '<', lte: '≤',
        between: '介于', contains: '包含', not_contains: '不包含',
        starts_with: '开头是', ends_with: '结尾是',
        in: '∈', not_in: '∉',
        is_null: '为空', is_not_null: '非空', is_empty: '为空字符串'
    };
    return map[op] || op;
}

function formatFilterValue(v) {
    if (v === null || v === undefined) return '—';
    if (Array.isArray(v)) {
        if (v.length === 2 && v.every(x => typeof x === 'number')) return `[${v[0]}, ${v[1]}]`;
        return `[${v.slice(0, 3).join(', ')}${v.length > 3 ? '...' : ''}]`;
    }
    const s = String(v);
    return s.length > 20 ? s.slice(0, 20) + '...' : s;
}
