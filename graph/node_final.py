"""
终审与输出节点

终审是全书级质量门，不再是事后报告：Director 列出需返修章节，未达轮次上限时
回到 final_revise 逐章返修并重审，闭合「发现全书级问题→修复」的回路；
达上限或无需返修才放行到 output。
"""

from __future__ import annotations

import json
from typing import Any

from core.config import get_config_paths
from core.config_models import AppConfig
from core.log import get_logger
from core.output import generate_output
from core.state import BookState
from core.state_validation import require_complete_book_state
from core.wordcount import count_words

logger = get_logger("nodes")


def node_final_review(state: BookState | dict[str, Any], director: Any) -> dict[str, Any]:
    """终审门：生成报告并判定是否需要全书级返修。"""
    logger.info("📋 [终审] 全书终审中...")
    s = BookState(**state) if isinstance(state, dict) else state
    result = director.final_review(s)
    report = _format_report(result)

    revise_ids = _extract_revise_chapters(result, s)
    if revise_ids and s.final_revision_round < s.max_final_revision_round:
        logger.warning("⚠️ [终审门] 需返修章节 %s，第 %d 轮返修...", revise_ids, s.final_revision_round + 1)
        # 把终审反馈写入对应章节，驱动 Writer 返修
        for ch_id in revise_ids:
            content = s.get_chapter_content(ch_id)
            if content:
                content.review_feedback = _chapter_final_feedback(result, ch_id)
                s.upsert_chapter_content(content)
        return {
            "chapters": [c.model_dump() for c in s.chapters],
            "final_report": report,
            "final_revision_chapters": revise_ids,
        }
    if revise_ids:
        logger.warning("⚠️ [终审门] 返修已达上限 %d，接受当前版本输出。", s.max_final_revision_round)
    return {"final_report": report, "final_revision_chapters": [], "current_phase": "completed"}


def node_final_revise(state: BookState | dict[str, Any], writer: Any) -> dict[str, Any]:
    """逐章执行终审返修，完成后清空待返修列表并回到终审重审。"""
    s = BookState(**state) if isinstance(state, dict) else state
    for ch_id in s.final_revision_chapters:
        if not s.set_current_chapter_by_id(ch_id):
            continue
        content = s.get_chapter_content(ch_id)
        if not content or not content.review_feedback:
            continue
        logger.info("✏️ [终审返修] 修改第%d章...", ch_id)
        markdown = writer.revise(s, content.review_feedback)
        content.markdown = markdown
        content.word_count = count_words(markdown)
        content.revision_count += 1
        content.review_feedback = ""
        s.upsert_chapter_content(content)
        s.clear_chapter_feedback(ch_id)
    return {
        "chapters": [c.model_dump() for c in s.chapters],
        "final_revision_chapters": [],
        "final_revision_round": s.final_revision_round + 1,
    }


def node_output(state: BookState | dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    """输出文件"""
    s = BookState(**state) if isinstance(state, dict) else state
    require_complete_book_state(s)
    output_dir = str(get_config_paths(cfg).output_dir)
    logger.info("📦 [输出] 生成文件到 %s...", output_dir)
    generate_output(s, output_dir, cfg.model_dump(mode="python"))
    logger.info("🎉 全书写作完成！")
    return {"output_dir": output_dir}


def _format_report(result: dict[str, Any]) -> str:
    return f"""# 终审报告

- 总分: {result.get("overall_score", "N/A")}/10
- 通过: {"✅ 是" if result.get("pass") else "❌ 否"}

## 评分明细
{json.dumps(result.get("dimension_scores", {}), ensure_ascii=False, indent=2)}

## 总结
{result.get("summary", "")}

## 改进建议
{chr(10).join(f"- {s}" for s in result.get("suggestions", []))}
"""


def _extract_revise_chapters(result: dict[str, Any], state: BookState) -> list[int]:
    """从终审报告提取需返修的合法章节 id（去重、须为已写章节）。"""
    raw = result.get("revise_chapters")
    if not isinstance(raw, list):
        return []
    valid_ids = {ch.chapter_id for ch in state.chapters}
    ids: list[int] = []
    for item in raw:
        ch_id = item.get("chapter_id") if isinstance(item, dict) else None
        if isinstance(ch_id, int) and ch_id in valid_ids and ch_id not in ids:
            ids.append(ch_id)
    return ids


def _chapter_final_feedback(result: dict[str, Any], chapter_id: int) -> str:
    """组装某章的终审返修反馈：优先用 revise_chapters 的 reason，附全书建议。"""
    reason = ""
    for item in result.get("revise_chapters", []):
        if isinstance(item, dict) and item.get("chapter_id") == chapter_id:
            reason = str(item.get("reason", ""))
            break
    suggestions = "；".join(str(s) for s in result.get("suggestions", []))
    return json.dumps(
        {"source": "final_review", "reason": reason, "book_suggestions": suggestions},
        ensure_ascii=False,
    )
