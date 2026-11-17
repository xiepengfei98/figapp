#!/usr/bin/env Rscript
#
# FigApp 全局配置 — 颜色库 + 中文字体
# 在脚本中 source 此文件即可使用
#

# ==================== 中文字体自动检测 ====================

.setup_chinese_font <- function() {
  font_family <- "sans"
  if (.Platform$OS.type == "windows") {
    candidates <- c("Microsoft YaHei", "SimHei", "SimSun", "KaiTi", "FangSong")
    # Windows: 使用 windowsFonts / extrafont
    for (f in candidates) {
      if (f %in% names(grDevices::windowsFonts()) || f %in% sysfonts::font_families()) {
        font_family <- f
        break
      }
    }
    # 兜底: 尝试 showtext
    if (requireNamespace("showtext", quietly = TRUE)) {
      showtext::showtext_auto(enable = TRUE)
    }
  } else if (Sys.info()["sysname"] == "Darwin") {
    candidates <- c("PingFang SC", "Heiti SC", "STHeiti")
    for (f in candidates) {
      if (f %in% sysfonts::font_families()) {
        font_family <- f
        break
      }
    }
    if (requireNamespace("showtext", quietly = TRUE)) {
      showtext::showtext_auto(enable = TRUE)
    }
  } else {
    candidates <- c("Noto Sans CJK SC", "WenQuanYi Micro Hei", "SimHei")
    for (f in candidates) {
      if (f %in% sysfonts::font_families()) {
        font_family <- f
        break
      }
    }
    if (requireNamespace("showtext", quietly = TRUE)) {
      showtext::showtext_auto(enable = TRUE)
    }
  }
  return(font_family)
}

FONT_FAMILY <- .setup_chinese_font()

# 设置 ggplot2 默认字体（如果已加载）
if ("ggplot2" %in% .packages()) {
  ggplot2::update_geom_defaults("text", list(family = FONT_FAMILY))
}

# ==================== 颜色配置加载 ====================

.find_color_config <- function() {
  paths <- c(
    Sys.getenv("FIGAPP_COLOR_CONFIG", unset = ""),
    file.path(dirname(sys.frame(1)$ofile), "color_config.json"),
    file.path(getwd(), "color_config.json")
  )
  for (p in paths) {
    if (p != "" && file.exists(p)) {
      return(p)
    }
  }
  return(NULL)
}

load_colors <- function(series_name = NULL) {
  path <- .find_color_config()
  if (!is.null(path)) {
    if (!requireNamespace("jsonlite", quietly = TRUE)) {
      warning("jsonlite package not found. Using default palette.")
      return(c("#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#DC0000"))
    }
    config <- jsonlite::fromJSON(path)
    
    # 如果指定了 series_name，从中查找
    if (!is.null(series_name) && !is.null(config$series)) {
      if (series_name %in% names(config$series)) {
        colors <- config$series[[series_name]]$colors
        if (length(colors) > 0) {
          return(colors)
        }
      }
    }
    
    # 否则用活跃方案
    active_series <- config$active_series %||% "aaas"
    if (!is.null(config$series) && active_series %in% names(config$series)) {
      colors <- config$series[[active_series]]$colors
      if (length(colors) > 0) {
        return(colors)
      }
    }
    
    # 兼容旧格式（直接 'colors' 键）
    colors <- config$colors
    if (length(colors) > 0) {
      return(colors)
    }
  }
  # fallback - NPG 配色
  return(c("#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#DC0000"))
}

get_group_colors <- function(groups, series_name = NULL) {
  palette <- load_colors(series_name)
  n <- length(groups)
  colors <- rep(palette, length.out = n)
  names(colors) <- groups
  return(colors)
}

get_palette <- function(n_colors = 8, series_name = NULL) {
  palette <- load_colors(series_name)
  return(rep(palette, length.out = n_colors))
}

GLOBAL_PALETTE <- load_colors()
