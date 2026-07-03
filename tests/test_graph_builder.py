from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.state import BookState, ChapterPlan, PartPlan
from core.state_validation import IncompleteBookStateError
from graph.builder import BookWriterGraph


class _CompletedIncompleteGraph:
    def __init__(self) -> None:
        self.invoked = False

    def get_state(self, config: dict[str, object]) -> object:
        state = BookState(
            current_phase="completed",
            parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述")])],
        )
        return SimpleNamespace(values=state.model_dump(), next=())

    def invoke(self, state: object, config: dict[str, object]) -> dict[str, object]:
        self.invoked = True
        return {}


def test_run_rejects_incomplete_completed_checkpoint_without_restarting() -> None:
    writer = object.__new__(BookWriterGraph)
    graph = _CompletedIncompleteGraph()
    writer.graph = graph

    with pytest.raises(IncompleteBookStateError, match="已写章节 0/1"):
        writer.run()

    assert graph.invoked is False


def test_graph_compiles_with_all_quality_gate_nodes_connected() -> None:
    """冒烟：新图（大纲门 / 合并质量门 / 终审门）能被 LangGraph 编译且节点齐全。"""
    graph = BookWriterGraph("config")
    nodes = set(graph.graph.get_graph().nodes.keys())

    # 三处质量门重构引入的关键节点必须在位且连通
    expected = {
        "planning",
        "plan_review",
        "fact_check",
        "style_check",
        "editor_review",
        "quality_gate",
        "revise",
        "final_review",
        "final_revise",
        "output",
    }
    assert expected <= nodes
