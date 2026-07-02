"""
输出模块 - 将书稿生成为结构化的 Markdown 文件
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.log import get_logger
from core.state import BookState

logger = get_logger("output")


def generate_output(state: BookState, output_dir: str, cfg: dict[str, Any] | None = None) -> str:
    """
    将全书内容输出为层级化的 Markdown 文件结构。

    输出结构：
    output/
    ├── 00-封面.md
    ├── 01-作者简介.md
    ├── 02-序.md
    ├── 03-导读.md
    ├── 04-目录.md
    ├── 05-基础篇/
    │   ├── 01-xxx.md
    │   └── ...
    ├── 06-技术篇/
    ├── 07-应用篇/
    ├── 08-附录.md
    ├── 09-伏笔报告.md
    └── 10-终审报告.md
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    _write_file(out / "00-封面.md", _generate_cover(state))

    if cfg and cfg.get("author", {}).get("profile"):
        _write_file(out / "01-作者简介.md", _generate_author_profile(cfg["author"]["profile"]))

    if cfg and cfg.get("author", {}).get("preface"):
        _write_file(out / "02-序.md", _generate_preface(cfg["author"]["preface"]))
        _write_file(out / "03-导读.md", _generate_reading_guide(cfg["author"]["preface"], state))

    _write_file(out / "04-目录.md", state.toc_markdown or _generate_toc(state))

    part_dirs = ["05-基础篇", "06-技术篇", "07-应用篇"]
    for part_idx, part in enumerate(state.parts):
        dir_name = part_dirs[part_idx] if part_idx < len(part_dirs) else f"{part_idx + 1:02d}-{part.name}"
        part_dir = out / dir_name
        part_dir.mkdir(parents=True, exist_ok=True)
        for chapter in part.chapters:
            content = state.get_chapter_content(chapter.id)
            if content:
                filename = f"{chapter.id:02d}-{chapter.title}.md"
                _write_file(part_dir / filename, content.markdown)

    _write_file(out / "08-附录.md", _generate_appendix())
    _write_file(out / "09-伏笔报告.md", _generate_foreshadow_report(state))

    if state.final_report:
        _write_file(out / "10-终审报告.md", state.final_report)

    logger.info("输出完成: %s", out)
    return str(out)


def _write_file(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug("已生成: %s", path)


def _generate_cover(state: BookState) -> str:
    return f"""# {state.book_title}

## {state.book_subtitle}

---

**作者**: {state.author}

**版本**: 第一版

---
"""


def _generate_author_profile(profile: dict[str, Any]) -> str:
    expertise = "\n".join(f"- {e}" for e in profile.get("expertise", []))
    return f"""# 关于作者

## {profile.get("name", "")}

**{profile.get("title", "")}**

{profile.get("bio", "").strip()}

### 核心领域

{expertise}

### 开源项目

**[{profile.get("project", "")}]({profile.get("project_url", "")})**

{profile.get("project_description", "").strip()}
"""


def _generate_preface(preface: dict[str, Any]) -> str:
    return f"""# {preface.get("title", "序")}

{preface.get("content", "").strip()}
"""


def _generate_reading_guide(preface: dict[str, Any], state: BookState) -> str:
    theme = preface.get("theme", "").strip()
    parts_info = []
    for part in state.parts:
        chapters = ", ".join(f"第{ch.id}章《{ch.title}》" for ch in part.chapters)
        parts_info.append(f"- **{part.name}**（{chapters}）")
    return f"""# 导读

{theme}

## 全书结构

{chr(10).join(parts_info)}

## 阅读建议

- **快速浏览**：先读每章的引言和本章小结，建立全局认知
- **深入学习**：按顺序阅读，每章末尾的思考与练习帮助巩固
- **按需查阅**：根据实际工作需要，直接跳转到相关章节
- **结合实践**：书中涉及的 IoT DC3 项目源码可在 GitHub 获取，建议边读边动手

## 本书约定

- 首次出现的专业术语附英文原文和简要解释
- 代码示例使用 fenced code block 并标注语言
- 图表按 `图X-X` / `表X-X` 编号
- 标题层级：`#` 篇名 → `##` 章名 → `###` 节名 → `####` 子节名
"""


def _generate_toc(state: BookState) -> str:
    lines = ["# 目录\n"]
    lines.append("- [关于作者](01-作者简介.md)")
    lines.append("- [序](02-序.md)")
    lines.append("- [导读](03-导读.md)")
    lines.append("")
    for _pi, part in enumerate(state.parts):
        lines.append(f"## {part.name}\n")
        for ch in part.chapters:
            lines.append(f"- 第{ch.id}章 {ch.title}")
        lines.append("")
    lines.append("- [附录](08-附录.md)")
    return "\n".join(lines)


def _generate_appendix() -> str:
    return """# 附录

## A. 术语表

（根据全书内容自动生成）

## B. 参考文献

（根据引用的参考资料自动生成）

## C. 索引

（根据关键词自动生成）
"""


def _generate_foreshadow_report(state: BookState) -> str:
    lines = ["# 伏笔报告\n"]
    lines.append("| ID | 描述 | 埋入章节 | 计划回收 | 状态 |")
    lines.append("|------|------|----------|----------|------|")
    for fs in state.foreshadows:
        lines.append(
            f"| {fs.id} | {fs.description} | 第{fs.planted_chapter}章 | 第{fs.planned_resolve_chapter}章 | {fs.status} |"
        )
    lines.append(f"\n总计: {len(state.foreshadows)} 个伏笔")
    resolved = sum(1 for f in state.foreshadows if f.status == "resolved")
    lines.append(f"已回收: {resolved} / {len(state.foreshadows)}")
    return "\n".join(lines)
