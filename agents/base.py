"""
Agent 基类和共用工具
"""

from __future__ import annotations

import json

from core.llm_client import LLMClient
from core.log import get_logger
from core.state import BookState, StyleConfig


class BaseAgent:
    """Agent 基类"""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = get_logger(self.__class__.__name__)

    def _build_style_prompt(self, style: StyleConfig) -> str:
        """构建风格规范提示词"""
        forbidden = "、".join(style.forbidden_words) if style.forbidden_words else "无"
        structure = "\n".join(f"  - {s}" for s in style.chapter_structure) if style.chapter_structure else "无"
        format_rules = "\n".join(f"  {k}: {v}" for k, v in style.format_rules.items()) if style.format_rules else "无"
        illustration_rules = self._build_illustration_prompt(style)
        return f"""## 写作风格规范
- 语气风格: {style.tone}
- 叙述视角: {style.perspective}
- 术语规则: {style.terminology_rule}
- 目标字数: {style.target_words_per_chapter}
- 禁用词汇: {forbidden}
- 章节结构:
{structure}
- 格式规范:
{format_rules}
{illustration_rules}"""

    def _build_illustration_prompt(self, style: StyleConfig) -> str:
        """构建全书统一图表规格提示词。"""
        if not style.illustrations:
            return ""
        marker = str(style.illustrations.get("marker", "book-figure"))
        rules = json.dumps(style.illustrations, ensure_ascii=False, indent=2)
        return f"""

## 配图规格标记
- 需要架构图、时序图、流程图、数据流图、金字塔图、分层图、拓扑图、生命周期图、矩阵图或时间线时，必须输出 fenced code block：```{marker}。
- `{marker}` 代码块只描述图表规格，供后续 HTML/SVG 统一绘制；不要在正文中生成 Markdown 图片路径、Mermaid、SVG、HTML 或 ASCII 图。
- 图表规格必须包含图名、用途、布局、元素、关系、图例、图注和渲染说明；配色和视觉语义必须遵守以下全书统一配置。
```json
{rules}
```"""

    def _build_foreshadow_prompt(self, state: BookState) -> str:
        """构建伏笔提示词"""
        planted = state.get_planted_foreshadows()
        if not planted:
            return "## 伏笔状态\n当前无未回收伏笔。"
        lines = ["## 未回收伏笔（需要在后续章节中呼应）"]
        for f in planted:
            lines.append(
                f"  - [{f.id}] 第{f.planted_chapter}章埋入: {f.description}（计划在第{f.planned_resolve_chapter}章回收）"
            )
        return "\n".join(lines)

    def _build_references_prompt(self, state: BookState) -> str:
        """构建参考资料提示词"""
        if not state.reference_chunks:
            return "## 参考资料\n无相关参考。"
        lines = ["## 参考资料（融合改写，不要直接引用）"]
        for i, ref in enumerate(state.reference_chunks, 1):
            lines.append(f"### 参考 {i}: {ref.source_file} - {ref.chapter_or_section}")
            lines.append(ref.text[:500])
            lines.append("")
        return "\n".join(lines)
