"""Chapter Architect Agent - 出版级章节蓝图设计。"""

from __future__ import annotations

import re
from typing import Any

from core.state import BlueprintSection, BookState, ChapterBlueprint

from .base import BaseAgent

_ARCHITECT_SYSTEM = """你是一位出版级技术图书章节架构师。
你的任务不是写正文，而是把章节设计成可出版的写作蓝图。

## 设计要求
1. 明确读者读完本章能解决什么工程问题
2. 为每个三级写作单元分配目标字数，合计接近章节目标字数
3. 每章至少规划一个工程案例和必要的代码/配置示例；真实案例必须依赖资料来源，无法确认时规划为“假设场景/示意案例”
4. 标明每节需要的事实证据或资料来源类型，避免无依据断言
5. 不要把每章设计成教科书模板；避免固定“引言/思考与练习”，按章节内容选择自然开篇、工程检查表、实践清单或延伸阅读
6. 每个三级写作单元都必须规划至少一个 `book-figure` 配图规格块，图表类型必须明确，例如 architecture、sequence、flowchart、dataflow、pyramid、layered、topology、lifecycle、matrix、timeline
7. sections 必须是扁平数组，每个元素都是三级写作单元，编号形如 1.1.1、1.1.2；不要只生成 1.1 或 1.2
8. 每个三级写作单元应该足够小，便于断点恢复、人工审稿和局部重写；每章通常 10-18 个三级写作单元
9. 输出严格 JSON，不要输出 Markdown 正文

## 输出格式
```json
{
  "chapter_id": 1,
  "title": "章节标题",
  "target_words": 12000,
  "reader_outcome": "读者读完能完成什么",
  "thesis": "本章核心论点",
  "sections": [
    {
      "section_id": "1.1.1",
      "title": "三级小节标题",
      "parent_title": "所属二级节标题",
      "heading": "1.1.1 三级小节标题",
      "target_words": 1500,
      "purpose": "小节目的",
      "key_points": ["要点"],
      "evidence_needed": ["需要查证的资料"],
    "required_elements": ["book-figure: 图表类型 + 图名 + 主要元素 + 关系 + 图例", "案例/代码/风险分析"]
    }
  ],
  "case_studies": ["案例"],
  "figures": ["图表规划"],
  "tables": ["表格规划"],
  "code_examples": ["代码或配置示例规划"],
  "learning_goals": ["学习目标"]
}
```"""


class ChapterArchitectAgent(BaseAgent):
    """章节蓝图 Agent。"""

    def build_blueprint(self, state: BookState) -> ChapterBlueprint | None:
        """为当前章节生成出版级蓝图。"""
        chapter = state.get_current_chapter()
        part = state.get_current_part()
        if not chapter or not part:
            return None

        target_words = state.writing.target_for_chapter(chapter.id)
        illustration_prompt = self._build_illustration_prompt(state.style)
        user_prompt = f"""请为以下章节设计出版级写作蓝图。

# 书籍信息
- 书名: {state.book_title}
- 副标题: {state.book_subtitle}
- 篇章: {part.name}

# 章节信息
- 第{chapter.id}章 {chapter.title}
- 概述: {chapter.summary}
- 章节目标字数: {target_words}

# 已有大纲
{chapter.outline or "暂无详细大纲，请基于章节概述设计。"}

# 核心要点
{chr(10).join(f"- {point}" for point in chapter.key_points) if chapter.key_points else "暂无，请补齐。"}

# 出版要求
- 面向工程师和高校师生
- 必须包含工程案例、实践建议；无来源案例只能规划为“假设场景/示意案例”
- 每个三级小节都必须配置至少一张图：在 figures 中写清图表编号建议、图表类型、图表目的、主要元素、关系、图例和应放入哪个三级小节；在每个 section.required_elements 中写入 `book-figure: 图表类型 + 图名 + 必备元素`
- 优先使用 architecture、sequence、flowchart、dataflow、pyramid、layered、topology、lifecycle、matrix、timeline 等专业图表类型；不要规划泛泛的“配图”
- 不强制“引言”和“思考与练习”，章节收束可规划为本章小结、工程检查表、实践清单或延伸阅读
- 对统计数据、版本号、平台能力等硬事实标明需要证据
- sections 必须生成到三级目录，section_id 必须以 {chapter.id}. 开头，例如 {chapter.id}.1.1、{chapter.id}.1.2、{chapter.id}.2.1
- 不要生成二级目录作为写作单元；二级目录只能通过 parent_title 表达

{illustration_prompt}

请输出严格 JSON。"""

        self.logger.info("设计第%d章出版级蓝图...", chapter.id)
        try:
            data = self.llm.chat_json(_ARCHITECT_SYSTEM, user_prompt, temperature=0.4)
        except ValueError as exc:
            self.logger.error("章节蓝图 JSON 解析失败")
            raise RuntimeError(f"第{chapter.id}章蓝图 JSON 解析失败，已阻断写作流程。") from exc
        return _normalize_blueprint(data, chapter.id, chapter.title, target_words)


def _normalize_blueprint(data: dict[str, Any], chapter_id: int, title: str, target_words: int) -> ChapterBlueprint:
    sections: list[BlueprintSection] = []
    seen_section_ids: set[str] = set()
    for index, item in enumerate(_required_dict_list(data.get("sections"), "sections")):
        section_id = _required_section_id(item.get("section_id"), chapter_id, f"sections[{index}].section_id")
        if section_id in seen_section_ids:
            raise RuntimeError(f"章节蓝图包含重复三级小节编号: {section_id}")
        seen_section_ids.add(section_id)
        title_value = item.get("title")
        title = _required_str(title_value, f"sections[{index}].title") if title_value is not None else _title_from_heading(
            _required_str(item.get("heading"), f"sections[{index}].heading"), section_id
        )
        heading = _required_str(item.get("heading"), f"sections[{index}].heading")
        if not heading.startswith(section_id):
            heading = f"{section_id} {title}"
        sections.append(
            BlueprintSection(
                section_id=section_id,
                title=title,
                parent_title=_required_str(item.get("parent_title"), f"sections[{index}].parent_title"),
                heading=heading,
                target_words=_required_positive_int(item.get("target_words"), f"sections[{index}].target_words"),
                purpose=_required_str(item.get("purpose"), f"sections[{index}].purpose"),
                key_points=_required_str_list(item.get("key_points"), f"sections[{index}].key_points", allow_empty=False),
                evidence_needed=_required_str_list(item.get("evidence_needed"), f"sections[{index}].evidence_needed"),
                required_elements=_required_str_list(item.get("required_elements"), f"sections[{index}].required_elements"),
            )
        )
    if not sections:
        raise RuntimeError(f"第{chapter_id}章蓝图缺少 sections，已阻断写作流程。")

    return ChapterBlueprint(
        chapter_id=chapter_id,
        title=title,
        target_words=_required_positive_int(data.get("target_words"), "target_words"),
        reader_outcome=_required_str(data.get("reader_outcome"), "reader_outcome"),
        thesis=_required_str(data.get("thesis"), "thesis"),
        sections=sections,
        case_studies=_required_str_list(data.get("case_studies"), "case_studies"),
        figures=_required_str_list(data.get("figures"), "figures"),
        tables=_required_str_list(data.get("tables"), "tables"),
        code_examples=_required_str_list(data.get("code_examples"), "code_examples"),
        learning_goals=_required_str_list(data.get("learning_goals"), "learning_goals"),
    )


def _required_dict_list(value: object, location: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"章节蓝图字段 {location} 必须是数组")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RuntimeError(f"章节蓝图字段 {location}[{index}] 必须是对象")
        result.append(item)
    return result


def _required_str(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"章节蓝图字段 {location} 必须是非空字符串")
    return value.strip()


def _required_positive_int(value: object, location: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"章节蓝图字段 {location} 必须是正整数")
    return value


def _required_section_id(value: object, chapter_id: int, location: str) -> str:
    section_id = _required_str(value, location)
    if not re.fullmatch(rf"{chapter_id}\.\d+\.\d+", section_id):
        raise RuntimeError(f"章节蓝图字段 {location} 必须是三级编号，如 {chapter_id}.1.1")
    return section_id


def _title_from_heading(heading: str, section_id: str) -> str:
    title = heading.removeprefix(section_id).strip()
    if not title:
        raise RuntimeError(f"章节蓝图字段 heading 缺少标题: {heading}")
    return title


def _required_str_list(value: object, location: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RuntimeError(f"章节蓝图字段 {location} 必须是字符串数组")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError(f"章节蓝图字段 {location}[{index}] 必须是非空字符串")
        result.append(item.strip())
    return result
