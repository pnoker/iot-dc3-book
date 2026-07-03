"""
Plan Reviewer Agent - 大纲质量门

大纲是全书质量的地基：章节切分、伏笔布局、知识递进都在此定死，一旦平庸，
后续所有章节都建在坏地基上，且章节内修订无法回改大纲。本 Agent 对多个候选大纲
打分择优，不达标则驳回要求重规划，使大纲环节成为真正的质量门而非无条件放行。
"""

from __future__ import annotations

from typing import Any

from core.state import BookState
from .base import BaseAgent

_PLAN_REVIEWER_SYSTEM = """你是一位资深的技术书籍策划总监，负责评审全书大纲方案。

## 评审维度（各 0-10）
1. structure: 章节切分是否合理、粒度均衡、无重叠无遗漏
2. progression: 基础→技术→应用的知识递进是否顺畅
3. foreshadow: 伏笔布局是否自然、埋入与回收章节配对合理
4. coverage: 是否完整覆盖主题应有的核心知识
5. differentiation: 各章要点是否边界清晰、避免跨章重复

## 任务
给定若干候选大纲方案，逐个打分，选出综合最优的一个（best_index，从 0 开始）。
若最优方案仍存在结构性缺陷（overall_score < 7），pass=false 并说明需重新规划的理由。

## 输出格式
```json
{
  "pass": true,
  "best_index": 0,
  "scores": [
    {"index": 0, "overall_score": 8, "dimension_scores": {"structure": 8, "progression": 8, "foreshadow": 7, "coverage": 8, "differentiation": 8}}
  ],
  "reason": "择优与判定理由"
}
```

## 判定规则
- 选中方案 overall_score < 7: pass = false（要求重新规划）"""


class PlanReviewerAgent(BaseAgent):
    """大纲评审 Agent"""

    def review(self, state: BookState, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """对候选大纲打分择优。返回 {pass, best_index, scores, reason}。"""
        if not candidates:
            return {"pass": False, "best_index": -1, "scores": [], "reason": "无候选大纲"}
        if len(candidates) == 1:
            # 单候选无从比较，仍打分判定是否达标
            listing = _format_candidate(0, candidates[0])
        else:
            listing = "\n\n".join(_format_candidate(i, c) for i, c in enumerate(candidates))

        user_prompt = f"""请评审以下 {len(candidates)} 个候选大纲方案。

# 书籍信息
- 书名: {state.book_title}
- 副标题: {state.book_subtitle}

# 候选方案
{listing}

请输出严格 JSON。"""

        self.logger.info("评审 %d 个候选大纲...", len(candidates))
        try:
            result = self.llm.chat_json(_PLAN_REVIEWER_SYSTEM, user_prompt, temperature=0.2)
        except ValueError:
            self.logger.error("大纲评审报告解析失败，默认选用首个候选")
            return {"pass": True, "best_index": 0, "scores": [], "reason": "评审解析失败，回退首个候选"}
        return _normalize_result(result, len(candidates))


def _format_candidate(index: int, candidate: dict[str, Any]) -> str:
    """把一个候选大纲（{parts, foreshadows}）格式化为可评审文本。"""
    lines = [f"## 候选 {index}"]
    for part in candidate.get("parts", []):
        lines.append(f"【{part.get('name', '')}】")
        for ch in part.get("chapters", []):
            outline = str(ch.get("outline", ""))[:200]
            points = "、".join(str(p) for p in ch.get("key_points", []))
            lines.append(f"  第{ch.get('id')}章 大纲: {outline} | 要点: {points}")
    fss = candidate.get("foreshadows", [])
    lines.append(f"  伏笔 {len(fss)} 个: " + "；".join(
        f"{fs.get('id')}(第{fs.get('planted_chapter')}→{fs.get('planned_resolve_chapter')}章)" for fs in fss
    ))
    return "\n".join(lines)


def _normalize_result(result: dict[str, Any], n: int) -> dict[str, Any]:
    """规整评审结果，确保 best_index 合法。"""
    best = result.get("best_index")
    if not isinstance(best, int) or not (0 <= best < n):
        best = 0
    return {
        "pass": bool(result.get("pass", True)),
        "best_index": best,
        "scores": result.get("scores", []),
        "reason": str(result.get("reason", "")),
    }
