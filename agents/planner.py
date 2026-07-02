"""
Planner Agent - 大纲规划 + 伏笔设计
"""

from __future__ import annotations

from typing import Any

from core.state import BookState, ForeshadowItem, PartPlan

from .base import BaseAgent

_PLANNER_SYSTEM = """你是一位资深的物联网技术书籍策划编辑。
你的任务是根据书籍主题和章节框架，生成：
1. 每章的详细大纲（含小节划分，最多 4 层子章节）
2. 全书伏笔规划表（在哪些章节埋下伏笔，在哪些章节回收）

## 子章节编号规则
- 第一层: {part_prefix}.{chapter_id} 标题
- 第二层: {part_prefix}.{chapter_id}.{sub_id} 标题
- 第三层: {part_prefix}.{chapter_id}.{sub_id}.{sub_id2} 标题
- 第四层（最深）: {part_prefix}.{chapter_id}.{sub_id}.{sub_id2}.{sub_id3} 标题

## 伏笔设计原则
- 伏笔要自然，不能生硬
- 前面章节提到的技术问题或现象，在后面章节给出解答
- 基础篇埋下技术疑问，技术篇解答
- 技术篇留下应用悬念，应用篇展开
- 每个伏笔要有明确的埋入点和回收点

输出严格的 JSON 格式。"""


class PlannerAgent(BaseAgent):
    """大纲规划 Agent"""

    def plan(self, state: BookState) -> tuple[list[PartPlan], list[ForeshadowItem]]:
        """执行规划，返回 (更新后的 parts, 伏笔列表)"""
        parts_desc: list[str] = []
        for part in state.parts:
            ch_list = [f"  第{ch.id}章 {ch.title}: {ch.summary}" for ch in part.chapters]
            parts_desc.append(f"\n【{part.name}】(编号前缀: {part.prefix})\n" + "\n".join(ch_list))

        user_prompt = f"""请为以下书籍生成详细大纲和伏笔规划。

# 书籍信息
- 书名: {state.book_title}
- 副标题: {state.book_subtitle}

# 章节框架
{chr(10).join(parts_desc)}

# 风格要求
- {state.style.tone}
- 术语规则: {state.style.terminology_rule}

请输出以下 JSON 格式：
```json
{{
  "parts": [
    {{
      "name": "基础篇",
      "chapters": [
        {{
          "id": 1,
          "outline": "详细大纲，包含所有子章节，使用编号如 一.1.1 标题",
          "key_points": ["要点1", "要点2"]
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
```"""

        self.logger.info("开始生成大纲和伏笔规划...")
        try:
            data = self.llm.chat_json(_PLANNER_SYSTEM, user_prompt, temperature=0.8)
        except ValueError:
            self.logger.error("大纲 JSON 解析失败")
            return state.parts, []

        raw_parts = _dict_items(data.get("parts"))
        raw_foreshadows = _dict_items(data.get("foreshadows"))

        # 更新 parts
        parts = []
        for part_data in raw_parts:
            orig_part = next((p for p in state.parts if p.name == part_data.get("name", "")), None)
            if orig_part is None:
                continue
            chapters = []
            for ch_data in _dict_items(part_data.get("chapters")):
                ch_id = ch_data.get("id")
                orig_ch = next((c for c in orig_part.chapters if c.id == ch_id), None)
                if orig_ch is None:
                    continue
                orig_ch.outline = str(ch_data.get("outline", ""))
                orig_ch.key_points = [str(item) for item in _list_items(ch_data.get("key_points"))]
                chapters.append(orig_ch)
            parts.append(type(orig_part)(name=orig_part.name, prefix=orig_part.prefix, chapters=chapters))

        foreshadows = [
            ForeshadowItem(
                id=str(fs.get("id", "")),
                description=str(fs.get("description", "")),
                planted_chapter=_int_value(fs.get("planted_chapter")),
                planned_resolve_chapter=_int_value(fs.get("planned_resolve_chapter")),
            )
            for fs in raw_foreshadows
        ]

        self.logger.info("大纲生成完成: %d 篇, %d 个伏笔", len(parts), len(foreshadows))
        return parts, foreshadows


def _dict_items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list_items(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0
