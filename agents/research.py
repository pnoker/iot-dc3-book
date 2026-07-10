"""
Research Agent - 参考资料检索
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.rag import RAGEngine
from core.state import BookState, EvidenceNote, ReferenceChunk, ResearchDossier
from core.web_research import fetch_web_evidence

from .base import BaseAgent

if TYPE_CHECKING:
    from collections.abc import Sequence

_RESEARCH_SYSTEM = """你是一位物联网领域的技术研究员。
你的任务是根据当前要写的章节主题，生成最佳的检索查询词，
以便从参考资料库中找到可校准事实、术语、标准和技术边界的资料。
参考资料库里可能包含较早期教材；查询应服务于事实核验，不要把教材结构当成写作结构。
请输出 3-5 个检索查询，每行一个，不要包含其他内容。"""


class ResearchAgent(BaseAgent):
    """参考资料检索 Agent"""

    def __init__(
            self,
            llm: object,
            rag: RAGEngine,
            query_categories: Sequence[str] | None = None,
            web_enabled: bool = False,
            web_urls: Sequence[str] | None = None,
            web_timeout_seconds: float = 10.0,
            web_max_chars_per_url: int = 1800,
    ) -> None:
        super().__init__(llm)  # type: ignore[arg-type]
        self.rag = rag
        # 本书检索限定的分类（空/None=全局检索所有分类）
        self.query_categories = list(query_categories) if query_categories else None
        self.web_enabled = web_enabled
        self.web_urls = list(web_urls) if web_urls else []
        self.web_timeout_seconds = web_timeout_seconds
        self.web_max_chars_per_url = web_max_chars_per_url
        self.last_queries: list[str] = []

    def search(self, state: BookState) -> list[ReferenceChunk]:
        """为当前章节检索参考资料"""
        chapter = state.get_current_chapter()
        if not chapter:
            return []

        query_context = f"第{chapter.id}章 {chapter.title}\n{chapter.summary}"
        if chapter.outline:
            query_context += f"\n大纲:\n{chapter.outline}"

        covered = state.get_covered_topics(exclude_chapter_id=chapter.id)
        dedup_hint = (
            f"\n\n以下主题已在其他章节覆盖，请生成聚焦本章差异化内容的查询，避免检索到与这些章节重复的资料：\n{covered}"
            if covered
            else ""
        )
        user_prompt = (
            f"当前要写的章节：\n{query_context}\n\n请生成检索查询词，用于从物联网参考资料中查找事实校准依据。{dedup_hint}"
        )

        self.logger.info("检索第%d章 %s 的参考资料...", chapter.id, chapter.title)
        response = self.llm.chat(_RESEARCH_SYSTEM, user_prompt, temperature=0.3)

        queries = [line.strip() for line in response.strip().split("\n") if line.strip() and not line.startswith("#")]
        queries.append(f"{chapter.title} {chapter.summary}")
        self.last_queries = queries[:5]

        all_chunks: list[ReferenceChunk] = []
        seen_texts: set[str] = set()
        for query in queries[:5]:
            chunks = self.rag.retrieve(query, top_k=5, categories=self.query_categories)
            for chunk in chunks:
                if chunk.text not in seen_texts:
                    seen_texts.add(chunk.text)
                    all_chunks.append(chunk)

        all_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        result = all_chunks[:12]
        self.logger.info("检索完成: %d 个参考段落", len(result))
        return result

    def build_dossier(self, state: BookState, chunks: list[ReferenceChunk]) -> ResearchDossier | None:
        """把检索结果整理为章节资料包。"""
        chapter = state.get_current_chapter()
        if not chapter:
            return None
        evidence_notes = [
            EvidenceNote(
                id=f"S{idx}",
                source_type="local",
                source=chunk.source_file,
                locator=chunk.chapter_or_section,
                excerpt=chunk.text[:500],
            )
            for idx, chunk in enumerate(chunks, 1)
        ]
        source_notes = [f"[{note.id}] {note.source} - {note.locator}: {note.excerpt}" for note in evidence_notes]
        web_notes: list[str] = []
        if self.web_enabled and self.web_urls:
            for idx, item in enumerate(
                    fetch_web_evidence(self.web_urls, self.web_timeout_seconds, self.web_max_chars_per_url), 1
            ):
                note = EvidenceNote(
                    id=f"W{idx}",
                    source_type="web",
                    source=item.title,
                    locator=item.url,
                    excerpt=item.excerpt,
                )
                evidence_notes.append(note)
                web_notes.append(f"[{note.id}] {note.source} - {note.locator}: {note.excerpt}")
        risks = [
            "统计数据、年份、版本号必须有明确来源",
            "IoT DC3 项目能力描述必须与官方文档一致",
            "虚构案例必须标注为假设场景，不能伪装成真实行业案例",
        ]
        return ResearchDossier(
            chapter_id=chapter.id,
            queries=self.last_queries,
            key_claims=chapter.key_points,
            evidence_notes=evidence_notes,
            source_notes=source_notes,
            web_notes=web_notes,
            evidence_policy="正文中的硬事实必须绑定 [S]/[W] 证据；资料包没有的来源不得写入正文。",
            risks=risks,
        )
