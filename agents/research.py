"""
Research Agent - 参考资料检索
"""

from __future__ import annotations

from core.rag import RAGEngine
from core.state import BookState, ReferenceChunk

from .base import BaseAgent

_RESEARCH_SYSTEM = """你是一位物联网领域的技术研究员。
你的任务是根据当前要写的章节主题，生成最佳的检索查询词，
以便从参考书籍库中找到最有价值的参考资料。
请输出 3-5 个检索查询，每行一个，不要包含其他内容。"""


class ResearchAgent(BaseAgent):
    """参考资料检索 Agent"""

    def __init__(self, llm: object, rag: RAGEngine) -> None:
        super().__init__(llm)  # type: ignore[arg-type]
        self.rag = rag

    def search(self, state: BookState) -> list[ReferenceChunk]:
        """为当前章节检索参考资料"""
        chapter = state.get_current_chapter()
        if not chapter:
            return []

        query_context = f"第{chapter.id}章 {chapter.title}\n{chapter.summary}"
        if chapter.outline:
            query_context += f"\n大纲:\n{chapter.outline}"

        user_prompt = f"当前要写的章节：\n{query_context}\n\n请生成检索查询词，用于从物联网参考书籍中查找相关资料。"

        self.logger.info("检索第%d章 %s 的参考资料...", chapter.id, chapter.title)
        response = self.llm.chat(_RESEARCH_SYSTEM, user_prompt, temperature=0.3)

        queries = [line.strip() for line in response.strip().split("\n") if line.strip() and not line.startswith("#")]
        queries.append(f"{chapter.title} {chapter.summary}")

        all_chunks: list[ReferenceChunk] = []
        seen_texts: set[str] = set()
        for query in queries[:5]:
            chunks = self.rag.retrieve(query, top_k=3)
            for chunk in chunks:
                if chunk.text not in seen_texts:
                    seen_texts.add(chunk.text)
                    all_chunks.append(chunk)

        all_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        result = all_chunks[:8]
        self.logger.info("检索完成: %d 个参考段落", len(result))
        return result
