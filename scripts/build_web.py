#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍出版稿 → VitePress Web 站点 转换脚本。

输入:
  output/                       book-builder build 产物（分章 md + figures + dividers）
  book/config/parts.yaml        篇章结构（篇 name/description + 章 id/title/description）
输出:
  docs/                         VitePress 源（生成内容页 + 静态资源 + sidebar.ts）

处理:
  1. 去 Pandoc 图片属性 {width=15cm}，转 <figure class="fig"> + <figcaption>
  2. 图片相对路径 ../figures/... → 绝对 /figures/...
  3. 注入 frontmatter（title / description）
  4. 章首插入章扉页（dividers/chapter-XX.png）
  5. 生成卷首单页 / 篇页 / 附录页 / 全书目录页
  6. 拷贝 figures、dividers → docs/public/
  7. 生成 docs/.vitepress/sidebar.ts

幂等：每次运行前清空生成产物，保留 .vitepress 手写文件、docs/index.md、public 手写资源。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from PIL import Image

try:
    import yaml
except ImportError:
    sys.exit("缺少 pyyaml，请用 `uv run python scripts/build_web.py` 运行（复用 book venv）。")

from jinja2 import Environment, FileSystemLoader, select_autoescape

# 插图主题适配（内联 SVG + 颜色变量），与 build_web 同目录
from fig_theme import (
    figure_id_of, load_figure_svg, gen_figures_css,
    collect_figure_styles, collect_rgba_hexes, audit_color_coverage, FIGURES_DIR,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
DOCS = ROOT / "docs"
PUBLIC = DOCS / "public"
VITEPRESS = DOCS / ".vitepress"
PARTS_YAML = ROOT / "book" / "config" / "parts.yaml"
DIVIDERS_DIR = ROOT / "book" / "dividers"

# 章/篇扉页 Jinja2 环境（与 src/book_builder/dividers.py 同一套模板与数据）
_DIV_ENV = Environment(
    loader=FileSystemLoader(DIVIDERS_DIR),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    trim_blocks=True,
    lstrip_blocks=True,
)

# divider.css 规则块解析与作用域化（web 端章扉页是内联小块，不是独立页面）
_DIVIDER_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
# 这些选择器是 PDF 独立渲染时用的全局页面尺寸规则，web 端必须丢弃，
# 否则会污染 VitePress 站点（html/body 固定 1240×1754 + overflow:hidden 导致无法滚动）。
_DIVIDER_DROP_SELECTORS = {"*", "html", "body", "html, body"}
# 变量定义块保留原样（--div-* 是全局变量，供 .divider-body 内引用）
_DIVIDER_VAR_SELECTORS = {":root", ".dark"}


def scope_divider_css(css: str) -> str:
    """把 divider.css 作用域化到 .divider-body 内，避免全局 html/body/h1 污染站点。"""
    # 先剥离注释，避免注释混入选择器（如 `/* 注释 */ :root`）
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    out: list[str] = []
    for m in _DIVIDER_RULE_RE.finditer(css):
        selector = " ".join(m.group(1).split())
        body = m.group(2)
        if selector in _DIVIDER_DROP_SELECTORS:
            continue
        if selector in _DIVIDER_VAR_SELECTORS:
            out.append(f"{selector} {{{body}}}")
            continue
        parts = [p.strip() for p in selector.split(",")]
        scoped = ", ".join(f".divider-body {p}" for p in parts)
        out.append(f"{scoped} {{{body}}}")
    return "\n".join(out)


# 封面（book/assets/cover.html）Jinja2 渲染：与 pdf.py _render_cover_html 同源。
COVER_HTML = ROOT / "book" / "assets" / "cover.html"
BOOK_YAML = ROOT / "book" / "config" / "book.yaml"


def scope_cover_css(css: str) -> str:
    """把封面 cover.html 的 <style> 作用域化到 .cover-body 内。

    - :root/.dark 变量块保留全局（--cover-* 供 .cover-body 引用 + 响应明暗主题）
    - body 选择器改挂 .cover-body（固定 A4 尺寸 mm 转 px，作缩放基准）
    - 其余选择器前缀 .cover-body；丢弃 @page/@media print（web 无打印上下文）
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # 移除 at-rule 块：@page（无嵌套）、@media print（一层嵌套）
    css = re.sub(r"@page\s*\{[^{}]*\}", "", css)
    css = re.sub(r"@media\s+print\s*\{[^{}]*\{[^{}]*\}[^{}]*\}", "", css)
    out: list[str] = []
    for m in _DIVIDER_RULE_RE.finditer(css):
        selector = " ".join(m.group(1).split())
        body = m.group(2)
        if selector in (":root", ".dark"):
            out.append(f"{selector} {{{body}}}")
            continue
        if selector == "body":
            # A4 210mm×297mm 按 96dpi（1mm≈3.7795px）折合 794×1123px，作缩放基准
            body = body.replace("210mm", "794px").replace("297mm", "1123px")
            out.append(f".cover-body {{{body}}}")
            continue
        if selector == "*":
            out.append(f".cover-body * {{{body}}}")
            continue
        parts = [p.strip() for p in selector.split(",")]
        scoped = ", ".join(f".cover-body {p}" for p in parts)
        out.append(f"{scoped} {{{body}}}")
    return "\n".join(out)


def render_cover_inline() -> tuple[str, str]:
    """渲染封面模板，返回 (作用域化 CSS, body HTML)。"""
    meta = yaml.safe_load(BOOK_YAML.read_text(encoding="utf-8"))
    template = Environment(
        autoescape=select_autoescape(enabled_extensions=("html",)),
    ).from_string(COVER_HTML.read_text(encoding="utf-8"))
    rendered = template.render(**meta)

    style_m = re.search(r"<style[^>]*>(.*?)</style>", rendered, re.DOTALL)
    css = style_m.group(1) if style_m else ""
    body_m = re.search(r"<body[^>]*>(.*?)</body>", rendered, re.DOTALL)
    body = body_m.group(1) if body_m else ""

    # logo.svg 相对路径 → 站点根
    body = body.replace('src="logo.svg"', 'src="/logo.svg"')
    return scope_cover_css(css), body


def gen_cover_art_ts(body_html: str) -> str:
    """生成 docs/.vitepress/theme/cover-art.ts（导出封面 body HTML 字符串）。"""
    return (
        "// 自动生成，请勿手改 —— 由 scripts/build_web.py 产出\n"
        f"export const coverBodyHtml = {json.dumps(body_html, ensure_ascii=False)}\n"
    )


# 篇关键词 → (web slug, 篇扉页图名)
PART_SLUGS = {
    "基础篇": ("foundations", "part-01"),
    "技术篇": ("technical", "part-02"),
    "应用篇": ("applications", "part-03"),
}

# 卷首单页：(output 源文件, 输出 slug, 显示名, frontmatter description)
PREFACE = [
    ("01-作者简介.md", "author", "关于作者",
     "IoT DC3 开源作者张红元——架构师、物联网专家，十余年工业物联网平台研发经验，著有《从工业软件到 AI 智能体》。"),
    ("02-序.md", "foreword", "序",
     "《从工业软件到 AI 智能体》作者自序——阐述写作初衷、全书定位与技术选型考量。"),
    ("03-导读.md", "guide", "导读",
     "《从工业软件到 AI 智能体》阅读指南——按读者角色（入门开发者、架构师、项目经理）推荐最佳阅读路径。"),
]

# output 篇目录前缀：第 1 篇 05、第 2 篇 06、第 3 篇 07
PART_DIR_OFFSET = 5

# ── 工具 ──────────────────────────────────────────────────────────────────

# ![alt](src) 或 ![alt](src){attrs}
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)(?:\s*\{[^}]*\})?")

# 资料溯源标注（写作过程的来源标记，出版不展示）
# ① （资料…）整块：覆盖 [S6]/[参考5]/[S1][S12]/C7-EVAL-02/参考1/自然语言描述 等所有形态
CITE_BLOCK_RE = re.compile(r"（资料[^（）]*）")
# ② 散落的 [S数字]/[S-xxx]/[S7, S8]/[参考数字]/[W-C7-xxx] 标记
#    （不动 [roundId] 等代码占位符，也不动「参考5.2.2节」这类无方括号的章节引用）
CITE_MARK_RE = re.compile(r"\[(?:S[^]]*|参考\d+|W-C7-[^]]*)\]")


def oneline(s: str) -> str:
    """多行描述压成一行（frontmatter description / meta 用）。"""
    return re.sub(r"\s+", " ", s or "").strip()


def git_lastmod(*paths: str) -> str:
    """获取指定路径最近一次 git 提交的 ISO 日期；失败时回退到最后提交日或当前时间。"""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--"] + list(paths),
            capture_output=True, text=True, cwd=str(ROOT), timeout=5,
        )
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%aI"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5,
        )
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


def js(s: str) -> str:
    """生成 JS/TS 字符串字面量。"""
    return json.dumps(s, ensure_ascii=False)


def web_src(src: str) -> str:
    """../figures/x.png → /figures/x.webp（网页用 WebP 优化版）"""
    s = re.sub(r"^(\.\./)+", "/", src)
    return s[:-4] + ".webp" if s.endswith(".png") else s


def fix_caption(alt: str) -> str:
    """图1-1 → 图 1-1（数字与"图"间加空格，便于阅读）。"""
    return re.sub(r"图(\d)", r"图 \1", alt)


def to_figure(m: re.Match) -> str:
    """插图转 <figure>：内联 theme 化 SVG（支持明暗主题）。

    从 src 解析 figure_id，读 SVG 源替换色值为 CSS 变量后内联进页面；
    源缺失时回退为 WebP <img>（保证构建不中断）。
    """
    alt, src = m.group(1), m.group(2)
    fig_id = figure_id_of(src)
    inline = load_figure_svg(fig_id) if fig_id else None
    caption = f"  <figcaption>{fix_caption(alt)}</figcaption>\n" if alt else ""
    anchor = f' id="{fig_id}"' if fig_id else ""
    if inline:
        # 内联 SVG：figcaption 前，SVG 自带 title/desc，外部再补 alt 语义用 <figure aria-label>
        return (
            f'<figure class="fig fig-svg"{anchor}>\n'
            f"  <div class=\"fig-svg-body\">{inline}</div>\n"
            f"{caption}"
            "</figure>"
        )
    return (
        f'<figure class="fig"{anchor}>\n'
        f'  <img src="{web_src(src)}" alt="{alt}" loading="lazy">\n'
        f"{caption}"
        "</figure>"
    )


def convert_images(md: str) -> str:
    return IMG_RE.sub(to_figure, md)


def gen_figures_manifest(parts: list[dict]) -> list[dict]:
    """扫描所有章节 md，生成全书插图清单（图库页数据源）。

    每个条目：id、图号、标题、章节号、章节名、文章锚点链接、缩略图路径。
    """
    manifest: list[dict] = []
    for i, part in enumerate(parts, start=1):
        slug, _ = slug_of(part)
        src_part_dir = OUTPUT / f"0{PART_DIR_OFFSET + (i - 1)}-{part['name']}"
        for ch in part["chapters"]:
            srcs = list(src_part_dir.glob(f"{ch['id']:02d}-*.md"))
            if not srcs:
                continue
            md = srcs[0].read_text(encoding="utf-8")
            for m in IMG_RE.finditer(md):
                alt, src = m.group(1), m.group(2)
                fig_id = figure_id_of(src)
                if not fig_id:
                    continue
                m_num = re.match(r"(图\s*\d+-\d+)\s*(.*)", alt.strip())
                if m_num:
                    num = fix_caption(m_num.group(1))
                    title = m_num.group(2).strip()
                else:
                    num, title = alt.strip(), ""
                manifest.append({
                    "id": fig_id,
                    "num": num,
                    "title": title,
                    "chapter": ch["id"],
                    "chapterTitle": ch["title"],
                    "url": f"/{slug}/chapter-{ch['id']}#{fig_id}",
                    "thumb": web_src(src),
                })
    return manifest


def clean_citations(md: str) -> str:
    """清除资料溯源标注（整块 + 散落标记）；保留正文「参考资料/资料包」叙述与代码占位符。"""
    md = CITE_BLOCK_RE.sub("", md)
    md = CITE_MARK_RE.sub("", md)
    return md


def fm(**kv) -> str:
    """生成 frontmatter。"""
    lines = ["---"]
    for k, v in kv.items():
        lines.append(f"{k}: {js(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def slug_of(part: dict) -> tuple[str, str]:
    key = part["name"].split("·")[0].strip()  # "基础篇 · ..." → "基础篇"
    if key not in PART_SLUGS:
        sys.exit(f"未知篇章「{key}」，请在 PART_SLUGS 补充映射。")
    return PART_SLUGS[key]


def render_divider_inline(context: dict[str, str]) -> str:
    """渲染章/篇扉页模板，提取 body 内容内联进页面（去掉 <link> 与空行）。

    扉页颜色由 divider.css 的 --div-* 变量驱动（:root 原色、.dark 暗色），
    divider.css 经 <link rel="stylesheet" href="/divider.css"> 全局加载。
    """
    template = _DIV_ENV.get_template(context["source_name"])
    rendered = template.render(**context)
    m = re.search(r"<body[^>]*>(.*?)</body>", rendered, re.DOTALL)
    if not m:
        return ""
    body = m.group(1)
    # 去掉模板自带的 divider.css 引用（web 端统一由 config.ts 加载 /divider.css）
    body = re.sub(r'<link[^>]*divider\.css[^>]*>', "", body)
    # 压缩空行，保持连续 HTML 块（避免 markdown-it 断裂）
    body = re.sub(r"\n[ \t]*\n+", "\n", body)
    return body


def part_divider_context(part: dict, part_index: int) -> dict[str, str]:
    """篇扉页 Jinja2 上下文（与 dividers.py _build_specs 的 part 分支一致）。"""
    themes = ("foundation", "technology", "application")
    theme = themes[(part_index - 1) % len(themes)]
    return {
        "source_name": f"part-{part_index:02d}.html",
        "kind": "part",
        "theme": theme,
        "number": f"{part_index:02d}",
        "label": f"第{part['prefix']}篇",
        "english_label": f"PART {part_index:02d}",
        "title": part["name"],
        "title_main": part["name"],
        "title_sub": "",
        "description": part["description"],
    }


def chapter_divider_context(part: dict, part_index: int, chapter: dict) -> dict[str, str]:
    """章扉页 Jinja2 上下文（与 dividers.py _build_specs 的 chapter 分支一致）。"""
    themes = ("foundation", "technology", "application")
    theme = themes[(part_index - 1) % len(themes)]
    title_main, _, title_sub = chapter["title"].partition("：")
    return {
        "source_name": f"chapter-{chapter['id']:02d}.html",
        "kind": "chapter",
        "theme": theme,
        "number": f"{chapter['id']:02d}",
        "label": f"第{chapter['id']}章",
        "english_label": f"CHAPTER {chapter['id']:02d}",
        "title": chapter["title"],
        "title_main": title_main,
        "title_sub": title_sub,
        "description": chapter["description"],
    }


# ── 页面生成 ──────────────────────────────────────────────────────────────

def convert_chapter(src: Path, cid: int, title: str, desc: str, date_modified: str = "", divider_html: str = "") -> str:
    body = src.read_text(encoding="utf-8")
    body = clean_citations(body)
    body = convert_images(body)
    divider = (
        '\n<figure class="chapter-divider">\n'
        f'  <div class="divider-body">{divider_html}</div>\n'
        "</figure>\n"
    )
    # 署名行（每章正文顶部：复制粘贴时归属信息随文字传播，而非只存在于页脚）
    byline = (
        '\n<div class="book-byline">'
        "作者：张红元 · © 2016–2026 · 保留所有权利 · "
        '<a href="/copyright">版权与许可</a>'
        "</div>\n"
    )
    # 在第一个 H1 之后插入署名 + 章扉页
    body = re.sub(r"^# [^\n]+", lambda m: m.group(0) + byline + divider, body, count=1, flags=re.M)
    fm_fields = {
        "title": f"第 {cid} 章　{title}",
        "description": oneline(desc),
    }
    if date_modified:
        fm_fields["dateModified"] = date_modified
    return fm(**fm_fields) + body.lstrip()


def convert_simple(src: Path, title: str, desc: str = "", date_modified: str = "") -> str:
    """卷首/附录等无篇章归属的页面：加 frontmatter，转图片。"""
    body = src.read_text(encoding="utf-8")
    body = clean_citations(body)
    body = convert_images(body)
    fm_fields = {"title": title, "description": oneline(desc)}
    if date_modified:
        fm_fields["dateModified"] = date_modified
    return fm(**fm_fields) + body.lstrip()


def gen_contents(parts: list[dict]) -> str:
    """全书目录页（链接指向 web 路由）。"""
    out = [fm(title="目录", description="《从工业软件到 AI 智能体》全书目录")]
    out.append("# 目录\n")
    for part in parts:
        slug, _ = slug_of(part)
        out.append(f"\n## {part['name']}\n")
        out.append(f"\n> {oneline(part.get('description', ''))}\n")
        out.append("")
        for ch in part["chapters"]:
            out.append(f"- [第 {ch['id']} 章　{ch['title']}](/{slug}/chapter-{ch['id']})")
    return "\n".join(out) + "\n"


def gen_part_index(part: dict, slug: str, divider_html: str = "") -> str:
    """篇扉页：篇图 + 篇名 + 概述 + 本章清单。"""
    desc = oneline(part.get("description", ""))
    out = [fm(title=part["name"], description=desc)]
    out.append(
        '<figure class="part-divider">\n'
        f'  <div class="divider-body">{divider_html}</div>\n'
        "</figure>\n"
    )
    out.append(f"# {part['name']}\n")
    out.append(f"\n> {desc}\n")
    out.append("\n## 本章包含\n")
    for ch in part["chapters"]:
        out.append(
            f"- [第 {ch['id']} 章　{ch['title']}](/{slug}/chapter-{ch['id']})"
            f" — {oneline(ch.get('description', ''))}"
        )
    return "\n".join(out) + "\n"


# VitePress 标题锚点 slug：与 vitepress 的 slugify 保持一致（用于 sidebar 二级菜单跳转锚点）
def vp_slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[\u0300-\u036F]", "", s)
    s = re.sub(r"[\u0000-\u001f]", "", s)
    s = re.sub(r"[\s\x60!@#$%^&*()\-_+=[\]{}|\\;:\"'\u201c\u201d\u2018\u2019<>,.?/]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    s = re.sub(r"^(\d)", r"_\1", s)
    return s.lower()


def _chapter_h2(ch_id, slug: str) -> list[str]:
    """读取某章 markdown 的二级标题（##），供 sidebar 二级菜单使用。"""
    f = DOCS / slug / f"chapter-{ch_id}.md"
    if not f.exists():
        return []
    return re.findall(r"^##\s+(.+)$", f.read_text(encoding="utf-8"), flags=re.M)


def gen_sidebar_ts(parts: list[dict]) -> str:
    L = [
        "// 自动生成，请勿手改 —— 由 scripts/build_web.py 产出",
        "import type {SidebarItem} from 'vitepress'",
        "",
        "export const sidebar: SidebarItem[] = [",
        "  {",
        "    text: '卷首',",
        "    items: [",
    ]
    for _, slug, label, _desc in PREFACE:
        L.append(f"      {{ text: {js(label)}, link: '/preface/{slug}' }},")
    L.append("      { text: '目录', link: '/preface/contents' },")
    L.append("    ],")
    L.append("  },")
    for part in parts:
        slug, _ = slug_of(part)
        L.append("  {")
        L.append(f"    text: {js(part['name'])},")
        L.append("    collapsed: false,")
        L.append("    items: [")
        for ch in part["chapters"]:
            title = f"第 {ch['id']} 章　{ch['title']}"
            link = f"/{slug}/chapter-{ch['id']}"
            subs = _chapter_h2(ch["id"], slug)
            if subs:
                L.append("      {")
                L.append(f"        text: {js(title)},")
                L.append("        collapsed: false,")
                L.append("        items: [")
                for h2 in subs:
                    L.append(f"          {{ text: {js(h2)}, link: {js(link + '#' + quote(vp_slugify(h2), safe=''))} }},")
                L.append("        ],")
                L.append("      },")
            else:
                L.append(f"      {{ text: {js(title)}, link: {js(link)} }},")
        L.append("    ],")
        L.append("  },")
    L.append("  { text: '附录', link: '/appendix/' },")
    L.append("  { text: '版权与许可', link: '/copyright' },")
    L.append("]")
    L.append("")
    return "\n".join(L)


# ── 资源 / 清理 ───────────────────────────────────────────────────────────

# 网页用图最大宽度：原 PNG 是印刷级（cover/divider 2480px、figure 2400px），
# 网页只需 ~800–1600px，缩放 + WebP 可把 ~53MB 降到 ~12MB，弱网体验大幅改善。
FIG_MAX_W = 1600      # 正文架构图（正文 ~800px，retina 2x 取 1600px）
DIVIDER_MAX_W = 1000  # 章 / 篇扉页
COVER_MAX_W = 800     # 首页 hero 封面


def optimize_to_webp(src: Path, dst: Path, max_width: int, quality: int = 85) -> tuple[int, int]:
    """缩放到 max_width 宽（按比例）并转 WebP。返回 (width, height)。"""
    with Image.open(src) as img:
        img = img.convert("RGB")
        w, h = img.width, img.height
        if w > max_width:
            h = round(h * max_width / w)
            w = max_width
            img = img.resize((w, h), Image.LANCZOS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, "WEBP", quality=quality, method=6)
        return (w, h)


# 图片引用正则（匹配完整 <img ...> 标签）
IMG_TAG_RE = re.compile(r'<img\s[^>]*?src="([^"]+)"[^>]*?>')


def add_img_dimensions_to_pages(dims: dict[str, tuple[int, int]]) -> None:
    """后处理所有生成的 .md 文件，为 <img> 标签添加 width/height（防止 CLS）。"""
    for md_file in DOCS.rglob("*.md"):
        if VITEPRESS in md_file.parents:
            continue  # 跳过 .vitepress 目录
        content = md_file.read_text(encoding="utf-8")

        def _add_dims(m: re.Match) -> str:
            tag = m.group(0)
            if "width=" in tag:
                return tag
            src = m.group(1).lstrip("/")
            if src in dims:
                w, h = dims[src]
                return tag.replace(">", f' width="{w}" height="{h}">')
            return tag

        content = IMG_TAG_RE.sub(_add_dims, content)
        md_file.write_text(content, encoding="utf-8")


def clean_generated() -> None:
    """删除脚本上次的生成产物（保留 .vitepress 手写、docs/index.md、public 手写资源）。"""
    for d in ["preface", "foundations", "technical", "applications", "appendix"]:
        shutil.rmtree(DOCS / d, ignore_errors=True)
    for d in ["figures", "dividers"]:
        shutil.rmtree(PUBLIC / d, ignore_errors=True)
    sb = VITEPRESS / "sidebar.ts"
    if sb.exists():
        sb.unlink()


def copy_assets() -> dict[str, tuple[int, int]]:
    """缩放并复制插图/扉页/封面到 docs/public/。返回 {相对路径: (width, height)} 映射。"""
    dims: dict[str, tuple[int, int]] = {}
    PUBLIC.mkdir(parents=True, exist_ok=True)
    # 插图：缩放 + WebP
    fig_src = OUTPUT / "figures"
    if fig_src.exists():
        for png in fig_src.rglob("*.png"):
            rel = png.relative_to(fig_src)
            w, h = optimize_to_webp(png, PUBLIC / "figures" / rel.with_suffix(".webp"), FIG_MAX_W)
            dims[f"figures/{rel.with_suffix('.webp')}"] = (w, h)
    # 扉页：缩放 + WebP
    div_src = OUTPUT / "dividers"
    if div_src.exists():
        for png in div_src.glob("*.png"):
            w, h = optimize_to_webp(png, PUBLIC / "dividers" / png.with_suffix(".webp").name, DIVIDER_MAX_W)
            dims[f"dividers/{png.with_suffix('.webp').name}"] = (w, h)
    # 封面：保留原 PNG（og:image）+ 生成 WebP
    cover = OUTPUT / "cover.png"
    if cover.exists():
        shutil.copy2(cover, PUBLIC / "cover.png")
        optimize_to_webp(cover, PUBLIC / "cover.webp", COVER_MAX_W)
    # 插图主题变量表（内联 SVG 颜色用）+ SVG 内 <style> 作用域化规则
    rgb_hexes = collect_rgba_hexes()
    (PUBLIC / "figures.css").write_text(
        gen_figures_css(rgb_hexes) + "\n" + collect_figure_styles(), encoding="utf-8"
    )
    # 全书插图 theme 化 SVG（预览页图库内联渲染，响应明暗主题；PNG 仅用于 PDF/MD 导出）
    svg_map = {}
    for f in sorted(FIGURES_DIR.glob("chapter-*/*.html")):
        svg_map[f.stem] = load_figure_svg(f.stem) or ""
    (PUBLIC / "figures-svg.json").write_text(
        json.dumps(svg_map, ensure_ascii=False), encoding="utf-8"
    )
    # 校验色值覆盖：缺失映射会让 var(--fig-*) 未定义，明/暗主题下显示异常（局部暗色）
    missing = audit_color_coverage()
    if missing:
        print("⚠️  插图存在 COLOR_MAP 未覆盖的色值（明暗主题会显示异常，请补全 scripts/fig_theme.py）：")
        for hexv, figs in sorted(missing.items()):
            print(f"    {hexv}: {sorted(figs)}")
    # 章/篇扉页主题样式（divider.css 已变量化：:root 原色、.dark 暗色）
    # web 端作用域化到 .divider-body，丢弃 html/body 全局页面尺寸规则，避免站点无法滚动。
    divider_css = DIVIDERS_DIR / "divider.css"
    if divider_css.exists():
        scoped = scope_divider_css(divider_css.read_text(encoding="utf-8"))
        (PUBLIC / "divider.css").write_text(scoped, encoding="utf-8")
    # 封面主题样式 + 内联 body（hero 主视觉，跟随明暗主题）
    if COVER_HTML.exists():
        cover_css, cover_body = render_cover_inline()
        (PUBLIC / "cover.css").write_text(cover_css, encoding="utf-8")
        (VITEPRESS / "theme" / "cover-art.ts").write_text(
            gen_cover_art_ts(cover_body), encoding="utf-8"
        )
    return dims


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    if not OUTPUT.exists():
        sys.exit(f"未找到 output/，请先运行 `uv run book-builder build`：{OUTPUT}")
    with open(PARTS_YAML, encoding="utf-8") as f:
        parts = yaml.safe_load(f)

    clean_generated()
    img_dims = copy_assets()

    # 全局最后修改时间（卷首/附录等无专属 manuscript 的页面回退到此值）
    global_lastmod = git_lastmod("book/manuscript/")

    # 卷首单页
    preface_dir = DOCS / "preface"
    preface_dir.mkdir(parents=True, exist_ok=True)
    for src_name, slug, label, pdesc in PREFACE:
        (preface_dir / f"{slug}.md").write_text(
            convert_simple(OUTPUT / src_name, label, desc=pdesc, date_modified=global_lastmod),
            encoding="utf-8",
        )
    # 全书目录页
    (preface_dir / "contents.md").write_text(gen_contents(parts), encoding="utf-8")

    # 篇与章
    for i, part in enumerate(parts, start=1):
        slug, divider_img = slug_of(part)
        src_part_dir = OUTPUT / f"0{PART_DIR_OFFSET + (i - 1)}-{part['name']}"
        out_dir = DOCS / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        part_html = render_divider_inline(part_divider_context(part, i))
        (out_dir / "index.md").write_text(
            gen_part_index(part, slug, divider_html=part_html), encoding="utf-8"
        )
        for ch in part["chapters"]:
            srcs = list(src_part_dir.glob(f"{ch['id']:02d}-*.md"))
            if not srcs:
                print(f"⚠️  未找到第 {ch['id']} 章源文件：{src_part_dir}")
                continue
            ch_lastmod = git_lastmod(f"book/manuscript/chapter-{ch['id']:02d}")
            ch_html = render_divider_inline(chapter_divider_context(part, i, ch))
            (out_dir / f"chapter-{ch['id']}.md").write_text(
                convert_chapter(
                    srcs[0], ch["id"], ch["title"], ch.get("description", ""),
                    date_modified=ch_lastmod, divider_html=ch_html,
                ),
                encoding="utf-8",
            )

    # 附录
    appendix_dir = DOCS / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    (appendix_dir / "index.md").write_text(
        convert_simple(OUTPUT / "08-附录.md", "附录", date_modified=global_lastmod),
        encoding="utf-8",
    )

    # 后处理：注入图片 width/height 防 CLS
    add_img_dimensions_to_pages(img_dims)

    # sidebar
    VITEPRESS.mkdir(parents=True, exist_ok=True)
    (VITEPRESS / "sidebar.ts").write_text(gen_sidebar_ts(parts), encoding="utf-8")

    # 全书插图清单（图库页数据源）
    manifest = gen_figures_manifest(parts)
    (PUBLIC / "figures-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    n_ch = sum(len(p["chapters"]) for p in parts)
    print(f"✓ 转换完成：{n_ch} 章 + 卷首 + 附录 → {DOCS.relative_to(ROOT)}")
    print(f"  静态资源：figures/ dividers/ → {PUBLIC.relative_to(ROOT)}/")
    print(f"  每页注入 dateModified（git 历史）")


def watch() -> None:
    """监听插图源/配置/扉页/封面改动，自动重跑转换（配合 vitepress dev 实现热更新）。

    用法：.venv/bin/python scripts/build_web.py --watch
    零依赖轮询实现：改动后重跑 main()，vitepress dev 检测 docs/ 变化自动刷新浏览器。
    注意：手稿（book/manuscript）改动需先跑 book-builder build，再回到本监听。
    """
    import time

    watch_roots = [
        ROOT / "book" / "figures",
        ROOT / "book" / "config",
        ROOT / "book" / "dividers",
        ROOT / "book" / "assets",
    ]

    def snapshot() -> dict[str, float]:
        sig: dict[str, float] = {}
        for root in watch_roots:
            if not root.exists():
                continue
            for f in root.rglob("*"):
                if f.is_file():
                    try:
                        sig[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        return sig

    prev = snapshot()
    print("👀 监听插图源 / 配置 / 扉页 / 封面改动，自动重建 docs …（Ctrl+C 退出）")
    print("   配合 `vitepress dev docs` 使用：改动后自动转换，浏览器自动刷新。\n")
    try:
        while True:
            time.sleep(1.5)
            cur = snapshot()
            if cur == prev:
                continue
            added = [p for p in cur if p not in prev]
            removed = [p for p in prev if p not in cur]
            changed = [p for p in cur if p in prev and cur[p] != prev[p]]
            print(
                f"🔄 检测到 {len(added) + len(removed) + len(changed)} 个文件改动"
                f"（新增 {len(added)} / 删除 {len(removed)} / 修改 {len(changed)}），重新转换…"
            )
            try:
                main()
            except SystemExit as e:
                print(f"⚠️  转换中止：{e}")
                continue
            prev = snapshot()
            print("✓ 已更新，等待下次改动…\n")
    except KeyboardInterrupt:
        print("\n已停止监听。")


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        main()
