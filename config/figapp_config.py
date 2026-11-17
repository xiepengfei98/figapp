#!/usr/bin/env python3
"""
FigApp 全局配置 — 颜色库 + 中文字体
脚本自动加载，无需手动调用。
"""

import os, sys, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ==================== 中文字体自动检测 ====================

def _setup_chinese_font():
    """自动检测并设置中文字体，解决白框问题"""
    font_family = 'sans-serif'
    candidate_fonts = []
    if sys.platform == 'win32':
        candidate_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong']
    elif sys.platform == 'darwin':
        candidate_fonts = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
    else:
        candidate_fonts = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
                           'Noto Sans SC', 'SimHei', 'Droid Sans Fallback']

    available = {f.name for f in fm.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in available:
            font_family = font_name
            break

    plt.rcParams['font.family'] = font_family
    plt.rcParams['font.sans-serif'] = [font_family] + plt.rcParams.get('font.sans-serif', [])
    plt.rcParams['axes.unicode_minus'] = False
    return font_family


FONT_FAMILY = _setup_chinese_font()

# ==================== 颜色配置加载 ====================

def _find_color_config():
    """查找颜色配置文件（优先 color_config.json 运行时注入，其次 colors.json 全局库）"""
    fnames = ['color_config.json', 'colors.json']
    paths = [os.environ.get('FIGAPP_COLOR_CONFIG', '')]
    for fn in fnames:
        paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), fn))
        paths.append(os.path.join(os.getcwd(), fn))
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def load_colors(series_name=None):
    """
    加载全局颜色列表，返回 list[str]
    series_name: 配色方案名称（如 'aaas', 'npg'），None 则用活跃方案
    """
    path = _find_color_config()
    if path:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 如果指定了 series_name，从中查找
            if series_name and 'series' in config:
                if series_name in config['series']:
                    colors = config['series'][series_name].get('colors', [])
                    if colors:
                        return colors
            # 否则用活跃方案
            else:
                active_series = config.get('active_series', 'aaas')
                if 'series' in config and active_series in config['series']:
                    colors = config['series'][active_series].get('colors', [])
                    if colors:
                        return colors
                # 兼容旧格式（直接 'colors' 键）
                colors = config.get('colors', [])
                if colors:
                    return colors
    # fallback - NPG 配色
    return ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4', '#91D1C2', '#DC0000']


def get_group_colors(groups, series_name=None):
    """
    根据分组列表返回颜色映射 dict[str, str]
    groups: list or pd.Series of group names (from data)
    series_name: 配色方案名称（可选）
    返回: {group_name: color_hex}
    
    用法：
        import pandas as pd
        data = pd.read_csv('data.csv')
        groups = data['group'].unique().tolist()
        color_map = get_group_colors(groups)
        # 或使用特定配色方案
        color_map = get_group_colors(groups, series_name='nejm')
    """
    palette = load_colors(series_name)
    if hasattr(groups, 'tolist'):  # pandas Series
        groups = groups.tolist()
    unique_groups = list(dict.fromkeys(groups)) if isinstance(groups, list) else list(set(groups))
    return {g: palette[i % len(palette)] for i, g in enumerate(unique_groups)}


def get_palette(n_colors=8, series_name=None):
    """
    获取指定长度的调色板
    n_colors: 需要的颜色数量
    series_name: 配色方案名称（可选）
    返回: list of color hex strings，循环获取超过长度的颜色
    """
    palette = load_colors(series_name)
    return [palette[i % len(palette)] for i in range(n_colors)]


GLOBAL_PALETTE = load_colors()
