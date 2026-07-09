"""Expander Agent - 出版级扩写。"""

from __future__ import annotations

from core.state import BookState
from core.wordcount import count_words

from .base import BaseAgent

_EXPANDER_SYSTEM = """你是一位资深技术书作者，擅长把偏薄的章节扩写成出版级内容。
扩写时必须增加实质内容：工程案例、步骤、对比、风险、最佳实践、图表解释或实践清单。
不要灌水，不要重复原文，不要虚构具体统计数据。输出完整 Markdown 章节。

证据纪律：统计数字、年份分界、版本号、标准状态、成本、性能、市场规模、项目效果、企业案例等硬事实，必须能在参考资料或研究资料包中找到明确依据。没有证据时，改为定性分析、假设场景或方法论步骤；不要编造来源，不要用新数字替换旧数字。"""

_SAFE_EXPANSION_GUIDE = """## 安全扩写策略
- 优先增加：概念解释、架构推理、工程权衡、部署步骤、风险清单、排障路径、术语辨析、实践清单。
- 可以增加 Markdown 表格或 Mermaid 图来解释结构，但不要使用不存在的本地图片路径。
- 所有真实案例都必须来自研究资料包；否则必须标注为“假设场景/示意案例”。
- 无证据时不要写具体百分比、金额、设备数量、年份分界、市场规模、时延、吞吐、节省比例。
- 如果质量反馈指出无来源断言，扩写时必须先删除或降级这些断言，再补足内容厚度。"""


class ExpanderAgent(BaseAgent):
    """章节扩写 Agent。"""

    def expand(self, state: BookState, markdown: str, feedback: str = "") -> str:
        chapter = state.get_current_chapter()
        if not chapter:
            return markdown
        target_words = max(state.quality.target_words_per_chapter, state.writing.target_for_chapter(chapter.id))
        max_words = int(target_words * state.quality.max_words_over_target_ratio) if state.quality.max_words_over_target_ratio else target_words
        current_words = count_words(markdown)
        if current_words >= state.quality.min_words_per_chapter:
            return markdown

        blueprint = chapter.blueprint.model_dump(mode="python") if chapter.blueprint else {}
        references = self._build_references_prompt(state)
        dossier = chapter.research_dossier.model_dump(mode="python") if chapter.research_dossier else {}
        user_prompt = f"""请将以下章节扩写到出版级质量。

# 章节
第{chapter.id}章 {chapter.title}

# 字数
- 当前字数: {current_words}
- 最低字数: {state.quality.min_words_per_chapter}
- 目标字数: {target_words}
- 字数上限: {max_words}

# 章节蓝图
{blueprint}

{references}

# 研究资料包
{dossier}

# 质量反馈
{feedback or "当前主要任务是补足内容厚度和出版要素。"}

{_SAFE_EXPANSION_GUIDE}

# 字数控制
- 扩写后应接近目标字数，但不得超过字数上限。
- 如果质量反馈要求修事实或引用，不要用新增段落堆字数；优先替换、压缩和重写问题段落。

# 当前正文
{markdown}

请输出扩写后的完整 Markdown 章节。"""
        self.logger.info("扩写第%d章: %d → 目标 %d 字", chapter.id, current_words, target_words)
        return self.llm.chat(_EXPANDER_SYSTEM, user_prompt, temperature=0.65, max_tokens=16384)
