"""
状态图构建器 - 组装 LangGraph 并提供公共接口
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agents.director import DirectorAgent
from agents.editor import EditorAgent
from agents.fact_checker import FactCheckerAgent
from agents.plan_reviewer import PlanReviewerAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from agents.style_guard import StyleGuardAgent
from agents.writer import WriterAgent
from core.config import get_config_paths, get_embed_config, get_llm_config, load_app_config
from core.llm_client import LLMClient
from core.log import get_logger
from core.output import generate_output
from core.rag import RAGEngine
from core.rag_contextualize import contextualize_chunk
from core.rag_rerank import rerank_chunks
from core.state import BookState, ChapterContent, ReferenceChunk
from core.state_validation import IncompleteBookStateError, is_complete_book_state, require_complete_book_state
from core.wordcount import count_words
from graph.node_chapter import node_research, node_write
from graph.node_final import node_final_review, node_final_revise, node_output
from graph.node_lifecycle import node_advance_chapter, node_indexing, node_init, node_plan_review, node_planning
from graph.node_quality import (
    node_editor_review,
    node_fact_check,
    node_quality_gate,
    node_revise,
    node_style_check,
)
from graph.routes import (
    route_after_final_review,
    route_after_plan_review,
    route_after_quality_gate,
    route_after_revise,
    route_next_chapter,
)

logger = get_logger("graph")


class BookWriterGraph:
    """
    书籍写作状态图编排器

    流程:
    START → init → indexing → planning → plan_review(大纲质量门, 不过则回退重规划)
        → [research → write → fact_check → style_check → editor_review
           → quality_gate(三门汇总判定) →(fail)revise / (pass)advance_chapter] 循环
        → final_review(终审质量门) →(需返修)final_revise→重审 / (通过)output → END
    """

    def __init__(self, config_path: str = "config") -> None:
        self.cfg = load_app_config(config_path)
        self.paths = get_config_paths(self.cfg)
        self.config_path = config_path

        # 初始化 LLM
        llm_cfg = get_llm_config(self.cfg)
        embed_cfg = get_embed_config(self.cfg)
        self.llm = LLMClient(**llm_cfg, **embed_cfg)

        # 初始化 RAG（rerank / 情境化默认关闭，开启时注入对应 LLM 闭包）
        ref_cfg = self.cfg.references
        reranker = None
        if ref_cfg.rerank_enabled:
            candidates = ref_cfg.rerank_candidates

            def reranker(query: str, chunks: list[ReferenceChunk], top_k: int) -> list[ReferenceChunk]:
                return rerank_chunks(self.llm, query, chunks[:candidates], top_k)

        contextualizer = None
        if ref_cfg.contextualize:
            def contextualizer(source: str, section: str, chunk_text: str) -> str:
                return contextualize_chunk(self.llm, source, section, chunk_text)

        self.rag = RAGEngine(
            embed_fn=self.llm.embed,
            embed_many_fn=self.llm.embed_many,
            chunk_size=ref_cfg.chunk_size,
            chunk_overlap=ref_cfg.chunk_overlap,
            persist_dir=str(self.paths.chroma_dir),
            bm25_path=str(self.paths.bm25_index),
            reranker=reranker,
            contextualizer=contextualizer,
            embed_model=embed_cfg["embed_model"],
        )

        # 初始化 Agent
        self.planner = PlannerAgent(self.llm)
        self.plan_reviewer = PlanReviewerAgent(self.llm)
        self.researcher = ResearchAgent(self.llm, self.rag, query_categories=ref_cfg.query_categories)
        self.writer = WriterAgent(self.llm)
        self.fact_checker = FactCheckerAgent(self.llm, self.rag, query_categories=ref_cfg.query_categories)
        self.editor = EditorAgent(self.llm)
        self.style_guard = StyleGuardAgent(self.llm)
        self.director = DirectorAgent(self.llm)

        # 构建图
        self.graph = self._build_graph()
        logger.info("BookWriterGraph 初始化完成")

    def _build_graph(self) -> Any:
        """构建 LangGraph 状态图"""
        builder = StateGraph(BookState)

        # 节点（使用 lambda 闭包注入依赖）
        builder.add_node("init", lambda s: node_init(s, self.cfg))
        builder.add_node("indexing", lambda s: node_indexing(s, self.cfg, self.rag))
        builder.add_node("planning", lambda s: node_planning(s, self.planner, self.plan_reviewer))
        builder.add_node("plan_review", lambda s: node_plan_review(s))
        builder.add_node("research", lambda s: node_research(s, self.researcher))
        builder.add_node("write", lambda s: node_write(s, self.writer))
        builder.add_node("fact_check", lambda s: node_fact_check(s, self.fact_checker))
        builder.add_node("style_check", lambda s: node_style_check(s, self.style_guard))
        builder.add_node("editor_review", lambda s: node_editor_review(s, self.editor))
        builder.add_node("quality_gate", lambda s: node_quality_gate(s))
        builder.add_node("revise", lambda s: node_revise(s))
        builder.add_node("advance_chapter", lambda s: node_advance_chapter(s))
        builder.add_node("final_review", lambda s: node_final_review(s, self.director))
        builder.add_node("final_revise", lambda s: node_final_revise(s, self.writer))
        builder.add_node("output", lambda s: node_output(s, self.cfg))

        # 边
        builder.add_edge(START, "init")
        builder.add_edge("init", "indexing")
        builder.add_edge("indexing", "planning")
        builder.add_edge("planning", "plan_review")

        # 大纲质量门：不通过则回退重规划
        builder.add_conditional_edges(
            "plan_review",
            route_after_plan_review,
            {
                "approved": "research",
                "revise_plan": "planning",
            },
        )

        # 章节生产：写作后三门顺序评审（纯打标），汇总于 quality_gate 统一判定
        builder.add_edge("research", "write")
        builder.add_edge("write", "fact_check")
        builder.add_edge("fact_check", "style_check")
        builder.add_edge("style_check", "editor_review")
        builder.add_edge("editor_review", "quality_gate")
        builder.add_conditional_edges(
            "quality_gate",
            route_after_quality_gate,
            {
                "pass": "advance_chapter",
                "fail": "revise",
            },
        )
        builder.add_conditional_edges(
            "revise",
            route_after_revise,
            {
                "revise": "write",  # 未达上限：带合并反馈重写
                "advance": "advance_chapter",  # 达上限：止损放行，推进下一章
            },
        )

        builder.add_conditional_edges(
            "advance_chapter",
            route_next_chapter,
            {
                "next": "research",
                "done": "final_review",
            },
        )

        # 终审质量门：有全书级问题则返修重审，否则输出
        builder.add_conditional_edges(
            "final_review",
            route_after_final_review,
            {
                "revise": "final_revise",
                "output": "output",
            },
        )
        builder.add_edge("final_revise", "final_review")
        builder.add_edge("output", END)

        data_dir = self.paths.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(self.paths.checkpoint_db)
        self._db_path = db_path
        conn = sqlite3.connect(db_path, check_same_thread=False)
        self._checkpointer = SqliteSaver(conn=conn)
        self._checkpointer.setup()
        logger.info("Checkpoint 持久化: %s", db_path)
        return builder.compile(checkpointer=self._checkpointer)

    def run(self, thread_id: str = "book-1", fresh: bool = False) -> dict[str, Any]:
        """执行全书写作流程"""
        config = {"configurable": {"thread_id": thread_id}}
        if fresh:
            self.reset_thread(thread_id)
        try:
            snapshot = self.graph.get_state(config)
            if snapshot and snapshot.values and not fresh:
                if not snapshot.next:
                    state = BookState(**snapshot.values)
                    require_complete_book_state(state)
                    logger.info("✅ 任务已完成，无需重复执行。若需重跑请使用 fresh/reset。")
                    return dict(snapshot.values)
                logger.info("🔄 检测到未完成的任务，从中断处继续...")
                return cast("dict[str, Any]", self.graph.invoke(None, config))
        except IncompleteBookStateError:
            raise
        except Exception:
            pass
        logger.info("🚀 开始写作...")
        initial_state = BookState().model_dump()
        return cast("dict[str, Any]", self.graph.invoke(initial_state, config))

    def resume(self, thread_id: str = "book-1", updates: dict[str, Any] | None = None) -> dict[str, Any]:
        """从中断处恢复执行"""
        config = {"configurable": {"thread_id": thread_id}}
        if updates:
            self.graph.update_state(config, updates)
        return cast("dict[str, Any]", self.graph.invoke(None, config))

    def get_book_state(self, thread_id: str = "book-1") -> BookState | None:
        """读取 checkpoint 中的 BookState。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        if not snapshot or not snapshot.values:
            return None
        return BookState(**snapshot.values)

    def get_status(self, thread_id: str = "book-1") -> dict[str, object]:
        """返回线程和 RAG 的运行状态。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        state = BookState(**snapshot.values) if snapshot and snapshot.values else None
        chapter = state.get_current_chapter() if state else None
        return {
            "thread_id": thread_id,
            "has_checkpoint": bool(snapshot and snapshot.values),
            "phase": state.current_phase if state else "not_started",
            "complete": is_complete_book_state(state) if state else False,
            "next_nodes": list(snapshot.next) if snapshot else [],
            "current_chapter": {"id": chapter.id, "title": chapter.title} if chapter else None,
            "chapters_written": len(state.chapters) if state else 0,
            "rag": self.rag.get_status(),
        }

    def export_state(self, thread_id: str, output_file: str) -> None:
        """导出 checkpoint 状态为 JSON，便于人工审阅和备份。"""
        state = self.get_book_state(thread_id)
        if state is None:
            raise ValueError(f"线程不存在或尚未开始: {thread_id}")
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, ensure_ascii=False, indent=2)

    def patch_chapter(self, thread_id: str, chapter_id: int, markdown: str) -> BookState:
        """用人工编辑后的 Markdown 覆盖 checkpoint 中的指定章节。"""
        state = self.get_book_state(thread_id)
        if state is None:
            raise ValueError(f"线程不存在或尚未开始: {thread_id}")
        if not state.set_current_chapter_by_id(chapter_id):
            raise ValueError(f"章节不存在: {chapter_id}")
        chapter = state.get_current_chapter()
        if chapter is None:
            raise ValueError(f"章节不存在: {chapter_id}")
        existing = state.get_chapter_content(chapter_id)
        content = ChapterContent(
            chapter_id=chapter_id,
            title=existing.title if existing else chapter.title,
            markdown=markdown,
            word_count=count_words(markdown),
            revision_count=existing.revision_count if existing else 0,
        )
        state.upsert_chapter_content(content)
        state.clear_chapter_feedback(chapter_id)
        state.mark_chapter_status(chapter_id, "written")
        self.graph.update_state({"configurable": {"thread_id": thread_id}}, state.model_dump())
        return state

    def revise_chapter(self, thread_id: str, chapter_id: int, feedback: str) -> BookState:
        """针对单章执行一次 LLM 修订，不推进整本书主流程。"""
        state = self.get_book_state(thread_id)
        if state is None:
            raise ValueError(f"线程不存在或尚未开始: {thread_id}")
        if not state.set_current_chapter_by_id(chapter_id):
            raise ValueError(f"章节不存在: {chapter_id}")
        content = state.get_chapter_content(chapter_id)
        if content is None:
            raise ValueError(f"章节尚无正文，无法修订: {chapter_id}")
        if content.revision_count >= state.max_revision_count:
            raise RuntimeError(f"第{chapter_id}章修订次数已达上限: {state.max_revision_count}")
        content.review_feedback = feedback
        state.needs_revision = True
        state.revision_target_chapter = chapter_id
        markdown = self.writer.revise(state, feedback)
        content.markdown = markdown
        content.word_count = count_words(markdown)
        content.revision_count += 1
        state.upsert_chapter_content(content)
        state.clear_chapter_feedback(chapter_id)
        state.mark_chapter_status(chapter_id, "written")
        self.graph.update_state({"configurable": {"thread_id": thread_id}}, state.model_dump())
        return state

    def regenerate_output(self, thread_id: str = "book-1") -> str:
        """仅根据 checkpoint 重新生成输出文件，不推进写作流程。"""
        state = self.get_book_state(thread_id)
        if state is None:
            raise ValueError(f"线程不存在或尚未开始: {thread_id}")
        output_dir = str(self.paths.output_dir)
        return generate_output(state, output_dir, self.cfg.model_dump(mode="python"))

    def reset_thread(self, thread_id: str = "book-1") -> None:
        """删除指定线程 checkpoint。调用方必须先完成确认。"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("delete from writes where thread_id = ?", (thread_id,))
            conn.execute("delete from checkpoints where thread_id = ?", (thread_id,))
            conn.commit()
