"""
Agent 基类和共用工具
"""

from __future__ import annotations

import json
from math import ceil
from typing import Any

from core.llm_client import LLMClient
from core.log import get_logger
from core.state import BookState, StyleConfig

# 对抗立场：追加到每个质量门 system 提示，让审查者默认"这一章有问题"，主动证伪而非放行。
_ADVERSARIAL_STANCE = """

## 审查立场
你的默认立场是「这一章存在问题」。请主动尝试证伪、找出不应通过的理由，而不是找理由放行。
只有在你认真尝试挑错后仍找不到实质问题时，才判 pass=true。
本次你只从下面这个特定视角审查，聚焦该视角内的问题，不必覆盖其它视角。"""


def _merge_by_text(reports: list[dict[str, Any]], key: str) -> list[Any]:
    """合并多份报告的列表字段，按内容去重（保留首次出现顺序）。"""
    merged: list[Any] = []
    seen: set[str] = set()
    for report in reports:
        items = report.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else str(item)
            if fingerprint not in seen:
                seen.add(fingerprint)
                merged.append(item)
    return merged


class BaseAgent:
    """Agent 基类"""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.logger = get_logger(self.__class__.__name__)

    def _adversarial_vote(
            self,
            base_system: str,
            user_prompt: str,
            perspectives: list[tuple[str, str]],
            *,
            temperature: float | None = None,
            enabled: bool = True,
    ) -> dict[str, Any]:
        """多视角对抗式复核。

        每个视角以「默认有问题」的立场独立判定一次，再多数表决聚合。
        enabled=False 或视角数 <= 1 时退化为单次自评（向后兼容）。
        """
        if not enabled or len(perspectives) <= 1:
            return self.llm.chat_json(base_system, user_prompt, temperature=temperature)

        reports: list[dict[str, Any]] = []
        for name, lens in perspectives:
            system = f"{base_system}{_ADVERSARIAL_STANCE}\n\n### 本次审查视角：{name}\n{lens}"
            reports.append(self.llm.chat_json(system, user_prompt, temperature=temperature))
        return self._aggregate_votes(reports)

    @staticmethod
    def _aggregate_votes(reports: list[dict[str, Any]]) -> dict[str, Any]:
        """多数表决聚合多份质量报告，保持与单次报告一致的字段形状。"""
        total = len(reports)
        fail_votes = sum(1 for r in reports if r.get("pass") is not True)
        # 多数表决：≥ ceil(N/2) 票判失败才算失败（3 票需 ≥2 票）。
        final_pass = fail_votes < ceil(total / 2)

        merged_issues = _merge_by_text(reports, "issues")
        merged_claims = _merge_by_text(reports, "claims")

        scores = [r["score"] for r in reports if isinstance(r.get("score"), (int, float))]
        summaries = [str(r.get("summary", "")).strip() for r in reports if str(r.get("summary", "")).strip()]

        aggregated: dict[str, Any] = {
            "pass": final_pass,
            "issues": merged_issues,
            "summary": f"{total} 票中 {fail_votes} 票判定不通过。" + " ".join(summaries),
        }
        if merged_claims:
            aggregated["claims"] = merged_claims
        if scores:
            aggregated["score"] = min(scores)
        return aggregated

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
