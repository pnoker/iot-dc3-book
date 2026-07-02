"""
终审与输出节点
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

logger = get_logger("nodes")


def node_final_review(state: BookState | dict[str, Any], director: Any) -> dict[str, Any]:
    """终审"""
    logger.info("📋 [终审] 全书终审中...")
    s = BookState(**state) if isinstance(state, dict) else state
    result = director.final_review(s)
    report = f"""# 终审报告

- 总分: {result.get("overall_score", "N/A")}/10
- 通过: {"✅ 是" if result.get("pass") else "❌ 否"}

## 评分明细
{json.dumps(result.get("dimension_scores", {}), ensure_ascii=False, indent=2)}

## 总结
{result.get("summary", "")}

## 改进建议
{chr(10).join(f"- {s}" for s in result.get("suggestions", []))}
"""
    return {"final_report": report, "current_phase": "completed"}


def node_output(state: BookState | dict[str, Any], cfg: AppConfig) -> dict[str, Any]:
    """输出文件"""
    s = BookState(**state) if isinstance(state, dict) else state
    require_complete_book_state(s)
    output_dir = str(get_config_paths(cfg).output_dir)
    logger.info("📦 [输出] 生成文件到 %s...", output_dir)
    generate_output(s, output_dir, cfg.model_dump(mode="python"))
    logger.info("🎉 全书写作完成！")
    return {"output_dir": output_dir}
