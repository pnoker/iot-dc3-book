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
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

try:
    import yaml
except ImportError:
    sys.exit("缺少 pyyaml，请用 `uv run python scripts/build_web.py` 运行（复用 book venv）。")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
DOCS = ROOT / "docs"
PUBLIC = DOCS / "public"
VITEPRESS = DOCS / ".vitepress"
PARTS_YAML = ROOT / "book" / "config" / "parts.yaml"

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

# 资料溯源标注（写作过程的来源标记，网站不展示）
# ① （资料…）整块：覆盖 [S6]/[参考5]/[S1][S12]/C7-EVAL-02/参考1/自然语言描述 等所有形态
CITE_BLOCK_RE = re.compile(r"（资料：?[^）]+）")
# ② 散落的 [S数字] [参考数字] 标记（不动 [roundId] 等代码占位符）
CITE_MARK_RE = re.compile(r"\[(?:S\d+|参考\d+)\]")


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
    alt, src = m.group(1), m.group(2)
    return (
        "<figure class=\"fig\">\n"
        f'  <img src="{web_src(src)}" alt="{alt}" loading="lazy">\n'
        f"  <figcaption>{fix_caption(alt)}</figcaption>\n"
        "</figure>"
    )


def convert_images(md: str) -> str:
    return IMG_RE.sub(to_figure, md)


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


# ── 页面生成 ──────────────────────────────────────────────────────────────

def convert_chapter(src: Path, cid: int, title: str, desc: str, date_modified: str = "") -> str:
    body = src.read_text(encoding="utf-8")
    body = clean_citations(body)
    body = convert_images(body)
    divider = (
        '\n<figure class="chapter-divider">\n'
        f'  <img src="/dividers/chapter-{cid:02d}.webp" alt="第 {cid} 章扉页" class="no-zoom">\n'
        "</figure>\n"
    )
    # 在第一个 H1 之后插入章扉页
    body = re.sub(r"^# [^\n]+", lambda m: m.group(0) + divider, body, count=1, flags=re.M)
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


def gen_part_index(part: dict, slug: str, divider_img: str) -> str:
    """篇扉页：篇图 + 篇名 + 概述 + 本章清单。"""
    desc = oneline(part.get("description", ""))
    out = [fm(title=part["name"], description=desc)]
    out.append(
        '<figure class="part-divider">\n'
        f'  <img src="/dividers/{divider_img}.webp" alt="{part["name"]}" class="no-zoom">\n'
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
            L.append(f"      {{ text: {js(title)}, link: '/{slug}/chapter-{ch['id']}' }},")
        L.append("    ],")
        L.append("  },")
    L.append("  { text: '附录', link: '/appendix/' },")
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
    for i, part in enumerate(parts):
        slug, divider_img = slug_of(part)
        src_part_dir = OUTPUT / f"0{PART_DIR_OFFSET + i}-{part['name']}"
        out_dir = DOCS / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.md").write_text(gen_part_index(part, slug, divider_img), encoding="utf-8")
        for ch in part["chapters"]:
            srcs = list(src_part_dir.glob(f"{ch['id']:02d}-*.md"))
            if not srcs:
                print(f"⚠️  未找到第 {ch['id']} 章源文件：{src_part_dir}")
                continue
            ch_lastmod = git_lastmod(f"book/manuscript/chapter-{ch['id']:02d}")
            (out_dir / f"chapter-{ch['id']}.md").write_text(
                convert_chapter(
                    srcs[0], ch["id"], ch["title"], ch.get("description", ""),
                    date_modified=ch_lastmod,
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

    n_ch = sum(len(p["chapters"]) for p in parts)
    print(f"✓ 转换完成：{n_ch} 章 + 卷首 + 附录 → {DOCS.relative_to(ROOT)}")
    print(f"  静态资源：figures/ dividers/ → {PUBLIC.relative_to(ROOT)}/")
    print(f"  每页注入 dateModified（git 历史）")


if __name__ == "__main__":
    main()
