"""分阶段出版工作流：知识库、大纲、写作。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from agents.assembler import ChapterAssemblerAgent
from agents.chapter_architect import ChapterArchitectAgent
from agents.plan_reviewer import PlanReviewerAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from agents.writer import WriterAgent
from core.config import config_to_book_state, get_config_paths, get_embed_config, get_llm_config, load_app_config
from core.llm_client import LLMClient
from core.log import get_logger
from core.output import generate_output
from core.rag import RAGEngine
from core.rag_contextualize import contextualize_chunk
from core.rag_rerank import rerank_chunks
from core.state import BookState, ChapterContent, ChapterPlan, ReferenceChunk, SectionContent, SectionPlan
from core.wordcount import count_words

logger = get_logger("workflow")

OUTLINE_VERSION = 1
WRITE_CHECKPOINT_VERSION = 1


class BookProject:
    """面向出版流程的显式三阶段编排器。"""

    def __init__(self, config_path: str = "config") -> None:
        self.cfg = load_app_config(config_path)
        self.paths = get_config_paths(self.cfg)
        self.config_path = config_path

        llm_cfg = get_llm_config(self.cfg)
        embed_cfg = get_embed_config(self.cfg)
        self.llm = LLMClient(**llm_cfg, **embed_cfg)
        self.rag = self._create_rag(embed_cfg)

        ref_cfg = self.cfg.references
        self.planner = PlannerAgent(self.llm)
        self.plan_reviewer = PlanReviewerAgent(self.llm)
        self.architect = ChapterArchitectAgent(self.llm)
        self.researcher = ResearchAgent(
            self.llm,
            self.rag,
            query_categories=ref_cfg.query_categories,
            web_enabled=ref_cfg.web_research.enabled,
            web_urls=ref_cfg.web_research.urls,
            web_timeout_seconds=ref_cfg.web_research.timeout_seconds,
            web_max_chars_per_url=ref_cfg.web_research.max_chars_per_url,
        )
        self.writer = WriterAgent(self.llm)
        self.assembler = ChapterAssemblerAgent(self.llm)

    def kb_status(self) -> dict[str, object]:
        """返回知识库状态。"""
        return {
            "manifest": str(self.paths.rag_manifest),
            "manifest_exists": self.paths.rag_manifest.exists(),
            "bm25_index": str(self.paths.bm25_index),
            "bm25_exists": self.paths.bm25_index.exists(),
            "rag": self.rag.get_status(),
        }

    def kb_build(self, *, rebuild: bool = False) -> dict[str, object]:
        """增量构建或显式重建知识库。"""
        if rebuild:
            self.reset_rag_index()
        count = self.rag.index_books(self.paths.reference_sources, str(self.paths.rag_manifest))
        return {"chunks": count, **self.kb_status()}

    def outline_status(self) -> dict[str, object]:
        """返回大纲阶段产物状态。"""
        current = self.outline_current_path
        approved = self.outline_approved_path
        result: dict[str, object] = {
            "current": str(current),
            "current_exists": current.exists(),
            "approved": str(approved),
            "approved_exists": approved.exists(),
        }
        if approved.exists():
            state = self.load_approved_outline()
            result.update(self._outline_metrics(state))
        elif current.exists():
            state = self._load_state_envelope(current, expected_kind="outline.current")
            result.update(self._outline_metrics(state))
        return result

    def outline_generate(self, *, force: bool = False) -> BookState:
        """生成全书高层大纲，并为每章生成三级写作单元。"""
        if self.outline_current_path.exists() and not force:
            raise RuntimeError(f"当前大纲已存在: {self.outline_current_path}。如需覆盖请使用 --force。")

        state = config_to_book_state(self.cfg)
        state.current_phase = "planning"
        candidates = self.planner.plan_candidates(state, n=2)
        review = self.plan_reviewer.review(state, candidates)
        best_index = review.get("best_index")
        if not isinstance(best_index, int) or not 0 <= best_index < len(candidates):
            raise RuntimeError(f"大纲评审 best_index 无效: {best_index}")
        if review.get("pass") is not True:
            raise RuntimeError(f"大纲评审未通过，已阻断: {review.get('reason', '')}")

        parts, foreshadows = self.planner.build_plan(state, candidates[best_index])
        state.parts = parts
        state.foreshadows = foreshadows
        for chapter in state.get_all_chapters_flat():
            self._build_chapter_sections(state, chapter)
        self._activate_first_section(state)
        state.current_phase = "plan_review"
        self._save_state_envelope(self.outline_current_path, state, kind="outline.current")
        return state

    def outline_approve(self, source: str | None = None) -> BookState:
        """批准大纲，写作阶段只消费 approved outline。"""
        source_path = Path(source).resolve() if source else self.outline_current_path
        state = self._load_state_envelope(source_path, expected_kind=None)
        self._validate_outline_ready(state)
        state.current_phase = "writing"
        self._activate_first_section(state)
        self._save_state_envelope(self.outline_approved_path, state, kind="outline.approved")
        return state

    def load_approved_outline(self) -> BookState:
        """读取已批准大纲。"""
        return self._load_state_envelope(self.outline_approved_path, expected_kind="outline.approved")

    def write_start(self, thread_id: str, *, fresh: bool = False) -> dict[str, object]:
        """基于已批准大纲创建小节级写作 checkpoint。"""
        checkpoint_path = self.write_checkpoint_path(thread_id)
        if checkpoint_path.exists() and not fresh:
            raise RuntimeError(f"写作 checkpoint 已存在: {checkpoint_path}。请使用 write resume，或 --fresh 重建。")
        state = self.load_approved_outline()
        state.section_contents = []
        state.chapters = []
        state.current_phase = "writing"
        self._activate_first_section(state)
        self._save_write_checkpoint(thread_id, state)
        return self.write_status(thread_id)

    def write_status(self, thread_id: str) -> dict[str, object]:
        """返回小节级写作 checkpoint 状态。"""
        path = self.write_checkpoint_path(thread_id)
        if not path.exists():
            return {"thread_id": thread_id, "has_checkpoint": False, "path": str(path)}
        state = self.load_write_checkpoint(thread_id)
        section = state.get_current_section()
        chapter = state.get_current_chapter()
        sections = state.get_all_sections_flat()
        return {
            "thread_id": thread_id,
            "has_checkpoint": True,
            "path": str(path),
            "phase": state.current_phase,
            "current_chapter": {"id": chapter.id, "title": chapter.title} if chapter else None,
            "current_section": {"id": section.id, "title": section.title} if section else None,
            "sections_written": len(state.section_contents),
            "sections_total": len(sections),
            "chapters_assembled": len(state.chapters),
        }

    def write_resume(self, thread_id: str, *, max_sections: int = 1) -> dict[str, object]:
        """从小节级 checkpoint 继续写作。每写完一个小节都会落盘。"""
        if max_sections <= 0:
            raise ValueError("max_sections 必须大于 0")
        state = self.load_write_checkpoint(thread_id)
        processed = 0
        while processed < max_sections and state.current_phase != "completed":
            section = state.get_current_section()
            if section is None:
                state.current_phase = "completed"
                break
            if state.get_section_content(section.id) is None:
                self._write_current_section(state, section)
                processed += 1
                self._save_write_checkpoint(thread_id, state)
            self._assemble_chapter_if_ready(state, section.chapter_id)
            if not state.advance_to_next_section():
                self._assemble_all_ready_chapters(state)
                state.current_phase = "completed"
                break
        self._save_write_checkpoint(thread_id, state)
        return self.write_status(thread_id)

    def write_export_output(self, thread_id: str) -> str:
        """根据小节级 checkpoint 中已组装章节导出 output。"""
        state = self.load_write_checkpoint(thread_id)
        return generate_output(state, str(self.paths.output_dir), self.cfg.model_dump(mode="python"))

    def patch_section(self, thread_id: str, section_id: str, markdown: str) -> BookState:
        """用人工编辑后的 Markdown 覆盖指定三级小节。"""
        state = self.load_write_checkpoint(thread_id)
        section = state.get_section_plan(section_id)
        if section is None:
            raise ValueError(f"三级小节不存在: {section_id}")
        content = SectionContent(
            section_id=section.id,
            chapter_id=section.chapter_id,
            title=section.title,
            markdown=markdown,
            word_count=count_words(markdown),
        )
        state.upsert_section_content(content)
        state.mark_section_status(section.id, "written")
        if state.get_chapter_content(section.chapter_id) is not None or self._chapter_sections_complete(
            state, section.chapter_id
        ):
            self._assemble_chapter(state, section.chapter_id)
        self._save_section_file(state, content)
        self._save_write_checkpoint(thread_id, state)
        return state

    def load_write_checkpoint(self, thread_id: str) -> BookState:
        """读取小节级写作 checkpoint。"""
        return self._load_state_envelope(self.write_checkpoint_path(thread_id), expected_kind="write.checkpoint")

    @property
    def outline_dir(self) -> Path:
        return self.paths.data_dir / "outlines"

    @property
    def outline_current_path(self) -> Path:
        return self.outline_dir / "current.json"

    @property
    def outline_approved_path(self) -> Path:
        return self.outline_dir / "approved.json"

    @property
    def manuscript_dir(self) -> Path:
        return self.paths.data_dir / "manuscript"

    def write_checkpoint_path(self, thread_id: str) -> Path:
        safe_thread_id = thread_id.replace("/", "_").replace("\\", "_")
        return self.paths.data_dir / "write" / f"{safe_thread_id}.json"

    def reset_rag_index(self) -> None:
        """清空本地知识库索引。"""
        self.rag.reset_index()
        for path in [self.paths.rag_manifest, Path(f"{self.paths.rag_manifest}.partial"), self.paths.bm25_index]:
            path.unlink(missing_ok=True)

    def _create_rag(self, embed_cfg: dict[str, object]) -> RAGEngine:
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

        return RAGEngine(
            embed_fn=self.llm.embed,
            embed_many_fn=self.llm.embed_many,
            chunk_size=ref_cfg.chunk_size,
            chunk_overlap=ref_cfg.chunk_overlap,
            persist_dir=str(self.paths.chroma_dir),
            bm25_path=str(self.paths.bm25_index),
            reranker=reranker,
            contextualizer=contextualizer,
            embed_model=str(embed_cfg["embed_model"]),
        )

    def _build_chapter_sections(self, state: BookState, chapter: ChapterPlan) -> None:
        if not state.set_current_chapter_by_id(chapter.id):
            raise RuntimeError(f"章节不存在: {chapter.id}")
        current = state.get_current_chapter()
        if current is None:
            raise RuntimeError(f"章节不存在: {chapter.id}")
        blueprint = self.architect.build_blueprint(state)
        if blueprint is None:
            raise RuntimeError(f"第{chapter.id}章蓝图生成失败")
        current.blueprint = blueprint
        current.sections = [
            SectionPlan(
                id=item.section_id,
                chapter_id=chapter.id,
                title=item.title,
                heading=item.heading,
                parent_title=item.parent_title,
                target_words=item.target_words,
                purpose=item.purpose,
                key_points=item.key_points,
                evidence_needed=item.evidence_needed,
                required_elements=item.required_elements,
            )
            for item in blueprint.sections
        ]

    def _activate_first_section(self, state: BookState) -> None:
        sections = state.get_all_sections_flat()
        if not sections:
            raise RuntimeError("已批准大纲缺少三级写作单元，不能进入写作。")
        state.set_current_section_by_id(sections[0].id)

    def _write_current_section(self, state: BookState, section: SectionPlan) -> None:
        if not state.set_current_section_by_id(section.id):
            raise RuntimeError(f"三级小节不存在: {section.id}")
        self._ensure_chapter_research(state)
        previous_brief = self._previous_section_brief(state, section)
        markdown = self.writer.write_planned_section(state, section, previous_brief=previous_brief)
        content = SectionContent(
            section_id=section.id,
            chapter_id=section.chapter_id,
            title=section.title,
            markdown=markdown,
            word_count=count_words(markdown),
        )
        state.upsert_section_content(content)
        state.mark_section_status(section.id, "written")
        self._save_section_file(state, content)
        logger.info("✅ [小节] %s 写作完成，%d 字", section.id, content.word_count)

    def _ensure_chapter_research(self, state: BookState) -> None:
        chapter = state.get_current_chapter()
        if chapter is None or chapter.research_dossier is not None:
            return
        chunks = self.researcher.search(state)
        dossier = self.researcher.build_dossier(state, chunks)
        if dossier is not None:
            chapter.research_dossier = dossier
        chapter.status = "researched"
        state.reference_chunks = chunks

    def _previous_section_brief(self, state: BookState, section: SectionPlan) -> str:
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == section.chapter_id), None)
        if chapter is None:
            return ""
        previous: SectionContent | None = None
        for item in chapter.sections:
            if item.id == section.id:
                break
            previous = state.get_section_content(item.id) or previous
        return previous.markdown[:600].replace("\n", " ") if previous else ""

    def _assemble_chapter_if_ready(self, state: BookState, chapter_id: int) -> None:
        if state.get_chapter_content(chapter_id) is not None:
            return
        if not self._chapter_sections_complete(state, chapter_id):
            return
        self._assemble_chapter(state, chapter_id)

    def _chapter_sections_complete(self, state: BookState, chapter_id: int) -> bool:
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
        if chapter is None or not chapter.sections:
            return False
        written_ids = {item.section_id for item in state.section_contents if item.chapter_id == chapter_id}
        return all(section.id in written_ids for section in chapter.sections)

    def _assemble_all_ready_chapters(self, state: BookState) -> None:
        for chapter in state.get_all_chapters_flat():
            self._assemble_chapter_if_ready(state, chapter.id)

    def _assemble_chapter(self, state: BookState, chapter_id: int) -> None:
        previous_section_id = state.current_section_id
        if not state.set_current_chapter_by_id(chapter_id):
            raise RuntimeError(f"章节不存在: {chapter_id}")
        chapter = state.get_current_chapter()
        if chapter is None:
            raise RuntimeError(f"章节不存在: {chapter_id}")
        sections = state.get_chapter_section_contents(chapter_id)
        if not sections:
            raise RuntimeError(f"第{chapter_id}章尚无小节正文，无法合稿。")
        raw_markdown = "\n\n".join([f"# 第{chapter.id}章 {chapter.title}", *(item.markdown.strip() for item in sections)])
        markdown = self.assembler.assemble(state, raw_markdown)
        content = ChapterContent(
            chapter_id=chapter.id,
            title=chapter.title,
            markdown=markdown,
            word_count=count_words(markdown),
        )
        state.upsert_chapter_content(content)
        state.mark_chapter_status(chapter.id, "written")
        if previous_section_id:
            state.set_current_section_by_id(previous_section_id)
        self._save_chapter_file(state, content)
        logger.info("📚 [合稿] 第%d章完成，%d 字", chapter.id, content.word_count)

    def _outline_metrics(self, state: BookState) -> dict[str, object]:
        sections = state.get_all_sections_flat()
        return {
            "parts": len(state.parts),
            "chapters": len(state.get_all_chapters_flat()),
            "sections": len(sections),
            "foreshadows": len(state.foreshadows),
        }

    def _validate_outline_ready(self, state: BookState) -> None:
        for chapter in state.get_all_chapters_flat():
            if chapter.blueprint is None:
                raise RuntimeError(f"第{chapter.id}章缺少章节蓝图，不能批准大纲。")
            if not chapter.sections:
                raise RuntimeError(f"第{chapter.id}章缺少三级写作单元，不能批准大纲。")
            for section in chapter.sections:
                if not section.id.startswith(f"{chapter.id}.") or len(section.id.split(".")) != 3:
                    raise RuntimeError(f"第{chapter.id}章包含非法三级小节编号: {section.id}")

    def _save_section_file(self, state: BookState, content: SectionContent) -> None:
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == content.chapter_id), None)
        if chapter is None:
            return
        path = self.manuscript_dir / f"chapter-{chapter.id:02d}" / f"{content.section_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.markdown, encoding="utf-8")

    def _save_chapter_file(self, state: BookState, content: ChapterContent) -> None:
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == content.chapter_id), None)
        if chapter is None:
            return
        path = self.manuscript_dir / f"chapter-{chapter.id:02d}" / "chapter.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.markdown, encoding="utf-8")

    def _save_write_checkpoint(self, thread_id: str, state: BookState) -> None:
        self._save_state_envelope(self.write_checkpoint_path(thread_id), state, kind="write.checkpoint")

    def _save_state_envelope(self, path: Path, state: BookState, *, kind: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": OUTLINE_VERSION if kind.startswith("outline.") else WRITE_CHECKPOINT_VERSION,
            "kind": kind,
            "state": state.model_dump(mode="python"),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_state_envelope(self, path: Path, *, expected_kind: str | None) -> BookState:
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        payload = cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8")))
        kind = payload.get("kind")
        if expected_kind is not None and kind != expected_kind:
            raise RuntimeError(f"文件类型不匹配: 期望 {expected_kind}，实际 {kind}")
        raw_state = payload.get("state")
        if not isinstance(raw_state, dict):
            raise RuntimeError(f"状态文件缺少 state 对象: {path}")
        return BookState.model_validate(raw_state)
