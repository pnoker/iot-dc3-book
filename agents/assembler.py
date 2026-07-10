"""Chapter Assembler Agent - 章节合稿与衔接。"""

from __future__ import annotations

from core.state import BookState

from .base import BaseAgent

_ASSEMBLER_SYSTEM = """你是一位技术图书责任编辑。
你的任务是合稿与润色：统一标题层级、消除重复、补齐过渡句、统一术语和图表编号。
不要删除实质内容，不要引入无来源的新统计数据。输出完整 Markdown 章节。"""


class ChapterAssemblerAgent(BaseAgent):
    """章节合稿 Agent。"""

    def assemble(self, state: BookState, markdown: str) -> str:
        chapter = state.get_current_chapter()
        if not chapter:
            return markdown
        style_prompt = self._build_style_prompt(state.style)
        user_prompt = f"""请对以下章节进行出版级合稿。

# 章节
第{chapter.id}章 {chapter.title}

{style_prompt}

# 合稿要求
- 保留完整内容和章节结构
- 统一标题层级与编号
- 补齐小节之间的自然衔接
- 检查章节收束是否自然，可使用方法论回扣、工程检查表、实践边界、趋势判断或延伸阅读；不要补教科书式本章小结或课后练习题
- 原样保留并规范化 `book-figure` 图表规格块；不要把它们转换成 Markdown 图片、Mermaid、SVG、HTML 或 ASCII 图
- 若章节已有多个 `book-figure`，统一图号、图名、图例和图注表达，确保后续 HTML/SVG 统一绘制
- 不要添加没有来源的统计数据

# 当前正文
{markdown}

请输出合稿后的完整 Markdown。"""
        self.logger.info("合稿第%d章...", chapter.id)
        return self.llm.chat(_ASSEMBLER_SYSTEM, user_prompt, temperature=0.35, max_tokens=16384)
