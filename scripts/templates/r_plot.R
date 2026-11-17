#!/usr/bin/env Rscript
#
# [图表名称] — R 版本
# ========================
# [简要描述图表用途]
#
# === 使用说明 =================================================================
# 1. 复制此文件到 scripts/R/，重命名为你的脚本名
# 2. 在 >>> PLOT CODE >>> 和 <<< PLOT CODE <<< 之间编写绘图代码
# 3. 修改脚本顶部的 @PARAM 声明（可选），定义可调参数
# 4. 在 scripts.json 中注册新脚本
#
# === 数据流 ===================================================================
# app.py 在运行目录生成 config.json，包含数据路径、参数、列映射、颜色等。
# 脚本接收 config.json 路径作为唯一命令行参数，自动完成：
#   1. 读取配置
#   2. 加载全局颜色与字体
#   3. 读取数据（自动检测编码）
#   4. 提取参数
#   5. 保存 PNG + PDF
#
# === 可用变量（模板已自动解析，可直接在 PLOT CODE 中使用）=====================
#   df, col_x, col_y, col_group, col_color, col_facet, col_label, col_size
#   palette, title, x_label, y_label
#   fig_width(=10), fig_height(=8), dpi(=300), font_size, alpha
# =============================================================================

options(repos = c(CRAN = "https://cloud.r-project.org"))


# ====================================================================
# 1. 安装/加载必要包（请勿修改此部分）
# ====================================================================

for (pkg in c("jsonlite", "ggplot2")) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
        install.packages(pkg, quiet = TRUE)
    }
    library(pkg, character.only = TRUE)
}


# ====================================================================
# 2. 读取配置文件（请勿修改此部分）
# ====================================================================

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("请提供 config.json 路径")

config <- jsonlite::fromJSON(args[1], simplifyVector = FALSE)

input_file  <- config$input
output_file <- config$output
output_pdf  <- if (is.null(config$output_pdf)) {
    sub("\\.png$", ".pdf", output_file)
} else config$output_pdf
params      <- if (is.null(config$parameters)) list() else config$parameters
col_mapping <- if (is.null(config$columns)) list() else config$columns
colors_data <- if (is.null(config$colors)) list() else config$colors


# ====================================================================
# 3. 加载全局配置（颜色 + 中文字体，请勿修改此部分）
# ====================================================================

figapp_env <- new.env()
tryCatch({
    source("figapp_config.R", local = figapp_env, echo = FALSE)
    FONT_FAMILY   <- figapp_env$FONT_FAMILY
    GLOBAL_PALETTE <- figapp_env$load_colors()
}, error = function(e) {
    FONT_FAMILY   <<- "sans"
    GLOBAL_PALETTE <<- c("#E64B35", "#4DBBD5", "#00A087", "#3C5488",
                         "#F39B7F", "#8491B4", "#91D1C2", "#DC0000")
})

# 获取颜色列表
if (!is.null(colors_data$palette) && length(colors_data$palette) > 0) {
    palette <- colors_data$palette
} else if (!is.null(colors_data$active_series) && nchar(colors_data$active_series) > 0) {
    tryCatch({
        palette <- figapp_env$load_colors(colors_data$active_series)
    }, error = function(e) {
        palette <<- GLOBAL_PALETTE
    })
} else {
    palette <- GLOBAL_PALETTE
}

# 设置 ggplot2 默认字体
if (exists("FONT_FAMILY") && "ggplot2" %in% .packages()) {
    tryCatch({
        ggplot2::update_geom_defaults("text", list(family = FONT_FAMILY))
    }, error = function(e) {})
}

`%||%` <- function(a, b) if (is.null(a) || is.na(a) || nchar(a) == 0) b else a


# ====================================================================
# 4. 读取数据（自动检测编码，请勿修改此部分）
# ====================================================================

ext <- tolower(tools::file_ext(input_file))
df <- if (ext %in% c("xlsx", "xls")) {
    if (!requireNamespace("readxl", quietly = TRUE)) install.packages("readxl")
    readxl::read_excel(input_file)
} else {
    sep <- if (ext == "txt") "\t" else ","
    encodings <- c("UTF-8", "GBK", "GB18030", "Latin-1")
    result <- NULL
    for (enc in encodings) {
        tryCatch({
            result <- read.csv(input_file, sep = sep, encoding = enc,
                               stringsAsFactors = FALSE)
            break
        }, error = function(e) {}, warning = function(w) {})
    }
    if (is.null(result)) stop("无法识别文件编码")
    result
}


# ====================================================================
# 5. 列名映射（请勿修改此部分）
# ====================================================================

col_x       <- col_mapping[["x"]]
col_y       <- col_mapping[["y"]]
col_group   <- col_mapping[["group"]]
col_color   <- col_mapping[["color"]]
col_facet   <- col_mapping[["facet"]]
col_label   <- col_mapping[["label"]]
col_size    <- col_mapping[["size"]]
col_subgroup <- col_mapping[["subgroup"]]


# ====================================================================
# 6. 提取绘图参数（请勿修改此部分）
# 如需添加可调参数，用 @PARAM 声明：
#   # @PARAM 参数名: 类型 = 默认值 | 显示标签
# 支持类型: str, int, float, bool, select
# ====================================================================

# @PARAM title: str =  | 图表标题
# @PARAM x_label: str =  | X 轴标签
# @PARAM y_label: str =  | Y 轴标签
# @PARAM fig_width: float = 10 | 图片宽度（英寸）
# @PARAM fig_height: float = 8 | 图片高度（英寸）
# @PARAM dpi: int = 300 | 输出分辨率
# @PARAM font_size: int = 12 | 基础字号
# @PARAM alpha: float = 0.7 | 透明度

title      <- if (is.null(params[["title"]])) "" else as.character(params[["title"]])
x_label    <- if (is.null(params[["x_label"]])) col_x %||% "" else as.character(params[["x_label"]])
y_label    <- if (is.null(params[["y_label"]])) col_y %||% "" else as.character(params[["y_label"]])
fig_width  <- if (is.null(params[["fig_width"]])) 10 else as.numeric(params[["fig_width"]])
fig_height <- if (is.null(params[["fig_height"]])) 8 else as.numeric(params[["fig_height"]])
dpi        <- if (is.null(params[["dpi"]])) 300 else as.integer(params[["dpi"]])
font_size  <- if (is.null(params[["font_size"]])) 12 else as.integer(params[["font_size"]])
alpha      <- if (is.null(params[["alpha"]])) 0.7 else as.numeric(params[["alpha"]])

# ggplot2 基础主题
base_theme <- theme_classic(base_size = font_size) +
    theme(
        plot.title    = element_text(hjust = 0.5, face = "bold", size = font_size + 2),
        axis.title    = element_text(size = font_size),
        axis.text     = element_text(size = font_size - 1),
        legend.position = "right",
        plot.margin   = margin(10, 10, 10, 10)
    )


# ====================================================================
# >>> PLOT CODE >>> — 在此处编写您的绘图代码
#     可用变量: df, col_x, col_y, col_group, col_color, col_facet,
#               col_label, col_size, palette, title, x_label, y_label,
#               fig_width, fig_height, dpi, font_size, alpha, base_theme
#
#     结果赋值给变量 p（ggplot 对象）
# ====================================================================

# ==================== 在此开始编写 ====================

# 示例：散点图
if (!is.null(col_x) && !is.null(col_y) &&
    col_x %in% colnames(df) && col_y %in% colnames(df)) {

    if (!is.null(col_group) && col_group %in% colnames(df)) {
        n_groups <- length(unique(df[[col_group]]))
        group_colors <- palette[1:min(n_groups, length(palette))]
        p <- ggplot(df, aes_string(x = col_x, y = col_y, color = col_group)) +
            geom_point(alpha = alpha, size = 3) +
            scale_color_manual(values = group_colors)
    } else {
        p <- ggplot(df, aes_string(x = col_x, y = col_y)) +
            geom_point(color = palette[1], alpha = alpha, size = 3)
    }

    p <- p + labs(title = title, x = x_label %||% col_x, y = y_label %||% col_y)
} else {
    # 占位：列映射不完整
    p <- ggplot(data.frame(msg = "请配置列映射")) +
        annotate("text", x = 1, y = 1, label = "请上传数据并配置列映射\n(columns → x, y)",
                 size = 5, color = "#999") +
        theme_void()
}

p <- p + base_theme

if (!is.null(col_facet) && col_facet %in% colnames(df)) {
    p <- p + facet_wrap(as.formula(paste("~", col_facet)))
}

# ==================== 在此结束编写 ====================

# <<< PLOT CODE <<<
# ====================================================================


# ====================================================================
# 7. 保存输出（请勿修改此部分）
# ====================================================================

ggsave(output_file, plot = p, width = fig_width, height = fig_height,
       dpi = dpi, units = "in")
ggsave(output_pdf, plot = p, width = fig_width, height = fig_height,
       dpi = dpi, units = "in")

cat(sprintf("输出: %s\n", basename(output_file)))
