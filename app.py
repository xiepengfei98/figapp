#!/usr/bin/env python3
"""
Script Hub - 交互式数据可视化脚本管理平台
Flask 主应用
"""

import os
import re
import sys
import json
import uuid
import socket
import base64
import subprocess
import difflib
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, request, jsonify, send_from_directory,
    render_template, url_for
)
from werkzeug.utils import secure_filename
import pandas as pd

# ============================================================
# 应用初始化
# ============================================================

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 上传限制
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails'

BASE_DIR = Path(__file__).parent

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'txt'}

# ============================================================
# 全局状态管理
# ============================================================

# 任务状态存储（内存），key: task_id, value: {status, result, ...}
task_store = {}

# 脚本配置热加载：scripts.json 被外部修改后，下一次请求自动生效，无需重启
SCRIPTS_CONFIG_PATH = BASE_DIR / 'config' / 'scripts.json'
_scripts_config_mtime = None


def load_scripts_config():
    """从磁盘重新读取 scripts.json，并记录文件修改时间"""
    global _scripts_config_mtime
    with open(SCRIPTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    try:
        _scripts_config_mtime = SCRIPTS_CONFIG_PATH.stat().st_mtime
    except OSError:
        _scripts_config_mtime = None
    return data


def save_scripts_config(config):
    """保存脚本配置文件，并同步内存中的修改时间戳，保证写入内容立即可见"""
    global scripts_config
    with open(SCRIPTS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    try:
        _scripts_config_mtime = SCRIPTS_CONFIG_PATH.stat().st_mtime
    except OSError:
        _scripts_config_mtime = None
    # 并发场景下全局可能被并发热加载替换，让全局指向本次保存的最新对象
    scripts_config = config


def refresh_scripts_config():
    """检测 scripts.json 是否被外部修改；已修改则热加载全局配置，返回是否发生了重载"""
    global scripts_config
    try:
        mtime = SCRIPTS_CONFIG_PATH.stat().st_mtime
    except OSError:
        return False
    if mtime != _scripts_config_mtime:
        scripts_config = load_scripts_config()
        return True
    return False


scripts_config = load_scripts_config()

# ============================================================
# 工具函数
# ============================================================

def allowed_file(filename):
    """检查文件扩展名是否合法"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_csv_auto_encoding(filepath, **kwargs):
    """读取 CSV 文件，自动检测编码（UTF-8 / GBK / GB18030 / Latin-1）。"""
    encodings = ['utf-8', 'gbk', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            return pd.read_csv(filepath, encoding=enc, **kwargs)
        except (UnicodeDecodeError, TypeError):
            continue
    return pd.read_csv(filepath, **kwargs)


def find_script(script_id):
    """根据 ID 查找脚本配置（先检测配置是否被外部修改）"""
    refresh_scripts_config()
    for s in scripts_config['scripts']:
        if s['id'] == script_id:
            return s
    return None

def find_rscript():
    """查找 Rscript 可执行文件路径，优先环境变量 > 常见路径 > PATH"""
    # 1. 环境变量 RSCRIPT_PATH
    env_path = os.environ.get('RSCRIPT_PATH', '')
    if env_path and Path(env_path).exists():
        return env_path

    # 2. 常见 Windows 安装路径
    common_paths = [
        # Program Files 下的各版本
        Path('C:/Program Files/R'),
        Path('C:/Program Files/R/R-4.4.0/bin/x64/Rscript.exe'),
        # 用户自定义路径
        Path('D:/software/R'),
        Path('D:/software/R/R-4.4.0/bin/x64/Rscript.exe'),
        Path('E:/software/R'),
    ]

    for candidate in common_paths:
        if candidate.is_dir():
            # 搜索目录下所有 Rscript.exe
            for exe in candidate.rglob('Rscript.exe'):
                return str(exe)
        elif candidate.exists():
            return str(candidate)

    # 3. 回退到 PATH 查找
    return 'Rscript'


def get_interpreter(language):
    """根据脚本语言获取解释器命令"""
    if language == 'R':
        return find_rscript()
    elif language == 'Python':
        return sys.executable
    raise ValueError(f'不支持的语言: {language}')


def get_lan_ip():
    """获取局域网 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def find_port_owner(port):
    """查找占用指定 TCP 端口的进程，返回 (pid, 进程名)；未被占用或查询失败返回 None"""
    try:
        out = subprocess.run(['netstat', '-ano'], capture_output=True,
                             text=True, timeout=10).stdout
        pid = None
        for line in out.splitlines():
            parts = line.split()
            if (len(parts) >= 5 and parts[0].upper().startswith('TCP')
                    and parts[1].endswith(f':{port}')
                    and parts[3].upper() == 'LISTENING'):
                pid = parts[4]
                break
        if not pid:
            return None
        try:
            t = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                               capture_output=True, text=True, timeout=10)
            name = t.stdout.strip().splitlines()[0].split()[0] if t.stdout.strip() else '未知'
        except Exception:
            name = '未知'
        return pid, name
    except Exception:
        return None


def get_process_cmdline(pid):
    """通过 PID 获取进程完整命令行，用于判断占用 5000 端口的是否为本应用"""
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return out or ''
    except Exception:
        return ''


# ============================================================
# 脚本参数解析（@PARAM 声明）
# ============================================================

PARAM_PATTERN = re.compile(
    r'#\s*@PARAM\s+(\w+)\s*:\s*(\w+)\s*=\s*(.*?)\s*\|\s*(.*)'
)

# 从 label 中提取选项: "label [opt1,opt2,opt3]" → (label, [opt1, opt2, opt3])
OPTIONS_IN_LABEL = re.compile(r'\s*\[(.+?)\]\s*$')

def parse_script_params(script_content):
    """从脚本内容中解析 @PARAM 声明

    格式: # @PARAM name: type = default | label
          # @PARAM name: select = default | label [opt1,opt2,opt3]
    支持类型: str, float, int, bool, select
    """
    params = []
    for m in PARAM_PATTERN.finditer(script_content):
        name, ptype, default_str, label = m.groups()
        default_str = default_str.strip()
        label = label.strip()

        # 提取 select 类型的选项列表
        options = []
        if ptype == 'select':
            opt_m = OPTIONS_IN_LABEL.search(label)
            if opt_m:
                options = [o.strip() for o in opt_m.group(1).split(',') if o.strip()]
                label = label[:opt_m.start()].strip()

        # 转换默认值为正确类型
        typed_default = default_str
        if ptype == 'int':
            try: typed_default = int(default_str)
            except: typed_default = 0
        elif ptype == 'float':
            try: typed_default = float(default_str)
            except: typed_default = 0.0
        elif ptype == 'bool':
            typed_default = default_str.lower() in ('true', '1', 'yes')
        elif ptype == 'select':
            typed_default = default_str if default_str else (options[0] if options else '')

        entry = {
            'name': name,
            'type': ptype,
            'default': typed_default,
            'label': label,
            'raw_default': default_str
        }
        if options:
            entry['options'] = options
        params.append(entry)
    return params


# ============================================================
# README 数据要求解析
# ============================================================

REQUIREMENTS_CACHE = None
SUGGESTIONS_FILE = BASE_DIR / 'config' / 'suggestions.json'


def parse_readme_requirements():
    """解析 D:\python_projects\knowage\03.项目\04.可视化 下所有 README.md 的数据要求"""
    source_dir = Path(r'D:\python_projects\knowage\03.项目\04.可视化')
    results = []
    if not source_dir.exists():
        return results
    for folder in sorted(source_dir.iterdir()):
        if not folder.is_dir():
            continue
        readme_path = folder / 'README.md'
        if not readme_path.exists():
            continue
        content = readme_path.read_text(encoding='utf-8')
        title = ''
        m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if m:
            title = m.group(1).strip()
        req_section = re.search(r'## 数据要求\s*\n([\s\S]*?)(?=\n## |\n---|\Z)', content)
        columns = []
        if req_section:
            table_text = req_section.group(1)
            for line in table_text.strip().split('\n'):
                line = line.strip()
                if line.startswith('|') and not re.match(r'^\|[\s\-:]+\|', line):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3 and parts[0] != '列名':
                        columns.append({
                            'name': parts[0],
                            'meaning': parts[1],
                            'type': parts[2]
                        })
        results.append({
            'folder': folder.name,
            'title': title,
            'columns': columns
        })
    return results


def init_requirements_cache():
    global REQUIREMENTS_CACHE
    if REQUIREMENTS_CACHE is None:
        REQUIREMENTS_CACHE = parse_readme_requirements()
    return REQUIREMENTS_CACHE


def load_suggestions():
    if SUGGESTIONS_FILE.exists():
        with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_suggestions(suggestions):
    with open(SUGGESTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)


def run_script_async(task_id, script, data_path, output_path, output_url):
    """异步执行脚本任务"""
    try:
        interpreter = get_interpreter(script['language'])
        script_path = BASE_DIR / script['path']

        if not script_path.exists():
            raise FileNotFoundError(f'脚本文件不存在: {script_path}')

        is_data_process = script.get('category') == 'data_process'

        # 运行目录
        run_dir = output_path.parent

        if is_data_process:
            # 数据处理脚本：保持旧 CLI 参数方式
            cmd = [interpreter, str(script_path), str(data_path), str(output_path)]
        else:
            # 绘图脚本：写入 config.json，以配置文件方式传递参数
            colors = get_active_colors()
            user_params = task_store[task_id].get('user_params', {})

            # 自动检测列映射：从数据文件中读取列名，匹配常见角色名称
            auto_columns = {}
            try:
                import pandas as _pd
                ext = data_path.suffix.lower()
                if ext == '.csv':
                    _df_headers = read_csv_auto_encoding(data_path, nrows=0)
                    _data_cols = _df_headers.columns.tolist()
                elif ext in ('.xlsx', '.xls'):
                    _data_cols = _pd.read_excel(data_path, nrows=1).columns.tolist()
                elif ext == '.txt':
                    _data_cols = _pd.read_csv(data_path, sep='\t', nrows=0).columns.tolist()
                else:
                    _data_cols = []

                _role_aliases = {
                    'x': ['x', 'x_axis', 'xaxis', 'time'],
                    'y': ['y', 'y_axis', 'yaxis', 'value', 'response'],
                    'label': ['label', 'time', 'frame', 'date', 'year', 'timestamp'],
                    'group': ['group', 'groups', 'class', 'category', 'type', 'treatment'],
                    'color': ['color', 'colour'],
                    'facet': ['facet', 'panel'],
                    'size': ['size', 'count', 'n'],
                }
                for _role, _aliases in _role_aliases.items():
                    for _alias in _aliases:
                        if _alias in _data_cols:
                            auto_columns[_role] = _alias
                            break
            except Exception:
                pass

            config = {
                'input': str(data_path),
                'output': str(output_path),
                'output_pdf': str(output_path.with_suffix('.pdf')),
                'parameters': user_params,
                'columns': auto_columns,
                'colors': {
                    'palette': colors,
                    'active_series': load_colors_config().get('active_series', 'npg')
                }
            }
            config_path = run_dir / 'config.json'
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False)
            cmd = [interpreter, str(script_path), str(config_path)]

        task_store[task_id]['status'] = 'running'
        task_store[task_id]['started_at'] = datetime.now().isoformat()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd=str(run_dir)
        )

        if result.returncode == 0:
            folder_name = run_dir.name

            result_data = {
                'output_url': output_url,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }

            is_data_process = script.get('category') == 'data_process'
            if is_data_process and output_path.suffix == '.csv' and output_path.exists():
                try:
                    out_df = read_csv_auto_encoding(output_path, nrows=50)
                    out_df = out_df.where(pd.notnull(out_df), None)
                    result_data['csv_preview'] = {
                        'columns': out_df.columns.tolist(),
                        'rows': [[None if pd.isnull(v) else v for v in row] for row in out_df.values],
                        'shape': [len(out_df), len(out_df.columns)]
                    }
                    result_data['csv_url'] = output_url
                    result_data['csv_download'] = output_url
                except Exception:
                    pass
            else:
                # 扫描输出目录中的 PDF/JPG 文件
                pdf_files = sorted(run_dir.glob('*.pdf'))
                jpg_files = sorted(list(run_dir.glob('*.jpg')) + list(run_dir.glob('*.jpeg')))
                if pdf_files:
                    result_data['pdf_url'] = f'/uploads/{folder_name}/{pdf_files[0].name}'
                if jpg_files:
                    result_data['jpg_url'] = f'/uploads/{folder_name}/{jpg_files[0].name}'

            task_store[task_id]['status'] = 'success'
            task_store[task_id]['result'] = result_data
            # 更新缩略图（如果配置了）
            if script.get('thumbnail'):
                thumb_path = BASE_DIR / script['thumbnail']
                if not thumb_path.exists() and output_path.exists():
                    import shutil
                    shutil.copy(str(output_path), str(thumb_path))
        else:
            task_store[task_id]['status'] = 'failed'
            task_store[task_id]['result'] = {
                'error': f'脚本执行失败 (exit code: {result.returncode})',
                'stdout': result.stdout,
                'stderr': result.stderr
            }

    except subprocess.TimeoutExpired as te:
        task_store[task_id]['status'] = 'failed'
        task_store[task_id]['result'] = {
            'error': '脚本执行超时（超过5分钟）',
            'stdout': te.stdout if te.stdout else '',
            'stderr': te.stderr if te.stderr else ''
        }
    except Exception as e:
        task_store[task_id]['status'] = 'failed'
        _stdout = result.stdout if 'result' in dir() and hasattr(result, 'stdout') else ''
        _stderr = result.stderr if 'result' in dir() and hasattr(result, 'stderr') else ''
        task_store[task_id]['result'] = {
            'error': str(e),
            'stdout': _stdout,
            'stderr': _stderr
        }

    task_store[task_id]['finished_at'] = datetime.now().isoformat()

    # 将任务元数据写入 run 目录下的 metadata.json
    try:
        folder_name = task_store[task_id].get('folder_name', '')
        if folder_name:
            run_dir = BASE_DIR / 'uploads' / folder_name
            meta_path = run_dir / 'metadata.json'
            result = task_store[task_id].get('result', {})
            meta = {
                'task_id': task_id,
                'script_id': task_store[task_id].get('script_id'),
                'script_name': task_store[task_id].get('script_name'),
                'script_language': task_store[task_id].get('script_language'),
                'script_description': task_store[task_id].get('script_description'),
                'data_filename': task_store[task_id].get('data_filename'),
                'source_filename': task_store[task_id].get('source_filename'),
                'is_filtered': task_store[task_id].get('is_filtered', False),
                'user_params': task_store[task_id].get('user_params', {}),
                'folder_name': folder_name,
                'status': task_store[task_id].get('status'),
                'created_at': task_store[task_id].get('created_at'),
                'started_at': task_store[task_id].get('started_at'),
                'finished_at': task_store[task_id].get('finished_at'),
                'output_url': result.get('output_url', ''),
                'pdf_url': result.get('pdf_url', ''),
                'jpg_url': result.get('jpg_url', ''),
                'error': result.get('error', ''),
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', '')
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # metadata 写入失败不影响主流程

# ============================================================
# 路由：页面渲染
# ============================================================

@app.route('/')
def index():
    """渲染主页面"""
    return render_template('index.html')

# ============================================================
# API：脚本管理
# ============================================================

@app.route('/api/scripts', methods=['GET'])
def get_scripts():
    """获取所有脚本，支持 ?language=R & ?category=data_process & ?modified=true 过滤"""
    refresh_scripts_config()
    language = request.args.get('language', 'all')
    category = request.args.get('category', '')
    modified_only = request.args.get('modified', '').lower() == 'true'
    scripts = scripts_config['scripts']

    if modified_only:
        scripts = [s for s in scripts if s.get('based_on')]
    elif category == 'data_process':
        scripts = [s for s in scripts if s.get('category') == 'data_process']
    elif language != 'all':
        scripts = [s for s in scripts if s['language'].lower() == language.lower()
                   and s.get('category') != 'data_process']

    return jsonify({'scripts': scripts, 'total': len(scripts)})

@app.route('/api/scripts/<script_id>', methods=['GET'])
def get_script_detail(script_id):
    """获取单个脚本详情"""
    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404

    script_path = BASE_DIR / script['path']
    script_content = ''
    parsed_params = []
    if script_path.exists():
        script_content = script_path.read_text(encoding='utf-8')
        parsed_params = parse_script_params(script_content)

    return jsonify({
        'script': script,
        'content': script_content,
        'parsed_params': parsed_params
    })

@app.route('/api/scripts/add', methods=['POST'])
def add_script():
    """添加新脚本"""
    try:
        data = request.form.to_dict()

        script_id = data.get('id', '').strip()
        if not script_id:
            return jsonify({'error': '脚本 ID 不能为空'}), 400

        if find_script(script_id):
            return jsonify({'error': f'脚本 ID "{script_id}" 已存在'}), 409

        script_name = data.get('name', '').strip()
        if not script_name:
            return jsonify({'error': '脚本名称不能为空'}), 400

        existing_names = [s['name'] for s in scripts_config['scripts']]
        if script_name in existing_names:
            return jsonify({'error': f'脚本名称 "{script_name}" 已存在'}), 409

        # 处理脚本文件上传
        script_file = request.files.get('script_file')
        if not script_file or script_file.filename == '':
            return jsonify({'error': '请上传脚本文件'}), 400

        language = data.get('language', 'Python')
        category = data.get('category', '').strip()

        if category == 'data_process':
            language = 'Python'
            sub_dir = 'data_process'
        elif language == 'R':
            sub_dir = 'R'
        else:
            sub_dir = 'python'

        filename = secure_filename(script_file.filename)
        dest_dir = BASE_DIR / 'scripts' / sub_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        script_path = dest_dir / filename
        script_file.save(str(script_path))

        # 处理缩略图
        thumbnail_path = ''
        thumb_file = request.files.get('thumbnail')
        if thumb_file and thumb_file.filename:
            thumb_name = secure_filename(thumb_file.filename)
            thumb_dest = BASE_DIR / 'thumbnails' / thumb_name
            thumb_file.save(str(thumb_dest))
            thumbnail_path = f'thumbnails/{thumb_name}'

        # 处理示例数据文件（可选）
        sample_data = ''
        data_format = data.get('data_format', '').strip()
        sample_data_file = request.files.get('sample_data_file')
        if sample_data_file and sample_data_file.filename:
            sample_name = secure_filename(sample_data_file.filename)
            sample_dest_dir = BASE_DIR / 'sample_data'
            sample_dest_dir.mkdir(parents=True, exist_ok=True)
            sample_path = sample_dest_dir / sample_name
            sample_data_file.save(str(sample_path))
            sample_data = sample_name
            # 如果未指定数据格式，从示例数据自动检测
            if not data_format:
                try:
                    sample_df = read_csv_auto_encoding(sample_path, nrows=0)
                    data_format = 'wide' if len(sample_df.columns) > 5 else 'long'
                except Exception:
                    pass

        new_script = {
            'id': script_id,
            'name': script_name,
            'language': language,
            'category': category,
            'path': f'scripts/{sub_dir}/{filename}',
            'description': data.get('description', ''),
            'thumbnail': thumbnail_path,
            'parameters': [p.strip() for p in data.get('parameters', '').split(',') if p.strip()],
            'input_format': data.get('input_format', 'csv'),
            'sample_data': sample_data if sample_data else '',
            'data_format': data_format if data_format else '',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        }

        config = scripts_config
        config['scripts'].append(new_script)
        save_scripts_config(config)

        return jsonify({'message': '脚本添加成功', 'script': new_script}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scripts/<script_id>', methods=['DELETE'])
def delete_script(script_id):
    """删除脚本（从配置中移除，同时删除脚本文件）
    权限控制：localhost 可删所有脚本，内网仅可删除修改版脚本（based_on）
    """
    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404

    # 权限检查：非 localhost 且非修改版脚本（数据处理等同于原始脚本），禁止删除
    is_localhost = request.remote_addr in ('127.0.0.1', 'localhost', '::1')
    is_modified = bool(script.get('based_on')) and script.get('category') != 'data_process'
    if not is_localhost and not is_modified:
        return jsonify({'error': '仅可删除修改版脚本，原始脚本和数据处理脚本请联系管理员'}), 403

    # 删除脚本文件
    script_file = BASE_DIR / script['path']
    if script_file.exists():
        script_file.unlink()

    config = scripts_config
    config['scripts'] = [s for s in config['scripts'] if s['id'] != script_id]
    save_scripts_config(config)

    return jsonify({'message': f'脚本 {script_id} 已删除'})


@app.route('/api/scripts/<script_id>/edit', methods=['POST'])
def edit_script(script_id):
    """修改脚本并另存为新脚本，不影响原脚本"""
    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': '缺少脚本内容'}), 400

    new_content = data['content']
    source = data.get('source', 'manual')
    new_id = data.get('new_id', '').strip()
    new_name = data.get('new_name', '').strip()

    if not new_id:
        return jsonify({'error': '新脚本 ID 不能为空'}), 400
    if not new_name:
        return jsonify({'error': '新脚本名称不能为空'}), 400
    if find_script(new_id):
        return jsonify({'error': f'脚本 ID "{new_id}" 已存在'}), 409

    # 确定新脚本文件路径
    orig_path = BASE_DIR / script['path']
    ext = orig_path.suffix
    lang_dir = 'R' if script['language'] == 'R' else 'python'
    dest_dir = BASE_DIR / 'scripts' / lang_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_path = dest_dir / f'{new_id}{ext}'
    new_path.write_text(new_content, encoding='utf-8')

    # 创建新脚本配置条目（复制原脚本元信息）
    new_script = {
        'id': new_id,
        'name': new_name,
        'language': script['language'],
        'path': f'scripts/{lang_dir}/{new_id}{ext}',
        'description': script.get('description', ''),
        'thumbnail': script.get('thumbnail', ''),
        'parameters': script.get('parameters', []),
        'input_format': script.get('input_format', 'csv'),
        'sample_data': script.get('sample_data', ''),
        'data_format': script.get('data_format', ''),
        'created_at': datetime.now().strftime('%Y-%m-%d'),
        'based_on': script_id
    }

    config = scripts_config
    config['scripts'].append(new_script)
    save_scripts_config(config)

    return jsonify({'message': '脚本已保存为新脚本', 'script': new_script}), 201

@app.route('/api/scripts/reload', methods=['GET'])
def reload_scripts():
    """热加载脚本配置"""
    global scripts_config
    scripts_config = load_scripts_config()
    return jsonify({'status': 'reloaded', 'count': len(scripts_config['scripts'])})

# ============================================================
# API：脚本执行
# ============================================================

@app.route('/api/run/<script_id>', methods=['POST'])
def run_script(script_id):
    """执行脚本"""
    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404

    # 创建统一的工作目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder_name = f'{script_id}_{timestamp}'
    run_dir = BASE_DIR / 'uploads' / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # 处理列选择（过滤列）
    selected_columns = request.form.get('columns', '')
    if selected_columns:
        try:
            selected_columns = json.loads(selected_columns)
        except (json.JSONDecodeError, TypeError):
            selected_columns = []

    # 处理数据文件
    import shutil
    use_filtered = request.form.get('use_filtered', '')
    use_uploaded = request.form.get('use_uploaded', '')
    use_project_data = request.form.get('use_project_data', '')  # 历史项目重分析
    is_filtered = False

    if use_filtered:
        filtered_path = BASE_DIR / 'uploads' / secure_filename(use_filtered)
        if not filtered_path.exists():
            return jsonify({'error': f'筛选文件不存在: {use_filtered}'}), 404
        ext = filtered_path.suffix
        data_filename = f'data{ext}'
        data_path = run_dir / data_filename
        shutil.copy(str(filtered_path), str(data_path))
        source_filename = use_filtered  # 记录原始筛选文件名
        is_filtered = True
    elif use_project_data:
        # 从历史项目目录中复制数据文件用于重分析
        project_dir = BASE_DIR / 'uploads' / secure_filename(use_project_data)
        if not project_dir.exists() or not project_dir.is_dir():
            return jsonify({'error': f'历史项目目录不存在: {use_project_data}'}), 404
        data_candidates = list(project_dir.glob('data.*'))
        if not data_candidates:
            return jsonify({'error': '历史项目中未找到数据文件'}), 404
        src_path = data_candidates[0]
        ext = src_path.suffix
        data_filename = f'data{ext}'
        data_path = run_dir / data_filename
        shutil.copy(str(src_path), str(data_path))
        source_filename = src_path.name
        is_filtered = False
    elif use_uploaded:
        uploaded_path = BASE_DIR / 'uploads' / secure_filename(use_uploaded)
        if not uploaded_path.exists():
            return jsonify({'error': f'已上传文件不存在: {use_uploaded}'}), 404
        ext = uploaded_path.suffix
        data_filename = f'data{ext}'
        data_path = run_dir / data_filename
        shutil.copy(str(uploaded_path), str(data_path))
        source_filename = use_uploaded
        is_filtered = False
    elif 'data_file' in request.files:
        data_file = request.files['data_file']
        if data_file.filename == '':
            return jsonify({'error': '请选择数据文件'}), 400
        if not allowed_file(data_file.filename):
            return jsonify({'error': f'不支持的文件格式，支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        ext = Path(data_file.filename).suffix
        data_filename = f'data{ext}'
        data_path = run_dir / data_filename
        data_file.save(str(data_path))
        source_filename = data_file.filename
        is_filtered = False
    else:
        return jsonify({'error': '请上传数据文件或指定已上传的文件名'}), 400

    # 处理列重命名
    column_renames = request.form.get('column_renames', '')
    if column_renames:
        try:
            column_renames = json.loads(column_renames)
        except (json.JSONDecodeError, TypeError):
            column_renames = {}

    # 如果指定了列选择/重命名，处理数据文件
    if (selected_columns or column_renames) and data_path.exists():
        try:
            ext = data_path.suffix.lower()
            if ext == '.csv':
                df = read_csv_auto_encoding(data_path)
            elif ext in ('.xlsx', '.xls'):
                df = pd.read_excel(data_path)
            else:
                df = read_csv_auto_encoding(data_path)

            # 先过滤列（使用原始列名）
            if selected_columns:
                available_cols = [c for c in selected_columns if c in df.columns]
                if available_cols:
                    df = df[available_cols]

            # 再重命名
            if column_renames:
                valid_renames = {k: v for k, v in column_renames.items() if k in df.columns}
                if valid_renames:
                    df.rename(columns=valid_renames, inplace=True)

            if ext == '.csv':
                df.to_csv(data_path, index=False)
            elif ext in ('.xlsx', '.xls'):
                df.to_excel(data_path, index=False)
        except Exception:
            pass  # 处理失败不影响执行，使用原始数据

    # 处理用户参数（来自 @PARAM 声明，前端 UI 控件修改后提交）
    user_params = request.form.get('parameters', '{}')
    if user_params:
        try:
            user_params = json.loads(user_params)
        except (json.JSONDecodeError, TypeError):
            user_params = {}

    # 输出文件在同一目录下（数据处理脚本输出 CSV）
    is_data_process = script.get('category') == 'data_process'
    if is_data_process:
        output_name = 'output.csv'
    else:
        output_name = f'{script_id}.png'
    output_path = run_dir / output_name
    output_url = f'/uploads/{folder_name}/{output_name}'

    # 创建任务（附带完整元数据）
    task_id = str(uuid.uuid4())
    # 复制全局配置到运行目录
    try:
        import shutil as _shutil
        lang = script.get('language', 'python').lower()
        if lang == 'python':
            _shutil.copy(str(BASE_DIR / 'config' / 'figapp_config.py'),
                       str(run_dir / 'figapp_config.py'))
        elif lang == 'r':
            _shutil.copy(str(BASE_DIR / 'config' / 'figapp_config.R'),
                       str(run_dir / 'figapp_config.R'))
        # 写入颜色配置
        colors = get_active_colors()
        color_config_path = run_dir / 'color_config.json'
        with open(color_config_path, 'w', encoding='utf-8') as _f:
            json.dump({'colors': colors, 'active_series': load_colors_config().get('active_series', 'npg')}, _f, ensure_ascii=False)
    except Exception:
        pass

    task_store[task_id] = {
        'id': task_id,
        'script_id': script_id,
        'script_name': script.get('name', script_id),
        'script_language': script.get('language', ''),
        'script_description': script.get('description', ''),
        'data_filename': data_filename,
        'source_filename': source_filename,
        'is_filtered': is_filtered,
        'folder_name': folder_name,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'user_params': user_params
    }

    thread = threading.Thread(
        target=run_script_async,
        args=(task_id, script, data_path, output_path, output_url),
        daemon=True
    )
    thread.start()

    return jsonify({
        'task_id': task_id,
        'message': '脚本已提交执行',
        'folder_name': folder_name
    }), 202

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查询任务执行状态"""
    task = task_store.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    response = {
        'task_id': task['id'],
        'status': task['status'],
        'script_id': task['script_id'],
        'script_name': task.get('script_name', ''),
        'script_language': task.get('script_language', ''),
        'script_description': task.get('script_description', ''),
        'data_filename': task.get('data_filename', ''),
        'source_filename': task.get('source_filename', ''),
        'is_filtered': task.get('is_filtered', False),
        'folder_name': task.get('folder_name', ''),
        'created_at': task.get('created_at'),
        'started_at': task.get('started_at'),
        'finished_at': task.get('finished_at')
    }

    if task['status'] in ('success', 'failed'):
        response['result'] = task['result']
        # 如果脚本生成了 PDF/JPG，直接提供下载链接
        if task['result'].get('pdf_url'):
            response['pdf_url'] = task['result']['pdf_url']
        if task['result'].get('jpg_url'):
            response['jpg_url'] = task['result']['jpg_url']

    return jsonify(response)

# ============================================================
# API：数据管理
# ============================================================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传数据文件"""
    if 'file' not in request.files:
        return jsonify({'error': '请选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '请选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的文件格式'}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_name = f'{timestamp}_{filename}'
    file_path = BASE_DIR / 'uploads' / unique_name
    file.save(str(file_path))

    # 读取列名和数据类型（不加载全部数据）
    columns = []
    dtypes = {}
    total_rows = 0
    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            df = read_csv_auto_encoding(file_path, nrows=0)
        elif ext in ('xlsx', 'xls'):
            df = pd.read_excel(file_path, nrows=0)
        elif ext == 'txt':
            df = read_csv_auto_encoding(file_path, sep='\t', nrows=0)
        else:
            df = read_csv_auto_encoding(file_path, nrows=0)
        columns = df.columns.tolist()
        dtypes = {c: str(df[c].dtype) for c in columns}
    except Exception:
        columns = []
        dtypes = {}

    # 快速获取总行数
    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ('xlsx', 'xls'):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                ws = wb.active
                total_rows = ws.max_row - 1 if ws.max_row else 0
                wb.close()
            except Exception:
                total_rows = 0
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    total_rows = sum(1 for _ in f) - 1
            except Exception:
                with open(file_path, 'r', encoding='gbk') as f:
                    total_rows = sum(1 for _ in f) - 1
    except Exception:
        total_rows = 0

    return jsonify({
        'filename': unique_name,
        'original_name': filename,
        'columns': columns,
        'total_rows': total_rows,
        'total_columns': len(columns),
        'dtypes': dtypes,
        'message': '文件上传成功'
    })

@app.route('/api/preview/<filename>', methods=['GET'])
def preview_file(filename):
    """预览上传数据的前10行"""
    file_path = BASE_DIR / 'uploads' / secure_filename(filename)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    rows = int(request.args.get('rows', 10))
    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            df = read_csv_auto_encoding(file_path, nrows=rows)
        elif ext in ('xlsx', 'xls'):
            df = pd.read_excel(file_path, nrows=rows)
        else:
            df = read_csv_auto_encoding(file_path, nrows=rows)

        rows_data = [[None if pd.isnull(v) else v for v in row] for row in df.values]
        return jsonify({
            'filename': filename,
            'columns': df.columns.tolist(),
            'rows': rows_data,
            'shape': [len(df), len(df.columns)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# 数据预览与筛选 API（分页、多维度筛选、导出）
# ============================================================

def _read_data_file(file_path, ext=None):
    """读取数据文件为 DataFrame，自动检测编码和格式。"""
    if ext is None:
        ext = file_path.suffix[1:].lower()
    ext = ext.lstrip('.')
    if ext == 'csv':
        return read_csv_auto_encoding(file_path)
    elif ext in ('xlsx', 'xls'):
        return pd.read_excel(file_path)
    elif ext == 'txt':
        return read_csv_auto_encoding(file_path, sep='\t')
    else:
        return read_csv_auto_encoding(file_path)


def _df_to_rows(df):
    """DataFrame 转为前端行数据格式。"""
    return [[None if pd.isnull(v) else _safe_value(v) for v in row]
            for row in df.values.tolist()]


def _safe_value(v):
    """将 numpy 类型转为 Python 原生类型，确保 JSON 可序列化。"""
    import numpy as np
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='replace')
    return v


@app.route('/api/data/<filename>/rows', methods=['GET'])
def data_rows(filename):
    """分页返回数据行，支持排序。"""
    file_path = BASE_DIR / 'uploads' / secure_filename(filename)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    try:
        page = int(request.args.get('page', 0))
        page_size = int(request.args.get('page_size', 25))
        sort_col = request.args.get('sort_col', '')
        sort_dir = request.args.get('sort_dir', 'asc')

        df = _read_data_file(file_path)
        total_rows = len(df)
        columns = df.columns.tolist()
        dtypes = {c: str(df[c].dtype) for c in columns}

        if sort_col and sort_col in df.columns:
            ascending = sort_dir != 'desc'
            df = df.sort_values(by=sort_col, ascending=ascending,
                                na_position='last')

        start = page * page_size
        end = min(start + page_size, total_rows)
        df_slice = df.iloc[start:end]

        return jsonify({
            'page': page,
            'page_size': page_size,
            'total_rows': total_rows,
            'total_columns': len(columns),
            'columns': columns,
            'rows': _df_to_rows(df_slice),
            'dtypes': dtypes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/<filename>/filter', methods=['POST'])
def data_filter(filename):
    """对数据文件应用多维度筛选，返回分页结果。"""
    file_path = BASE_DIR / 'uploads' / secure_filename(filename)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    try:
        body = request.get_json(force=True)
        filters = body.get('filters', [])
        logic = body.get('logic', 'and')
        page = int(body.get('page', 0))
        page_size = int(body.get('page_size', 25))

        df = _read_data_file(file_path)
        total_count = len(df)
        columns = df.columns.tolist()

        if filters:
            mask = _build_filter_mask(df, filters, logic)
            df = df[mask]

        filtered_count = len(df)

        start = page * page_size
        end = min(start + page_size, filtered_count)
        df_slice = df.iloc[start:end]

        return jsonify({
            'filtered_count': filtered_count,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'columns': columns,
            'rows': _df_to_rows(df_slice)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _build_filter_mask(df, filters, logic='and'):
    """根据筛选条件构建布尔掩码。"""
    import numpy as np
    masks = []
    for f in filters:
        col = f.get('column', '')
        op = f.get('operator', 'eq')
        val = f.get('value', None)

        if col not in df.columns:
            continue

        series = df[col]

        if op == 'is_null':
            masks.append(series.isnull())
        elif op == 'is_not_null':
            masks.append(series.notnull())
        elif op == 'is_empty':
            masks.append(series.astype(str).str.strip().eq('') | series.isnull())
        elif op == 'eq':
            masks.append(series == val)
        elif op == 'neq':
            masks.append(series != val)
        elif op in ('gt', 'gte', 'lt', 'lte'):
            try:
                num_series = pd.to_numeric(series, errors='coerce')
                num_val = float(val)
                if op == 'gt':
                    masks.append(num_series > num_val)
                elif op == 'gte':
                    masks.append(num_series >= num_val)
                elif op == 'lt':
                    masks.append(num_series < num_val)
                else:
                    masks.append(num_series <= num_val)
            except (ValueError, TypeError):
                pass
        elif op == 'between':
            if isinstance(val, list) and len(val) >= 2:
                try:
                    num_series = pd.to_numeric(series, errors='coerce')
                    lo, hi = float(val[0]), float(val[1])
                    masks.append((num_series >= lo) & (num_series <= hi))
                except (ValueError, TypeError):
                    pass
        elif op == 'in':
            if isinstance(val, list):
                masks.append(series.isin(val))
        elif op == 'not_in':
            if isinstance(val, list):
                masks.append(~series.isin(val))
        elif op == 'contains':
            masks.append(series.astype(str).str.contains(
                str(val), case=False, na=False))
        elif op == 'not_contains':
            masks.append(~series.astype(str).str.contains(
                str(val), case=False, na=False))
        elif op == 'starts_with':
            masks.append(series.astype(str).str.startswith(
                str(val), na=False))
        elif op == 'ends_with':
            masks.append(series.astype(str).str.endswith(
                str(val), na=False))

    if not masks:
        return pd.Series([True] * len(df), index=df.index)

    if logic == 'or':
        result = masks[0]
        for m in masks[1:]:
            result = result | m
    else:
        result = masks[0]
        for m in masks[1:]:
            result = result & m

    return result.fillna(False)


@app.route('/api/data/<filename>/export', methods=['POST'])
def data_export(filename):
    """将筛选/列选择/重命名后的数据导出为新文件。"""
    file_path = BASE_DIR / 'uploads' / secure_filename(filename)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    try:
        body = request.get_json(force=True)
        filters = body.get('filters', [])
        logic = body.get('logic', 'and')
        selected_columns = body.get('columns', [])
        column_renames = body.get('column_renames', {})

        df = _read_data_file(file_path)

        if filters:
            mask = _build_filter_mask(df, filters, logic)
            df = df[mask]

        if selected_columns:
            available = [c for c in selected_columns if c in df.columns]
            if available:
                df = df[available]

        if column_renames:
            valid_renames = {k: v for k, v in column_renames.items()
                             if k in df.columns}
            if valid_renames:
                df.rename(columns=valid_renames, inplace=True)

        export_id = str(uuid.uuid4())[:8]
        orig_name = Path(filename).stem
        filtered_name = f'filtered_{export_id}_{orig_name}.csv'
        filtered_path = BASE_DIR / 'uploads' / filtered_name
        df.to_csv(filtered_path, index=False, encoding='utf-8')

        return jsonify({
            'filtered_filename': filtered_name,
            'filtered_rows': len(df),
            'filtered_columns': df.columns.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/<filename>/stats', methods=['GET'])
def data_stats(filename):
    """返回每列统计信息（类型、min/max、唯一值数等），驱动筛选器 UI。"""
    file_path = BASE_DIR / 'uploads' / secure_filename(filename)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    try:
        df = _read_data_file(file_path)
        stats = {}
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            is_numeric = pd.api.types.is_numeric_dtype(df[col])
            col_info = {
                'dtype': dtype_str,
                'unique': int(df[col].nunique()),
                'nulls': int(df[col].isnull().sum())
            }
            if is_numeric:
                col_info['min'] = _safe_value(df[col].min())
                col_info['max'] = _safe_value(df[col].max())
            else:
                sample = df[col].dropna().unique()[:20].tolist()
                col_info['sample_values'] = [_safe_value(v) for v in sample]
            stats[col] = col_info

        return jsonify({
            'filename': filename,
            'total_rows': len(df),
            'columns': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/column-values/<filename>', methods=['GET'])
def column_values(filename):
    """读取完整数据文件，返回每列的唯一值（供前端筛选）
       支持 ?filtered_filename=xxx 读取已筛选文件。"""
    filtered_name = request.args.get('filtered_filename', '')
    target = filtered_name if filtered_name else filename
    file_path = BASE_DIR / 'uploads' / secure_filename(target)
    if not file_path.exists():
        return jsonify({'error': '文件不存在'}), 404

    try:
        df = _read_data_file(file_path)

        columns = df.columns.tolist()
        total_rows = len(df)

        # 每列唯一值（最多返回 200 个，避免响应过大）
        col_values = {}
        for col in columns:
            try:
                uniq = df[col].dropna().unique().tolist()
                try:
                    uniq_sorted = sorted(uniq, key=lambda x: (x is None, x))
                except TypeError:
                    uniq_sorted = sorted([str(v) for v in uniq])
                truncated = len(uniq_sorted) > 200
                col_values[col] = {
                    'values': [_safe_value(v) if not pd.isnull(v) else None
                               for v in uniq_sorted[:200]],
                    'total_unique': len(uniq_sorted),
                    'truncated': truncated
                }
            except Exception:
                col_values[col] = {'values': [], 'total_unique': 0, 'truncated': False}

        return jsonify({
            'filename': target,
            'columns': columns,
            'column_values': col_values,
            'total_rows': total_rows
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/uploads', methods=['GET'])
def list_uploads():
    """列出所有上传的文件和执行文件夹"""
    upload_dir = BASE_DIR / 'uploads'
    items = []
    for entry in upload_dir.iterdir():
        if entry.is_file():
            items.append({
                'type': 'file',
                'filename': entry.name,
                'size': entry.stat().st_size,
                'modified': datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
            })
        elif entry.is_dir():
            sub_files = [f for f in entry.iterdir() if f.is_file()]
            items.append({
                'type': 'folder',
                'filename': entry.name,
                'file_count': len(sub_files),
                'modified': datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
            })
    items.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'items': items})

# ============================================================
# API：历史项目
# ============================================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """列出所有已执行的分析项目（按时间倒序）"""
    upload_dir = BASE_DIR / 'uploads'
    projects = []
    if upload_dir.exists():
        for entry in upload_dir.iterdir():
            if entry.is_dir():
                meta_path = entry / 'metadata.json'
                if meta_path.exists():
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        png_files = list(entry.glob('*.png'))
                        projects.append({
                            'folder_name': entry.name,
                            'script_name': meta.get('script_name', ''),
                            'script_language': meta.get('script_language', ''),
                            'script_description': meta.get('script_description', ''),
                            'status': meta.get('status', 'unknown'),
                            'created_at': meta.get('created_at', ''),
                            'finished_at': meta.get('finished_at', ''),
                            'output_url': meta.get('output_url', ''),
                            'has_image': len(png_files) > 0,
                            'modified': datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
                        })
                    except Exception:
                        pass
        projects.sort(key=lambda x: x.get('finished_at', x.get('created_at', '')), reverse=True)
    return jsonify({'projects': projects, 'total': len(projects)})

@app.route('/api/projects/<folder_name>', methods=['GET'])
def get_project(folder_name):
    """获取单个项目详情"""
    project_dir = BASE_DIR / 'uploads' / folder_name
    if not project_dir.exists() or not project_dir.is_dir():
        return jsonify({'error': '项目不存在'}), 404

    meta_path = project_dir / 'metadata.json'
    meta = {}
    if meta_path.exists():
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

    # 加载脚本的 @PARAM 声明，用于历史项目参数控件和重分析
    parsed_params = []
    script_id = meta.get('script_id', '')
    if script_id:
        script = find_script(script_id)
        if script:
            script_path = BASE_DIR / script['path']
            if script_path.exists():
                try:
                    content = script_path.read_text(encoding='utf-8')
                    parsed_params = parse_script_params(content)
                except Exception:
                    pass

    # 列出目录下所有文件
    files = []
    for f in project_dir.iterdir():
        if f.is_file():
            files.append({
                'filename': f.name,
                'size': f.stat().st_size,
                'url': f'/uploads/{folder_name}/{f.name}'
            })

    # 检查脚本直接生成的 PDF/JPG
    pdf_files = sorted(list(project_dir.glob('*.pdf')))
    jpg_files = sorted(list(project_dir.glob('*.jpg')) + list(project_dir.glob('*.jpeg')))

    result = {
        'folder_name': folder_name,
        'metadata': meta,
        'files': files,
        'parsed_params': parsed_params
    }
    if pdf_files:
        result['pdf_url'] = f'/uploads/{folder_name}/{pdf_files[0].name}'
    if jpg_files:
        result['jpg_url'] = f'/uploads/{folder_name}/{jpg_files[0].name}'

    # 加载已保存的 AI 分析
    analysis_path = project_dir / 'ai_analysis.json'
    if analysis_path.exists():
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                result['ai_analysis'] = json.load(f)
        except Exception:
            pass

    return jsonify(result)

@app.route('/api/projects/<folder_name>', methods=['DELETE'])
def delete_project(folder_name):
    """删除历史项目"""
    import shutil
    project_dir = BASE_DIR / 'uploads' / folder_name
    if not project_dir.exists():
        return jsonify({'error': '项目不存在'}), 404
    shutil.rmtree(str(project_dir))
    return jsonify({'message': f'项目 {folder_name} 已删除'})


@app.route('/api/projects', methods=['DELETE'])
def clear_all_projects():
    """清除全部历史项目 — 删除 uploads 下所有文件和子目录"""
    import shutil
    upload_dir = BASE_DIR / 'uploads'
    count = 0
    file_count = 0
    if upload_dir.exists():
        for entry in upload_dir.iterdir():
            if entry.is_dir():
                shutil.rmtree(str(entry))
                count += 1
            else:
                entry.unlink()
                file_count += 1
    return jsonify({'message': f'已清除 {count} 个历史项目目录和 {file_count} 个文件', 'count': count})

# ============================================================
# API：格式转换 (PNG → PDF / JPG)
# ============================================================

@app.route('/api/convert/<folder_name>/<fmt>', methods=['GET'])
def convert_image(folder_name, fmt):
    """将项目中的 PNG 转换为 PDF 或 JPG"""
    if fmt not in ('pdf', 'jpg'):
        return jsonify({'error': '不支持的格式，支持: pdf, jpg'}), 400

    project_dir = BASE_DIR / 'uploads' / folder_name
    if not project_dir.exists():
        return jsonify({'error': '项目不存在'}), 404

    # 查找 PNG 文件
    png_files = list(project_dir.glob('*.png'))
    if not png_files:
        return jsonify({'error': '项目中无 PNG 图片'}), 404

    png_path = png_files[0]

    try:
        from PIL import Image
        img = Image.open(png_path)

        if fmt == 'pdf':
            output_name = f'{png_path.stem}.pdf'
            output_path = project_dir / output_name
            if not output_path.exists():
                img = img.convert('RGB')
                img.save(str(output_path), 'PDF')
            return send_from_directory(str(project_dir), output_name,
                                       as_attachment=True,
                                       download_name=output_name)

        elif fmt == 'jpg':
            output_name = f'{png_path.stem}.jpg'
            output_path = project_dir / output_name
            if not output_path.exists():
                img = img.convert('RGB')
                img.save(str(output_path), 'JPEG', quality=95)
            return send_from_directory(str(project_dir), output_name,
                                       as_attachment=True,
                                       download_name=output_name)

    except ImportError:
        return jsonify({'error': 'Pillow 库未安装，无法转换格式'}), 500
    except Exception as e:
        return jsonify({'error': f'格式转换失败: {str(e)}'}), 500


# ============================================================
# AI 模型配置
# ============================================================

AI_MODELS = {
    'deepseek-v4-flash': {
        'base_url': 'https://api.deepseek.com',
        'api_key_env': 'DEEPSEEK_API_KEY',
        'model_id': 'deepseek-v4-flash',
        'label': 'DeepSeek V4 Flash',
        'provider': 'DeepSeek',
        'protocol': 'openai'
    },
    'mimo-v2.5': {
        'base_url': 'https://token-plan-cn.xiaomimimo.com/v1',
        'api_key_env': 'MINIMAX_API_KEY',
        'model_id': 'mimo-v2.5',
        'label': 'Mimo V2.5',
        'provider': 'Xiaomimo',
        'protocol': 'openai'
    }
}


def get_ai_model_config(model_name='mimo-v2.5'):
    """获取 AI 模型配置，未知模型回退到默认"""
    if model_name not in AI_MODELS:
        model_name = 'mimo-v2.5'
    config = AI_MODELS[model_name]
    api_key = os.environ.get(config['api_key_env'], '')
    return config, api_key


def ai_chat_completion(model_name, system_prompt, messages, temperature=0.3, max_tokens=4000):
    """统一 AI 聊天完成，支持 OpenAI 和 Anthropic 协议，返回 (text, error)"""
    config, api_key = get_ai_model_config(model_name)
    if not api_key:
        return None, f"未设置 {config['api_key_env']} 环境变量，无法使用 {config['label']}"

    protocol = config.get('protocol', 'openai')
    model_id = config['model_id']
    base_url = config['base_url'].rstrip('/')

    try:
        if protocol == 'anthropic':
            # 直接使用 httpx 调用，只发送 Authorization: Bearer 头
            import httpx

            # 提取用户消息内容
            user_content = ''
            for msg in messages:
                if msg.get('role') == 'user':
                    user_content = msg.get('content', '')
                    break
            if not user_content:
                return None, '未找到用户消息内容'

            payload = {
                "model": model_id,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "anthropic-version": "2023-06-01"
            }

            resp = httpx.post(
                f"{base_url}/messages",
                headers=headers,
                json=payload,
                timeout=300
            )
            if resp.status_code != 200:
                detail = resp.text[:500]
                return None, f"Anthropic API 错误 ({resp.status_code}): {detail}"

            result = resp.json()
            text = ''
            for block in result.get('content', []):
                if block.get('type') == 'text':
                    text += block.get('text', '')
            return text, None
        else:
            # OpenAI 协议
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content, None

    except ImportError as e:
        lib = 'httpx' if protocol == 'anthropic' else 'openai'
        return None, f"缺少 {lib} 库，请执行: pip install {lib}"
    except Exception as e:
        return None, str(e)


# ============================================================
# API：AI 模型列表
# ============================================================

@app.route('/api/ai/models', methods=['GET'])
def get_ai_models():
    """获取可用的 AI 模型列表及配置状态
    支持 scope 参数：
      - scope=image-analysis: 仅返回图片分析可用的模型（小米 Mimo）
      - scope=script-modify 或不传: 仅返回脚本修改可用的模型（DeepSeek）
    """
    scope = request.args.get('scope', 'script-modify')
    model_ids = []
    if scope == 'image-analysis':
        model_ids = ['mimo-v2.5']  # 图片分析只保留小米
    else:
        model_ids = ['deepseek-v4-flash']  # 其他功能只保留 DeepSeek

    models = []
    for key, config in AI_MODELS.items():
        if key not in model_ids:
            continue
        api_key = os.environ.get(config['api_key_env'], '')
        models.append({
            'id': key,
            'label': config['label'],
            'provider': config['provider'],
            'available': bool(api_key),
            'default': key == 'mimo-v2.5' if scope == 'image-analysis' else key == 'deepseek-v4-flash'
        })
    return jsonify({'models': models})


# ============================================================
# API：AI 修改脚本
# ============================================================

@app.route('/api/ai/modify', methods=['POST'])
def ai_modify_script():
    """使用 AI 修改脚本（支持多模型）"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    script_content = data.get('script_content', '')
    user_request = data.get('user_request', '')
    script_language = data.get('language', 'Python')
    model_name = data.get('model', 'deepseek-v4-flash')

    if not script_content:
        return jsonify({'error': '请输入脚本内容'}), 400
    if not user_request:
        return jsonify({'error': '请输入修改需求'}), 400

    system_prompt = f"""你是一个{script_language}数据可视化专家。
你的任务是根据用户需求修改绘图脚本。
规则：
1. 保持脚本结构和数据读取方式不变
2. 只修改用户明确要求的部分
3. 添加注释标记修改位置（# MODIFIED: 说明）
4. 返回完整可运行脚本，不要省略任何部分
5. 如果需求不明确，采用最合理的默认值"""

    modified_script, error = ai_chat_completion(model_name, system_prompt,
        [{"role": "user", "content": f"""原始脚本：
```{script_language.lower()}
{script_content}

修改需求：{user_request}

请返回修改后的完整脚本："""}],
        temperature=0.3, max_tokens=4000
    )
    if error:
        return jsonify({'error': error, 'hint': '请检查环境变量或模型配置'}), 503

    try:
        # 清理可能的 markdown 代码块标记
        if modified_script.startswith('```'):
            lines = modified_script.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            modified_script = '\n'.join(lines)

        # 生成 diff
        diff = difflib.HtmlDiff()
        diff_html = diff.make_table(
            script_content.splitlines(keepends=True),
            modified_script.splitlines(keepends=True),
            fromdesc='原始脚本',
            todesc='修改后脚本',
            context=True,
            numlines=3
        )

        explanation = "脚本已根据您的需求修改完成。请查看 diff 对比确认修改内容。"

        return jsonify({
            'modified_script': modified_script,
            'diff_html': diff_html,
            'explanation': explanation
        })

    except Exception as e:
        return jsonify({'error': f'AI 调用失败: {str(e)}'}), 500

@app.route('/api/ai/save', methods=['POST'])
def ai_save_script():
    """保存 AI 修改后的脚本为新脚本"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    script_id = data.get('script_id')
    new_content = data.get('content')
    new_id = data.get('new_id', '').strip()
    new_name = data.get('new_name', '').strip()

    if not script_id or not new_content:
        return jsonify({'error': '缺少必要参数'}), 400
    if not new_id:
        return jsonify({'error': '新脚本 ID 不能为空'}), 400
    if not new_name:
        return jsonify({'error': '新脚本名称不能为空'}), 400

    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404
    if find_script(new_id):
        return jsonify({'error': f'脚本 ID "{new_id}" 已存在'}), 409

    orig_path = BASE_DIR / script['path']
    ext = orig_path.suffix
    lang_dir = 'R' if script['language'] == 'R' else 'python'
    dest_dir = BASE_DIR / 'scripts' / lang_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_path = dest_dir / f'{new_id}{ext}'
    new_path.write_text(new_content, encoding='utf-8')

    new_script = {
        'id': new_id,
        'name': new_name,
        'language': script['language'],
        'path': f'scripts/{lang_dir}/{new_id}{ext}',
        'description': script.get('description', ''),
        'thumbnail': script.get('thumbnail', ''),
        'parameters': script.get('parameters', []),
        'input_format': script.get('input_format', 'csv'),
        'sample_data': script.get('sample_data', ''),
        'data_format': script.get('data_format', ''),
        'created_at': datetime.now().strftime('%Y-%m-%d'),
        'based_on': script_id
    }

    config = scripts_config
    config['scripts'].append(new_script)
    save_scripts_config(config)

    return jsonify({'message': '脚本已保存为新脚本', 'script': new_script}), 201

# ============================================================
# API：AI 数据驱动的脚本推荐
# ============================================================

@app.route('/api/ai/recommend', methods=['POST'])
def ai_recommend_script():
    """上传表格，AI 根据列名和前10行数据推荐/修改脚本"""
    script_id = request.form.get('script_id', '').strip()
    if not script_id:
        return jsonify({'error': '请提供脚本 ID'}), 400

    script = find_script(script_id)
    if not script:
        return jsonify({'error': '脚本不存在'}), 404

    # 读取脚本内容
    script_path = BASE_DIR / script['path']
    if not script_path.exists():
        return jsonify({'error': '脚本文件不存在'}), 404
    script_content = script_path.read_text(encoding='utf-8')

    # 处理数据文件
    use_uploaded = request.form.get('use_uploaded', '')
    if use_uploaded:
        data_path = BASE_DIR / 'uploads' / secure_filename(use_uploaded)
        if not data_path.exists():
            return jsonify({'error': f'已上传文件不存在: {use_uploaded}'}), 404
    elif 'data_file' in request.files:
        data_file = request.files['data_file']
        if data_file.filename == '':
            return jsonify({'error': '请上传数据文件'}), 400
        filename = secure_filename(data_file.filename)
        data_path = BASE_DIR / 'uploads' / f'_ai_rec_{filename}'
        data_file.save(str(data_path))
    else:
        return jsonify({'error': '请上传数据文件或指定已上传的文件名'}), 400

    # 处理列选择和重命名
    selected_columns = request.form.get('columns', '')
    if selected_columns:
        try:
            selected_columns = json.loads(selected_columns)
        except (json.JSONDecodeError, TypeError):
            selected_columns = []

    column_renames = request.form.get('column_renames', '')
    if column_renames:
        try:
            column_renames = json.loads(column_renames)
        except (json.JSONDecodeError, TypeError):
            column_renames = {}

    # 读取前10行数据
    try:
        ext = data_path.suffix.lower()
        if ext == '.csv':
            df = read_csv_auto_encoding(data_path, nrows=10)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(data_path, nrows=10)
        else:
            df = read_csv_auto_encoding(data_path, nrows=10)

        # 先过滤列（使用原始列名）
        if selected_columns:
            available_cols = [c for c in selected_columns if c in df.columns]
            if available_cols:
                df = df[available_cols]

        # 再重命名
        if column_renames:
            valid_renames = {k: v for k, v in column_renames.items() if k in df.columns}
            if valid_renames:
                df.rename(columns=valid_renames, inplace=True)

        columns = df.columns.tolist()
        rows_data = [[None if pd.isnull(v) else v for v in row] for row in df.values]
        shape = [len(df), len(df.columns)]

        # 构建数据摘要文本
        col_info = []
        for col in columns:
            sample_vals = df[col].dropna().head(5).tolist()
            col_info.append({
                'name': col,
                'dtype': str(df[col].dtype),
                'sample_values': [str(v) for v in sample_vals]
            })

        data_summary = f"表格形状: {shape[0]} 行 x {shape[1]} 列\n\n列信息:\n"
        for ci in col_info:
            samples = ', '.join(ci['sample_values'])
            data_summary += f"  - {ci['name']} (类型: {ci['dtype']}), 示例值: {samples}\n"

        # 前10行数据文本
        preview_text = f"前10行数据:\n{df.head(10).to_string(index=False)}\n"

    except Exception as e:
        return jsonify({'error': f'读取数据文件失败: {str(e)}'}), 500

    # 调用 AI
    model_name = request.form.get('model', 'deepseek-v4-flash')

    system_prompt = f"""你是一个{script['language']}数据可视化专家。
你的任务是根据用户上传的数据表格的列名和前10行数据，自动修改绘图脚本，使其适配用户的数据结构。

规则：
1. 分析数据的列名和示例值，理解每列数据的含义
2. 将脚本中的列名映射为用户数据中实际的列名
3. 保持脚本原有结构和绘图逻辑不变
4. 仅修改列名引用和与数据结构相关的部分
5. 使用 # MODIFIED: 注释标记所有修改位置
6. 返回完整的可运行脚本，不要省略任何部分
7. 如果无法确定映射关系，添加注释说明并保留原列名
8. 在脚本开头添加注释说明列名映射关系"""

    user_prompt = f"""脚本语言: {script['language']}
脚本名称: {script.get('name', script_id)}

数据列信息:
{data_summary}

{preview_text}

原始脚本:
```{script['language'].lower()}
{script_content}
```

请根据以上数据列名，修改脚本中的列名引用，使其能直接使用这个数据文件运行。
返回完整修改后的脚本。"""

    modified_script, error = ai_chat_completion(model_name, system_prompt,
        [{"role": "user", "content": user_prompt}],
        temperature=0.3, max_tokens=4000
    )
    if error:
        return jsonify({'error': error, 'hint': '请检查环境变量或模型配置'}), 503

    try:
        # 清理 markdown 代码块
        if modified_script.startswith('```'):
            lines = modified_script.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            modified_script = '\n'.join(lines)

        # 生成 diff
        diff = difflib.HtmlDiff()
        diff_html = diff.make_table(
            script_content.splitlines(keepends=True),
            modified_script.splitlines(keepends=True),
            fromdesc='原始脚本',
            todesc='AI 推荐脚本（已适配数据列名）',
            context=True,
            numlines=3
        )

        mapping_lines = [l for l in modified_script.split('\n') if l.strip().startswith('#') and ('列名' in l or '映射' in l or 'column' in l.lower())]
        explanation = '\n'.join(mapping_lines) if mapping_lines else 'AI 已根据上传数据的列名自动调整脚本。请查看代码对比确认修改。'

        return jsonify({
            'modified_script': modified_script,
            'diff_html': diff_html,
            'explanation': explanation,
            'preview': {
                'columns': columns,
                'rows': rows_data,
                'shape': shape
            }
        })

    except Exception as e:
        return jsonify({'error': f'AI 调用失败: {str(e)}'}), 500


@app.route('/api/ai/analyze-image', methods=['POST'])
def ai_analyze_image():
    """分析图表图片——直接发送 PNG 图片给多模态 AI，不上传脚本和数据
    默认使用 mimo-v2.5，返回结果中包含 model_used"""
    # 支持 JSON 和 multipart/form-data 两种请求方式
    if request.is_json:
        data = request.get_json()
        folder_name = data.get('folder_name', '')
        model_name = data.get('model', 'mimo-v2.5')
    else:
        folder_name = request.form.get('folder_name', '')
        model_name = request.form.get('model', 'mimo-v2.5')

    # 1. 读取图片 (优先级: folder_name > 上传文件)
    image_base64 = None

    if folder_name:
        run_dir = BASE_DIR / 'uploads' / folder_name
        png_files = sorted(run_dir.glob('*.png'))
        if not png_files:
            return jsonify({'error': f'在 "{folder_name}" 中未找到 PNG 图片'}), 404
        with open(png_files[0], 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

    if not image_base64 and 'image' in request.files:
        img_file = request.files['image']
        image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

    if not image_base64:
        return jsonify({'error': '未找到图片。请指定 folder_name 或上传图片文件'}), 400

    # 2. 构建多模态 prompt
    system_prompt = """你是一个专业的数据可视化分析师。请直接分析用户提供的图表图片。

请严格按照以下格式输出，用 [SECTION] 作为分隔标记：

[SECTION: 图表结果解读]

### 图表结果描述（可直接用于论文 / 报告）

用一段简洁专业的学术语言描述图表内容。必须包含以下要素：
- 图表类型及用途
- 各组/各类别的整体水平排序和差异
- 各组的具体数值特征（均值区间、数据范围、分布形态）
- 离散程度对比
- 偏态和异常值情况
- 整体结论

### 详细解读

**1. 图形元素含义**
- 逐一说明图表中各视觉元素代表的统计含义

**2. 核心对比**
- 按数值大小排列各组/各类别
- 每组给出：数值水平、均值/中位数、数据集中区间

**3. 数据分布与离散程度**
- 描述分布形态（对称/偏态/多峰）
- 对比各组离散度

**4. 集中趋势**
- 均值与中位数的关系
- 有无极端值或异常值

**5. 核心结论**
- 2-4条简洁结论

[SECTION: 图表改进建议]

从图表制作的角度，给出具体的改进建议。每条建议包含：
- **改进方向**：要解决什么问题
- **具体话术**：可直接用于提示脚本修改的自然语言描述
- **预期效果**：改进后的效果

至少给出 3 条改进建议。"""

    user_prompt = "请分析这张统计图表图片，给出结果解读和改进建议。"

    # 3. 构造多模态消息（文字 + 图片）
    vision_messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
        ]
    }]

    try:
        ai_text, error = ai_chat_completion(
            model_name, system_prompt, vision_messages,
            temperature=0.3, max_tokens=4000
        )
        if error:
            raise Exception(error)

        # 4. 按 SECTION 标记拆分
        interpretation = ''
        suggestions = ''
        parts = ai_text.split('[SECTION: 图表改进建议]')
        if len(parts) >= 2:
            interpretation = parts[0].replace('[SECTION: 图表结果解读]', '').strip()
            suggestions = parts[1].strip()
        else:
            parts = ai_text.split('[SECTION:')
            for p in parts:
                p = p.strip()
                if p.startswith('图表结果解读]'):
                    interpretation = p.replace('图表结果解读]', '').strip()
                elif p.startswith('图表改进建议]'):
                    suggestions = p.replace('图表改进建议]', '').strip()
            if not interpretation:
                interpretation = ai_text

        # 5. 保存分析结果到项目目录
        if folder_name:
            try:
                run_dir = BASE_DIR / 'uploads' / folder_name
                analysis_path = run_dir / 'ai_analysis.json'
                analysis_data = {
                    'interpretation': interpretation,
                    'suggestions': suggestions,
                    'model_used': model_name,
                    'analyzed_at': datetime.now().isoformat()
                }
                with open(analysis_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # 6. 返回结果，包含 model_used
        return jsonify({
            'interpretation': interpretation,
            'suggestions': suggestions,
            'model_used': model_name
        })

    except Exception as e:
        return jsonify({'error': f'AI 图像分析失败: {str(e)}'}), 500


# ============================================================
# API：使用建议 & 脚本推荐
# ============================================================

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """获取所有使用建议"""
    suggestions = load_suggestions()
    return jsonify({'suggestions': suggestions, 'total': len(suggestions)})


@app.route('/api/suggestions', methods=['POST'])
def add_suggestion():
    """提交使用建议"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请填写建议内容'}), 400
    script_id = data.get('script_id', '')
    script_name = data.get('script_name', '')
    content = data.get('content', '')
    if not content.strip():
        return jsonify({'error': '建议内容不能为空'}), 400
    suggestions = load_suggestions()
    suggestion = {
        'id': str(uuid.uuid4())[:8],
        'script_id': script_id,
        'script_name': script_name,
        'content': content.strip(),
        'created_at': datetime.now().isoformat()
    }
    suggestions.insert(0, suggestion)
    save_suggestions(suggestions)
    return jsonify({'message': '建议已提交', 'suggestion': suggestion}), 201


@app.route('/api/suggestions/<suggestion_id>', methods=['DELETE'])
def delete_suggestion(suggestion_id):
    """删除建议"""
    suggestions = load_suggestions()
    suggestions = [s for s in suggestions if s['id'] != suggestion_id]
    save_suggestions(suggestions)
    return jsonify({'message': '建议已删除'})


@app.route('/api/data-requirements', methods=['GET'])
def get_data_requirements():
    """获取所有脚本的数据要求（从 README 解析）"""
    reqs = init_requirements_cache()
    return jsonify({'requirements': reqs, 'total': len(reqs)})


@app.route('/api/data-requirements/columns', methods=['GET'])
def get_unique_columns():
    """获取所有 README 中唯一的列名，供推荐页选择"""
    reqs = init_requirements_cache()
    seen = {}
    for req in reqs:
        for col in req['columns']:
            name = col['name'].strip()
            if name not in seen:
                seen[name] = {'name': name, 'meaning': col['meaning'], 'type': col['type']}
    columns = sorted(seen.values(), key=lambda x: x['name'])
    return jsonify({'columns': columns, 'total': len(columns)})


# 列名别名映射（中英文，帮助模糊匹配用户数据列名到 README 标准列名）
COLUMN_ALIASES = {
    'group': ['treatment', 'condition', 'type', 'class', 'species', 'strain',
              'cohort', 'arm', 'phenotype', 'cluster', 'batch', 'dose_group',
              'tissue', 'region', 'organ', 'cell_type', 'genotype',
              '分组', '组别', '处理', '类别', '类型', '种属', '物种', '组织', '细胞类型',
              '性别', '年龄组'],
    'value': ['expression', 'measurement', 'count', 'score', 'intensity', 'level',
              'abundance', 'concentration', 'quantity', 'amount', 'rate', 'ratio',
              'fold_change', 'signal', 'reading', 'assay',
              '值', '数值', '表达量', '测量值', '浓度', '含量', '丰度', '得分', '评分',
              '强度', '水平', '比值', '倍数', '风险', '风险评分', '等级', '评估结果'],
    'category': ['label', 'name', 'id', 'identifier', 'kind', 'species_name',
                 'gene_name', 'sample_id', 'item', 'product', 'department',
                 '名称', '标签', '编号', '标识', '类别名', '项目', '产品'],
    'x': ['x_axis', 'xaxis', 'time', 'dose', 'concentration', 'x_val', 'x_value',
          'pos_x', 'coordinate_x', 'x_coord',
          'x轴', '时间', '剂量', '浓度', '坐标x'],
    'y': ['y_axis', 'yaxis', 'response', 'output', 'y_val', 'y_value',
          'pos_y', 'coordinate_y', 'y_coord',
          'y轴', '响应', '结果', '输出', '坐标y'],
    'gene': ['gene_id', 'gene_symbol', 'symbol', 'ensembl', 'entrez', 'probe',
             '基因', '基因名', '基因符号'],
    'sample': ['sample_id', 'sample_name', 'specimen', 'patient_id', 'subject',
               '样本', '样本编号', '样品', '患者', '受试者', '病例', '样本号'],

    'size': ['point_size', 'dot_size', 'bubble_size', 'radius', 'diameter',
             '大小', '尺寸', '半径', '直径'],
    'weight': ['mass', 'body_weight', 'load', 'importance',
               '体重', '重量', '质量', '权重'],
    'label': ['tag', 'annotation', 'marker', 'note', 'display_name',
              '标注', '注释', '标记'],
    'log2FC': ['log2fc', 'logfc', 'foldchange', 'fc', 'log2_fold_change', 'lfc',
               '差异倍数', '倍数变化'],
    'pvalue': ['p_value', 'pval', 'p.val', 'p', 'significance', 'fdr', 'padj', 'qvalue',
               'p值', '显著性', '矫正p值', 'q值'],
    'time': ['timestamp', 'date', 'hour', 'day', 'week', 'month', 'year', 'duration',
             '时间', '日期', '年份', '月份', '天数'],
    'subgroup': ['sub_group', 'subtype', 'subcategory', 'subset',
                 '亚组', '子组', '子类'],
    'variable': ['var', 'feature', 'parameter', 'attribute', 'predictor', 'factor',
                 '变量', '特征', '参数', '因素', '指标'],
    'sd': ['stddev', 'stdev', 'standard_deviation', 'error', 'se', 'sem',
           '标准差', '标准误', '误差'],
}
_PREPARED_ALIASES = None


def _get_alias_map():
    """构建小写化的别名反向映射: {alias_lower: canonical_name}"""
    global _PREPARED_ALIASES
    if _PREPARED_ALIASES is None:
        _PREPARED_ALIASES = {}
        for canonical, aliases in COLUMN_ALIASES.items():
            _PREPARED_ALIASES[canonical.lower()] = canonical
            for a in aliases:
                _PREPARED_ALIASES[a.lower()] = canonical
    return _PREPARED_ALIASES


def _fuzzy_match(user_col, candidates, threshold=0.6):
    """返回 candidates 中与 user_col 最匹配的项及分数，无匹配返回 (None, 0)"""
    from difflib import SequenceMatcher
    alias_map = _get_alias_map()
    best_score = 0
    best_match = None

    # 1. 精确匹配（含别名）
    if user_col in alias_map:
        canonical = alias_map[user_col]
        if canonical in candidates:
            return canonical, 1.0

    for cand in candidates:
        # 精确相等
        if user_col == cand.lower():
            return cand, 1.0
        # 子串包含（要求较短串长度 >= 较长串的 50%，避免单字母误匹配）
        shorter = min(len(user_col), len(cand))
        longer = max(len(user_col), len(cand))
        if (user_col in cand.lower() or cand.lower() in user_col) and shorter >= longer * 0.5:
            score = 0.85
            if score > best_score:
                best_score = score
                best_match = cand
        # difflib 相似度（要求 >= 0.65）
        ratio = SequenceMatcher(None, user_col, cand.lower()).ratio()
        if ratio >= 0.65 and ratio > best_score:
            best_score = ratio
            best_match = cand

    # 用别名再试一次 best_match 的 canonical
    if best_match and best_score < 0.85:
        alias_canonical = alias_map.get(user_col, '')
        if alias_canonical and alias_canonical in candidates:
            return alias_canonical, 0.9

    if best_score >= threshold:
        return best_match, best_score
    return None, 0


@app.route('/api/recommend', methods=['POST'])
def recommend_scripts():
    """根据用户数据列名模糊匹配推荐脚本"""
    data = request.get_json()
    if not data or 'columns' not in data:
        return jsonify({'error': '请提供数据列名'}), 400

    user_columns_raw = [c.strip().lower() for c in data['columns'] if c.strip()]
    if not user_columns_raw:
        return jsonify({'error': '请提供至少一个列名'}), 400

    # 从中文字段名中提取英文（括号内），如 "尿嘧啶（Uracil）" → "uracil"
    english_extras = []
    for col in list(user_columns_raw):
        m = re.findall(r'[（(]([a-zA-Z][a-zA-Z0-9\s\-_.]+)[）)]', col)
        for eng in m:
            eng_clean = eng.strip().lower()
            if eng_clean and eng_clean not in user_columns_raw:
                english_extras.append(eng_clean)
    user_columns_raw.extend(english_extras)

    reqs = init_requirements_cache()
    matches = []
    alias_map = _get_alias_map()

    for req in reqs:
        req_required = set()
        req_optional = set()
        req_col_map = {}  # canonical_lower -> original display name
        for col in req['columns']:
            col_name = col['name'].strip()
            col_lower = col_name.lower()
            req_col_map[col_lower] = col_name
            if '(可选)' in col['name'] or '(可选)' in col['meaning']:
                req_optional.add(col_lower)
            else:
                req_required.add(col_lower)

        total_required = len(req_required)
        if total_required == 0:
            continue

        # 对每个 README 要求的列名，找用户列名中的最佳匹配
        matched_req = {}  # req_col -> (user_col, score)
        used_user_cols = set()

        for req_col in req_required:
            best_score = 0
            best_user = None
            for user_col in user_columns_raw:
                if user_col in used_user_cols:
                    continue
                match, score = _fuzzy_match(user_col, {req_col})
                if match and score > best_score:
                    best_score = score
                    best_user = user_col
            if best_user:
                matched_req[req_col] = (best_user, best_score)
                used_user_cols.add(best_user)

        # 检查可选的
        matched_opt = {}
        for req_col in req_optional:
            for user_col in user_columns_raw:
                if user_col in used_user_cols:
                    continue
                match, score = _fuzzy_match(user_col, {req_col})
                if match and score >= 0.7:
                    matched_opt[req_col] = (user_col, score)
                    used_user_cols.add(user_col)
                    break

        matched_required_count = len(matched_req)
        score = matched_required_count / total_required if total_required > 0 else 0

        # 至少匹配了一个必填列才纳入推荐
        if matched_required_count == 0:
            continue

        matches.append({
            'folder': req['folder'],
            'title': req['title'],
            'columns': req['columns'],
            'score': score,
            'matched_required': [{'req': req_col_map.get(k, k), 'user': v[0], 'score': round(v[1], 2)}
                                 for k, v in matched_req.items()],
            'matched_optional': [{'req': req_col_map.get(k, k), 'user': v[0], 'score': round(v[1], 2)}
                                 for k, v in matched_opt.items()],
            'missing': [req_col_map.get(k, k) for k in (req_required - set(matched_req.keys()))],
            'match_ratio': f'{matched_required_count}/{total_required}'
        })

    # 按匹配比例降序，同比例按可选匹配数降序
    matches.sort(key=lambda x: (x['score'], len(x['matched_optional'])), reverse=True)

    # 分类
    excellent = [m for m in matches if m['score'] == 1.0]
    good = [m for m in matches if 0.5 <= m['score'] < 1.0]
    weak = [m for m in matches if 0 < m['score'] < 0.5]

    return jsonify({
        'recommendations': matches,
        'excellent': excellent,
        'good': good,
        'weak': weak,
        'total': len(matches),
        'user_columns': user_columns_raw
    })


# ============================================================
# 文件服务
# ============================================================

@app.route('/outputs/<filename>')
def serve_output(filename):
    """提供输出图表文件"""
    return send_from_directory(str(BASE_DIR / 'outputs'), filename)

@app.route('/uploads/<path:filepath>')
def serve_upload(filepath):
    """提供上传文件及执行结果（支持子目录）"""
    return send_from_directory(str(BASE_DIR / 'uploads'), filepath)

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """提供缩略图文件"""
    return send_from_directory(str(BASE_DIR / 'thumbnails'), filename)

@app.route('/sample_data/<filename>')
def serve_sample_data(filename):
    """提供示例数据文件"""
    return send_from_directory(str(BASE_DIR / 'sample_data'), filename)

@app.route('/api/sample-data', methods=['GET'])
def list_sample_data():
    """列出所有示例数据文件"""
    sample_dir = BASE_DIR / 'sample_data'
    files = []
    if sample_dir.exists():
        for f in sample_dir.iterdir():
            if f.is_file() and f.suffix in ('.csv', '.xlsx', '.txt'):
                files.append({
                    'filename': f.name,
                    'size': f.stat().st_size
                })
    return jsonify({'files': files})

# ============================================================
# 错误处理
# ============================================================

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件大小超过限制（最大50MB）'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': '页面不存在'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': '服务器内部错误'}), 500


# ============================================================
# API：全局颜色库管理
# ============================================================

def load_colors_config():
    config_path = BASE_DIR / 'config' / 'colors.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'active_series': 'npg', 'series': {}, 'custom': []}


def save_colors_config(config):
    config_path = BASE_DIR / 'config' / 'colors.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


@app.route('/api/colors', methods=['GET'])
def get_colors():
    """获取全局颜色配置"""
    config = load_colors_config()
    return jsonify(config)


@app.route('/api/colors/active', methods=['POST'])
def set_active_color_series():
    """设置当前激活的颜色系列"""
    data = request.get_json()
    series_id = data.get('series_id', '')
    config = load_colors_config()
    if series_id not in config.get('series', {}) and series_id != 'custom':
        return jsonify({'error': '无效的颜色系列ID'}), 400
    config['active_series'] = series_id
    save_colors_config(config)
    return jsonify({'message': '已切换颜色系列', 'active_series': series_id})


@app.route('/api/colors/custom', methods=['POST'])
def save_custom_colors():
    """保存自定义颜色系列"""
    data = request.get_json()
    colors = data.get('colors', [])
    name = data.get('name', '自定义配色').strip()
    if len(colors) < 2:
        return jsonify({'error': '至少需要2个颜色'}), 400
    config = load_colors_config()
    custom_entry = {
        'id': str(uuid.uuid4())[:8],
        'name': name,
        'colors': colors,
        'created_at': datetime.now().isoformat()
    }
    config.setdefault('custom', []).append(custom_entry)
    save_colors_config(config)
    return jsonify({'message': '自定义配色已保存', 'custom': custom_entry}), 201


@app.route('/api/colors/custom/<custom_id>', methods=['DELETE'])
def delete_custom_colors(custom_id):
    """删除自定义颜色系列"""
    config = load_colors_config()
    config['custom'] = [c for c in config.get('custom', []) if c['id'] != custom_id]
    save_colors_config(config)
    return jsonify({'message': '已删除'})


def get_active_colors():
    """获取当前激活的颜色列表（供脚本执行时使用）"""
    config = load_colors_config()
    active = config.get('active_series', 'npg')
    if active == 'custom' and config.get('custom'):
        return config['custom'][-1].get('colors', [])
    return config.get('series', {}).get(active, {}).get('colors', ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4', '#91D1C2', '#DC0000'])


# ============================================================
# 应用启动
# ============================================================

if __name__ == '__main__':
    for folder in ['uploads', 'thumbnails', 'scripts/R', 'scripts/python', 'scripts/data_process', 'config']:
        (BASE_DIR / folder).mkdir(parents=True, exist_ok=True)

    # ---- 启动环境诊断 ----
    print('=' * 60)
    print('  Script Hub - 交互式数据可视化脚本管理平台')
    print('=' * 60)
    print(f'  Python: {sys.executable}')
    print(f'  工作目录: {BASE_DIR / "uploads"}')

    # 验证脚本依赖的关键模块
    required_modules = {
        'matplotlib': 'matplotlib',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'seaborn': 'seaborn',
        'scipy': 'scipy',
        'PIL': 'pillow',
    }
    missing = []
    for mod, pkg in required_modules.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(f'{mod} (pip install {pkg})')
    if missing:
        print('  [WARN] 缺少以下模块:')
        for m in missing:
            print(f'         - {m}')
    else:
        print(f'  关键模块: 全部就绪 ({len(required_modules)} 项)')
    print('-' * 60)

    # 预热 README 数据要求缓存
    reqs = init_requirements_cache()
    print(f'  README 数据要求: {len(reqs)} 个脚本')

    lan_ip = get_lan_ip()
    print(f'  本地访问: http://127.0.0.1:5000')
    if lan_ip:
        print(f'  LAN  访问: http://{lan_ip}:5000')

    # ---- 端口冲突检测：占用者为本应用旧实例时友好提示并退出，其他程序占用时才警告 ----
    # 仅在主进程执行（WERKZEUG_RUN_MAIN=true 的是 debug 重载子进程），
    # 避免 reloader 自动重启时新旧子进程短暂重叠被误判为“重复启动”。
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        port = 5000
        try:
            _probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _probe.bind(('0.0.0.0', port))
            _probe.close()
            print(f'  端口 {port}: 空闲')
        except OSError:
            owner = find_port_owner(port)
            is_self = False
            if owner:
                # 命令行包含 app.py 的 python 进程，视为本应用自身的旧实例
                is_self = 'app.py' in get_process_cmdline(owner[0]).lower()
            if is_self:
                print('=' * 60)
                print(f'  本应用已在运行 (PID={owner[0]})，无需重复启动。')
                print(f'  请直接访问: http://127.0.0.1:5000')
                print(f'  如需重启: 先关闭旧窗口，或执行  taskkill /PID {owner[0]} /F  后重新 start.bat')
                print('=' * 60)
                sys.exit(0)
            else:
                print('=' * 60)
                print(f'  [错误] 端口 {port} 已被其他程序占用，无法启动本应用！')
                if owner:
                    print(f'         占用进程: PID={owner[0]}  {owner[1]}')
                    print(f'         修复: 执行  netstat -ano | findstr :{port}  确认占用者后，taskkill /PID {owner[0]} /F')
                else:
                    print(f'         修复: 执行  netstat -ano | findstr :{port}  找到占用 PID 后 taskkill /PID <PID> /F')
                print(f'         或修改 app.py 末尾的 port = {port} 更换端口。')
                print('=' * 60)
                sys.exit(1)
        print('=' * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
