"""分阶段出版工作流：知识库、大纲、写作。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from agents.assembler import ChapterAssemblerAgent
from agents.chapter_architect import ChapterArchitectAgent
from agents.citation_guard import CitationGuardAgent
from agents.director import DirectorAgent
from agents.editor import EditorAgent
from agents.expander import ExpanderAgent
from agents.fact_checker import FactCheckerAgent
from agents.plan_reviewer import PlanReviewerAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from agents.style_guard import StyleGuardAgent
from agents.writer import WriterAgent
from core.config import config_to_book_state, get_config_paths, get_embed_config, get_llm_config, load_app_config
from core.llm_client import LLMClient
from core.log import get_logger
from core.markdown_assets import extract_book_figures, find_invalid_book_figures
from core.output import generate_output
from core.quality_rules import ensure_book_releasable, evaluate_chapter_quality
from core.rag import RAGEngine
from core.rag_contextualize import contextualize_chunk
from core.rag_rerank import rerank_chunks
from core.state import (
    BookState,
    ChapterContent,
    ChapterPlan,
    QualitySettings,
    ReferenceChunk,
    SectionContent,
    SectionPlan,
)
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
        self.expander = ExpanderAgent(self.llm)
        self.fact_checker = FactCheckerAgent(self.llm, self.rag, query_categories=ref_cfg.query_categories)
        self.citation_guard = CitationGuardAgent(self.llm)
        self.style_guard = StyleGuardAgent(self.llm)
        self.editor = EditorAgent(self.llm)
        self.director = DirectorAgent(self.llm)

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
            "revision_policy": {
                "max_revision_rounds": state.max_revision_count,
                "max_final_revision_rounds": state.max_final_revision_round,
                "continue_on_failure": state.quality.continue_on_failure,
            },
            "review_failed_sections": self._review_failed_sections(state),
            "quality_failed_chapters": self._quality_failed_chapters(state),
            "final_review": self._final_review_status(state),
        }

    def write_resume(self, thread_id: str, *, target: str = "current") -> dict[str, object]:
        """按目标范围从小节级 checkpoint 继续写作。每写完一个小节都会落盘。"""
        state = self.load_write_checkpoint(thread_id)
        target_sections = self._resolve_write_target_sections(state, target)
        processed = 0
        for section in target_sections:
            section_content = state.get_section_content(section.id)
            if section_content is None:
                self._write_current_section(state, section, thread_id)
                processed += 1
                self._save_write_checkpoint(thread_id, state)
            elif section.status == "written":
                previous_brief = self._previous_section_brief(state, section)
                section_content = self._review_section_until_pass(state, section, section_content, previous_brief, thread_id)
                state.upsert_section_content(section_content)
                self._save_section_file(state, section_content)
                self._save_write_checkpoint(thread_id, state)
            self._assemble_chapter_if_ready(state, section.chapter_id, thread_id=thread_id)
        self._move_to_next_unwritten_section(state, target_sections[-1].id, thread_id=thread_id)
        self._save_write_checkpoint(thread_id, state)
        status = self.write_status(thread_id)
        status["target"] = target
        status["sections_processed"] = processed
        return status

    def write_export_output(self, thread_id: str) -> str:
        """根据小节级 checkpoint 中已组装章节导出 output。"""
        state = self.load_write_checkpoint(thread_id)
        if state.current_phase == "completed":
            ensure_book_releasable(state, base_dir=self.paths.project_dir)
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
        previous_brief = self._previous_section_brief(state, section)
        content = self._review_section_until_pass(state, section, content, previous_brief, thread_id)
        state.upsert_section_content(content)
        if state.get_chapter_content(section.chapter_id) is not None or self._chapter_sections_complete(
            state, section.chapter_id
        ):
            self._assemble_chapter(state, section.chapter_id, thread_id=thread_id)
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

    def _resolve_write_target_sections(self, state: BookState, target: str) -> list[SectionPlan]:
        normalized = target.strip().lower() if target.strip() else "current"
        sections = state.get_all_sections_flat()
        if not sections:
            raise RuntimeError("写作 checkpoint 缺少三级写作单元。")

        if normalized in {"current", "."}:
            section = state.get_current_section()
            if section is None:
                raise RuntimeError("当前写作断点不存在。")
            return [section]

        if normalized in {"all", "full", "book", "全部", "全量"}:
            return sections

        if re.fullmatch(r"\d+", normalized):
            chapter_id = int(normalized)
            matched = [section for section in sections if section.chapter_id == chapter_id]
            if not matched:
                raise ValueError(f"章节不存在或没有三级小节: {target}")
            return matched

        if re.fullmatch(r"\d+\.\d+", normalized):
            prefix = f"{normalized}."
            matched = [section for section in sections if section.id.startswith(prefix)]
            if not matched:
                raise ValueError(f"二级节不存在或没有三级小节: {target}")
            return matched

        if re.fullmatch(r"\d+\.\d+\.\d+", normalized):
            section = state.get_section_plan(normalized)
            if section is None:
                raise ValueError(f"三级小节不存在: {target}")
            return [section]

        raise ValueError("写作目标格式错误，应为 all、1、1.1 或 1.1.1")

    def _move_to_next_unwritten_section(self, state: BookState, last_section_id: str, *, thread_id: str | None = None) -> None:
        sections = state.get_all_sections_flat()
        if not sections:
            state.current_phase = "completed"
            return

        start_index = next((index + 1 for index, section in enumerate(sections) if section.id == last_section_id), 0)
        ordered_sections = [*sections[start_index:], *sections[:start_index]]
        for section in ordered_sections:
            if state.get_section_content(section.id) is None:
                state.set_current_section_by_id(section.id)
                state.current_phase = "writing"
                return

        self._assemble_all_ready_chapters(state, thread_id=thread_id)
        state.current_phase = "completed"
        self._final_review_if_ready(state, thread_id=thread_id)

    def _write_current_section(self, state: BookState, section: SectionPlan, thread_id: str) -> None:
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
        self._save_write_checkpoint(thread_id, state)
        content = self._review_section_until_pass(state, section, content, previous_brief, thread_id)
        state.upsert_section_content(content)
        self._save_section_file(state, content)
        logger.info("✅ [小节] %s 写作完成，%d 字", section.id, content.word_count)

    def _review_section_until_pass(
            self,
            state: BookState,
            section: SectionPlan,
            content: SectionContent,
            previous_brief: str,
            thread_id: str,
    ) -> SectionContent:
        """执行小节级基础质量闭环。"""
        for round_index in range(state.max_revision_count + 1):
            issues = self._section_quality_issues(state, section, content)
            if not issues:
                content.review_feedback = ""
                content.revision_feedback = ""
                content.revision_count = round_index
                state.mark_section_status(section.id, "reviewed")
                logger.info("✅ [小节审校] %s 通过", section.id)
                return content

            feedback = self._json_feedback(
                {
                    "pass": False,
                    "section_id": section.id,
                    "issues": issues,
                }
            )
            content.review_feedback = feedback
            content.revision_feedback = feedback
            state.upsert_section_content(content)
            self._save_section_file(state, content)
            self._save_write_checkpoint(thread_id, state)
            if round_index >= state.max_revision_count:
                content.revision_count = round_index
                state.mark_section_status(section.id, "review_failed")
                state.upsert_section_content(content)
                self._save_section_file(state, content)
                self._save_write_checkpoint(thread_id, state)
                message = f"小节 {section.id} 质量审校未通过，已达修订上限。"
                logger.warning("⚠️ [小节审校] %s 已标记 review_failed 并继续", message)
                if not state.quality.continue_on_failure:
                    raise RuntimeError(message)
                return content

            revised = self.writer.revise_planned_section(
                state,
                section,
                content.markdown,
                feedback,
                previous_brief=previous_brief,
            )
            content = SectionContent(
                section_id=section.id,
                chapter_id=section.chapter_id,
                title=section.title,
                markdown=revised,
                word_count=count_words(revised),
                revision_feedback=feedback,
                revision_count=round_index + 1,
            )
            state.upsert_section_content(content)
            self._save_section_file(state, content)
            self._save_write_checkpoint(thread_id, state)

        return content

    def _section_quality_issues(
            self,
            state: BookState,
            section: SectionPlan,
            content: SectionContent,
    ) -> list[dict[str, str]]:
        """返回小节级确定性质量问题。"""
        issues: list[dict[str, str]] = []
        markdown = content.markdown.strip()
        if not markdown:
            issues.append({"code": "section.empty", "message": "小节正文为空。", "suggestion": "重新撰写完整小节。"})
            return issues

        min_words = max(200, int(section.target_words * 0.55)) if section.target_words else 200
        if content.word_count < min_words:
            issues.append(
                {
                    "code": "section.too_short",
                    "message": f"小节 {content.word_count} 字，低于目标 {section.target_words} 的基础下限 {min_words}。",
                    "suggestion": "补足概念解释、工程场景、风险分析、步骤清单或表格说明；不要灌水。",
                }
            )

        if section.id not in markdown and section.title not in markdown and section.heading not in markdown:
            issues.append(
                {
                    "code": "section.missing_heading",
                    "message": f"小节缺少对应标题: {section.heading}",
                    "suggestion": "使用当前小节编号和标题作为 Markdown 标题。",
                }
            )

        min_figures = state.quality.min_figures_per_section
        marker = str((state.style.illustrations or {}).get("marker", "book-figure"))
        if min_figures > 0:
            figure_count = len(extract_book_figures(markdown, marker=marker))
            if figure_count < min_figures:
                issues.append(
                    {
                        "code": "section.missing_book_figure",
                        "message": f"小节完整 `{marker}` 规格块数量 {figure_count}，要求至少 {min_figures} 个。",
                        "suggestion": "补充清晰的配图规格块，包含图表类型、标题、用途、布局、元素、关系、图例、图注和 HTML/SVG 渲染说明。",
                    }
                )
        required_fields = (state.style.illustrations or {}).get("required_fields")
        if not isinstance(required_fields, list):
            required_fields = None
        invalid_figures = find_invalid_book_figures(markdown, marker=marker, required_fields=required_fields)
        if invalid_figures:
            issues.append(
                {
                    "code": "section.invalid_book_figure",
                    "message": "图表规格块不完整: " + "；".join(invalid_figures[:3]),
                    "suggestion": f"补齐 `{marker}` 规格块中的图名、用途、布局、元素、关系、图例、图注和渲染说明。",
                }
            )

        for word in state.style.forbidden_words:
            if word and word in markdown:
                issues.append(
                    {
                        "code": "section.forbidden_word",
                        "message": f"小节包含禁用词: {word}",
                        "suggestion": "替换为符合全书风格的专业表达。",
                    }
                )
        return issues

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

    def _assemble_chapter_if_ready(self, state: BookState, chapter_id: int, *, thread_id: str | None = None) -> None:
        if state.get_chapter_content(chapter_id) is not None:
            chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
            if chapter is not None and chapter.status not in {"approved", "quality_failed"}:
                self._review_chapter_until_pass(state, chapter_id, thread_id=thread_id)
            return
        if not self._chapter_sections_complete(state, chapter_id):
            return
        self._assemble_chapter(state, chapter_id, thread_id=thread_id)

    def _chapter_sections_complete(self, state: BookState, chapter_id: int) -> bool:
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
        if chapter is None or not chapter.sections:
            return False
        written_ids = {item.section_id for item in state.section_contents if item.chapter_id == chapter_id}
        return all(section.id in written_ids for section in chapter.sections)

    def _assemble_all_ready_chapters(self, state: BookState, *, thread_id: str | None = None) -> None:
        for chapter in state.get_all_chapters_flat():
            self._assemble_chapter_if_ready(state, chapter.id, thread_id=thread_id)

    def _assemble_chapter(self, state: BookState, chapter_id: int, *, thread_id: str | None = None) -> None:
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
        self._save_chapter_file(state, content)
        if thread_id is not None:
            self._save_write_checkpoint(thread_id, state)
        content = self._review_chapter_until_pass(state, chapter.id, thread_id=thread_id)
        if previous_section_id:
            state.set_current_section_by_id(previous_section_id)
        self._save_chapter_file(state, content)
        logger.info("📚 [合稿] 第%d章完成，%d 字", chapter.id, content.word_count)

    def _review_chapter_until_pass(
            self,
            state: BookState,
            chapter_id: int,
            *,
            thread_id: str | None = None,
    ) -> ChapterContent:
        """执行章节级出版质量闭环。"""
        if not state.set_current_chapter_by_id(chapter_id):
            raise RuntimeError(f"章节不存在: {chapter_id}")
        content = state.get_chapter_content(chapter_id)
        if content is None:
            raise RuntimeError(f"第{chapter_id}章尚无正文，无法审校。")

        for round_index in range(state.max_revision_count + 1):
            deterministic_report = evaluate_chapter_quality(state, content, base_dir=self.paths.project_dir)
            if not deterministic_report.pass_:
                content.publication_feedback = deterministic_report.to_feedback()
                content.revision_feedback = content.publication_feedback
                state.upsert_chapter_content(content)
                self._save_chapter_file(state, content)
                if thread_id is not None:
                    self._save_write_checkpoint(thread_id, state)
                if round_index >= state.max_revision_count:
                    message = f"第{chapter_id}章出版质量门未通过，已达修订上限。"
                    return self._mark_chapter_quality_failed(state, content, message, thread_id=thread_id)
                content = self._revise_chapter_from_feedback(
                    state,
                    content,
                    deterministic_report.to_feedback(),
                    round_index + 1,
                )
                continue

            fact_report = self.fact_checker.check(state)
            citation_report = self.citation_guard.check(state)
            style_report = self.style_guard.check(state)
            editor_report = self.editor.review(state)
            self._store_chapter_quality_reports(
                state,
                content,
                publication_feedback="",
                fact_report=fact_report,
                citation_report=citation_report,
                style_report=style_report,
                editor_report=editor_report,
            )
            content = state.get_chapter_content(chapter_id)
            if content is None:
                raise RuntimeError(f"第{chapter_id}章审校后正文丢失。")
            self._save_chapter_file(state, content)
            if thread_id is not None:
                self._save_write_checkpoint(thread_id, state)

            if all(
                self._report_passed(report)
                for report in [fact_report, citation_report, style_report, editor_report]
            ):
                content.fact_feedback = ""
                content.citation_feedback = ""
                content.style_feedback = ""
                content.review_feedback = ""
                content.publication_feedback = ""
                content.revision_feedback = ""
                state.upsert_chapter_content(content)
                self._apply_foreshadow_checks(state, chapter_id, editor_report)
                state.mark_chapter_status(chapter_id, "approved")
                logger.info("✅ [章节质量门] 第%d章通过", chapter_id)
                return content

            if round_index >= state.max_revision_count:
                content.revision_feedback = self._chapter_revision_feedback(content)
                state.upsert_chapter_content(content)
                message = f"第{chapter_id}章 LLM 质量门未通过，已达修订上限。"
                return self._mark_chapter_quality_failed(state, content, message, thread_id=thread_id)
            content = self._revise_chapter_from_feedback(
                state,
                content,
                self._chapter_revision_feedback(content),
                round_index + 1,
            )

        return content

    def _revise_chapter_from_feedback(
            self,
            state: BookState,
            content: ChapterContent,
            feedback: str,
            revision_count: int,
    ) -> ChapterContent:
        """按反馈修订章节，并在偏薄时优先扩写。"""
        revised = self.expander.expand(state, content.markdown, feedback)
        if revised.strip() == content.markdown.strip():
            revised = self.writer.revise(state, feedback)
        new_content = ChapterContent(
            chapter_id=content.chapter_id,
            title=content.title,
            markdown=revised,
            word_count=count_words(revised),
            revision_feedback=feedback,
            revision_count=revision_count,
        )
        state.upsert_chapter_content(new_content)
        self._save_chapter_file(state, new_content)
        logger.info("🔁 [章节修订] 第%d章第%d轮修订完成，%d 字", content.chapter_id, revision_count, new_content.word_count)
        return new_content

    def _mark_chapter_quality_failed(
            self,
            state: BookState,
            content: ChapterContent,
            message: str,
            *,
            thread_id: str | None,
    ) -> ChapterContent:
        """章节达到修订上限后保留反馈、标记失败，并按配置决定是否继续。"""
        state.mark_chapter_status(content.chapter_id, "quality_failed")
        state.upsert_chapter_content(content)
        self._save_chapter_file(state, content)
        if thread_id is not None:
            self._save_write_checkpoint(thread_id, state)
        logger.warning("⚠️ [章节质量门] %s 已标记 quality_failed 并继续", message)
        if not state.quality.continue_on_failure:
            raise RuntimeError(message)
        return content

    def _store_chapter_quality_reports(
            self,
            state: BookState,
            content: ChapterContent,
            *,
            publication_feedback: str,
            fact_report: dict[str, Any],
            citation_report: dict[str, Any],
            style_report: dict[str, Any],
            editor_report: dict[str, Any],
    ) -> None:
        """把章节质量报告写回状态，供断点恢复和人工审阅。"""
        content.publication_feedback = publication_feedback
        content.fact_feedback = "" if self._report_passed(fact_report) else self._json_feedback(fact_report)
        content.citation_feedback = "" if self._report_passed(citation_report) else self._json_feedback(citation_report)
        content.style_feedback = "" if self._report_passed(style_report) else self._json_feedback(style_report)
        content.review_feedback = "" if self._report_passed(editor_report) else self._json_feedback(editor_report)
        raw_checks = editor_report.get("foreshadow_checks")
        content.foreshadow_checks = raw_checks if isinstance(raw_checks, list) else []
        state.upsert_chapter_content(content)

    def _chapter_revision_feedback(self, content: ChapterContent) -> str:
        """汇总章节所有未通过质量反馈。"""
        feedback_parts = [
            ("出版确定性质量门", content.publication_feedback),
            ("事实核查", content.fact_feedback),
            ("引用守门", content.citation_feedback),
            ("风格校验", content.style_feedback),
            ("编辑审校", content.review_feedback),
        ]
        lines = [f"## {title}\n{feedback}" for title, feedback in feedback_parts if feedback]
        return "\n\n".join(lines) if lines else "章节质量门未通过，请全面修订。"

    @staticmethod
    def _report_passed(report: dict[str, Any]) -> bool:
        return report.get("pass") is True

    @staticmethod
    def _json_feedback(payload: object) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _apply_foreshadow_checks(self, state: BookState, chapter_id: int, editor_report: dict[str, Any]) -> None:
        """根据编辑审校结果更新伏笔状态。"""
        checks = editor_report.get("foreshadow_checks")
        if not isinstance(checks, list):
            return
        done_by_id = {
            str(item.get("id")): str(item.get("type"))
            for item in checks
            if isinstance(item, dict) and item.get("done") is True and item.get("id")
        }
        for item in state.foreshadows:
            check_type = done_by_id.get(item.id)
            if check_type == "resolve" and item.planned_resolve_chapter == chapter_id:
                item.status = "resolved"

    def _final_review_if_ready(self, state: BookState, *, thread_id: str | None = None) -> None:
        """所有章节完成后执行全书终审。"""
        expected_chapter_ids = {chapter.id for chapter in state.get_all_chapters_flat()}
        written_chapter_ids = {content.chapter_id for content in state.chapters if content.markdown.strip()}
        if not expected_chapter_ids or not expected_chapter_ids <= written_chapter_ids:
            return

        for round_index in range(state.max_final_revision_round + 1):
            review = self.director.final_review(state)
            state.final_report = self._json_feedback(review)
            revise_chapter_ids = self._final_review_revise_chapter_ids(state, review)
            if self._report_passed(review) and not revise_chapter_ids:
                state.final_revision_chapters = []
                state.publication_approved = True
                state.current_phase = "completed"
                if thread_id is not None:
                    self._save_write_checkpoint(thread_id, state)
                logger.info("🏁 [终审] 全书通过出版终审")
                return

            state.final_revision_chapters = revise_chapter_ids
            state.publication_approved = False
            if round_index >= state.max_final_revision_round:
                if thread_id is not None:
                    self._save_write_checkpoint(thread_id, state)
                message = "全书终审未通过，已达终审返修上限。"
                logger.warning("⚠️ [终审] %s 已保留 final_report 并继续", message)
                if not state.quality.continue_on_failure:
                    raise RuntimeError(message)
                return

            for chapter_id in revise_chapter_ids:
                self._revise_chapter_for_final_review(state, chapter_id, review, round_index + 1)
                self._review_chapter_until_pass(state, chapter_id, thread_id=thread_id)
            state.final_revision_round = round_index + 1
            if thread_id is not None:
                self._save_write_checkpoint(thread_id, state)

    def _revise_chapter_for_final_review(
            self,
            state: BookState,
            chapter_id: int,
            review: dict[str, Any],
            revision_round: int,
    ) -> None:
        """根据全书终审反馈返修指定章节。"""
        if not state.set_current_chapter_by_id(chapter_id):
            raise RuntimeError(f"终审要求返修不存在的章节: {chapter_id}")
        content = state.get_chapter_content(chapter_id)
        if content is None:
            raise RuntimeError(f"终审要求返修尚未合稿的章节: {chapter_id}")
        feedback = self._json_feedback(
            {
                "source": "final_review",
                "chapter_id": chapter_id,
                "review": review,
            }
        )
        revised = self.writer.revise(state, feedback)
        new_content = ChapterContent(
            chapter_id=content.chapter_id,
            title=content.title,
            markdown=revised,
            word_count=count_words(revised),
            review_feedback=feedback,
            revision_feedback=feedback,
            revision_count=content.revision_count + revision_round,
        )
        state.upsert_chapter_content(new_content)
        self._save_chapter_file(state, new_content)

    @staticmethod
    def _final_review_revise_chapter_ids(state: BookState, review: dict[str, Any]) -> list[int]:
        raw = review.get("revise_chapters")
        if not isinstance(raw, list):
            return []
        existing_ids = {chapter.id for chapter in state.get_all_chapters_flat()}
        result: list[int] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            chapter_id = item.get("chapter_id")
            if isinstance(chapter_id, int) and chapter_id in existing_ids and chapter_id not in result:
                result.append(chapter_id)
        return result

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
        state = BookState.model_validate(raw_state)
        return self._apply_runtime_quality_settings(state)

    def _apply_runtime_quality_settings(self, state: BookState) -> BookState:
        """让质量门运行策略始终跟随当前 quality.yaml。"""
        quality = QualitySettings(**self.cfg.quality.model_dump())
        state.quality = quality
        state.max_revision_count = quality.max_revision_rounds
        state.max_final_revision_round = quality.max_final_revision_rounds
        return state

    def _review_failed_sections(self, state: BookState) -> list[dict[str, object]]:
        """汇总达到修订上限的小节，供 status 展示人工处理原因。"""
        failed: list[dict[str, object]] = []
        for section in state.get_all_sections_flat():
            if section.status != "review_failed":
                continue
            content = state.get_section_content(section.id)
            failed.append(
                {
                    "id": section.id,
                    "chapter_id": section.chapter_id,
                    "title": section.title,
                    "revision_count": content.revision_count if content else 0,
                    "feedback": self._feedback_excerpt(content.revision_feedback if content else ""),
                }
            )
        return failed

    def _quality_failed_chapters(self, state: BookState) -> list[dict[str, object]]:
        """汇总达到修订上限的章节，供 status 展示人工处理原因。"""
        failed: list[dict[str, object]] = []
        for chapter in state.get_all_chapters_flat():
            if chapter.status != "quality_failed":
                continue
            content = state.get_chapter_content(chapter.id)
            feedback = self._chapter_revision_feedback(content) if content else ""
            failed.append(
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "revision_count": content.revision_count if content else 0,
                    "feedback": self._feedback_excerpt(feedback),
                }
            )
        return failed

    def _final_review_status(self, state: BookState) -> dict[str, object] | None:
        """返回全书终审未通过原因摘要。"""
        if not state.final_report:
            return None
        return {
            "publication_approved": state.publication_approved,
            "revision_round": state.final_revision_round,
            "revision_chapters": state.final_revision_chapters,
            "feedback": self._feedback_excerpt(state.final_report),
        }

    @staticmethod
    def _feedback_excerpt(feedback: str, *, limit: int = 1200) -> str:
        text = feedback.strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit]}...（已截断）"
