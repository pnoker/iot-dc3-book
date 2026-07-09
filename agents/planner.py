"""
Planner Agent - 大纲规划 + 伏笔设计
"""

from __future__ import annotations

from typing import Any

from core.state import BookState, ChapterPlan, ForeshadowItem, PartPlan

from .base import BaseAgent

_PLANNER_SYSTEM = """你是一位资深的物联网技术书籍策划编辑。
你的任务是生成「全书级」高层规划，不生成章节蓝图或详细小节树。
后续 ChapterArchitect 会为单章生成出版级蓝图；本阶段只决定章节边界、核心论题和伏笔布局。

## 输出约束
- 必须覆盖输入中的所有篇章和所有章节，每章只出现一次。
- part.name 必须逐字复制输入篇章名，不得改名、缩写或合并。
- 每章 outline 必须是单行字符串，80-180 个中文字，使用分号串联 4-6 个论述重点。
- outline 禁止包含换行符、Markdown 标题、四级子章节树、长段落。
- 每章 key_points 输出 3-5 个短语，每个短语不超过 24 个中文字。
- foreshadows 输出 4-8 个，必须自然、具体，回收章节必须晚于埋入章节。
- 输出必须是严格 JSON object，不要 Markdown 代码块，不要解释文字。

## 伏笔设计原则
- 伏笔要自然，不能生硬
- 前面章节提到的技术问题或现象，在后面章节给出解答
- 基础篇埋下技术疑问，技术篇解答
- 技术篇留下应用悬念，应用篇展开
- 每个伏笔要有明确的埋入点和回收点

输出严格的 JSON 格式。"""


class PlannerAgent(BaseAgent):
    """大纲规划 Agent"""

    def plan_candidates(self, state: BookState, n: int = 2) -> list[dict[str, Any]]:
        """生成 n 个候选大纲的原始 JSON（{parts, foreshadows}），供 PlanReviewer 择优。

        全书结构是高杠杆决策，一次成型易平庸；生成多个候选再择优，显著提升地基质量。
        """
        user_prompt = self._build_prompt(state)
        candidates: list[dict[str, Any]] = []
        self.logger.info("开始生成 %d 个候选大纲...", n)
        for i in range(n):
            try:
                # 递增温度制造方案差异，避免 n 个候选雷同
                data = self.llm.chat_json(_PLANNER_SYSTEM, user_prompt, temperature=0.8 + 0.1 * i)
                candidates.append(data)
            except ValueError as exc:
                self.logger.error("第 %d 个候选大纲 JSON 解析失败", i)
                raise RuntimeError(f"第 {i + 1} 个候选大纲 JSON 解析失败，已阻断规划流程。") from exc
        return candidates

    def build_plan(self, state: BookState, data: dict[str, Any]) -> tuple[list[PartPlan], list[ForeshadowItem]]:
        """将一个候选大纲 JSON 落地为 (parts, 伏笔列表)。"""
        raw_parts = _required_dict_list(data.get("parts"), "parts")
        raw_foreshadows = _required_dict_list(data.get("foreshadows"), "foreshadows")
        valid_chapter_ids = {chapter.id for part in state.parts for chapter in part.chapters}

        parts: list[PartPlan] = []
        seen_parts: set[str] = set()
        seen_chapters: set[int] = set()
        for part_data in raw_parts:
            part_name = _required_str(part_data.get("name"), "parts[].name")
            if part_name in seen_parts:
                raise RuntimeError(f"候选大纲包含重复篇章: {part_name}")
            seen_parts.add(part_name)
            orig_part = next((part for part in state.parts if part.name == part_name), None)
            if orig_part is None:
                raise RuntimeError(f"候选大纲包含未知篇章: {part_name}")

            raw_chapters = _required_dict_list(part_data.get("chapters"), f"parts[{part_name}].chapters")
            chapters: list[ChapterPlan] = []
            part_chapter_ids = {chapter.id for chapter in orig_part.chapters}
            for ch_data in raw_chapters:
                ch_id = _required_int(ch_data.get("id"), f"parts[{part_name}].chapters[].id")
                if ch_id in seen_chapters:
                    raise RuntimeError(f"候选大纲包含重复章节: 第{ch_id}章")
                if ch_id not in part_chapter_ids:
                    raise RuntimeError(f"候选大纲第{ch_id}章不属于篇章 {part_name}")
                orig_ch = next(c for c in orig_part.chapters if c.id == ch_id)
                outline = _required_outline(ch_data.get("outline"), f"第{ch_id}章 outline")
                key_points = _required_str_list(
                    ch_data.get("key_points"), f"第{ch_id}章 key_points", max_items=6, max_length=32
                )
                chapters.append(orig_ch.model_copy(update={"outline": outline, "key_points": key_points}))
                seen_chapters.add(ch_id)
            if {chapter.id for chapter in chapters} != part_chapter_ids:
                missing_chapter_ids = sorted(part_chapter_ids - {chapter.id for chapter in chapters})
                raise RuntimeError(f"候选大纲篇章 {part_name} 缺少章节: {missing_chapter_ids}")
            parts.append(type(orig_part)(name=orig_part.name, prefix=orig_part.prefix, chapters=chapters))

        expected_part_names = {part.name for part in state.parts}
        if seen_parts != expected_part_names:
            missing_part_names = sorted(expected_part_names - seen_parts)
            raise RuntimeError(f"候选大纲缺少篇章: {missing_part_names}")

        foreshadows: list[ForeshadowItem] = []
        seen_foreshadows: set[str] = set()
        for fs in raw_foreshadows:
            fs_id = _required_str(fs.get("id"), "foreshadows[].id")
            if fs_id in seen_foreshadows:
                raise RuntimeError(f"候选大纲包含重复伏笔: {fs_id}")
            planted_chapter = _required_int(fs.get("planted_chapter"), f"伏笔 {fs_id} planted_chapter")
            planned_resolve_chapter = _required_int(fs.get("planned_resolve_chapter"), f"伏笔 {fs_id} planned_resolve_chapter")
            if planted_chapter not in valid_chapter_ids or planned_resolve_chapter not in valid_chapter_ids:
                raise RuntimeError(f"伏笔 {fs_id} 引用了不存在的章节")
            if planned_resolve_chapter <= planted_chapter:
                raise RuntimeError(f"伏笔 {fs_id} 的回收章节必须晚于埋入章节")
            foreshadows.append(
                ForeshadowItem(
                    id=fs_id,
                    description=_required_str(fs.get("description"), f"伏笔 {fs_id} description"),
                    planted_chapter=planted_chapter,
                    planned_resolve_chapter=planned_resolve_chapter,
                )
            )
            seen_foreshadows.add(fs_id)

        self.logger.info("大纲落地: %d 篇, %d 个伏笔", len(parts), len(foreshadows))
        return parts, foreshadows

    def _build_prompt(self, state: BookState) -> str:
        parts_desc: list[str] = []
        for part in state.parts:
            ch_list = [f"  第{ch.id}章 {ch.title}: {ch.summary}" for ch in part.chapters]
            parts_desc.append(f"\n【{part.name}】(编号前缀: {part.prefix})\n" + "\n".join(ch_list))

        return f"""请为以下书籍生成全书级紧凑大纲和伏笔规划。

# 书籍信息
- 书名: {state.book_title}
- 副标题: {state.book_subtitle}

# 章节框架
{chr(10).join(parts_desc)}

# 风格要求
- {state.style.tone}
- 术语规则: {state.style.terminology_rule}

请输出以下 JSON 结构。注意：不要输出 Markdown 代码块；outline 必须单行、简洁，详细小节蓝图由后续 Agent 生成。

{{
  "parts": [
    {{
      "name": "必须逐字复制输入篇章名",
      "chapters": [
        {{
          "id": 1,
          "outline": "本章定位；核心论题；工程主线；与前后章节边界；需避免的重复点",
          "key_points": ["核心概念", "工程问题", "实践抓手"]
        }}
      ]
    }}
  ],
  "foreshadows": [
    {{
      "id": "F001",
      "description": "伏笔描述",
      "planted_chapter": 1,
      "planned_resolve_chapter": 6
    }}
  ]
}}
"""


def _required_dict_list(value: object, location: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"候选大纲字段 {location} 必须是数组")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RuntimeError(f"候选大纲字段 {location}[{index}] 必须是对象")
        result.append(item)
    return result


def _required_str(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"候选大纲字段 {location} 必须是非空字符串")
    return value.strip()


def _required_outline(value: object, location: str) -> str:
    outline = _required_str(value, location)
    if "\n" in outline or "\r" in outline:
        raise RuntimeError(f"候选大纲字段 {location} 必须是单行字符串，不得包含换行")
    if len(outline) > 500:
        raise RuntimeError(f"候选大纲字段 {location} 过长，必须保持全书级紧凑规划")
    return outline


def _required_int(value: object, location: str) -> int:
    if not isinstance(value, int):
        raise RuntimeError(f"候选大纲字段 {location} 必须是整数")
    return value


def _required_str_list(
        value: object, location: str, *, max_items: int | None = None, max_length: int | None = None
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"候选大纲字段 {location} 必须是非空字符串数组")
    if max_items is not None and len(value) > max_items:
        raise RuntimeError(f"候选大纲字段 {location} 最多允许 {max_items} 项")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError(f"候选大纲字段 {location}[{index}] 必须是非空字符串")
        text = item.strip()
        if max_length is not None and len(text) > max_length:
            raise RuntimeError(f"候选大纲字段 {location}[{index}] 过长")
        result.append(text)
    return result
