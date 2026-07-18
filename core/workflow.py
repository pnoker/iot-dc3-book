"""分阶段出版工作流：知识库、大纲、写作。"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from agents.assembler import ChapterAssemblerAgent
from agents.chapter_architect import ChapterArchitectAgent
from agents.citation_guard import CitationGuardAgent
from agents.director import DirectorAgent
from agents.editor import EditorAgent
from agents.expander import ExpanderAgent
from agents.fact_checker import FactCheckerAgent
from agents.figure_designer import FigureDesignerAgent
from agents.plan_reviewer import PlanReviewerAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from agents.style_guard import StyleGuardAgent
from agents.writer import WriterAgent
from core.ai_flavor import detect_ai_flavor
from core.config import config_to_book_state, get_config_paths, get_embed_config, get_llm_config, load_app_config
from core.config_models import AppConfig
from core.figure_brief_migration import (
    FigureBriefSyncResult,
    FigureBriefUpgradeResult,
    sync_chapter_figure_briefs_from_sections,
    upgrade_book_figure_briefs,
)
from core.figures import (
    audit_figure_assets,
    build_figure_assets,
    collect_figure_assets_for_export,
    write_figure_polish_plan,
)
from core.llm_client import LLMClient
from core.log import get_logger
from core.markdown_assets import extract_book_figures, find_invalid_book_figures
from core.output import generate_markdown_output, generate_pdf_output, generate_word_output
from core.publication_audit import audit_has_blocking_issues, summarize_publication_audit
from core.quality_rules import check_originality, ensure_book_releasable, evaluate_chapter_quality
from core.rag import RAGEngine
from core.rag_contextualize import contextualize_chunk
from core.rag_rerank import rerank_chunks
from core.reference_markers import ReferenceCleanMode, audit_reference_markers, clean_reference_markers
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

if TYPE_CHECKING:
    from collections.abc import Iterator

OUTLINE_VERSION = 1
WRITE_CHECKPOINT_VERSION = 1
WORKER_CHECKPOINT_VERSION = 1
WRITE_LOCK_STALE_SECONDS = 300
_HEAVY_CHAPTER_REVISION_LOCK = threading.Lock()


class BookProject:
    """面向出版流程的显式三阶段编排器。"""

    _write_artifacts = True

    def __init__(self, config_path: str = "config", *, cfg: AppConfig | None = None) -> None:
        self.cfg = cfg.model_copy(deep=True) if cfg is not None else load_app_config(config_path)
        self.paths = get_config_paths(self.cfg)
        self.config_path = config_path
        self._write_artifacts = True
        self._write_checkpoint_path_override: Path | None = None
        self._write_checkpoint_kind_override: str | None = None

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
        self.figure_designer = FigureDesignerAgent(
            self.llm,
            polish_rounds=max(0, int(getattr(self.cfg.style.illustrations, "ai_polish_rounds", 1))),
            timeout_seconds=float(getattr(self.cfg.style.illustrations, "ai_timeout_seconds", 25.0)),
            max_tokens=int(getattr(self.cfg.style.illustrations, "ai_max_tokens", 2048)),
            retry_attempts=int(getattr(self.cfg.style.illustrations, "ai_retry_attempts", 1)),
            json_retry_attempts=int(getattr(self.cfg.style.illustrations, "ai_json_retry_attempts", 1)),
            circuit_breaker_failures=int(getattr(self.cfg.style.illustrations, "ai_circuit_breaker_failures", 3)),
            skill_dir=self.paths.project_dir / ".claude" / "skills" / "architecture-diagram",
        )

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
        self._refresh_runtime_settings(state)
        self._validate_outline_ready(state)
        state.current_phase = "writing"
        self._activate_first_section(state)
        self._save_state_envelope(self.outline_approved_path, state, kind="outline.approved")
        return state

    def load_approved_outline(self) -> BookState:
        """读取已批准大纲。"""
        state = self._load_state_envelope(self.outline_approved_path, expected_kind="outline.approved")
        self._refresh_runtime_settings(state)
        return state

    def write_start(self, thread_id: str, *, fresh: bool = False) -> dict[str, object]:
        """基于已批准大纲创建小节级写作 checkpoint。"""
        with self._write_operation_lock(thread_id, "write.start"):
            checkpoint_path = self.write_checkpoint_path(thread_id)
            if checkpoint_path.exists() and not fresh:
                raise RuntimeError(f"写作 checkpoint 已存在: {checkpoint_path}。请使用 write resume，或 --fresh 重建。")
            self._clear_thread_worker_checkpoints(thread_id)
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
        state = self.load_write_checkpoint_with_workers(thread_id)
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
            "worker_checkpoints": self._worker_checkpoint_status(thread_id),
        }

    def write_audit(self, thread_id: str) -> dict[str, object]:
        """返回 checkpoint、稿件漂移、质量失败和出版审计诊断。"""
        path = self.write_checkpoint_path(thread_id)
        result: dict[str, object] = {
            "thread_id": thread_id,
            "checkpoint": str(path),
            "checkpoint_exists": path.exists(),
            "lock": self._write_lock_status(thread_id),
            "worker_checkpoints": self._worker_checkpoint_status(thread_id),
        }
        if not path.exists():
            result["recommended_commands"] = ["uv run python main.py write start"]
            return result
        state = self.load_write_checkpoint_with_workers(thread_id)
        publication_audit = summarize_publication_audit(state)
        result.update(
            {
                "progress": self._progress_breakdown(state),
                "manuscript_drift": self._manuscript_drift(state),
                "quality_failures": self._quality_failure_summary(state),
                "publication_audit": publication_audit,
                "recommended_commands": self._recommended_commands(state, publication_audit),
            }
        )
        return result

    def write_resume(self, thread_id: str, *, target: str = "current") -> dict[str, object]:
        """按目标范围从小节级 checkpoint 继续写作。每写完一个小节都会落盘。"""
        with self._write_operation_lock(thread_id, "write.resume"):
            state = self.load_write_checkpoint(thread_id)
            target_sections = self._resolve_write_target_sections(state, target)
            if self._should_parallelize_chapters(state, target_sections):
                return self._write_chapters_parallel(state, target_sections, thread_id, target)
            processed = 0
            touched_chapter_ids: set[int] = set()
            for section in target_sections:
                touched_chapter_ids.add(section.chapter_id)
                section_content = state.get_section_content(section.id)
                if section_content is None:
                    self._write_current_section(state, section, thread_id=thread_id)
                    processed += 1
                    self._save_write_checkpoint(thread_id, state)
                elif section.status in {"written", "review_failed"}:
                    previous_brief = self._previous_section_brief(state, section)
                    section_content = self._review_section_until_pass(state, section, section_content, previous_brief, thread_id)
                    state.upsert_section_content(section_content)
                    self._save_section_file(state, section_content)
                    self._save_write_checkpoint(thread_id, state)
                    processed += 1
                self._assemble_chapter_if_ready(state, section.chapter_id, thread_id=thread_id)
            for chapter_id in sorted(touched_chapter_ids):
                self._assemble_chapter_if_ready(state, chapter_id, thread_id=thread_id, retry_failed=True)
            self._move_to_next_unwritten_section(state, target_sections[-1].id, thread_id=thread_id)
            self._save_write_checkpoint(thread_id, state)
            status = self.write_status(thread_id)
            status["target"] = target
            status["sections_processed"] = processed
            return status

    def _should_parallelize_chapters(self, state: BookState, target_sections: list[SectionPlan]) -> bool:
        """仅在目标覆盖多个完整章节时启用章节并发，章内仍顺序写作。"""
        if not state.writing.parallel_chapters or state.writing.parallel_workers <= 1:
            return False
        by_chapter: dict[int, list[str]] = {}
        for section in target_sections:
            by_chapter.setdefault(section.chapter_id, []).append(section.id)
        if len(by_chapter) <= 1:
            return False
        for chapter_id, section_ids in by_chapter.items():
            chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
            if chapter is None:
                return False
            expected_ids = [section.id for section in chapter.sections]
            if section_ids != expected_ids:
                return False
        return True

    def _write_chapters_parallel(
            self,
            state: BookState,
            target_sections: list[SectionPlan],
            thread_id: str,
            target: str,
    ) -> dict[str, object]:
        """按章节并发起草，主线程合并 checkpoint 并执行全书终审。"""
        chapter_ids = list(dict.fromkeys(section.chapter_id for section in target_sections))
        workers = min(state.writing.parallel_workers, len(chapter_ids))
        processed = 0
        failed_chapters: list[int] = []
        logger.info("🚀 [并发写作] %d 个章节并发起草，workers=%d", len(chapter_ids), workers)
        display_state = self._overlay_worker_checkpoints_for_read(thread_id, deepcopy(state))
        for chapter_id in chapter_ids:
            logger.info("🧭 [并发写作] 第%d章待处理: %s", chapter_id, self._chapter_resume_plan(display_state, chapter_id))
        # 在主线程提交前一次性备好每章的隔离快照，避免 worker 线程内 deepcopy 与主线程合并同一 state 竞争。
        snapshots = {chapter_id: deepcopy(state) for chapter_id in chapter_ids}
        executor = ThreadPoolExecutor(max_workers=workers)
        shutdown_done = False
        futures = {
            executor.submit(self._write_chapter_in_isolated_state, snapshots[chapter_id], chapter_id, thread_id): chapter_id
            for chapter_id in chapter_ids
        }
        try:
            for future in as_completed(futures):
                chapter_id = futures[future]
                try:
                    isolated_state = future.result()
                except Exception:
                    # 单章失败不拖垮其它已完成章节：记录后继续合并剩余结果。
                    logger.exception("⚠️ [并发写作] 第%d章起草失败，跳过合并，继续其它章节", chapter_id)
                    failed_chapters.append(chapter_id)
                    continue
                processed += self._merge_chapter_state(state, isolated_state, chapter_id)
                self._save_write_checkpoint(thread_id, state)
                self._save_chapter_artifacts(state, chapter_id)
                self._clear_worker_checkpoint(thread_id, chapter_id)
                logger.info("✅ [并发写作] 第%d章已合并 checkpoint", chapter_id)
        except KeyboardInterrupt:
            logger.warning("⏹️ [并发写作] 收到中断，等待运行中的章节 worker 保存 checkpoint 后退出")
            for future in futures:
                future.cancel()
            self._shutdown_executor_after_interrupt(executor)
            shutdown_done = True
            raise
        finally:
            if not shutdown_done:
                executor.shutdown(wait=True)

        self._move_to_next_unwritten_section(state, target_sections[-1].id, thread_id=thread_id)
        self._save_write_checkpoint(thread_id, state)
        status = self.write_status(thread_id)
        status["target"] = target
        status["sections_processed"] = processed
        status["parallel_chapters"] = True
        status["parallel_workers"] = workers
        status["chapters_processed"] = len(chapter_ids) - len(failed_chapters)
        if failed_chapters:
            status["failed_chapters"] = failed_chapters
        return status

    @staticmethod
    def _shutdown_executor_after_interrupt(executor: ThreadPoolExecutor) -> None:
        """中断并发写作时等待 worker 收尾，避免锁释放后后台线程继续写 checkpoint。"""
        while True:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
                return
            except KeyboardInterrupt:
                logger.warning("⏳ [并发写作] 正在等待 worker checkpoint 落盘，请勿重复中断")

    def _write_chapter_in_isolated_state(self, isolated: BookState, chapter_id: int, thread_id: str) -> BookState:
        """在独立状态副本中顺序写完一个章节，避免线程间抢写 checkpoint。

        isolated 已由主线程在提交前 deepcopy 备好，本方法不再触碰共享 state。
        """
        worker_checkpoint = self.worker_checkpoint_path(thread_id, chapter_id)
        if worker_checkpoint.exists():
            isolated = self._load_worker_checkpoint(thread_id, chapter_id)
            logger.info("↩️ [并发写作] 第%d章从 worker checkpoint 恢复", chapter_id)
        worker = self._new_worker_project()
        previous = worker._write_artifacts
        previous_checkpoint_path = getattr(worker, "_write_checkpoint_path_override", None)
        previous_checkpoint_kind = getattr(worker, "_write_checkpoint_kind_override", None)
        worker._write_artifacts = False
        worker._write_checkpoint_path_override = worker_checkpoint
        worker._write_checkpoint_kind_override = "write.worker.checkpoint"
        try:
            return worker._write_chapter_in_worker_state(isolated, chapter_id, thread_id=thread_id)
        finally:
            worker._write_artifacts = previous
            worker._write_checkpoint_path_override = previous_checkpoint_path
            worker._write_checkpoint_kind_override = previous_checkpoint_kind

    def _new_worker_project(self) -> BookProject:
        """创建线程内独立项目实例，避免共享 LLM/RAG 客户端。"""
        return type(self)(self.config_path, cfg=self.cfg)

    def _write_chapter_in_worker_state(self, isolated: BookState, chapter_id: int, *, thread_id: str) -> BookState:
        """在线程私有项目实例中顺序写完一个章节。"""
        if not isolated.set_current_chapter_by_id(chapter_id):
            raise RuntimeError(f"章节不存在: {chapter_id}")
        chapter = isolated.get_current_chapter()
        if chapter is None:
            raise RuntimeError(f"章节不存在: {chapter_id}")
        for section in chapter.sections:
            section_content = isolated.get_section_content(section.id)
            if section_content is None:
                self._write_current_section(isolated, section, thread_id=thread_id)
            elif section.status in {"written", "review_failed"}:
                logger.info("🔁 [小节重审] %s %s", section.id, section.title)
                previous_brief = self._previous_section_brief(isolated, section)
                section_content = self._review_section_until_pass(
                    isolated,
                    section,
                    section_content,
                    previous_brief,
                    thread_id=thread_id,
                )
                isolated.upsert_section_content(section_content)
        self._assemble_chapter_if_ready(isolated, chapter_id, thread_id=thread_id, retry_failed=True)
        return isolated

    def _chapter_resume_plan(self, state: BookState, chapter_id: int) -> str:
        """返回并发章节恢复时会优先处理的小节摘要，供日志诊断。"""
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
        if chapter is None:
            return "章节不存在"
        pending = []
        for section in chapter.sections:
            section_content = state.get_section_content(section.id)
            if section_content is None:
                pending.append(f"{section.id}(待写作)")
            elif section.status == "written":
                pending.append(f"{section.id}(待审校)")
            elif section.status == "review_failed":
                pending.append(f"{section.id}(审校未通过)")
        if pending:
            return ", ".join(pending[:8]) + (f" 等 {len(pending)} 个" if len(pending) > 8 else "")
        chapter_status = chapter.status
        if chapter_status == "quality_failed":
            return "章节质量门未通过，重跑章节质量闭环"
        return "无待处理小节"

    def _merge_chapter_state(self, state: BookState, source: BookState, chapter_id: int) -> int:
        """把隔离状态中的单章产物合回主 checkpoint。"""
        processed = 0
        source_chapter = next((item for item in source.get_all_chapters_flat() if item.id == chapter_id), None)
        target_chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
        if source_chapter is None or target_chapter is None:
            raise RuntimeError(f"章节不存在: {chapter_id}")
        target_chapter.status = source_chapter.status
        target_chapter.research_dossier = source_chapter.research_dossier
        target_chapter.foreshadows_planted = source_chapter.foreshadows_planted
        target_chapter.foreshadows_resolved = source_chapter.foreshadows_resolved
        for source_section in source_chapter.sections:
            target_section = state.get_section_plan(source_section.id)
            if target_section is not None:
                target_section.status = source_section.status
        for content in source.get_chapter_section_contents(chapter_id):
            if state.get_section_content(content.section_id) is None:
                processed += 1
            state.upsert_section_content(content)
        chapter_content = source.get_chapter_content(chapter_id)
        if chapter_content is not None:
            state.upsert_chapter_content(chapter_content)
        self._merge_foreshadows(state, source)
        return processed

    def _save_chapter_artifacts(self, state: BookState, chapter_id: int) -> None:
        """把 checkpoint 中指定章节的正文同步到 manuscript 文件。"""
        for content in state.get_chapter_section_contents(chapter_id):
            self._save_section_file(state, content)
        chapter_content = state.get_chapter_content(chapter_id)
        if chapter_content is not None:
            self._save_chapter_file(state, chapter_content)

    @staticmethod
    def _merge_foreshadows(state: BookState, source: BookState) -> None:
        """合并并发章节对伏笔账本的状态更新，避免后完成的章节覆盖先完成章节。"""
        by_id = {item.id: item for item in state.foreshadows}
        precedence = {"planted": 0, "abandoned": 1, "resolved": 2}
        for source_item in source.foreshadows:
            target_item = by_id.get(source_item.id)
            if target_item is None:
                state.foreshadows.append(source_item)
                continue
            if precedence.get(source_item.status, 0) > precedence.get(target_item.status, 0):
                target_item.status = source_item.status

    def write_export(self, thread_id: str, target: str = "all", *, draft: bool = False) -> dict[str, object]:
        """导出出版稿或当前草稿 Markdown、Word。"""
        export_target = target.strip().lower()
        if export_target not in {"markdown", "word", "pdf", "all"}:
            raise ValueError("导出目标无效，请使用 markdown、word、pdf 或 all")
        if draft:
            state = self.load_write_checkpoint_with_workers(thread_id)
            return self._generate_export(state, export_target, output_dir=self.paths.output_dir / "draft", draft=True)
        with self._write_operation_lock(thread_id, f"write.export.{export_target}"):
            state = self.load_write_checkpoint(thread_id)
            self._ensure_export_ready(state)
            return self._generate_export(state, export_target, output_dir=self.paths.output_dir, draft=False)

    def write_figures_build(self, thread_id: str, *, draft: bool = False, force: bool = False) -> dict[str, object]:
        """从当前 checkpoint 生成 HTML/SVG/PNG 图表资产，落到 .data/figures 权威存储。"""
        state = self.load_write_checkpoint_with_workers(thread_id)
        result = build_figure_assets(
            state,
            self.paths.data_dir,
            figures_dir=self.paths.figures_dir,
            illustrations=state.style.illustrations,
            designer=getattr(self, "figure_designer", None),
            force=force,
            project_dir=self.paths.project_dir,
            require_polished=self._require_polished_figures(draft=draft),
        )
        return result.to_dict()

    def write_figures_audit(self, thread_id: str, *, draft: bool = False) -> dict[str, object]:
        """审计最终入书图表的生成状态与精品图覆盖率。"""
        state = self.load_write_checkpoint_with_workers(thread_id)
        return audit_figure_assets(
            state,
            self.paths.data_dir,
            figures_dir=self.paths.figures_dir,
            illustrations=state.style.illustrations,
            project_dir=self.paths.project_dir,
        )

    def write_figures_polish_plan(self, thread_id: str) -> dict[str, object]:
        """生成出版级精品图重绘计划和逐图 prompt。"""
        state = self.load_write_checkpoint_with_workers(thread_id)
        plan_path = self.paths.project_dir / "assets" / "figures" / "polished" / "polish-plan.json"
        return write_figure_polish_plan(
            state,
            plan_path,
            illustrations=state.style.illustrations,
            project_dir=self.paths.project_dir,
        )

    def write_references_audit(self, thread_id: str) -> dict[str, object]:
        """审计全书内部资料标记 `[S]/[W]`。"""
        state = self.load_write_checkpoint_with_workers(thread_id)
        return audit_reference_markers(state).to_dict()

    def write_references_clean(self, thread_id: str, *, mode: ReferenceCleanMode) -> dict[str, object]:
        """把内部资料标记移除或转换为出版注释。"""
        with self._write_operation_lock(thread_id, f"write.references.clean.{mode}"):
            active_workers = self._active_worker_checkpoint_paths(thread_id)
            if active_workers:
                raise RuntimeError(
                    "引用清理被拒绝：仍存在未合并的章节 worker checkpoint。"
                    "请先执行 write resume 合并或确认无并发写作后再清理。"
                    f" 未合并文件: {', '.join(str(path) for path in active_workers[:5])}"
                )
            state = self.load_write_checkpoint(thread_id)
            checkpoint_path = self.write_checkpoint_path(thread_id)
            checkpoint_backup = self._backup_checkpoint_for_operation(checkpoint_path, f"references-clean-{mode}")
            manuscript_backup = self._backup_manuscript_for_operation(f"references-clean-{mode}")
            result = clean_reference_markers(state, mode=mode)
            if result.changed_files:
                for section_content in state.section_contents:
                    self._save_section_file(state, section_content)
                for chapter_content in state.chapters:
                    self._save_chapter_file(state, chapter_content)
                state.publication_approved = False
                self._save_write_checkpoint(thread_id, state)
            payload = result.to_dict()
            payload.update(
                {
                    "thread_id": thread_id,
                    "checkpoint": str(checkpoint_path),
                    "checkpoint_backup": str(checkpoint_backup) if checkpoint_backup is not None else None,
                    "manuscript_backup": str(manuscript_backup) if manuscript_backup is not None else None,
                    "publication_approved": state.publication_approved,
                }
            )
            return payload

    def _generate_export(
            self,
            state: BookState,
            export_target: str,
            *,
            output_dir: Path,
            draft: bool,
    ) -> dict[str, object]:
        cfg = self.cfg.model_dump(mode="python")
        figure_result = collect_figure_assets_for_export(
            state,
            output_dir / "figures",
            source_figures_dir=self.paths.figures_dir,
            illustrations=state.style.illustrations,
        )
        if figure_result.missing:
            first = figure_result.missing[0]
            raise RuntimeError(
                "导出被拒绝：图表资产缺失。请先执行 `figures build` 生成全部图表。"
                f"缺失 {len(figure_result.missing)} 个，权威 manifest: {figure_result.manifest}，"
                f"首个缺失: 第{first.chapter_id}章 {first.figure_id} - {first.reason}"
            )
        markdown_result = generate_markdown_output(state, str(output_dir), cfg, figure_assets=figure_result.assets)
        result: dict[str, object] = {"target": export_target, "draft": draft, **markdown_result}
        result["figures_dir"] = figure_result.figures_dir
        result["figure_manifest"] = figure_result.manifest
        result["figures_generated"] = len(figure_result.assets)
        if draft:
            audit_report = summarize_publication_audit(state)
            result["publication_ready"] = audit_report.get("pass") is True
            result["warning"] = "草稿导出仅用于预览，未通过出版门禁，不能作为定稿。"
            result["blocking_issue_count"] = audit_report.get("blocking_issue_count", 0)
        if export_target in {"word", "all"}:
            result["word_file"] = generate_word_output(
                str(markdown_result["book_markdown"]),
                output_dir / self.cfg.output.word_file,
                reference_docx=self._word_reference_docx_path(),
                pandoc_bin=self.cfg.output.pandoc_bin,
            )
        if export_target in {"pdf", "all"}:
            css = output_dir / "pdf_style.css"
            if not css.exists():
                css = self.paths.output_dir / "pdf_style.css"
            cover_html = self.paths.project_dir / "assets" / "cover.html"
            pdf_path = generate_pdf_output(
                str(markdown_result.get("book_clean") or markdown_result["book_markdown"]),
                output_dir / "book.pdf",
                css_file=css if css.exists() else None,
                pandoc_bin=self.cfg.output.pandoc_bin,
                cover_html=cover_html if cover_html.exists() else None,
            )
            if pdf_path:
                result["pdf_file"] = pdf_path
        return result

    def _ensure_export_ready(self, state: BookState) -> None:
        """导出前强制确认整书已经达到出版状态。"""
        issues: list[str] = []
        if state.current_phase != "completed":
            issues.append(f"当前阶段不是 completed: {state.current_phase}")
        if not state.publication_approved:
            issues.append("全书终审尚未通过: publication_approved=false")
        missing_sections = [section.id for section in state.get_all_sections_flat() if state.get_section_content(section.id) is None]
        failed_sections = [section.id for section in state.get_all_sections_flat() if section.status != "reviewed"]
        missing_chapters = [chapter.id for chapter in state.get_all_chapters_flat() if state.get_chapter_content(chapter.id) is None]
        failed_chapters = [chapter.id for chapter in state.get_all_chapters_flat() if chapter.status != "approved"]
        if missing_sections:
            issues.append("缺少小节正文: " + ", ".join(missing_sections[:10]))
        if failed_sections:
            issues.append("小节审校未全部通过: " + ", ".join(failed_sections[:10]))
        if missing_chapters:
            issues.append("缺少章节合稿: " + ", ".join(str(item) for item in missing_chapters[:10]))
        if failed_chapters:
            issues.append("章节质量门未全部通过: " + ", ".join(str(item) for item in failed_chapters[:10]))
        if self._require_polished_figures(draft=False):
            figure_audit = audit_figure_assets(
                state,
                self.paths.data_dir,
                figures_dir=self.paths.figures_dir,
                illustrations=state.style.illustrations,
                project_dir=self.paths.project_dir,
            )
            if figure_audit.get("pass") is not True:
                blocking = figure_audit.get("blocking", [])
                preview: list[str] = []
                if isinstance(blocking, list):
                    for item in blocking[:10]:
                        if isinstance(item, dict):
                            preview.append(str(item.get("figure_id") or item.get("title") or "unknown"))
                suffix = ": " + ", ".join(preview) if preview else ""
                issues.append(f"出版级精品图未全部就绪{suffix}")
        if issues:
            raise RuntimeError("导出被拒绝，书稿尚未达到出版状态。" + " | ".join(issues))
        ensure_book_releasable(state, base_dir=self.paths.project_dir)

    def _require_polished_figures(self, *, draft: bool) -> bool:
        illustrations = self.cfg.style.illustrations
        return bool(
            illustrations.polished_required_for_draft if draft else illustrations.polished_required_for_export
        )

    def _word_reference_docx_path(self) -> Path | None:
        reference_docx = self.cfg.output.word_reference_docx.strip()
        if not reference_docx:
            return None
        reference_path = Path(reference_docx)
        return reference_path if reference_path.is_absolute() else self.paths.project_dir / reference_path

    def patch_section(self, thread_id: str, section_id: str, markdown: str) -> BookState:
        """用人工编辑后的 Markdown 覆盖指定三级小节。"""
        with self._write_operation_lock(thread_id, "write.patch_section"):
            state = self.load_write_checkpoint(thread_id)
            section = state.get_section_plan(section_id)
            if section is None:
                raise ValueError(f"三级小节不存在: {section_id}")
            content = SectionContent(
                section_id=section.id,
                chapter_id=section.chapter_id,
                title=section.title,
                markdown=self._normalize_markdown_output(markdown),
                word_count=count_words(self._normalize_markdown_output(markdown)),
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

    def recover_manuscript(self, thread_id: str) -> dict[str, object]:
        """把现有 manuscript 草稿显式导入小节级 checkpoint。"""
        with self._write_operation_lock(thread_id, "write.recover_manuscript"):
            return self._recover_manuscript_unlocked(thread_id)

    def write_figures_upgrade_briefs(self, thread_id: str, *, dry_run: bool = False) -> dict[str, object]:
        """把 checkpoint 和 manuscript 中的旧版 `book-figure` 升级为出版级结构化 brief。"""
        with self._write_operation_lock(thread_id, "write.figures.upgrade_briefs"):
            state = self.load_write_checkpoint(thread_id)
            checkpoint_path = self.write_checkpoint_path(thread_id)
            backup_path = None if dry_run else self._backup_checkpoint_for_operation(checkpoint_path, "figure-brief-upgrade")
            manuscript_backup = None if dry_run else self._backup_manuscript_for_operation("figure-brief-upgrade")

            section_stats = self._upgrade_section_figure_briefs(state, write_files=not dry_run)
            chapter_stats = self._upgrade_chapter_figure_briefs(state, write_files=not dry_run)
            sync_stats = self._sync_chapter_figure_briefs_from_sections(state, write_files=not dry_run)
            if not dry_run:
                state.publication_approved = False
                self._save_write_checkpoint(thread_id, state)

            total = self._merge_upgrade_stats(section_stats, chapter_stats)
            return {
                "thread_id": thread_id,
                "dry_run": dry_run,
                "checkpoint": str(checkpoint_path),
                "checkpoint_backup": str(backup_path) if backup_path is not None else None,
                "manuscript_backup": str(manuscript_backup) if manuscript_backup is not None else None,
                "sections": section_stats,
                "chapters": chapter_stats,
                "chapter_section_sync": sync_stats,
                "total": total,
            }

    def _upgrade_section_figure_briefs(self, state: BookState, *, write_files: bool) -> dict[str, object]:
        changed_files: list[str] = []
        results: list[FigureBriefUpgradeResult] = []
        for content in state.section_contents:
            result = upgrade_book_figure_briefs(content.markdown)
            results.append(result)
            if result.changed_blocks:
                content.markdown = result.markdown
                content.word_count = count_words(result.markdown)
                changed_files.append(f"chapter-{content.chapter_id:02d}/{content.section_id}.md")
                if write_files:
                    self._save_section_file(state, content)
        return self._upgrade_stats(results, changed_files)

    def _upgrade_chapter_figure_briefs(self, state: BookState, *, write_files: bool) -> dict[str, object]:
        changed_files: list[str] = []
        results: list[FigureBriefUpgradeResult] = []
        for content in state.chapters:
            result = upgrade_book_figure_briefs(content.markdown)
            results.append(result)
            if result.changed_blocks:
                content.markdown = result.markdown
                content.word_count = count_words(result.markdown)
                changed_files.append(f"chapter-{content.chapter_id:02d}/chapter.md")
                if write_files:
                    self._save_chapter_file(state, content)
        return self._upgrade_stats(results, changed_files)

    def _sync_chapter_figure_briefs_from_sections(self, state: BookState, *, write_files: bool) -> dict[str, object]:
        changed_files: list[str] = []
        results: list[FigureBriefSyncResult] = []
        for content in state.chapters:
            section_markdowns = [section.markdown for section in state.get_chapter_section_contents(content.chapter_id)]
            result = sync_chapter_figure_briefs_from_sections(content.markdown, section_markdowns)
            results.append(result)
            if result.changed_blocks:
                content.markdown = result.markdown
                content.word_count = count_words(result.markdown)
                changed_files.append(f"chapter-{content.chapter_id:02d}/chapter.md")
                if write_files:
                    self._save_chapter_file(state, content)
        return self._sync_stats(results, changed_files)

    @staticmethod
    def _upgrade_stats(results: list[FigureBriefUpgradeResult], changed_files: list[str]) -> dict[str, object]:
        failures = [failure for result in results for failure in result.failures]
        return {
            "files_scanned": len(results),
            "files_changed": len(changed_files),
            "changed_files": changed_files,
            "total_blocks": sum(result.total_blocks for result in results),
            "changed_blocks": sum(result.changed_blocks for result in results),
            "repaired_blocks": sum(result.repaired_blocks for result in results),
            "failed_blocks": sum(result.failed_blocks for result in results),
            "failures": failures[:20],
        }

    @staticmethod
    def _merge_upgrade_stats(*groups: dict[str, object]) -> dict[str, object]:
        return {
            "files_scanned": sum(BookProject._upgrade_stat_int(group, "files_scanned") for group in groups),
            "files_changed": sum(BookProject._upgrade_stat_int(group, "files_changed") for group in groups),
            "total_blocks": sum(BookProject._upgrade_stat_int(group, "total_blocks") for group in groups),
            "changed_blocks": sum(BookProject._upgrade_stat_int(group, "changed_blocks") for group in groups),
            "repaired_blocks": sum(BookProject._upgrade_stat_int(group, "repaired_blocks") for group in groups),
            "failed_blocks": sum(BookProject._upgrade_stat_int(group, "failed_blocks") for group in groups),
        }

    @staticmethod
    def _sync_stats(results: list[FigureBriefSyncResult], changed_files: list[str]) -> dict[str, object]:
        return {
            "files_scanned": len(results),
            "files_changed": len(changed_files),
            "changed_files": changed_files,
            "total_blocks": sum(result.total_blocks for result in results),
            "changed_blocks": sum(result.changed_blocks for result in results),
            "unmatched_blocks": sum(result.unmatched_blocks for result in results),
            "inserted_blocks": sum(result.inserted_blocks for result in results),
        }

    @staticmethod
    def _upgrade_stat_int(group: dict[str, object], key: str) -> int:
        value = group.get(key, 0)
        return value if isinstance(value, int) else 0

    def _recover_manuscript_unlocked(self, thread_id: str) -> dict[str, object]:
        state = self.load_write_checkpoint(thread_id)
        checkpoint_path = self.write_checkpoint_path(thread_id)
        backup_path = self._backup_checkpoint(checkpoint_path)
        recovered_sections: list[str] = []
        failed_sections: list[str] = []
        recovered_chapters: list[int] = []
        quality_failed_chapters: list[int] = []

        for chapter in state.get_all_chapters_flat():
            for section in chapter.sections:
                if state.get_section_content(section.id) is not None:
                    continue
                section_path = self._section_file_path(chapter.id, section.id)
                if not section_path.exists():
                    continue
                markdown = self._normalize_markdown_output(section_path.read_text(encoding="utf-8"))
                section_content = SectionContent(
                    section_id=section.id,
                    chapter_id=section.chapter_id,
                    title=section.title,
                    markdown=markdown,
                    word_count=count_words(markdown),
                )
                issues = self._section_quality_issues(state, section, section_content)
                if issues:
                    feedback = self._json_feedback({"pass": False, "section_id": section.id, "issues": issues})
                    section_content.review_feedback = feedback
                    section_content.revision_feedback = feedback
                    section_content.revision_count = state.max_revision_count
                    state.mark_section_status(section.id, "review_failed")
                    failed_sections.append(section.id)
                else:
                    state.mark_section_status(section.id, "reviewed")
                state.upsert_section_content(section_content)
                recovered_sections.append(section.id)

            chapter_path = self._chapter_file_path(chapter.id)
            if chapter_path.exists() and state.get_chapter_content(chapter.id) is None:
                markdown = self._normalize_markdown_output(chapter_path.read_text(encoding="utf-8"))
                chapter_content = ChapterContent(
                    chapter_id=chapter.id,
                    title=chapter.title,
                    markdown=markdown,
                    word_count=count_words(markdown),
                )
                report = evaluate_chapter_quality(state, chapter_content, base_dir=self.paths.project_dir)
                if report.pass_:
                    state.mark_chapter_status(chapter.id, "written")
                else:
                    feedback = report.to_feedback()
                    chapter_content.publication_feedback = feedback
                    chapter_content.revision_feedback = feedback
                    chapter_content.revision_count = state.max_revision_count
                    state.mark_chapter_status(chapter.id, "quality_failed")
                    quality_failed_chapters.append(chapter.id)
                state.upsert_chapter_content(chapter_content)
                recovered_chapters.append(chapter.id)

        self._move_to_first_missing_section(state)
        self._save_write_checkpoint(thread_id, state)
        return {
            "thread_id": thread_id,
            "checkpoint": str(checkpoint_path),
            "backup": str(backup_path) if backup_path is not None else None,
            "sections_recovered": len(recovered_sections),
            "recovered_sections": recovered_sections,
            "review_failed_sections": failed_sections,
            "chapters_recovered": len(recovered_chapters),
            "recovered_chapters": recovered_chapters,
            "quality_failed_chapters": quality_failed_chapters,
            "current_section": state.current_section_id,
            "sections_written": len(state.section_contents),
            "chapters_assembled": len(state.chapters),
        }

    def _move_to_first_missing_section(self, state: BookState) -> None:
        for section in state.get_all_sections_flat():
            if state.get_section_content(section.id) is None:
                state.set_current_section_by_id(section.id)
                state.current_phase = "writing"
                return
        state.current_phase = "completed"

    def _backup_checkpoint(self, checkpoint_path: Path) -> Path | None:
        if not checkpoint_path.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = checkpoint_path.with_name(f"{checkpoint_path.stem}.before-recover-{timestamp}{checkpoint_path.suffix}")
        shutil.copy2(checkpoint_path, backup_path)
        return backup_path

    def _backup_checkpoint_for_operation(self, checkpoint_path: Path, operation: str) -> Path | None:
        if not checkpoint_path.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_path = checkpoint_path.with_name(f"{checkpoint_path.stem}.before-{operation}-{timestamp}{checkpoint_path.suffix}")
        shutil.copy2(checkpoint_path, backup_path)
        return backup_path

    def _backup_manuscript_for_operation(self, operation: str) -> Path | None:
        if not self.manuscript_dir.exists():
            return None
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_dir = self.paths.data_dir / "backups" / f"manuscript.before-{operation}-{timestamp}"
        shutil.copytree(self.manuscript_dir, backup_dir)
        return backup_dir

    def load_write_checkpoint(self, thread_id: str) -> BookState:
        """读取小节级写作 checkpoint。"""
        state = self._load_state_envelope(self.write_checkpoint_path(thread_id), expected_kind="write.checkpoint")
        self._refresh_runtime_settings(state)
        return state

    def load_write_checkpoint_with_workers(self, thread_id: str) -> BookState:
        """读取主 checkpoint，并叠加尚未合并的章节 worker checkpoint 供只读展示。"""
        state = self.load_write_checkpoint(thread_id)
        return self._overlay_worker_checkpoints_for_read(thread_id, state)

    def _overlay_worker_checkpoints_for_read(self, thread_id: str, state: BookState) -> BookState:
        for worker_path in sorted(self.worker_checkpoint_dir(thread_id).glob("chapter-*.json")):
            chapter_id = self._chapter_id_from_worker_checkpoint(worker_path)
            if chapter_id is None:
                continue
            try:
                worker_state = self._load_state_envelope(worker_path, expected_kind="write.worker.checkpoint")
                self._refresh_runtime_settings(worker_state)
            except RuntimeError:
                logger.exception("worker checkpoint 读取失败，已跳过只读叠加: %s", worker_path)
                continue
            self._merge_chapter_state(state, worker_state, chapter_id)
        return state

    @staticmethod
    def _chapter_id_from_worker_checkpoint(path: Path) -> int | None:
        match = re.fullmatch(r"chapter-(\d+)\.json", path.name)
        return int(match.group(1)) if match else None

    def _active_worker_checkpoint_paths(self, thread_id: str) -> list[Path]:
        return [
            path
            for path in sorted(self.worker_checkpoint_dir(thread_id).glob("chapter-*.json"))
            if self._chapter_id_from_worker_checkpoint(path) is not None
        ]

    def _refresh_runtime_settings(self, state: BookState) -> None:
        """用当前配置刷新可调运行策略，保留已生成的大纲和正文。"""
        if not isinstance(self.cfg, AppConfig):
            self._apply_runtime_quality_settings(state)
            return
        fresh = config_to_book_state(self.cfg)
        state.style = fresh.style
        state.writing = fresh.writing
        state.quality = fresh.quality
        state.max_revision_count = fresh.max_revision_count
        state.max_final_revision_round = fresh.max_final_revision_round

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
        return self.paths.data_dir / "write" / f"{self._safe_thread_id(thread_id)}.json"

    def write_lock_path(self, thread_id: str) -> Path:
        return self.paths.data_dir / "write" / f"{self._safe_thread_id(thread_id)}.lock"

    def worker_checkpoint_dir(self, thread_id: str) -> Path:
        return self.paths.data_dir / "write" / "workers" / self._safe_thread_id(thread_id)

    def worker_checkpoint_path(self, thread_id: str, chapter_id: int) -> Path:
        return self.worker_checkpoint_dir(thread_id) / f"chapter-{chapter_id:02d}.json"

    @staticmethod
    def _safe_thread_id(thread_id: str) -> str:
        return thread_id.replace("/", "_").replace("\\", "_")

    @contextmanager
    def _write_operation_lock(self, thread_id: str, operation: str) -> Iterator[None]:
        lock_path = self.write_lock_path(thread_id)
        token = f"{os.getpid()}-{uuid.uuid4().hex}"
        self._acquire_write_lock(lock_path, thread_id=thread_id, operation=operation, token=token)
        try:
            yield
        finally:
            self._release_write_lock(lock_path, token=token)

    def _acquire_write_lock(self, lock_path: Path, *, thread_id: str, operation: str, token: str) -> None:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "thread_id": thread_id,
            "operation": operation,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "token": token,
        }
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        while True:
            try:
                fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError as exc:
                if self._is_stale_write_lock(lock_path):
                    lock_path.unlink(missing_ok=True)
                    continue
                raise RuntimeError(self._active_lock_message(lock_path)) from exc
            try:
                os.write(fd, encoded)
                os.fsync(fd)
            finally:
                os.close(fd)
            self._fsync_directory(lock_path.parent)
            return

    def _release_write_lock(self, lock_path: Path, *, token: str) -> None:
        try:
            payload = cast("dict[str, Any]", json.loads(lock_path.read_text(encoding="utf-8")))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if payload.get("token") == token:
            lock_path.unlink(missing_ok=True)
            self._fsync_directory(lock_path.parent)

    def _is_stale_write_lock(self, lock_path: Path) -> bool:
        try:
            payload = cast("dict[str, Any]", json.loads(lock_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return self._lock_file_age_seconds(lock_path) > WRITE_LOCK_STALE_SECONDS
        pid = payload.get("pid")
        if isinstance(pid, int):
            return not self._pid_is_running(pid)
        return self._lock_file_age_seconds(lock_path) > WRITE_LOCK_STALE_SECONDS

    @staticmethod
    def _pid_is_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _lock_file_age_seconds(lock_path: Path) -> float:
        try:
            return datetime.now().timestamp() - lock_path.stat().st_mtime
        except OSError:
            return 0.0

    @staticmethod
    def _active_lock_message(lock_path: Path) -> str:
        try:
            payload = cast("dict[str, Any]", json.loads(lock_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return f"写作任务锁已存在且仍有效: {lock_path}"
        pid = payload.get("pid", "unknown")
        operation = payload.get("operation", "unknown")
        started_at = payload.get("started_at", "unknown")
        return f"已有写作任务正在运行: pid={pid}, operation={operation}, started_at={started_at}, lock={lock_path}"

    def _worker_checkpoint_status(self, thread_id: str) -> dict[str, object]:
        checkpoint_dir = self.worker_checkpoint_dir(thread_id)
        if not checkpoint_dir.exists():
            return {"count": 0, "chapters": []}
        chapters: list[dict[str, object]] = []
        for path in sorted(checkpoint_dir.glob("chapter-*.json")):
            match = re.fullmatch(r"chapter-(\d+)\.json", path.name)
            if match is None:
                continue
            try:
                updated_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            except OSError:
                updated_at = ""
            chapters.append({"chapter_id": int(match.group(1)), "path": str(path), "updated_at": updated_at})
        return {"count": len(chapters), "chapters": chapters}

    def _write_lock_status(self, thread_id: str) -> dict[str, object]:
        lock_path = self.write_lock_path(thread_id)
        if not lock_path.exists():
            return {"exists": False, "path": str(lock_path)}
        try:
            payload = cast("dict[str, Any]", json.loads(lock_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return {"exists": True, "path": str(lock_path), "readable": False, "stale": self._is_stale_write_lock(lock_path)}
        pid = payload.get("pid")
        running = self._pid_is_running(pid) if isinstance(pid, int) else False
        return {
            "exists": True,
            "path": str(lock_path),
            "readable": True,
            "stale": not running,
            "pid": pid,
            "operation": payload.get("operation"),
            "started_at": payload.get("started_at"),
        }

    def _progress_breakdown(self, state: BookState) -> dict[str, object]:
        section_status = Counter(section.status for section in state.get_all_sections_flat())
        chapter_status = Counter(chapter.status for chapter in state.get_all_chapters_flat())
        total_words = sum(content.word_count or count_words(content.markdown) for content in state.chapters)
        return {
            "phase": state.current_phase,
            "current_section": state.current_section_id,
            "sections": dict(sorted(section_status.items())),
            "chapters": dict(sorted(chapter_status.items())),
            "section_contents": len(state.section_contents),
            "chapter_contents": len(state.chapters),
            "total_words": total_words,
        }

    def _manuscript_drift(self, state: BookState) -> dict[str, object]:
        content_section_ids = {content.section_id for content in state.section_contents}
        content_chapter_ids = {content.chapter_id for content in state.chapters}
        expected_section_paths = {
            content.section_id: self._section_file_path(content.chapter_id, content.section_id)
            for content in state.section_contents
        }
        expected_chapter_paths = {
            content.chapter_id: self._chapter_file_path(content.chapter_id)
            for content in state.chapters
        }
        missing_section_files = [section_id for section_id, path in expected_section_paths.items() if not path.exists()]
        missing_chapter_files = [chapter_id for chapter_id, path in expected_chapter_paths.items() if not path.exists()]
        orphan_section_files: list[str] = []
        orphan_chapter_files: list[int] = []
        if self.manuscript_dir.exists():
            for path in sorted(self.manuscript_dir.glob("chapter-*/*.md")):
                if path.name == "chapter.md":
                    chapter_id = self._chapter_id_from_dir(path.parent.name)
                    if chapter_id is not None and chapter_id not in content_chapter_ids:
                        orphan_chapter_files.append(chapter_id)
                    continue
                section_id = path.stem
                if section_id not in content_section_ids:
                    orphan_section_files.append(section_id)
        return {
            "missing_section_files": missing_section_files,
            "missing_chapter_files": missing_chapter_files,
            "orphan_section_files": orphan_section_files,
            "orphan_chapter_files": sorted(set(orphan_chapter_files)),
        }

    @staticmethod
    def _chapter_id_from_dir(name: str) -> int | None:
        match = re.fullmatch(r"chapter-(\d+)", name)
        return int(match.group(1)) if match is not None else None

    def _quality_failure_summary(self, state: BookState) -> dict[str, object]:
        section_codes: Counter[str] = Counter()
        chapter_codes: Counter[str] = Counter()
        failed_sections: list[str] = []
        failed_chapters: list[int] = []
        for section in state.get_all_sections_flat():
            if section.status != "review_failed":
                continue
            failed_sections.append(section.id)
            section_content = state.get_section_content(section.id)
            if section_content is not None:
                section_codes.update(self._quality_issue_codes(section_content.revision_feedback or section_content.review_feedback))
        for chapter in state.get_all_chapters_flat():
            if chapter.status != "quality_failed":
                continue
            failed_chapters.append(chapter.id)
            chapter_content = state.get_chapter_content(chapter.id)
            if chapter_content is not None:
                chapter_codes.update(self._quality_issue_codes(self._chapter_revision_feedback(chapter_content)))
        return {
            "failed_sections": failed_sections,
            "failed_chapters": failed_chapters,
            "section_issue_codes": dict(sorted(section_codes.items())),
            "chapter_issue_codes": dict(sorted(chapter_codes.items())),
        }

    def _quality_issue_codes(self, feedback: str) -> list[str]:
        codes: list[str] = []
        for payload in self._json_objects_from_text(feedback):
            self._collect_issue_codes(payload, codes)
        return codes

    def _collect_issue_codes(self, payload: object, codes: list[str]) -> None:
        if isinstance(payload, dict):
            code = payload.get("code")
            if isinstance(code, str):
                codes.append(code)
            for value in payload.values():
                self._collect_issue_codes(value, codes)
        elif isinstance(payload, list):
            for item in payload:
                self._collect_issue_codes(item, codes)

    @staticmethod
    def _recommended_commands(state: BookState, publication_audit: dict[str, object]) -> list[str]:
        commands: list[str] = []
        missing_section = next(
            (section.id for section in state.get_all_sections_flat() if state.get_section_content(section.id) is None),
            "",
        )
        failed_section = next((section.id for section in state.get_all_sections_flat() if section.status == "review_failed"), "")
        failed_chapter = next((chapter.id for chapter in state.get_all_chapters_flat() if chapter.status == "quality_failed"), 0)
        if missing_section:
            commands.append(f"uv run python main.py write resume {missing_section}")
            commands.append("uv run python main.py write resume all")
        if failed_section:
            commands.append(f"uv run python main.py write resume {failed_section}")
        if failed_chapter:
            commands.append(f"uv run python main.py write section {failed_chapter}")
            commands.append(f"uv run python main.py write resume {failed_chapter}")
        if audit_has_blocking_issues(publication_audit):
            commands.append("uv run python main.py write audit")
        if not commands and state.current_phase == "completed" and state.publication_approved:
            commands.append("uv run python main.py write export all")
        return list(dict.fromkeys(commands))

    def _load_worker_checkpoint(self, thread_id: str, chapter_id: int) -> BookState:
        state = self._load_state_envelope(
            self.worker_checkpoint_path(thread_id, chapter_id), expected_kind="write.worker.checkpoint"
        )
        self._refresh_runtime_settings(state)
        return state

    def _clear_worker_checkpoint(self, thread_id: str, chapter_id: int) -> None:
        self.worker_checkpoint_path(thread_id, chapter_id).unlink(missing_ok=True)

    def _clear_thread_worker_checkpoints(self, thread_id: str) -> None:
        shutil.rmtree(self.worker_checkpoint_dir(thread_id), ignore_errors=True)

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

    def _write_current_section(self, state: BookState, section: SectionPlan, thread_id: str | None) -> None:
        if not state.set_current_section_by_id(section.id):
            raise RuntimeError(f"三级小节不存在: {section.id}")
        self._ensure_chapter_research(state)
        previous_brief = self._previous_section_brief(state, section)
        markdown = self._normalize_markdown_output(self.writer.write_planned_section(state, section, previous_brief=previous_brief))
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
        if thread_id is not None:
            self._save_write_checkpoint(thread_id, state)
        content = self._review_section_until_pass(state, section, content, previous_brief, thread_id)
        state.upsert_section_content(content)
        self._save_section_file(state, content)
        logger.info("✅ [小节] %s 写作完成，%d 字", section.id, content.word_count)

    @staticmethod
    def _normalize_markdown_output(markdown: str) -> str:
        """移除 LLM 偶发的解释前缀和整篇 Markdown 代码围栏。"""
        text = markdown.strip()
        fence_match = re.search(r"```(?:markdown|md)\s*\n", text, flags=re.IGNORECASE)
        heading_match = re.search(r"^#{1,6}\s+", text, flags=re.MULTILINE)
        if fence_match and (heading_match is None or fence_match.start() < heading_match.start()):
            text = text[fence_match.end():].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
            return text
        if heading_match and heading_match.start() > 0:
            prefix = text[:heading_match.start()].strip()
            if re.search(r"(以下是|完整.*Markdown|合稿后的完整|我将按照|已统一标题)", prefix):
                return text[heading_match.start():].strip()
        return text

    @staticmethod
    def _chapter_revision_shrank_too_much(state: BookState, original: str, revised: str) -> bool:
        """防止整章修订被 LLM 异常压缩成摘要或代码块残片。"""
        original_words = count_words(original)
        revised_words = count_words(revised)
        if original_words < 2000:
            return False
        min_acceptable = int(original_words * 0.45)
        if state.quality.enabled and original_words >= state.quality.min_words_per_chapter:
            min_acceptable = max(min_acceptable, state.quality.min_words_per_chapter)
        return revised_words < min_acceptable

    def _review_section_until_pass(
            self,
            state: BookState,
            section: SectionPlan,
            content: SectionContent,
            previous_brief: str,
            thread_id: str | None,
    ) -> SectionContent:
        """执行小节级基础质量闭环。"""
        for round_index in range(state.max_revision_count + 1):
            issues = self._section_quality_issues(state, section, content)
            if not issues:
                content.review_feedback = ""
                content.revision_feedback = ""
                content.revision_count = round_index
                state.mark_section_status(section.id, "reviewed")
                state.upsert_section_content(content)
                self._save_section_file(state, content)
                if thread_id is not None:
                    self._save_write_checkpoint(thread_id, state)
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
            if thread_id is not None:
                self._save_write_checkpoint(thread_id, state)
            if round_index >= state.max_revision_count:
                content.revision_count = round_index
                state.mark_section_status(section.id, "review_failed")
                state.upsert_section_content(content)
                self._save_section_file(state, content)
                if thread_id is not None:
                    self._save_write_checkpoint(thread_id, state)
                message = f"小节 {section.id} 质量审校未通过，已达修订上限。"
                logger.warning("⚠️ [小节审校] %s 已标记 review_failed 并继续", message)
                if not state.quality.continue_on_failure:
                    raise RuntimeError(message)
                return content

            revised = self._normalize_markdown_output(self.writer.revise_planned_section(
                state,
                section,
                content.markdown,
                feedback,
                previous_brief=previous_brief,
            ))
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
            if thread_id is not None:
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
        allowed_types = (state.style.illustrations or {}).get("allowed_types")
        if not isinstance(allowed_types, list):
            allowed_types = None
        invalid_figures = find_invalid_book_figures(
            markdown,
            marker=marker,
            required_fields=required_fields,
            allowed_types=allowed_types,
        )
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

    def _assemble_chapter_if_ready(
            self,
            state: BookState,
            chapter_id: int,
            *,
            thread_id: str | None = None,
            retry_failed: bool = False,
    ) -> None:
        if state.get_chapter_content(chapter_id) is not None:
            chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
            if chapter is not None and (chapter.status not in {"approved", "quality_failed"} or (retry_failed and chapter.status == "quality_failed")):
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
        content = self._assemble_chapter_from_sections(state, chapter_id)
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

    def _assemble_chapter_from_sections(
            self,
            state: BookState,
            chapter_id: int,
            *,
            revision_count: int = 0,
    ) -> ChapterContent:
        """根据当前小节正文重新合成章节正文。"""
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
        if chapter is None:
            raise RuntimeError(f"章节不存在: {chapter_id}")
        sections = state.get_chapter_section_contents(chapter_id)
        if not sections:
            raise RuntimeError(f"第{chapter_id}章尚无小节正文，无法合稿。")
        raw_markdown = "\n\n".join([f"# 第{chapter.id}章 {chapter.title}", *(item.markdown.strip() for item in sections)])
        markdown = self._normalize_markdown_output(self.assembler.assemble(state, raw_markdown))
        return ChapterContent(
            chapter_id=chapter.id,
            title=chapter.title,
            markdown=markdown,
            word_count=count_words(markdown),
            revision_count=revision_count,
        )

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
            # 原创性检索开销大（每段一次 embedding）；仅在确定性门已通过时才跑，避免为必然失败的章节白付成本。
            if deterministic_report.pass_:
                originality_issues = check_originality(
                    self.rag,
                    content,
                    state.quality,
                    categories=self.cfg.references.query_categories,
                )
                if originality_issues:
                    deterministic_report = deterministic_report.model_copy(
                        update={
                            "pass_": False,
                            "issues": [*deterministic_report.issues, *originality_issues],
                        }
                    )
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
                content = self._revise_chapter_or_sections_from_feedback(
                    state,
                    content,
                    deterministic_report.to_feedback(),
                    round_index + 1,
                    thread_id=thread_id,
                )
                continue

            fact_report, citation_report, style_report, editor_report = self._run_chapter_llm_quality_gates(state, chapter_id)
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
                self._annotate_ai_flavor(content)
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
            content = self._revise_chapter_or_sections_from_feedback(
                state,
                content,
                self._chapter_revision_feedback(content),
                round_index + 1,
                thread_id=thread_id,
            )

        return content

    def _run_chapter_llm_quality_gates(
            self,
            state: BookState,
            chapter_id: int,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """并行执行互不依赖的章节 LLM 质量门，降低审校墙钟时间。"""
        gates = {
            "fact": self.fact_checker.check,
            "citation": self.citation_guard.check,
            "style": self.style_guard.check,
            "editor": self.editor.review,
        }
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=len(gates)) as executor:
            futures = {name: executor.submit(gate, state) for name, gate in gates.items()}
            results = {name: future.result() for name, future in futures.items()}
        logger.info("⏱️ [章节质量门] 第%d章 LLM 门并行完成，耗时 %.1fs", chapter_id, time.perf_counter() - started)
        return results["fact"], results["citation"], results["style"], results["editor"]

    def _revise_chapter_or_sections_from_feedback(
            self,
            state: BookState,
            content: ChapterContent,
            feedback: str,
            revision_count: int,
            *,
            thread_id: str | None,
    ) -> ChapterContent:
        """优先按反馈定位三级小节局部返修，定位不到再整章兜底。"""
        section_ids = self._feedback_section_ids(state, content.chapter_id, feedback)
        if section_ids:
            logger.info("🎯 [章节质量门] 第%d章定位到局部小节: %s", content.chapter_id, ", ".join(section_ids))
            return self._revise_sections_from_chapter_feedback(
                state,
                content,
                section_ids,
                feedback,
                revision_count,
                thread_id=thread_id,
            )
        logger.info("🧩 [章节质量门] 第%d章反馈无法定位三级小节，进入章节级修订", content.chapter_id)
        return self._revise_chapter_from_feedback(state, content, feedback, revision_count)

    def _revise_sections_from_chapter_feedback(
            self,
            state: BookState,
            content: ChapterContent,
            section_ids: list[str],
            feedback: str,
            revision_count: int,
            *,
            thread_id: str | None,
    ) -> ChapterContent:
        """仅修订被章节质量门定位到的三级小节，并重新合稿。"""
        previous_section_id = state.current_section_id
        revised_count = 0
        for section_id in section_ids:
            section = state.get_section_plan(section_id)
            section_content = state.get_section_content(section_id)
            if section is None or section_content is None:
                continue
            if not state.set_current_section_by_id(section_id):
                continue
            previous_brief = self._previous_section_brief(state, section)
            revised_markdown = self._normalize_markdown_output(self.writer.revise_planned_section(
                state,
                section,
                section_content.markdown,
                feedback,
                previous_brief=previous_brief,
            ))
            revised_content = SectionContent(
                section_id=section.id,
                chapter_id=section.chapter_id,
                title=section.title,
                markdown=revised_markdown,
                word_count=count_words(revised_markdown),
                revision_feedback=feedback,
                revision_count=revision_count,
            )
            state.upsert_section_content(revised_content)
            state.mark_section_status(section.id, "written")
            self._save_section_file(state, revised_content)
            reviewed_content = self._review_section_until_pass(
                state,
                section,
                revised_content,
                previous_brief,
                thread_id,
            )
            state.upsert_section_content(reviewed_content)
            self._save_section_file(state, reviewed_content)
            revised_count += 1

        if previous_section_id:
            state.set_current_section_by_id(previous_section_id)
        if revised_count == 0:
            return self._revise_chapter_from_feedback(state, content, feedback, revision_count)

        assembled = self._assemble_chapter_from_sections(state, content.chapter_id, revision_count=revision_count)
        assembled.revision_feedback = feedback
        state.upsert_chapter_content(assembled)
        self._save_chapter_file(state, assembled)
        if thread_id is not None:
            self._save_write_checkpoint(thread_id, state)
        logger.info(
            "🔁 [章节局部修订] 第%d章第%d轮修订 %d 个小节后重新合稿，%d 字",
            content.chapter_id,
            revision_count,
            revised_count,
            assembled.word_count,
        )
        return assembled

    def _feedback_section_ids(self, state: BookState, chapter_id: int, feedback: str) -> list[str]:
        """从质量反馈中提取可局部修订的三级小节编号。"""
        known_ids = [section.id for section in state.get_all_sections_flat() if section.chapter_id == chapter_id]
        known = set(known_ids)
        result: list[str] = []
        for section_id in self._section_ids_from_json_feedback(feedback, known):
            if section_id not in result:
                result.append(section_id)
        for section_id in re.findall(rf"\b{chapter_id}\.\d+\.\d+\b", feedback):
            if section_id in known and section_id not in result:
                result.append(section_id)
        return result

    def _section_ids_from_json_feedback(self, feedback: str, known: set[str]) -> list[str]:
        """解析 JSON 反馈中的 section_id 字段。"""
        result: list[str] = []
        for payload in self._json_objects_from_text(feedback):
            self._collect_section_ids(payload, known, result)
        return result

    @staticmethod
    def _json_objects_from_text(text: str) -> list[object]:
        decoder = json.JSONDecoder()
        payloads: list[object] = []
        index = 0
        while index < len(text):
            start = text.find("{", index)
            if start < 0:
                break
            try:
                payload, end = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                index = start + 1
                continue
            payloads.append(payload)
            index = start + end
        return payloads

    def _collect_section_ids(self, payload: object, known: set[str], result: list[str]) -> None:
        if isinstance(payload, dict):
            section_id = payload.get("section_id")
            if isinstance(section_id, str) and section_id in known and section_id not in result:
                result.append(section_id)
            for value in payload.values():
                self._collect_section_ids(value, known, result)
        elif isinstance(payload, list):
            for item in payload:
                self._collect_section_ids(item, known, result)

    def _revise_chapter_from_feedback(
            self,
            state: BookState,
            content: ChapterContent,
            feedback: str,
            revision_count: int,
    ) -> ChapterContent:
        """按反馈修订章节，并在偏薄时优先扩写。"""
        current_markdown = self._normalize_markdown_output(content.markdown)
        revised = self._normalize_markdown_output(self.expander.expand(state, current_markdown, feedback))
        if revised.strip() == current_markdown.strip():
            with _HEAVY_CHAPTER_REVISION_LOCK:
                logger.info("🚦 [章节修订] 第%d章进入整章重写限流区", content.chapter_id)
                revised = self._normalize_markdown_output(self.writer.revise(state, feedback))
        if self._chapter_revision_shrank_too_much(state, current_markdown, revised):
            original_words = count_words(current_markdown)
            revised_words = count_words(revised)
            logger.warning(
                "⚠️ [章节修订] 第%d章修订结果异常缩水，已拒收: %d → %d 字",
                content.chapter_id,
                original_words,
                revised_words,
            )
            guarded = content.model_copy(
                update={
                    "markdown": current_markdown,
                    "word_count": original_words,
                    "revision_feedback": feedback,
                    "revision_count": revision_count,
                }
            )
            state.upsert_chapter_content(guarded)
            return guarded
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
        self._annotate_ai_flavor(content)
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

    def _annotate_ai_flavor(self, content: ChapterContent) -> None:
        """检测 AI 腔并记录为软提示，不阻断质量门。"""
        issues = detect_ai_flavor(content.markdown)
        content.ai_flavor_feedback = "\n".join(f"- {issue}" for issue in issues)
        if issues:
            logger.info("✍️ [AI 腔软提示] 第%d章发现 %d 类痕迹，已记录供人工参考", content.chapter_id, len(issues))

    def _final_review_if_ready(self, state: BookState, *, thread_id: str | None = None) -> None:
        """所有章节完成后执行全书终审。"""
        expected_chapter_ids = {chapter.id for chapter in state.get_all_chapters_flat()}
        written_chapter_ids = {content.chapter_id for content in state.chapters if content.markdown.strip()}
        if not expected_chapter_ids or not expected_chapter_ids <= written_chapter_ids:
            return

        audit_report = summarize_publication_audit(state)
        if audit_has_blocking_issues(audit_report):
            state.final_report = self._json_feedback(audit_report)
            state.final_revision_chapters = self._final_review_revise_chapter_ids(state, audit_report)
            state.publication_approved = False
            if thread_id is not None:
                self._save_write_checkpoint(thread_id, state)
            logger.warning("⚠️ [终审] 确定性出版审计未通过，已阻断 LLM 终审并保留问题清单")
            if not state.quality.continue_on_failure:
                raise RuntimeError("确定性出版审计未通过，已阻断出版终审。")
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
        revised = self._normalize_markdown_output(self.writer.revise(state, feedback))
        current_markdown = self._normalize_markdown_output(content.markdown)
        if self._chapter_revision_shrank_too_much(state, current_markdown, revised):
            logger.warning(
                "⚠️ [终审返修] 第%d章修订结果异常缩水，已拒收: %d → %d 字",
                chapter_id,
                count_words(current_markdown),
                count_words(revised),
            )
            return
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
        if not self._write_artifacts:
            return
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == content.chapter_id), None)
        if chapter is None:
            return
        path = self._section_file_path(chapter.id, content.section_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.markdown, encoding="utf-8")

    def _save_chapter_file(self, state: BookState, content: ChapterContent) -> None:
        if not self._write_artifacts:
            return
        chapter = next((item for item in state.get_all_chapters_flat() if item.id == content.chapter_id), None)
        if chapter is None:
            return
        path = self._chapter_file_path(chapter.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.markdown, encoding="utf-8")

    def _section_file_path(self, chapter_id: int, section_id: str) -> Path:
        return self.manuscript_dir / f"chapter-{chapter_id:02d}" / f"{section_id}.md"

    def _chapter_file_path(self, chapter_id: int) -> Path:
        return self.manuscript_dir / f"chapter-{chapter_id:02d}" / "chapter.md"

    def _save_write_checkpoint(self, thread_id: str, state: BookState) -> None:
        path = getattr(self, "_write_checkpoint_path_override", None) or self.write_checkpoint_path(thread_id)
        kind = getattr(self, "_write_checkpoint_kind_override", None) or "write.checkpoint"
        self._save_state_envelope(path, state, kind=kind)

    def _save_state_envelope(self, path: Path, state: BookState, *, kind: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        version = WORKER_CHECKPOINT_VERSION if kind == "write.worker.checkpoint" else WRITE_CHECKPOINT_VERSION
        if kind.startswith("outline."):
            version = OUTLINE_VERSION
        payload = {
            "version": version,
            "kind": kind,
            "state": state.model_dump(mode="python"),
        }
        self._atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))

    def _atomic_write_text(self, path: Path, text: str) -> None:
        tmp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
        try:
            with tmp_path.open("w", encoding="utf-8") as file:
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            tmp_path.replace(path)
            self._fsync_directory(path.parent)
        finally:
            tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

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

    def _apply_runtime_quality_settings(self, state: BookState) -> BookState:
        """让质量门运行策略始终跟随当前 quality.yaml。"""
        quality_cfg = getattr(self.cfg, "quality", None)
        if quality_cfg is None:
            return state
        if hasattr(quality_cfg, "model_dump"):
            quality_data = quality_cfg.model_dump()
        elif isinstance(quality_cfg, dict):
            quality_data = quality_cfg
        else:
            quality_data = vars(quality_cfg)
        quality = QualitySettings(**quality_data)
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
