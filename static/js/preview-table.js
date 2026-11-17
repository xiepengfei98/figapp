/**
 * 分页数据预览表格组件
 * 依赖：main.js 中的 state, escapeHtml(), showToast()
 */

// ============================================================
// 核心渲染
// ============================================================

async function renderPreviewTable() {
    const fname = state.workspace.uploadedFile;
    if (!fname) return;

    const { currentPage, pageSize, sortColumn, sortDirection } = state.workspace;

    let url = `/api/data/${encodeURIComponent(fname)}/rows?page=${currentPage}&page_size=${pageSize}`;
    if (sortColumn) {
        url += `&sort_col=${encodeURIComponent(sortColumn)}&sort_dir=${sortDirection}`;
    }

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.error) {
            showToast('加载数据失败: ' + data.error, 'danger');
            return;
        }

        state.workspace.totalRows = data.total_rows;
        state._workspaceLastColumns = data.columns;
        state._workspaceLastRows = data.rows;
        renderTableHeader(data.columns);
        renderTableBody(data.rows, data.columns);
        renderPagination(data.total_rows, data.page, data.page_size);
        updateColCountBadge();
    } catch (err) {
        showToast('请求数据失败: ' + err.message, 'danger');
    }
}

function renderTableHeader(columns) {
    const thead = document.querySelector('#workspacePreviewTable thead');
    const selected = state.workspace.selectedColumns;
    const renamed = state.workspace.columnRenames;

    // 首次渲染时初始化 selectedColumns
    if (!selected || selected.length === 0) {
        state.workspace.selectedColumns = [...columns];
    }

    thead.innerHTML = '<tr>' + columns.map((c) => {
        const displayName = renamed[c] || c;
        const isItalic = !!renamed[c];
        const checked = state.workspace.selectedColumns.includes(c) ? 'checked' : '';
        return `<th style="user-select:none;">
            <input type="checkbox" ${checked} style="cursor:pointer; margin-right:4px;"
                   data-col="${escapeHtml(String(c))}"
                   onclick="event.stopPropagation(); toggleTableColumnCb(this)">
            <span class="col-name-text${isItalic ? ' renamed-col' : ''}"
                  data-original="${escapeHtml(String(c))}"
                  ondblclick="event.stopPropagation(); startRenameColumn('${escapeHtml(String(c))}', this)"
                  title="${isItalic ? '原名: ' + escapeHtml(String(c)) + '\n双击可重新编辑' : '双击可重命名列'}">${escapeHtml(String(displayName))}</span>
        </th>`;
    }).join('') + '</tr>';
}

function renderTableBody(rows, columns) {
    const tbody = document.querySelector('#workspacePreviewTable tbody');
    state._workspaceLastRows = rows;
    state._workspaceLastColumns = columns;
    if (!rows || rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${columns.length}" class="text-center text-muted py-3">
            无匹配数据</td></tr>`;
        return;
    }
    tbody.innerHTML = rows.map(row =>
        '<tr>' + row.map(cell =>
            `<td>${escapeHtml(cell == null ? '' : String(cell))}</td>`).join('') + '</tr>'
    ).join('');
}

// ============================================================
// 分页
// ============================================================

function goToPage(n) {
    const totalPages = Math.ceil(state.workspace.totalRows / state.workspace.pageSize) || 1;
    if (n < 0 || n >= totalPages) return;
    state.workspace.currentPage = n;
    renderPreviewTable();
}

function changePageSize(n) {
    state.workspace.pageSize = n;
    state.workspace.currentPage = 0;
    renderPreviewTable();
}

function renderPagination(totalRows, currentPage, pageSize) {
    const totalPages = Math.ceil(totalRows / pageSize) || 1;
    const start = totalRows > 0 ? currentPage * pageSize + 1 : 0;
    const end = Math.min((currentPage + 1) * pageSize, totalRows);

    // 页面信息
    document.getElementById('pageInfo').textContent =
        `显示 ${start}-${end}，共 ${totalRows} 行`;

    // 页码按钮
    const nav = document.getElementById('paginationNav');
    const maxButtons = 7;
    let pages = [];
    if (totalPages <= maxButtons) {
        for (let i = 0; i < totalPages; i++) pages.push(i);
    } else {
        pages.push(0);
        let left = Math.max(1, currentPage - 2);
        let right = Math.min(totalPages - 2, currentPage + 2);
        if (currentPage <= 3) {
            right = Math.min(maxButtons - 2, totalPages - 1);
        }
        if (currentPage >= totalPages - 4) {
            left = Math.max(1, totalPages - maxButtons + 1);
        }
        if (left > 1) pages.push(-1); // ellipsis
        for (let i = left; i <= right; i++) pages.push(i);
        if (right < totalPages - 2) pages.push(-2); // ellipsis
        if (totalPages > 1) pages.push(totalPages - 1);
    }

    nav.innerHTML = `
        <li class="page-item${currentPage === 0 ? ' disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(0); return false;">&laquo;</a>
        </li>
        <li class="page-item${currentPage === 0 ? ' disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${currentPage - 1}); return false;">&lsaquo;</a>
        </li>
        ${pages.map(p => {
            if (p < 0) return '<li class="page-item disabled"><span class="page-link">...</span></li>';
            return `<li class="page-item${p === currentPage ? ' active' : ''}">
                <a class="page-link" href="#" onclick="goToPage(${p}); return false;">${p + 1}</a></li>`;
        }).join('')}
        <li class="page-item${currentPage >= totalPages - 1 ? ' disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${currentPage + 1}); return false;">&rsaquo;</a>
        </li>
        <li class="page-item${currentPage >= totalPages - 1 ? ' disabled' : ''}">
            <a class="page-link" href="#" onclick="goToPage(${totalPages - 1}); return false;">&raquo;</a>
        </li>`;

    document.getElementById('previewPagination').style.display = totalRows > 0 ? '' : 'none';
    document.getElementById('pageSizeSelect').value = pageSize;
}

// ============================================================
// 排序
// ============================================================

function sortByColumn(col) {
    if (state.workspace.sortColumn === col) {
        state.workspace.sortDirection = state.workspace.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        state.workspace.sortColumn = col;
        state.workspace.sortDirection = 'asc';
    }
    state.workspace.currentPage = 0;
    renderPreviewTable();
}

// ============================================================
// 列选择
// ============================================================

async function applyColumnSelection() {
    const selected = state.workspace.selectedColumns;
    if (!selected || selected.length === 0) {
        showToast('请先勾选需要显示的列', 'warning');
        return;
    }
    const filename = state.workspace.uploadedFile;
    if (!filename) return;

    try {
        const res = await fetch(`/api/data/${encodeURIComponent(filename)}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                columns: selected,
                column_renames: state.workspace.columnRenames || {}
            })
        });
        const data = await res.json();
        if (data.error) {
            showToast('应用失败: ' + data.error, 'danger');
            return;
        }
        // 使用导出后的文件作为新的数据源
        state.workspace.filteredFileName = data.filtered_filename;
        state.workspace.currentPage = 0;
        // 重新加载预览表格
        await renderPreviewTable();
        updateDownloadLink();
        showToast('已应用列勾选，共 ' + selected.length + ' 列', 'success');
    } catch (err) {
        showToast('应用勾选失败: ' + err.message, 'danger');
    }
}

function toggleTableColumnCb(cb) {
    const colName = cb.dataset.col;
    if (cb.checked) {
        if (!state.workspace.selectedColumns.includes(colName)) {
            state.workspace.selectedColumns.push(colName);
        }
    } else {
        state.workspace.selectedColumns = state.workspace.selectedColumns.filter(c => c !== colName);
    }
    updateColCountBadge();
    if (typeof onColumnSelectionChanged === 'function') onColumnSelectionChanged();
}

function selectAllColumns() {
    document.querySelectorAll('#workspacePreviewTable thead input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
        const col = cb.dataset.col;
        if (!state.workspace.selectedColumns.includes(col)) {
            state.workspace.selectedColumns.push(col);
        }
    });
    updateColCountBadge();
    if (typeof onColumnSelectionChanged === 'function') onColumnSelectionChanged();
}

function deselectAllColumns() {
    document.querySelectorAll('#workspacePreviewTable thead input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    state.workspace.selectedColumns = [];
    updateColCountBadge();
    if (typeof onColumnSelectionChanged === 'function') onColumnSelectionChanged();
}

function invertColumnSelection() {
    const allCols = [];
    document.querySelectorAll('#workspacePreviewTable thead input[type="checkbox"]').forEach(cb => {
        allCols.push(cb.dataset.col);
    });
    const newSelected = allCols.filter(c => !state.workspace.selectedColumns.includes(c));
    state.workspace.selectedColumns = newSelected;
    document.querySelectorAll('#workspacePreviewTable thead input[type="checkbox"]').forEach(cb => {
        cb.checked = newSelected.includes(cb.dataset.col);
    });
    updateColCountBadge();
    if (typeof onColumnSelectionChanged === 'function') onColumnSelectionChanged();
}

function updateColCountBadge() {
    const total = document.querySelectorAll('#workspacePreviewTable thead input[type="checkbox"]').length;
    const selected = state.workspace.selectedColumns.length;
    const el = document.getElementById('selectedColCount');
    if (el) el.textContent = `${selected}/${total}`;
}

// ============================================================
// 列重命名（从 main.js 迁移）
// ============================================================

function startRenameColumn(originalName, spanEl) {
    const currentDisplay = spanEl.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentDisplay;
    input.style.cssText = 'width:80px; font-size:0.75rem; padding:2px 4px; border:1px solid var(--primary); border-radius:3px;';
    input.dataset.original = originalName;

    const finish = () => {
        const newName = input.value.trim();
        if (newName && newName !== originalName) {
            spanEl.textContent = newName;
            spanEl.classList.add('renamed-col');
            spanEl.title = `原名: ${originalName}\n双击可重新编辑`;
            state.workspace.columnRenames[originalName] = newName;
        }
        input.replaceWith(spanEl);
        updateColCountBadge();
        if (typeof onColumnSelectionChanged === 'function') onColumnSelectionChanged();
    };

    const cancel = () => {
        input.replaceWith(spanEl);
    };

    input.addEventListener('blur', finish);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); finish(); }
        if (e.key === 'Escape') { e.preventDefault(); cancel(); }
    });

    spanEl.replaceWith(input);
    input.focus();
    input.select();
}
