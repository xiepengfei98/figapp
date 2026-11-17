# FigApp · 交互式数据可视化脚本管理平台

<div align="center">

**VizScript Hub** — 基于 Flask 的轻量级科研绘图脚本管理平台

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

一个可在本地或局域网运行的 Web 平台，用于**管理、执行和 AI 辅助修改** R / Python 数据可视化脚本。内置 200+ 科研绘图脚本，支持 CSV / Excel / TXT 数据上传、异步执行、结果预览与脚本热加载。

> ⚠️ **隐私提示**：本平台默认在本机运行，上传的数据仅保存在本地 `uploads/` 目录。该目录已被 `.gitignore` 排除，**不会**被提交到仓库。请勿将包含真实受试者信息或敏感健康数据的数据文件提交到任何公开仓库。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [AI 功能配置（可选）](#ai-功能配置可选)
- [项目结构](#项目结构)
- [API 接口](#api-接口)
- [添加自定义脚本](#添加自定义脚本)
- [部署说明](#部署说明)
- [安全说明](#安全说明)
- [许可证](#许可证)

---

## 功能特性

- **脚本管理**：浏览 / 添加 / 删除 R 与 Python 可视化脚本，支持 200+ 内置科研绘图模板
- **数据上传**：支持 CSV、Excel（xlsx/xls）、TXT，拖拽上传，单文件上限 50 MB
- **脚本执行**：后台异步执行，实时状态轮询，自动生成 PDF/PNG 图表与日志
- **结果展示**：在线预览生成的图表与数据表，支持按组配色方案
- **AI 助手**：通过兼容 OpenAI 接口的模型智能修改脚本代码、分析图像（可选）
- **热加载**：脚本注册中心 `config/scripts.json` 支持热加载，无需重启服务
- **数据预处理**：内置长表 / 宽表互转等数据处理工具

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.9+ · Flask 3.0 |
| 前端 | Bootstrap 5 · 原生 JavaScript（本地 vendor，无需外网） |
| 绘图 | Matplotlib · Seaborn · Plotly · ggplot2（R） |
| 数据处理 | pandas · openpyxl |
| AI（可选） | DeepSeek API / MiniMax 兼容端点（OpenAI 兼容格式） |
| 脚本执行 | `subprocess` 调用 `Rscript` / `python` |

## 快速开始

### 1. 环境要求

- Python 3.9+
- R（**可选**，仅运行 R 脚本时需要），建议安装 `ggplot2` 等包

### 2. 安装

**Windows（推荐）**：双击运行 `setup.bat`，自动创建虚拟环境并安装依赖。

**手动安装**：

```bash
python -m venv venv
# Windows
venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS / Linux
source venv/bin/activate && pip install -r requirements.txt
```

### 3. 启动

**Windows**：双击运行 `start.bat`。

**手动启动**：

```bash
# Windows
venv\Scripts\python.exe app.py
# macOS / Linux
python app.py
```

浏览器访问 <http://127.0.0.1:5000>。

## AI 功能配置（可选）

AI 助手为**可选功能**，不配置也能正常使用所有绘图功能。所有密钥均通过**环境变量**提供，**切勿**写入脚本或提交到仓库。

```bash
# Windows 命令提示符（当前会话）
set DEEPSEEK_API_KEY=你的密钥
set MINIMAX_API_KEY=你的令牌

# Windows PowerShell（当前会话）
$env:DEEPSEEK_API_KEY="你的密钥"
$env:MINIMAX_API_KEY="你的令牌"

# macOS / Linux
export DEEPSEEK_API_KEY=你的密钥
export MINIMAX_API_KEY=你的令牌
```

也可将上述变量永久写入操作系统环境变量。参考 [`.env.example`](.env.example) 了解所需变量清单（该文件仅为模板，**不要**把真实密钥填进被提交的任何文件）。

| 变量 | 用途 | 是否必需 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | AI 脚本修改助手 | 否 |
| `MINIMAX_API_KEY` | 图像分析 | 否 |

## 项目结构

```
figapp/
├── app.py                      # Flask 主应用与全部 API
├── requirements.txt            # Python 依赖
├── setup.bat / start.bat       # Windows 一键安装 / 启动脚本
├── .env.example                # 环境变量模板（无真实密钥）
├── config/
│   ├── scripts.json            # 脚本注册中心（200+ 脚本元数据）
│   ├── colors.json             # 全局配色方案库
│   └── figapp_config.py / .R   # 脚本运行时配置（字体 / 配色）
├── scripts/
│   ├── python/                 # Python 绘图脚本（200+）
│   ├── R/                      # R 绘图脚本
│   ├── data_process/           # 数据预处理脚本（长宽表互转）
│   └── templates/              # 新脚本模板
├── static/
│   ├── css/                    # 自定义样式
│   ├── js/                     # 前端交互逻辑
│   └── vendor/                 # 本地第三方库（Bootstrap / Plotly，离线可用）
├── templates/index.html        # 单页应用模板
├── sample_data/                # 示例数据（可安全公开）
├── uploads/                    # 用户上传数据（运行时生成，不提交）[.gitkeep]
├── outputs/                    # 生成的图表（运行时生成，不提交）[.gitkeep]
└── thumbnails/                 # 脚本缩略图（运行时生成，不提交）[.gitkeep]
```

> `uploads/`、`outputs/`、`thumbnails/` 中的历史文件均为本地运行产物，**未纳入版本控制**，克隆仓库后由程序按需重建。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scripts` | 获取脚本列表 |
| POST | `/api/scripts/add` | 添加脚本 |
| DELETE | `/api/scripts/<id>` | 删除脚本 |
| POST | `/api/run/<id>` | 执行脚本 |
| GET | `/api/status/<task_id>` | 查询任务状态 |
| POST | `/api/upload` | 上传数据文件 |
| GET | `/api/preview/<filename>` | 预览数据 |
| POST | `/api/ai/modify` | AI 修改脚本 |

## 添加自定义脚本

1. 将 `.R` 或 `.py` 文件放入 `scripts/R/` 或 `scripts/python/`。
2. 在平台上点击「添加新脚本」填写信息，或直接编辑 `config/scripts.json`。
3. 脚本接收两个命令行参数：`<数据文件路径> <输出文件路径>`。
4. 如需 AI 功能，参考 `scripts/templates/` 下的模板编写脚本头注释。

## 部署说明

将本仓库克隆到目标机器后：

1. 运行 `setup.bat` 创建虚拟环境并安装依赖。
2. 如需运行 R 脚本，安装 R 及必要包。
3. 运行 `start.bat` 启动服务，访问 <http://127.0.0.1:5000>。
4. **局域网访问**：服务默认绑定 `0.0.0.0:5000`，启动时会显示本机 LAN IP。请将示例中的 `<LAN-IP>` 替换为你自己的局域网地址，同一网络内的设备即可访问。

> 🔒 局域网模式下任何同网段设备都可访问本服务及上传的数据，请仅在可信网络中使用，或自行增加身份认证。

## 安全说明

- **密钥**：所有 API 密钥仅通过环境变量传入；任何提交到仓库的密钥都应视为已泄露并立即轮换。
- **数据**：`uploads/`、`outputs/`、`thumbnails/` 已加入 `.gitignore`，用于隔离可能敏感的研究数据。发布前请再次确认没有数据文件被强制添加。
- **调试模式**：`app.py` 以 Flask `debug=True` 启动，仅限本地开发使用。**生产环境请务必关闭 debug 模式**，并置于反向代理之后。
- **访问控制**：当前版本不含用户登录鉴权，请勿直接暴露到公网。

## 许可证

本项目采用 [MIT License](LICENSE) 开源，详见 `LICENSE` 文件。

---

<div align="center">

如果本项目对你有帮助，欢迎 Star ⭐

</div>
