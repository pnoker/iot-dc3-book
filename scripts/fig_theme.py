#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插图主题适配：把 SVG 源（book/figures/*.html）转为可响应明暗主题的内联 SVG。

策略：SVG 源保持纯色值（PDF 出版链路不动），本模块在 web 派生环节
把 fill/stroke 色值替换为 CSS 变量 var(--fig-<hex>)，并生成 figures.css
（:root 定义 light 原色、.dark 定义暗色对应值）。颜色映射按 Tailwind
色板做「亮度阶反转」：浅底→深底、深字→浅字、语义描边→提亮档。

本文件是颜色映射的唯一权威来源（light → dark），供 build_web.py 复用。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = ROOT / "book" / "figures"

# light → dark 映射。键为小写 hex（含/不含 # 均可），值为小写 hex。
# 规则：
#  - 中性色（slate）按阶反转：50→900、900→100、200 边框→700 等
#  - 语义色浅底（50/100/200 卡片底）→ 对应深底（800/900）
#  - 语义色深字/描边（600~800）→ 对应亮档（300/400）
#  - 自定义近白底 → 中性深底 #1e293b（描边保留语义色）
COLOR_MAP: dict[str, str] = {
    # ── 中性色 slate/gray ──
    "f8fafc": "0f172a",   # slate-50 页面背景
    "f1f5f9": "1e293b",   # slate-100
    "e2e8f0": "334155",   # slate-200 边框
    "cbd5e1": "475569",   # slate-300 边框
    "94a3b8": "64748b",   # slate-400
    "64748b": "94a3b8",   # slate-500 弱文字
    "475569": "94a3b8",   # slate-600 副文字
    "334155": "cbd5e1",   # slate-700 中文字
    "0f172a": "f1f5f9",   # slate-900 主文字
    "999": "64748b",      # 自定义灰
    "fff": "1e293b",      # 英文 white（画布/白底卡片）
    "ffffff": "1e293b",   # 画布白 / 白底卡片

    # ── blue ──
    "eff6ff": "1e3a8a",   # blue-50 底 → blue-900
    "dbeafe": "1e40af",   # blue-100 → blue-800
    "bfdbfe": "1e40af",   # blue-200 → blue-800
    "93c5fd": "3b82f6",   # blue-300 → blue-500
    "2563eb": "60a5fa",   # blue-600 主色 → blue-400
    "1d4ed8": "60a5fa",   # blue-700
    "1e40af": "93c5fd",   # blue-800

    # ── teal ──
    "f0fdfa": "134e4a",   # teal-50 → teal-900
    "ccfbf1": "115e59",   # teal-100 → teal-800
    "99f6e4": "0f766e",   # teal-200 → teal-700
    "5eead4": "0d9488",   # teal-300 → teal-600
    "0f766e": "2dd4bf",   # teal-700 主色 → teal-400

    # ── emerald ──
    "ecfdf5": "064e3b",   # emerald-50 → emerald-900
    "d1fae5": "065f46",   # emerald-100 → emerald-800
    "a7f3d0": "047857",   # emerald-200 → emerald-700
    "059669": "34d399",   # emerald-600
    "047857": "34d399",   # emerald-700
    "065f46": "6ee7b7",   # emerald-800
    "10b981": "34d399",   # emerald-500

    # ── green ──
    "f0fdf4": "14532d",   # green-50 → green-900
    "dcfce7": "166534",   # green-100 → green-800
    "bbf7d0": "15803d",   # green-200 → green-700
    "86efac": "16a34a",   # green-300 → green-600
    "22c55e": "4ade80",   # green-500
    "16a34a": "4ade80",   # green-600 主色
    "15803d": "4ade80",   # green-700
    "166534": "86efac",   # green-800

    # ── orange ──
    "fff7ed": "7c2d12",   # orange-50 → orange-900
    "ffedd5": "9a3412",   # orange-100 → orange-800
    "fed7aa": "c2410c",   # orange-200 → orange-700
    "fdba74": "ea580c",   # orange-300 → orange-600
    "f97316": "fb923c",   # orange-500 主色 → orange-400
    "ea580c": "fb923c",   # orange-600
    "c2410c": "fb923c",   # orange-700
    "9a3412": "fdba74",   # orange-800

    # ── amber ──
    "fffbeb": "78350f",   # amber-50 → amber-900
    "fef3c7": "92400e",   # amber-100 → amber-800
    "fde68a": "b45309",   # amber-200 → amber-700
    "fcd34d": "d97706",   # amber-300 → amber-600
    "f59e0b": "fbbf24",   # amber-500
    "d97706": "fbbf24",   # amber-600 警示
    "b45309": "fcd34d",   # amber-700
    "92400e": "fcd34d",   # amber-800

    # ── red ──
    "fef2f2": "450a0a",   # red-50 → red-950
    "fee2e2": "7f1d1d",   # red-100 → red-900
    "dc2626": "f87171",   # red-600 主色 → red-400
    "b91c1c": "fca5a5",   # red-700
    "991b1b": "fca5a5",   # red-800
    "7f1d1d": "fca5a5",   # red-900

    # ── violet ──
    "f5f3ff": "2e1065",   # violet-50 → violet-950
    "ede9fe": "4c1d95",   # violet-100 → violet-900
    "ddd6fe": "5b21b6",   # violet-200 → violet-800
    "c4b5fd": "6d28d9",   # violet-300 → violet-700
    "a78bfa": "7c3aed",   # violet-400 → violet-600
    "7c3aed": "a78bfa",   # violet-600 主色 → violet-400
    "6d28d9": "c4b5fd",   # violet-700

    # ── cyan ──
    "ecfeff": "164e63",   # cyan-50 → cyan-900
    "0891b2": "22d3ee",   # cyan-600

    # ── 自定义近白底（描边保留语义色，底统一中性深灰）──
    "f0f8ff": "1e293b",   # aliceblue（蓝调白）
    "f0fbf5": "1e293b",
    "f3faf6": "1e293b",
    "f5fcf9": "1e293b",
    "f7faff": "1e293b",
    "f8fcfb": "1e293b",
    "faf5ff": "1e293b",
    "faf8ff": "1e293b",
    "fbfdff": "1e293b",
    "fefce8": "1e293b",
    "fff7e6": "1e293b",
    "fff8dc": "1e293b",
    "fff8e7": "1e293b",
    "fff9f2": "1e293b",
    "fffbf4": "1e293b",

    # ── rgba() 专用：半透明背景分区 / 填充的语义色（原浅色 → 深色调）──
    "87cefa": "1e3a8a",   # skyblue 室外域浅蓝 → blue-900
    "ffff00": "78350f",   # 过渡区纯黄 → amber-900
    "c8c8c8": "475569",   # 室内域中性浅灰 → slate-600
}

# 色值 → CSS 变量名。var(--fig-<hex>)；覆盖 fill/stroke/stop-color 属性
_COLOR_RE = re.compile(r'(fill|stroke|stop-color)="(#[0-9a-fA-F]{3,8})"')
# rgba(r,g,b,a) 半透明色（背景分区/填充）：颜色部分变量化，透明度保留
_RGBA_RE = re.compile(
    r'(fill|stroke)="rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)"'
)


def to_var_color(m: re.Match) -> str:
    attr, hexv = m.group(1), m.group(2).lstrip("#").lower()
    return f'{attr}="var(--fig-{hexv})"'


def _to_rgb_var(m: re.Match) -> str:
    attr = m.group(1)
    r, g, b = int(m.group(2)), int(m.group(3)), int(m.group(4))
    a = m.group(5) or "1"
    hexv = f"{r:02x}{g:02x}{b:02x}"
    if hexv in COLOR_MAP:
        return f'{attr}="rgba(var(--fig-rgb-{hexv}), {a})"'
    return m.group(0)


def _hex_to_rgb(hexv: str) -> tuple[int, int, int]:
    return int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)


def svg_to_theme(svg_markup: str) -> str:
    """把一段 SVG（含内联）中的色值替换为 CSS 变量（含 rgba/stop-color）。

    并压缩空行：markdown-it 的 HTML 块规则遇空行会中断 HTML 块，
    导致 Vue 编译器看到断裂标签（"Element is missing end tag"），
    因此内联进 .md 前必须去掉空行，保持连续 HTML 块。
    """
    out = _COLOR_RE.sub(to_var_color, svg_markup)
    out = _RGBA_RE.sub(_to_rgb_var, out)
    # 英文色名 white / black 等
    out = re.sub(r'(fill|stroke)="white"', r'\1="var(--fig-ffffff)"', out, flags=re.IGNORECASE)
    # 压缩空行（保留单换行，标签间不断裂）
    out = re.sub(r'\n[ \t]*\n+', '\n', out)
    return out


def collect_rgba_hexes() -> set[str]:
    """扫描所有图，返回 rgba() 中用到、且已在 COLOR_MAP 的颜色 hex。"""
    hexes: set[str] = set()
    for f in sorted(FIGURES_DIR.glob("chapter-*/*.html")):
        inline = extract_inline_svg(f.read_text(encoding="utf-8"))
        for m in _RGBA_RE.finditer(inline):
            r, g, b = int(m.group(2)), int(m.group(3)), int(m.group(4))
            hexv = f"{r:02x}{g:02x}{b:02x}"
            if hexv in COLOR_MAP:
                hexes.add(hexv)
    return hexes


def extract_inline_svg(html: str) -> str:
    """从 figure HTML 源提取 data-figure-root 容器内的 SVG 内容。

    兼容多种源结构（出版工具演进的历史写法）：
      1. <main class="page" data-figure-root>…嵌套 <svg>…</main>
      2. <main class="figure" data-figure-root>…<svg>…</main>
      3. <div data-figure-root>…<svg>…</div>
      4. <svg data-figure-root>…嵌套 <svg>…</svg>（data-figure-root 标在 svg 上）
    """
    m = re.search(r'<([a-zA-Z]+)([^>]*?\sdata-figure-root[^>]*)>', html, re.DOTALL)
    if not m:
        return ""
    tag = m.group(1)
    full_open = m.group(0)
    start = m.end()

    # 栈匹配：从开标签后开始，跳过嵌套的同名标签，找配对的闭合标签
    open_pat = re.compile(rf'<{tag}(?:\s[^>]*)?/?>', re.IGNORECASE)
    close_pat = re.compile(rf'</{tag}\s*>', re.IGNORECASE)
    depth = 1
    pos = start
    while depth > 0:
        om = open_pat.search(html, pos)
        cm = close_pat.search(html, pos)
        if cm is None:
            return ""  # 未闭合，异常源
        if om and om.start() < cm.start():
            # 跳过自闭合 <tag/>
            if not om.group(0).endswith("/>"):
                depth += 1
            pos = om.end()
        else:
            depth -= 1
            pos = cm.end()

    container = html[m.start():pos]
    # 若容器本身是 svg，直接返回；否则返回其 innerHTML（剥离 main/div 包装）
    if tag.lower() == "svg":
        return container
    inner = re.sub(r'^<[a-zA-Z]+[^>]*>', '', container, count=1)
    inner = re.sub(r'</[a-zA-Z]+>$', '', inner, count=1)
    return inner


def gen_figures_css(rgb_hexes: set[str] | None = None) -> str:
    """生成 figures.css：:root 定义原色、.dark 定义暗色对应值。

    rgb_hexes 是 rgba() 用到的颜色 hex 集合，额外生成 --fig-rgb-<hex>
    变量（三个 0-255 数字），供 rgba(var(--fig-rgb-<hex>), alpha) 引用。
    """
    rgb_hexes = rgb_hexes or set()
    lines = [
        "/* 自动生成，请勿手改 —— 由 scripts/fig_theme.py 产出 */",
        ":root {",
    ]
    for hexv, dark in sorted(COLOR_MAP.items()):
        if hexv == "fff":
            continue  # 统一用 ffffff
        lines.append(f"  --fig-{hexv}: #{hexv};")
    for hexv in sorted(rgb_hexes):
        r, g, b = _hex_to_rgb(hexv)
        lines.append(f"  --fig-rgb-{hexv}: {r}, {g}, {b};")
    lines.append("}")
    lines.append("")
    lines.append(".dark {")
    for hexv, dark in sorted(COLOR_MAP.items()):
        if hexv == "fff":
            continue
        lines.append(f"  --fig-{hexv}: #{dark};")
    for hexv in sorted(rgb_hexes):
        dr, dg, db = _hex_to_rgb(COLOR_MAP[hexv])
        lines.append(f"  --fig-rgb-{hexv}: {dr}, {dg}, {db};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def figure_id_of(src: str) -> str | None:
    """从图片 src 解析 figure_id（如 ../figures/fig-03-01.png → fig-03-01）。"""
    m = re.search(r"(fig-\d{2}-\d{2})", src)
    return m.group(1) if m else None


# SVG 内 <style> 标签：VitePress dev 模式（client 组件模板）会拒绝 <style>/<script>，
# 且其中的颜色是硬编码、暗色主题不生效。须提取出来、作用域化到 .fig-<id> 类。
_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_STYLE_COLOR_RE = re.compile(r"(fill|stroke)\s*:\s*(#[0-9a-fA-F]{3,8})\b", re.IGNORECASE)


def _extract_and_scope_style(svg: str, figure_id: str) -> tuple[str, str]:
    """提取 SVG 内 <style>，颜色变量化 + 作用域化到 .fig-<id>。

    返回 (移除 <style> 后的 svg, 作用域化后的 CSS 规则)。
    """
    scoped_rules: list[str] = []

    def _repl(m: re.Match) -> str:
        css_text = m.group(1)
        # 颜色变量化：fill: #xxx → fill: var(--fig-xxx)
        css_text = _STYLE_COLOR_RE.sub(
            lambda cm: f"{cm.group(1)}: var(--fig-{cm.group(2).lstrip('#').lower()})",
            css_text,
        )
        for rule in css_text.split("}"):
            if "{" not in rule:
                continue
            sel, body = rule.split("{", 1)
            sels = [s.strip() for s in sel.split(",") if s.strip()]
            if not sels:
                continue
            scoped = ", ".join(f".{figure_id} {s}" for s in sels)
            scoped_rules.append(f"{scoped} {{{body}}}")
        return ""

    svg_out = _STYLE_RE.sub(_repl, svg)
    return svg_out, "\n".join(scoped_rules)


def collect_figure_styles() -> str:
    """扫描所有图，收集 SVG 内 <style> 作用域化后的 CSS 规则（追加到 figures.css）。"""
    rules: list[str] = []
    for f in sorted(FIGURES_DIR.glob("chapter-*/*.html")):
        inline = extract_inline_svg(f.read_text(encoding="utf-8"))
        _, scoped = _extract_and_scope_style(inline, f.stem)
        if scoped:
            rules.append(scoped)
    return "\n".join(rules)


def load_figure_svg(figure_id: str) -> str | None:
    """按 figure_id 定位并返回 theme 化的内联 SVG；找不到返回 None。"""
    chapter = figure_id.split("-")[1]  # fig-03-01 → 03
    src_file = FIGURES_DIR / f"chapter-{chapter}" / f"{figure_id}.html"
    if not src_file.exists():
        return None
    html = src_file.read_text(encoding="utf-8")
    inline = extract_inline_svg(html)
    # 提取并作用域化 <style>（移除标签，规则交给 figures.css）
    inline, _ = _extract_and_scope_style(inline, figure_id)
    # 给最外层 svg 根加类，供作用域化规则匹配
    inline = re.sub(r"<svg\b", f'<svg class="{figure_id}"', inline, count=1, flags=re.IGNORECASE)
    return svg_to_theme(inline)


if __name__ == "__main__":
    css = gen_figures_css()
    print(css)
