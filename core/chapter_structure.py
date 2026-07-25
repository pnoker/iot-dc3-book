"""章节 Markdown 标题结构的确定性构建与校验。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.state import ChapterPlan, SectionContent, SectionPlan

_SECTION_ID_RE = re.compile(r"^(?P<chapter>\d+)\.(?P<group>\d+)\.(?P<section>\d+)$")
_ATX_HEADING_RE = re.compile(r"^(?P<indent> {0,3})(?P<marks>#{1,6})(?:[ \t]+|$)(?P<title>.*)$")
_FENCE_RE = re.compile(r"^ {0,3}(?P<marks>`{3,}|~{3,}).*$")


@dataclass(frozen=True)
class MarkdownHeading:
    """代码围栏外的 ATX 标题。"""

    level: int
    title: str


@dataclass(frozen=True)
class ChapterHeadingStructure:
    """由章节规划派生的唯一合法 H1/H2/H3 骨架。"""

    chapter_heading: str
    parent_headings: tuple[str, ...]
    section_headings: tuple[str, ...]
    ordered_headings: tuple[MarkdownHeading, ...]


@dataclass(frozen=True)
class _PlannedSection:
    plan: SectionPlan
    group_id: str
    parent_heading: str
    section_heading: str


def expected_chapter_heading_structure(chapter: ChapterPlan) -> ChapterHeadingStructure:
    """校验规划并返回章节应有的 H1/H2/H3。"""
    planned_sections = _validate_and_prepare_sections(chapter)
    chapter_heading = f"第{chapter.id}章 {chapter.title.strip()}"
    parent_headings: list[str] = []
    ordered_headings = [MarkdownHeading(level=1, title=chapter_heading)]
    for item in planned_sections:
        if not parent_headings or parent_headings[-1] != item.parent_heading:
            parent_headings.append(item.parent_heading)
            ordered_headings.append(MarkdownHeading(level=2, title=item.parent_heading))
        ordered_headings.append(MarkdownHeading(level=3, title=item.section_heading))
    return ChapterHeadingStructure(
        chapter_heading=chapter_heading,
        parent_headings=tuple(parent_headings),
        section_headings=tuple(item.section_heading for item in planned_sections),
        ordered_headings=tuple(ordered_headings),
    )


def build_structured_chapter_markdown(chapter: ChapterPlan, contents: list[SectionContent]) -> str:
    """按规划顺序构建章节，并独占管理 H1/H2/H3。"""
    planned_sections = _validate_and_prepare_sections(chapter)
    content_by_id: dict[str, SectionContent] = {}
    for content in contents:
        if content.chapter_id != chapter.id:
            raise RuntimeError(
                f"小节 {content.section_id} 的 chapter_id={content.chapter_id}，与第{chapter.id}章不一致。"
            )
        if content.section_id in content_by_id:
            raise RuntimeError(f"第{chapter.id}章存在重复小节正文: {content.section_id}")
        content_by_id[content.section_id] = content

    planned_ids = {item.plan.id for item in planned_sections}
    missing_ids = [item.plan.id for item in planned_sections if item.plan.id not in content_by_id]
    if missing_ids:
        raise RuntimeError(f"第{chapter.id}章缺少小节正文: {', '.join(missing_ids)}")
    extra_ids = sorted(set(content_by_id) - planned_ids, key=_section_sort_key)
    if extra_ids:
        raise RuntimeError(f"第{chapter.id}章存在规划外小节正文: {', '.join(extra_ids)}")

    blocks = [f"# 第{chapter.id}章 {chapter.title.strip()}"]
    previous_group_id = ""
    for item in planned_sections:
        if item.group_id != previous_group_id:
            blocks.append(f"## {item.parent_heading}")
            previous_group_id = item.group_id
        blocks.append(normalize_section_markdown(item.plan, content_by_id[item.plan.id].markdown))
    return "\n\n".join(block.strip() for block in blocks if block.strip()).strip()


def normalize_section_markdown(section: SectionPlan, markdown: str) -> str:
    """强制小节顶级标题为 H3，并把内部标题约束在 H4-H6。"""
    section_title = _section_title(section)
    canonical_heading = f"### {section.id} {section_title}"
    lines = markdown.strip().splitlines()
    normalized_lines: list[str] = []
    matching_heading_count = 0
    previous_internal_level = 3
    active_fence: tuple[str, int] | None = None

    for line in lines:
        fence = _FENCE_RE.match(line)
        if active_fence is not None:
            normalized_lines.append(line)
            if fence is not None:
                marks = fence.group("marks")
                if marks[0] == active_fence[0] and len(marks) >= active_fence[1]:
                    active_fence = None
            continue
        if fence is not None:
            marks = fence.group("marks")
            active_fence = (marks[0], len(marks))
            normalized_lines.append(line)
            continue

        heading = _ATX_HEADING_RE.match(line)
        if heading is None:
            normalized_lines.append(line)
            continue
        title = _clean_heading_title(heading.group("title"))
        if _heading_has_section_id(title, section.id):
            if any(line.strip() for line in normalized_lines):
                raise RuntimeError(f"小节 {section.id} 的编号标题前存在正文或模型说明。")
            matching_heading_count += 1
            continue
        requested_level = max(4, len(heading.group("marks")))
        normalized_level = min(6, requested_level, previous_internal_level + 1)
        previous_internal_level = normalized_level
        normalized_lines.append(f"{heading.group('indent')}{'#' * normalized_level} {title}")

    if matching_heading_count > 1:
        raise RuntimeError(f"小节 {section.id} 正文包含重复编号标题。")
    body = "\n".join(normalized_lines).strip()
    return f"{canonical_heading}\n\n{body}" if body else canonical_heading


def extract_markdown_headings(markdown: str) -> list[MarkdownHeading]:
    """提取代码围栏外的 ATX 标题。"""
    headings: list[MarkdownHeading] = []
    active_fence: tuple[str, int] | None = None
    for line in markdown.splitlines():
        fence = _FENCE_RE.match(line)
        if active_fence is not None:
            if fence is not None:
                marks = fence.group("marks")
                if marks[0] == active_fence[0] and len(marks) >= active_fence[1]:
                    active_fence = None
            continue
        if fence is not None:
            marks = fence.group("marks")
            active_fence = (marks[0], len(marks))
            continue
        heading = _ATX_HEADING_RE.match(line)
        if heading is None:
            continue
        headings.append(
            MarkdownHeading(
                level=len(heading.group("marks")),
                title=_clean_heading_title(heading.group("title")),
            )
        )
    return headings


def _validate_and_prepare_sections(chapter: ChapterPlan) -> list[_PlannedSection]:
    if not chapter.title.strip():
        raise RuntimeError(f"第{chapter.id}章标题为空。")
    if not chapter.sections:
        raise RuntimeError(f"第{chapter.id}章没有三级小节规划。")

    result: list[_PlannedSection] = []
    parent_titles: dict[str, str] = {}
    previous_key: tuple[int, int, int] | None = None
    seen_ids: set[str] = set()
    for section in chapter.sections:
        match = _SECTION_ID_RE.fullmatch(section.id)
        if match is None or int(match.group("chapter")) != chapter.id or section.chapter_id != chapter.id:
            raise RuntimeError(f"第{chapter.id}章包含非法三级小节编号: {section.id}")
        if section.id in seen_ids:
            raise RuntimeError(f"第{chapter.id}章包含重复三级小节编号: {section.id}")
        seen_ids.add(section.id)
        key = tuple(int(part) for part in section.id.split("."))
        if previous_key is not None and key <= previous_key:
            raise RuntimeError(f"第{chapter.id}章小节顺序未严格递增: {section.id}")
        previous_key = key

        group_id = f"{match.group('chapter')}.{match.group('group')}"
        parent_title = _strip_number_prefix(section.parent_title, group_id)
        if not parent_title:
            raise RuntimeError(f"小节 {section.id} 的 parent_title 为空。")
        existing_parent = parent_titles.get(group_id)
        if existing_parent is not None and existing_parent != parent_title:
            raise RuntimeError(f"二级节 {group_id} 的 parent_title 冲突: {existing_parent!r} != {parent_title!r}。")
        parent_titles[group_id] = parent_title
        result.append(
            _PlannedSection(
                plan=section,
                group_id=group_id,
                parent_heading=f"{group_id} {parent_title}",
                section_heading=f"{section.id} {_section_title(section)}",
            )
        )
    return result


def _section_title(section: SectionPlan) -> str:
    title = _strip_number_prefix(section.title, section.id)
    heading_title = _strip_number_prefix(section.heading, section.id)
    if not title or not heading_title:
        raise RuntimeError(f"小节 {section.id} 的 title 或 heading 为空。")
    if title != heading_title:
        raise RuntimeError(f"小节 {section.id} 的 title 与 heading 不一致: {title!r} != {heading_title!r}。")
    return title


def _strip_number_prefix(value: str, number: str) -> str:
    text = re.sub(r"\s+", " ", value.strip())
    prefix = re.compile(rf"^{re.escape(number)}(?=$|[\s、:：.．\-—])(?:[\s、:：.．\-—]+)?")
    return prefix.sub("", text, count=1).strip()


def _heading_has_section_id(title: str, section_id: str) -> bool:
    return re.match(rf"^{re.escape(section_id)}(?=$|[\s、:：．\-—])", title) is not None


def _clean_heading_title(title: str) -> str:
    return re.sub(r"[ \t]+#+[ \t]*$", "", title).strip()


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in section_id.split("."))
    except ValueError:
        return (10**9,)
