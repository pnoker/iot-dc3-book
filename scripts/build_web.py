#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍手稿 → VitePress Web 站点 转换脚本（手稿即终稿，无导出中间层）。

输入:
  book/manuscript/            中文终稿手稿（章=chapter-XX/X.Y.md 节文件，卷首/附录=preface/*.md、appendix.md）
  book/manuscript-en/         英文终稿手稿（镜像结构，翻译多少生成多少）
  book/config/parts(-en).yaml 篇章结构
  book/figures/               插图：{fig-id}.html 图源 + {fig-id}.yaml 注册表（spec+双语 caption+labels）
  book/assets/ cover.html/cover.png、book/dividers/
输出:
  docs/                       VitePress 源（内容页 + 侧栏 + public 静态资源）

处理:
  1. 手稿中的插图锚点 @[fig-XX-YY] → 内联 theme 化 SVG（明暗主题 + 注册表双语 caption/labels）
  2. 注入 frontmatter（title / description）
  3. 章首插入章扉页（dividers/chapter-XX.html 内联渲染）
  4. 生成篇页 / 全书目录页 / 卷首 / 附录（中英两棵手稿树同构处理）
  5. 生成 docs/.vitepress/sidebar.ts 与 sidebar.en.ts

幂等：每次运行前清空生成产物，保留 .vitepress 手写文件、docs/index.md、docs/en/、public 手写资源。
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
    load_figure_registry, load_figure_svg, gen_figures_css,
    collect_figure_styles, collect_rgba_hexes, audit_color_coverage, FIGURES_DIR,
    has_cjk,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PUBLIC = DOCS / "public"
VITEPRESS = DOCS / ".vitepress"
PARTS_YAML = ROOT / "book" / "config" / "parts.yaml"
DIVIDERS_DIR = ROOT / "book" / "dividers"
MANUSCRIPT = ROOT / "book" / "manuscript"

# 英文版：parts-en.yaml 提供篇章结构，manuscript-en/ 提供已翻译手稿；
# 两者任一缺失则跳过英文生成（sidebar.en.ts 仍输出空骨架，config.ts 的 import 不会悬空）
PARTS_EN_YAML = ROOT / "book" / "config" / "parts-en.yaml"
MANUSCRIPT_EN = ROOT / "book" / "manuscript-en"
EN_DOCS = DOCS / "en"

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

# 卷首单页：(手稿源文件, 输出 slug, 显示名, frontmatter description)
PREFACE = [
    ("author.md", "author", "关于作者",
     "IoT DC3 开源作者张红元——架构师、物联网专家，十余年工业物联网平台研发经验，著有《从工业软件到 AI 智能体》。"),
    ("foreword.md", "foreword", "序",
     "《从工业软件到 AI 智能体》作者自序——阐述写作初衷、全书定位与技术选型考量。"),
    ("guide.md", "guide", "导读",
     "《从工业软件到 AI 智能体》阅读指南——按读者角色（入门开发者、架构师、项目经理）推荐最佳阅读路径。"),
]

# ── 工具 ──────────────────────────────────────────────────────────────────

# 手稿中的插图锚点（单行，语言无关）：@[fig-XX-YY]
# 图的规格/双语文本都在注册表 book/figures/chapter-XX/{fig-id}.yaml 里管理
FIGURE_ANCHOR_RE = re.compile(r"^@\[(fig-\d{2}-\d{2})\]\s*$", re.MULTILINE)

# 手稿节文件名: X.Y.md
_SECTION_FILE_RE = re.compile(r"^\d+\.\d+$")
# 手稿 frontmatter 块
_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


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


def fix_caption(alt: str) -> str:
    """图1-1 → 图 1-1（数字与"图"间加空格，便于阅读）。"""
    return re.sub(r"图(\d)", r"图 \1", alt)


def figure_html(fig_id: str, caption: str, lang: str) -> str:
    """插图锚点 → <figure>：内联 theme 化 SVG（明暗主题 + 注册表 labels 文本覆盖）。

    SVG 源缺失时输出 caption-only 占位并告警（不中断构建）。
    """
    inline = load_figure_svg(fig_id, lang)
    cap = f"  <figcaption>{fix_caption(caption)}</figcaption>\n" if caption else ""
    anchor = f' id="{fig_id}"'
    if inline:
        return (
            f'<figure class="fig fig-svg"{anchor}>\n'
            f'  <div class="fig-svg-body">{inline}</div>\n'
            f"{cap}"
            "</figure>"
        )
    print(f"⚠️  插图缺少 SVG 源：{fig_id}（仅输出图注）")
    return (
        f'<figure class="fig"{anchor}>\n'
        f"{cap}"
        "</figure>"
    )


def resolve_anchors(md: str, lang: str = "zh") -> str:
    """把手稿中的 @[fig-XX-YY] 锚点替换为内联插图。

    figcaption 用图标题（短句；长图注已在 SVG 内部，避免重复）：
    zh 取注册表 title；en 优先 labels.en 中标题键的译文，缺失回落中文标题。
    """
    def repl(m: re.Match) -> str:
        fig_id = m.group(1)
        reg = load_figure_registry(fig_id)
        title = str(reg.get("title") or fig_id)
        if lang != "zh":
            title = _figure_title_en(fig_id, reg) or title
        return figure_html(fig_id, title, lang)

    return FIGURE_ANCHOR_RE.sub(repl, md)


def _figure_title_en(fig_id: str, reg: dict) -> str | None:
    """按语言解析插图短标题:labels.en 精确键 → 去空格归一 → 图号前缀(图N-M)。"""
    labels_en = ((reg.get("labels") or {}).get("en")) or {}
    title = str(reg.get("title") or "")
    if title in labels_en:
        return labels_en[title]
    norm = lambda x: re.sub(r"\s+", "", x)
    for k, v in labels_en.items():
        if norm(k) == norm(title):
            return v
    ch_no, fig_no = fig_id.split("-")[1], fig_id.split("-")[2]
    prefix_re = re.compile(rf"^图\s*{int(ch_no)}-{int(fig_no)}\b")
    for k, v in labels_en.items():
        if prefix_re.match(k):
            return v
    return None


def assemble_chapter(manuscript_dir: Path, cid: int, title: str, h1: str) -> str:
    """组装章手稿：H1 + 可选 _intro.md + 按文件名排序的 X.Y.md 节文件。"""
    ch_dir = Path(manuscript_dir) / f"chapter-{cid:02d}"
    if not ch_dir.exists():
        return ""
    files = sorted(
        (f for f in ch_dir.glob("*.md") if _SECTION_FILE_RE.match(f.stem)),
        key=lambda f: tuple(int(p) for p in f.stem.split(".")),
    )
    if not files:
        return ""
    lines = [h1]
    intro_file = ch_dir / "_intro.md"
    if intro_file.exists():
        intro = intro_file.read_text(encoding="utf-8").strip()
        if intro:
            lines += ["", intro]
    for sf in files:
        text = sf.read_text(encoding="utf-8")
        m = _FM_RE.match(text)
        lines += ["", (text[m.end():].strip() if m else text.strip())]
    return "\n".join(lines).strip()


def gen_figures_manifest(parts: list[dict], chapters_md: dict[int, str]) -> list[dict]:
    """生成全书插图清单（图库页数据源；条目：id/num/title/chapter/url）。

    chapters_md 传入的是锚点已解析为内联插图的章稿，
    因此扫描 <figure … id="fig-XX-YY"> 而非 @[fig] 锚点。
    """
    fig_in_body_re = re.compile(r'<figure[^>]*\bid="(fig-\d{2}-\d{2})"')
    manifest: list[dict] = []
    for part in parts:
        slug, _ = slug_of(part)
        for ch in part["chapters"]:
            md = chapters_md.get(ch["id"])
            if not md:
                continue
            parsed = parse_chapter_md(md)
            for sec in parsed["sections"]:
                if not sec["stem"]:
                    continue
                body = "\n".join(sec["body"])
                for m in fig_in_body_re.finditer(body):
                    fig_id = m.group(1)
                    reg = load_figure_registry(fig_id)
                    title_src = str(reg.get("title") or "")
                    m_num = re.match(r"(图\s*\d+-\d+)\s*(.*)", title_src)
                    if m_num:
                        num, title = fix_caption(m_num.group(1)), m_num.group(2).strip()
                    else:
                        num, title = "", title_src
                    manifest.append({
                        "id": fig_id,
                        "num": num,
                        "title": title,
                        "chapter": ch["id"],
                        "chapterTitle": ch["title"],
                        "url": section_link(slug, ch["id"], sec["stem"]) + "#" + fig_id,
                        "thumb": "",
                    })
    return manifest


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

BYLINE = (
    '<div class="book-byline">'
    "作者：张红元 · © 2016–2026 · 保留所有权利 · "
    '<a href="/copyright">版权与许可</a>'
    "</div>"
)

_FENCE_RE = re.compile(r"^\s*```")
_H1_RE = re.compile(r"^#\s+(.+)$")
_H2_RE = re.compile(r"^##\s+(.+)$")
_H3_RE = re.compile(r"^###\s+(.+)$")


def parse_chapter_md(md: str) -> dict:
    """解析章 markdown → {h1, intro, sections: [{stem, title, body}]}。

    节内 H3/H4 子标题整体降一级（H3→H2、H4→H3），作为页面正文标题。
    """
    lines = md.split("\n")
    in_code = False
    h1 = ""
    intro: list[str] = []
    sections: list[dict] = []
    cur_section: dict | None = None

    def append(line: str) -> None:
        if cur_section is not None:
            cur_section["body"].append(line)
        else:
            intro.append(line)

    for line in lines:
        if _FENCE_RE.match(line):
            append(line)
            in_code = not in_code
            continue
        if in_code:
            append(line)
            continue
        m = _H1_RE.match(line)
        if m:
            h1 = m.group(1).strip()
            continue
        m = _H2_RE.match(line)
        if m:
            title = m.group(1).strip()
            stem = re.match(r"^(\d+\.\d+)(?=\s|$)", title)
            cur_section = {"stem": stem.group(1) if stem else "", "title": title, "body": []}
            sections.append(cur_section)
            continue
        # H3/H4/H5 → 整体降一级
        m = re.match(r"^(#{3,6})\s+(.*)$", line)
        if m:
            line = "#" * (len(m.group(1)) - 1) + " " + m.group(2)
        append(line)

    return {"h1": h1, "intro": "\n".join(intro).strip(), "sections": sections}


def extract_description(body: str, max_len: int = 130) -> str:
    """从正文首段提取 description（跳过标题/代码/列表/表格/HTML）。"""
    text = re.sub(r"^#.*$", "", body, flags=re.M)
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith(("```", ">", "-", "*", "|", "<", "!")):
            continue
        desc = re.sub(r"[\*\`]", "", s).strip()
        if len(desc) >= 20:
            return desc[:max_len] + ("…" if len(desc) > max_len else "")
    return ""


def section_link(slug: str, cid: int, stem: str) -> str:
    return f"/{slug}/chapter-{cid}/{stem.replace('.', '-')}"


def gen_section_nav(prev, nxt) -> str:
    """小节上/下导航。prev/nxt 为 (title, link) 或 None。"""
    parts = []
    if prev:
        parts.append(f'<a class="nav-prev" href="{prev[1]}">← {prev[0]}</a>')
    if nxt:
        parts.append(f'<a class="nav-next" href="{nxt[1]}">{nxt[0]} →</a>')
    if not parts:
        return ""
    return '\n<nav class="section-nav">\n  ' + '\n  '.join(parts) + '\n</nav>\n'


def gen_section_page(sec: dict, slug: str, cid: int, prev, nxt) -> str:
    """生成单个节页面 md（节标题 = 页面 H1，节内 H3/H4 已在 parse 时降级）。"""
    title = sec["title"]
    desc = extract_description("\n".join(sec["body"]))
    body = "\n".join(sec["body"]).strip()
    parts = [fm(title=title, description=desc)]
    parts.append(f"# {title}\n")
    parts.append(BYLINE)
    parts.append("")
    parts.append(body)
    nav = gen_section_nav(prev, nxt)
    if nav:
        parts.append("")
        parts.append(nav)
    return "\n".join(parts) + "\n"


def gen_chapter_overview(desc: str, sections: list[dict]) -> str:
    """把章描述拓展成一段简洁的概览总结（连贯成段，不列节标题）。"""
    topics = []
    for s in sections:
        if not s["stem"]:
            continue
        topic = re.sub(r"^\d+\.\d+\s*", "", s["title"]).strip()
        topic = re.split(r"[：——]", topic)[0].strip()
        if topic:
            topics.append(topic)
    base = desc.rstrip("。！？；\n").rstrip()
    if not topics:
        return base
    if len(topics) == 1:
        chain = f"聚焦{topics[0]}"
    elif len(topics) == 2:
        chain = f"先讲{topics[0]}，最后落在{topics[1]}"
    elif len(topics) <= 5:
        mid = "、".join(topics[1:-1])
        chain = f"先讲{topics[0]}，再到{mid}，最后落在{topics[-1]}"
    else:
        mid = "、".join(topics[1:4]) + f"等{len(topics) - 1}个主题"
        chain = f"先讲{topics[0]}，再到{mid}，最后落在{topics[-1]}"
    return f"{base}。本章{chain}。"


def gen_chapter_index(cid: int, title: str, desc: str, intro: str, sections: list[dict], slug: str, divider_html: str) -> str:
    """生成章首页：章扉页（overview 拓展为概览总结）+ 章引言。

    章标题由扉页视觉承载（frontmatter title 仍保留，供 SEO/标题栏/面包屑），
    扉页的描述扩展成一段连贯总结，正文不再重复 H1，也不另挂导读卡片。
    """
    parts = [fm(title=f"第 {cid} 章　{title}", description=oneline(desc))]
    if divider_html:
        overview = gen_chapter_overview(desc, sections)
        divider_html = re.sub(
            r'<p class="overview">.*?</p>',
            f'<p class="overview">{overview}</p>',
            divider_html,
            flags=re.DOTALL,
        )
        parts.append(
            '<figure class="chapter-divider">\n'
            f'  <div class="divider-body">{divider_html}</div>\n'
            "</figure>\n"
        )
    if intro:
        parts.append(intro)
        parts.append("")
    return "\n".join(parts) + "\n"


def convert_simple(src: Path, title: str, desc: str = "", date_modified: str = "", lang: str = "zh") -> str:
    """卷首/附录等无篇章归属的页面：加 frontmatter，解析插图锚点。"""
    body = resolve_anchors(src.read_text(encoding="utf-8"), lang)
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
            out.append(f"- [第 {ch['id']} 章　{ch['title']}](/{slug}/chapter-{ch['id']}/)")
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
            f"- [第 {ch['id']} 章　{ch['title']}](/{slug}/chapter-{ch['id']}/)"
            f" — {oneline(ch.get('description', ''))}"
        )
    return "\n".join(out) + "\n"


def gen_sidebar_ts(parts: list[dict], parsed_by_cid: dict[int, dict]) -> str:
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
    for i, part in enumerate(parts, start=1):
        slug, _ = slug_of(part)
        L.append("  {")
        L.append(f"    text: {js(part['name'])},")
        L.append("    collapsed: false,")
        L.append("    items: [")
        for ch in part["chapters"]:
            title = f"第 {ch['id']} 章　{ch['title']}"
            link = f"/{slug}/chapter-{ch['id']}/"
            parsed = parsed_by_cid.get(ch["id"])
            if not parsed:
                L.append(f"      {{ text: {js(title)}, link: {js(link)} }},")
                continue
            sec_items = []
            for s in parsed["sections"]:
                if s["stem"]:
                    sec_items.append(
                        f"        {{ text: {js(s['title'])}, link: {js(section_link(slug, ch['id'], s['stem']))} }},"
                    )
            if sec_items:
                L.append("      {")
                L.append(f"        text: {js(title)},")
                L.append(f"        link: {js(link)},")
                L.append("        collapsed: true,")
                L.append("        items: [")
                L.append("\n".join(sec_items))
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


# ── 英文版（/en/ locale）───────────────────────────────────────────────────
#
# 英文译文是中文的镜像：book/config/parts-en.yaml 提供篇章结构，
# book/manuscript-en/chapter-XX/X.Y.md 提供已翻译的节（缺失的章保持纯中文）。
# 复用中文的解析与插图内联管线，仅页面文案与链接前缀不同。

BYLINE_EN = (
    '<div class="book-byline">'
    "Author: Zhang Hongyuan · © 2016–2026 · All Rights Reserved · "
    '<a href="/en/copyright">Copyright &amp; License</a>'
    "</div>"
)

# 英文卷首页：(slug, 显示名, frontmatter description)；源文件 manuscript-en/preface/{slug}.md
PREFACE_EN = [
    ("author", "About the Author",
     "Zhang Hongyuan, creator of the open-source IoT DC3 platform — architect and IoT specialist with over a decade of industrial IoT platform engineering."),
    ("foreword", "Foreword",
     "The author's foreword to From Industrial Software to AI Agents — why the book was written, what it covers, and the thinking behind its technical choices."),
    ("guide", "How to Read This Book",
     "A reading guide to From Industrial Software to AI Agents — recommended paths by reader role: newcomers, platform developers, and AI engineers."),
]

def en_section_link(slug: str, cid: int, stem: str) -> str:
    return f"/en/{slug}/chapter-{cid}/{stem.replace('.', '-')}"


def assemble_en_chapter(cid: int, title: str) -> str:
    """英文章组装（同 assemble_chapter，H1 用英文格式）。"""
    return assemble_chapter(MANUSCRIPT_EN, cid, title, f"# Chapter {cid}. {title}")


def en_part_divider_context(part: dict, part_index: int) -> dict[str, str]:
    themes = ("foundation", "technology", "application")
    return {
        "source_name": f"part-{part_index:02d}.html",
        "kind": "part",
        "theme": themes[(part_index - 1) % len(themes)],
        "number": f"{part_index:02d}",
        "label": f"Part {part.get('prefix', part_index)}",
        "english_label": f"PART {part_index:02d}",
        "title": part["name"],
        "title_main": part["name"],
        "title_sub": "",
        "description": part["description"],
    }


def en_chapter_divider_context(part: dict, part_index: int, chapter: dict) -> dict[str, str]:
    themes = ("foundation", "technology", "application")
    title_main, _, title_sub = chapter["title"].partition(":")
    return {
        "source_name": f"chapter-{chapter['id']:02d}.html",
        "kind": "chapter",
        "theme": themes[(part_index - 1) % len(themes)],
        "number": f"{chapter['id']:02d}",
        "label": f"Chapter {chapter['id']}",
        "english_label": f"CHAPTER {chapter['id']:02d}",
        "title": chapter["title"],
        "title_main": title_main,
        "title_sub": title_sub.strip(),
        "title_sep": ": ",
        "description": chapter["description"],
    }


def gen_en_section_page(sec: dict, prev, nxt) -> str:
    title = sec["title"]
    desc = extract_description("\n".join(sec["body"]))
    body = "\n".join(sec["body"]).strip()
    parts = [fm(title=title, description=desc)]
    parts.append(f"# {title}\n")
    parts.append(BYLINE_EN)
    parts.append("")
    parts.append(body)
    nav = gen_section_nav(prev, nxt)
    if nav:
        parts.append("")
        parts.append(nav)
    return "\n".join(parts) + "\n"


def gen_en_chapter_index(cid: int, title: str, desc: str, intro: str, sections: list[dict], divider_html: str) -> str:
    """英文章首页：扉页 overview 直接使用 parts-en 的章描述（不重复标题与导读卡片）。"""
    parts = [fm(title=f"Chapter {cid}. {title}", description=oneline(desc))]
    if divider_html:
        parts.append(
            '<figure class="chapter-divider">\n'
            f'  <div class="divider-body">{divider_html}</div>\n'
            "</figure>\n"
        )
    if intro:
        parts.append(intro)
        parts.append("")
    return "\n".join(parts) + "\n"


def gen_en_part_index(part: dict, slug: str, divider_html: str, translated: dict[int, dict]) -> str:
    desc = oneline(part.get("description", ""))
    out = [fm(title=part["name"], description=desc)]
    if divider_html:
        out.append(
            '<figure class="part-divider">\n'
            f'  <div class="divider-body">{divider_html}</div>\n'
            "</figure>\n"
        )
    out.append(f"# {part['name']}\n")
    out.append(f"\n> {desc}\n")
    out.append("\n## Chapters in this part\n")
    for ch in part["chapters"]:
        line_title = f"Chapter {ch['id']}. {ch['title']}"
        cdesc = oneline(ch.get("description", ""))
        if ch["id"] in translated:
            out.append(f"- [{line_title}](/en/{slug}/chapter-{ch['id']}/) — {cdesc}")
        else:
            out.append(
                f"- {line_title} — {cdesc}"
                f" *(not yet translated — [read in Chinese](/{slug}/chapter-{ch['id']}/))*"
            )
    return "\n".join(out) + "\n"


def gen_en_contents(parts_zh: list[dict], parts_en: list[dict], translated: dict[int, dict]) -> str:
    out = [fm(title="Contents", description="Table of contents — From Industrial Software to AI Agents")]
    out.append("# Contents\n")
    for part_zh, part_en in zip(parts_zh, parts_en):
        slug, _ = slug_of(part_zh)
        out.append(f"\n## {part_en['name']}\n")
        out.append(f"\n> {oneline(part_en.get('description', ''))}\n")
        out.append("")
        for ch in part_en["chapters"]:
            line_title = f"Chapter {ch['id']}. {ch['title']}"
            if ch["id"] in translated:
                out.append(f"- [{line_title}](/en/{slug}/chapter-{ch['id']}/)")
            else:
                out.append(f"- [{line_title}](/{slug}/chapter-{ch['id']}/) *(Chinese)*")
    return "\n".join(out) + "\n"


def gen_sidebar_en_ts(parts_zh: list[dict], parts_en: list[dict], translated: dict[int, dict]) -> str:
    L = [
        "// 自动生成，请勿手改 —— 由 scripts/build_web.py 产出（英文 /en/ 侧栏，未翻译章节为纯文本）",
        "import type {SidebarItem} from 'vitepress'",
        "",
        "export const sidebarEn: SidebarItem[] = [",
        "  {",
        "    text: 'Front Matter',",
        "    items: [",
    ]
    for slug, label, _desc in PREFACE_EN:
        if (MANUSCRIPT_EN / "preface" / f"{slug}.md").exists():
            L.append(f"      {{ text: {js(label)}, link: '/en/preface/{slug}' }},")
    L.append("      { text: 'Contents', link: '/en/preface/contents' },")
    L.append("    ],")
    L.append("  },")
    for i, (part_zh, part_en) in enumerate(zip(parts_zh, parts_en), start=1):
        slug, _ = slug_of(part_zh)
        L.append("  {")
        L.append(f"    text: {js(part_en['name'])},")
        L.append("    collapsed: false,")
        L.append("    items: [")
        for ch in part_en["chapters"]:
            title = f"Chapter {ch['id']}. {ch['title']}"
            link = f"/en/{slug}/chapter-{ch['id']}/"
            if ch["id"] not in translated:
                L.append(f"      {{ text: {js(title)} }},")
                continue
            parsed = translated[ch["id"]]["parsed"]
            sec_items = [
                f"        {{ text: {js(s['title'])}, link: {js(en_section_link(slug, ch['id'], s['stem']))} }},"
                for s in parsed["sections"] if s["stem"]
            ]
            if sec_items:
                L.append("      {")
                L.append(f"        text: {js(title)},")
                L.append(f"        link: {js(link)},")
                L.append("        collapsed: true,")
                L.append("        items: [")
                L.extend(sec_items)
                L.append("        ],")
                L.append("      },")
            else:
                L.append(f"      {{ text: {js(title)}, link: {js(link)} }},")
        L.append("    ],")
        L.append("  },")
    if (MANUSCRIPT_EN / "appendix.md").exists():
        L.append("  { text: 'Appendix', link: '/en/appendix/' },")
    else:
        L.append("  { text: 'Appendix' },")
    L.append("  { text: 'Copyright & License', link: '/en/copyright' },")
    L.append("]")
    L.append("")
    return "\n".join(L)


EMPTY_SIDEBAR_EN = (
    "// 自动生成，请勿手改 —— 尚无英文手稿（book/manuscript-en/）时的空骨架\n"
    "import type {SidebarItem} from 'vitepress'\n"
    "\n"
    "export const sidebarEn: SidebarItem[] = []\n"
)


def generate_en(parts_zh: list[dict], parts_en: list[dict]) -> None:
    """从 manuscript-en/ 生成 docs/en/ 英文站点（仅已翻译部分；docs/en/index.md、copyright.md 为手写保留）。"""
    if len(parts_zh) != len(parts_en):
        sys.exit(f"parts-en.yaml 篇数({len(parts_en)})与 parts.yaml({len(parts_zh)})不一致。")
    EN_DOCS.mkdir(parents=True, exist_ok=True)
    en_lastmod = git_lastmod("book/manuscript-en/")

    # 卷首（仅生成已有译文的页面）
    preface_dir = EN_DOCS / "preface"
    preface_dir.mkdir(parents=True, exist_ok=True)
    for slug, label, desc in PREFACE_EN:
        src = MANUSCRIPT_EN / "preface" / f"{slug}.md"
        if src.exists():
            (preface_dir / f"{slug}.md").write_text(
                convert_simple(src, label, desc=desc, date_modified=en_lastmod, lang="en"),
                encoding="utf-8",
            )
    # 附录（已翻译才生成）
    appendix_en = MANUSCRIPT_EN / "appendix.md"
    if appendix_en.exists():
        appendix_dir = EN_DOCS / "appendix"
        appendix_dir.mkdir(parents=True, exist_ok=True)
        (appendix_dir / "index.md").write_text(
            convert_simple(appendix_en, "Appendix", date_modified=en_lastmod, lang="en"),
            encoding="utf-8",
        )

    # 解析已翻译章节（按 parts 顺序），构建英文小节线性导航链
    translated: dict[int, dict] = {}
    en_sections: list[dict] = []
    for i, (part_zh, part_en) in enumerate(zip(parts_zh, parts_en), start=1):
        slug, _f = slug_of(part_zh)
        for ch in part_en["chapters"]:
            md = assemble_en_chapter(ch["id"], ch["title"])
            if not md:
                continue
            md = resolve_anchors(md, "en")
            parsed = parse_chapter_md(md)
            if not any(s["stem"] for s in parsed["sections"]):
                continue
            translated[ch["id"]] = {"idx": i, "part_zh": part_zh, "part_en": part_en, "ch": ch, "parsed": parsed}
            for s in parsed["sections"]:
                if s["stem"]:
                    en_sections.append({
                        "slug": slug, "cid": ch["id"], "sec": s,
                        "link": en_section_link(slug, ch["id"], s["stem"]),
                    })

    order = {(x["slug"], x["cid"], x["sec"]["stem"]): k for k, x in enumerate(en_sections)}

    # 篇页
    for i, (part_zh, part_en) in enumerate(zip(parts_zh, parts_en), start=1):
        slug, _ = slug_of(part_zh)
        out_dir = EN_DOCS / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        divider_html = render_divider_inline(en_part_divider_context(part_en, i))
        (out_dir / "index.md").write_text(
            gen_en_part_index(part_en, slug, divider_html, translated), encoding="utf-8"
        )

    # 章首页 + 节页（英文小节之间互相导航）
    for cid, m in translated.items():
        slug, _ = slug_of(m["part_zh"])
        ch, parsed = m["ch"], m["parsed"]
        ch_dir = EN_DOCS / slug / f"chapter-{cid}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        ch_html = render_divider_inline(en_chapter_divider_context(m["part_en"], m["idx"], ch))
        (ch_dir / "index.md").write_text(
            gen_en_chapter_index(
                cid, ch["title"], ch.get("description", ""), parsed["intro"],
                parsed["sections"], ch_html,
            ),
            encoding="utf-8",
        )
        for s in parsed["sections"]:
            if not s["stem"]:
                continue
            idx = order[(slug, cid, s["stem"])]
            prev = en_sections[idx - 1] if idx > 0 else None
            nxt = en_sections[idx + 1] if idx < len(en_sections) - 1 else None
            prev_t = (prev["sec"]["title"], prev["link"]) if prev else None
            nxt_t = (nxt["sec"]["title"], nxt["link"]) if nxt else None
            (ch_dir / f"{s['stem'].replace('.', '-')}.md").write_text(
                gen_en_section_page(s, prev_t, nxt_t), encoding="utf-8"
            )

    # 全书目录页（英文）
    (preface_dir / "contents.md").write_text(
        gen_en_contents(parts_zh, parts_en, translated), encoding="utf-8"
    )

    # 英文侧栏
    (VITEPRESS / "sidebar.en.ts").write_text(
        gen_sidebar_en_ts(parts_zh, parts_en, translated), encoding="utf-8"
    )

    # 审计：英文页内联 SVG 中仍残留的中文标注（缺 figures-i18n 映射或译文不完整）
    fig_anchor_re = re.compile(r'id="(fig-\d{2}-\d{2})"')
    en_fig_ids: set[str] = set()
    for f in EN_DOCS.rglob("*.md"):
        en_fig_ids.update(fig_anchor_re.findall(f.read_text(encoding="utf-8")))
    unresolved = sorted(
        fid for fid in en_fig_ids
        if (svg := load_figure_svg(fid, "en")) and has_cjk(svg)
    )
    if unresolved:
        print("⚠️  英文页以下插图仍含中文标注（补 book/figures-i18n/chapter-XX/ 映射后重跑）：")
        for fid in unresolved:
            print(f"    {fid}")

    n_sec = len(en_sections)
    n_ch = len(translated)
    print(f"✓ 英文版：{n_ch} 章已翻译（{n_sec} 节）→ {EN_DOCS.relative_to(ROOT)}/")
    if n_ch < sum(len(p["chapters"]) for p in parts_zh):
        print("  未翻译章节保持纯中文（侧栏中为纯文本条目）")


# ── 资源 / 清理 ───────────────────────────────────────────────────────────

def clean_generated() -> None:
    """删除脚本上次的生成产物（保留 .vitepress 手写、docs/index.md、public 手写资源、docs/en/index.md 手写首页）。"""
    for d in ["preface", "foundations", "technical", "applications", "appendix"]:
        shutil.rmtree(DOCS / d, ignore_errors=True)
        shutil.rmtree(EN_DOCS / d, ignore_errors=True)
    for d in ["figures", "dividers"]:
        shutil.rmtree(PUBLIC / d, ignore_errors=True)
    for name in ["sidebar.ts", "sidebar.en.ts"]:
        sb = VITEPRESS / name
        if sb.exists():
            sb.unlink()


def copy_assets() -> None:
    """生成/拷贝 public 静态资源（figures.css、figures-svg.json、divider/cover 样式、封面 PNG）。"""
    PUBLIC.mkdir(parents=True, exist_ok=True)
    # 封面 PNG（og:image）：静态资产 book/assets/cover.png，改 cover.html 后手动重渲染
    cover = ROOT / "book" / "assets" / "cover.png"
    if cover.exists():
        shutil.copy2(cover, PUBLIC / "cover.png")
    else:
        print("⚠️  缺少 book/assets/cover.png（og:image 将失效）")
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


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    with open(PARTS_YAML, encoding="utf-8") as f:
        parts = yaml.safe_load(f)

    clean_generated()
    copy_assets()

    # 全局最后修改时间（卷首/附录等无专属 manuscript 的页面回退到此值）
    global_lastmod = git_lastmod("book/manuscript/")

    # 卷首单页（源 = 手稿 manuscript/preface/）
    preface_dir = DOCS / "preface"
    preface_dir.mkdir(parents=True, exist_ok=True)
    for src_name, slug, label, pdesc in PREFACE:
        src = MANUSCRIPT / "preface" / src_name
        if not src.exists():
            print(f"⚠️  缺少卷首手稿：{src}")
            continue
        (preface_dir / f"{slug}.md").write_text(
            convert_simple(src, label, desc=pdesc, date_modified=global_lastmod),
            encoding="utf-8",
        )
    # 全书目录页
    (preface_dir / "contents.md").write_text(gen_contents(parts), encoding="utf-8")

    # 组装全部中文章（手稿 → H1+引言+各节，锚点 → 内联插图）
    chapters_md: dict[int, str] = {}
    parsed_by_cid: dict[int, dict] = {}
    for part in parts:
        for ch in part["chapters"]:
            md = assemble_chapter(MANUSCRIPT, ch["id"], ch["title"], f"# 第{ch['id']}章 {ch['title']}")
            if not md:
                print(f"⚠️  未找到第 {ch['id']} 章手稿：{MANUSCRIPT}/chapter-{ch['id']:02d}/")
                continue
            chapters_md[ch["id"]] = resolve_anchors(md, "zh")

    # 篇与章（两遍：先 parse 全书小节构建线性导航，再生成页面）
    chapters_meta: list[dict] = []
    all_sections: list[dict] = []
    for i, part in enumerate(parts, start=1):
        slug, _ = slug_of(part)
        out_dir = DOCS / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        part_html = render_divider_inline(part_divider_context(part, i))
        (out_dir / "index.md").write_text(
            gen_part_index(part, slug, divider_html=part_html), encoding="utf-8"
        )
        for ch in part["chapters"]:
            md = chapters_md.get(ch["id"])
            if not md:
                continue
            parsed = parse_chapter_md(md)
            parsed_by_cid[ch["id"]] = parsed
            chapters_meta.append({"i": i, "part": part, "slug": slug, "ch": ch, "parsed": parsed})
            for s in parsed["sections"]:
                if s["stem"]:
                    all_sections.append({
                        "slug": slug, "cid": ch["id"], "sec": s,
                        "link": section_link(slug, ch["id"], s["stem"]),
                    })

    order = {(x["slug"], x["cid"], x["sec"]["stem"]): k for k, x in enumerate(all_sections)}
    for m in chapters_meta:
        slug, ch, parsed = m["slug"], m["ch"], m["parsed"]
        ch_dir = DOCS / slug / f"chapter-{ch['id']}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        ch_html = render_divider_inline(chapter_divider_context(m["part"], m["i"], ch))
        (ch_dir / "index.md").write_text(
            gen_chapter_index(
                ch["id"], ch["title"], ch.get("description", ""), parsed["intro"],
                parsed["sections"], slug, ch_html,
            ),
            encoding="utf-8",
        )
        for s in parsed["sections"]:
            if not s["stem"]:
                continue
            idx = order[(slug, ch["id"], s["stem"])]
            prev = all_sections[idx - 1] if idx > 0 else None
            nxt = all_sections[idx + 1] if idx < len(all_sections) - 1 else None
            prev_t = (prev["sec"]["title"], prev["link"]) if prev else None
            nxt_t = (nxt["sec"]["title"], nxt["link"]) if nxt else None
            (ch_dir / f"{s['stem'].replace('.', '-')}.md").write_text(
                gen_section_page(s, slug, ch["id"], prev_t, nxt_t),
                encoding="utf-8",
            )

    # 附录（源 = 手稿 manuscript/appendix.md）
    appendix_dir = DOCS / "appendix"
    appendix_dir.mkdir(parents=True, exist_ok=True)
    appendix_src = MANUSCRIPT / "appendix.md"
    if appendix_src.exists():
        (appendix_dir / "index.md").write_text(
            convert_simple(appendix_src, "附录", date_modified=global_lastmod),
            encoding="utf-8",
        )

    # sidebar
    VITEPRESS.mkdir(parents=True, exist_ok=True)
    (VITEPRESS / "sidebar.ts").write_text(
        gen_sidebar_ts(parts, parsed_by_cid), encoding="utf-8"
    )

    # 英文版（/en/）：有 manuscript-en 时生成，否则输出空侧栏骨架保证 import 不悬空
    if MANUSCRIPT_EN.exists() and PARTS_EN_YAML.exists():
        with open(PARTS_EN_YAML, encoding="utf-8") as f:
            parts_en = yaml.safe_load(f)
        generate_en(parts, parts_en)
    else:
        (VITEPRESS / "sidebar.en.ts").write_text(EMPTY_SIDEBAR_EN, encoding="utf-8")

    # 全书插图清单（图库页数据源）
    manifest = gen_figures_manifest(parts, chapters_md)
    (PUBLIC / "figures-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    n_ch = len(parsed_by_cid)
    print(f"✓ 转换完成：{n_ch} 章 + 卷首 + 附录 → {DOCS.relative_to(ROOT)}/")
    print(f"  插图锚点 → 内联 SVG（明暗主题 + 注册表双语）")
    print(f"  每页注入 dateModified（git 历史）")


def watch() -> None:
    """监听插图源/配置/扉页/封面改动，自动重跑转换（配合 vitepress dev 实现热更新）。

    用法：.venv/bin/python scripts/build_web.py --watch
    零依赖轮询实现：改动后重跑 main()，vitepress dev 检测 docs/ 变化自动刷新浏览器。
    """
    import time

    watch_roots = [
        ROOT / "book" / "manuscript",
        ROOT / "book" / "manuscript-en",
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
