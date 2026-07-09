"""
Writer Agent - 逐章写作与修改
"""

from __future__ import annotations

from core.state import BlueprintSection, BookState, ChapterBlueprint, SectionPlan

from .base import BaseAgent

_WRITER_SYSTEM = """你是一位资深的物联网技术书籍作者。
你的任务是根据详细大纲和参考资料，撰写高质量的技术书籍章节。

## 写作原则
1. 内容专业准确，参考资料需融合改写，不能直接复制
2. 语言通俗易懂，面向工程师和高校师生
3. 适当使用示例、类比来解释复杂概念
4. 按照指定的章节结构撰写：自然开篇 → 正文分节 → 章节收束；不要机械使用“引言”“思考与练习”模板
5. 在合适的地方埋入或回收伏笔，使全书前后呼应
6. 严格遵守格式规范和术语规范
7. 证据优先：统计数字、年份分界、版本号、标准状态、成本、性能、市场规模、项目效果、企业案例等硬事实，必须能在参考资料或研究资料包中找到明确依据
8. 没有证据的硬事实不要写；需要讲解时改为定性分析、作者归纳、假设场景或方法论步骤，并明确标注“假设场景/示意”
9. 扩充篇幅时优先增加原理解释、工程权衡、检查清单、流程步骤、风险分析、对比表和实践清单，不得用虚构数字、虚构真实项目或伪来源凑字数
10. 每个三级小节必须至少包含一个完整 `book-figure` 规格块，用于后续统一 HTML/SVG 绘制
11. 去除 AI 腔，写得像人写的：不用"在当今…时代""随着…的发展""综上所述""值得注意的是"这类套话开场和过渡；不把内容硬凑成"不仅…而且…更…"的排比三连；不在每段结尾加"这为…奠定了基础""具有重要意义"这类空心总结句；敢下明确判断和取舍，而不是一味"既要…也要"的中立平滑；长短句交错、段落有疏密，不要句句等长节奏均匀；克制加粗和冒号列表，用论述代替罗列

## 输出要求
- 输出完整的 Markdown 格式章节正文
- 使用正确的标题层级（# ## ### ####）
- 不要输出章节编号以外的元信息
- 确保内容充实，达到目标字数"""

_EVIDENCE_DISCIPLINE = """## 证据纪律（必须遵守）
- 凡是统计数字、百分比、年份分界、版本号、标准冻结时间、市场规模、成本、时延、吞吐、节省比例、渗透率、项目效果等硬事实，必须来自“参考资料/研究资料包”中明确出现的信息。
- 研究资料包中的 [S] 是本地知识库证据，[W] 是显式 URL 在线证据；引用硬事实时优先在句末用“（资料：[S1]）”这类形式标明证据编号。
- 如果资料中没有明确依据：删除具体数字，改为定性表述；或明确写成“假设场景/示意案例”，且不要给出会被误认为真实项目数据的精确数值。
- 不要编造 Gartner、IDC、IoT Analytics、Cisco、3GPP、企业项目、城市项目等来源；资料包没有的来源不得写入正文。
- 可以用表格、流程、检查清单、风险矩阵、架构解释、伪代码和实践清单扩充内容，这些不需要虚构统计数据。
- 章节宁可少一些硬数字，也不能出现无法核验的硬数字。"""


class WriterAgent(BaseAgent):
    """章节写作 Agent"""

    def write(self, state: BookState) -> str:
        """为当前章节撰写正文"""
        chapter = state.get_current_chapter()
        part = state.get_current_part()
        if not chapter or not part:
            return ""

        prev_summary = state.get_previous_chapters_summary(last_n=2)
        style_prompt = self._build_style_prompt(state.style)
        foreshadow_prompt = self._build_foreshadow_prompt(state)
        ref_prompt = self._build_references_prompt(state)
        covered = state.get_covered_topics(exclude_chapter_id=chapter.id)
        dedup_prompt = (
            f"\n## 其他章节已覆盖内容（本章勿重复展开，如需提及请一句带过并指向对应章节）\n{covered}"
            if covered
            else ""
        )

        # 伏笔任务
        foreshadow_hints: list[str] = []
        for fs in state.foreshadows:
            if fs.planted_chapter == chapter.id and fs.status == "planted":
                foreshadow_hints.append(f"- 请在本章适当位置埋入伏笔: {fs.description}")
            if fs.planned_resolve_chapter == chapter.id and fs.status == "planted":
                foreshadow_hints.append(f"- 请在本章回收之前埋下的伏笔: {fs.description}")
        foreshadow_instruction = "\n## 本章伏笔任务\n" + "\n".join(foreshadow_hints) if foreshadow_hints else ""

        user_prompt = f"""请撰写以下章节：

# 章节信息
- 篇: {part.name}
- 章节: 第{chapter.id}章 {chapter.title}
- 编号前缀: {part.prefix}
- 概述: {chapter.summary}

# 详细大纲
{chapter.outline}

# 核心要点
{chr(10).join(f"- {p}" for p in chapter.key_points)}

{ref_prompt}

{_EVIDENCE_DISCIPLINE}

{foreshadow_prompt}

{foreshadow_instruction}

# 前文摘要（保持连贯性）
{prev_summary if prev_summary else "这是全书第一章，无需前文。"}
{dedup_prompt}

{style_prompt}

请开始撰写完整的章节正文。"""

        self.logger.info("撰写第%d章 %s...", chapter.id, chapter.title)
        if state.writing.sectional_drafting and chapter.blueprint and chapter.blueprint.sections:
            return self._write_from_blueprint(state, chapter.blueprint, user_prompt)
        return self.llm.chat(_WRITER_SYSTEM, user_prompt, temperature=0.8, max_tokens=16384)

    def revise(self, state: BookState, feedback: str) -> str:
        """根据审校反馈修改章节"""
        chapter = state.get_current_chapter()
        content = state.get_chapter_content(chapter.id) if chapter else None
        if not chapter or not content:
            return ""

        style_prompt = self._build_style_prompt(state.style)
        ref_prompt = self._build_references_prompt(state)
        dossier = chapter.research_dossier.model_dump(mode="python") if chapter.research_dossier else {}
        user_prompt = f"""请根据以下审校反馈修改第{chapter.id}章 {chapter.title}。

这是出版级 release 修订，不允许表面应付。反馈中列出的事实、引用、出版质量问题必须逐条解决。

# 审校反馈
{feedback}

{ref_prompt}

# 研究资料包
{dossier}

{_EVIDENCE_DISCIPLINE}

	# 强制修订协议
	- 对反馈中标为 unsupported、partial 或 major 的断言：必须删除、改成定性表述，或用研究资料包中明确证据重写。
	- 对缺少来源的市场规模、百分比、成本、性能、年份分界、案例效果：不要保留原数字；不要换一个新数字。
	- 对反馈中的 word_count.too_long：必须压缩到质量报告给出的 max_words 以内，优先删重复铺垫、旁支历史、无证据硬数字和泛泛口号，不得用新增小节抵消压缩。
	- 对真实案例没有证据时，改为“假设场景/示意案例”，并删除精确成本、比例、时延、数量等伪真实数据。
	- 保留章节厚度时，用概念解释、架构推理、工程检查清单、对比表、风险矩阵和实践步骤补足。
	- 输出前自检：正文中不得再出现反馈指出的无来源断言。

# 当前正文
{content.markdown}

{style_prompt}

请输出修改后的完整章节正文（Markdown 格式）。"""

        self.logger.info("修改第%d章...", chapter.id)
        return self.llm.chat(_WRITER_SYSTEM, user_prompt, temperature=0.35, max_tokens=16384)

    def write_planned_section(self, state: BookState, section: SectionPlan, previous_brief: str = "") -> str:
        """按三级写作单元撰写正文，用于小节级 checkpoint 流程。"""
        chapter = state.get_current_chapter()
        if chapter is None:
            return ""
        blueprint = chapter.blueprint or ChapterBlueprint(chapter_id=chapter.id, title=chapter.title)
        dossier = chapter.research_dossier.model_dump(mode="python") if chapter.research_dossier else {}
        base_prompt = self._build_section_base_prompt(state)
        blueprint_section = BlueprintSection(
            section_id=section.id,
            title=section.title,
            parent_title=section.parent_title,
            heading=section.heading,
            target_words=section.target_words,
            purpose=section.purpose,
            key_points=section.key_points,
            evidence_needed=section.evidence_needed,
            required_elements=section.required_elements,
        )
        return self._write_section(state, blueprint_section, blueprint, dossier, base_prompt, previous_brief)

    def revise_planned_section(
            self,
            state: BookState,
            section: SectionPlan,
            markdown: str,
            feedback: str,
            previous_brief: str = "",
    ) -> str:
        """按质量反馈修订单个三级小节。"""
        chapter = state.get_current_chapter()
        if chapter is None:
            return markdown
        base_prompt = self._build_section_base_prompt(state)
        user_prompt = f"""请只修订当前三级小节，不要输出整章。

# 全章写作上下文
{base_prompt}

{_EVIDENCE_DISCIPLINE}

# 当前小节任务
- 小节编号与标题: {section.heading}
- 目标字数: {section.target_words}
- 小节目的: {section.purpose}
- 要点: {"；".join(section.key_points) if section.key_points else "按蓝图展开"}
- 需要证据: {"；".join(section.evidence_needed) if section.evidence_needed else "无特殊证据要求"}
- 必备元素: {"；".join(section.required_elements) if section.required_elements else "无特殊元素要求"}

# 小节级配图约束
- 不要用 Markdown 图片、Mermaid、SVG、HTML 或 ASCII 图充当占位图；必须在本小节保留或补充至少一个完整 `book-figure` 规格块。
- 即使必备元素中没有显式写 `book-figure`，也要根据本小节内容选择合适的 architecture、sequence、flowchart、dataflow、pyramid、layered、topology、lifecycle、matrix 或 timeline 图表类型。
- `book-figure` 规格块必须清晰描述图表类型、专业图例、元素、关系、图注和 HTML/SVG 渲染说明。

# 前一个小节摘要
{previous_brief or "这是本章第一个小节。"}

# 质量反馈
{feedback}

# 当前小节正文
{markdown}

请输出修订后的该小节 Markdown。必须保留合适的 ## 或 ### 标题，不要输出整章标题。"""
        self.logger.info("修订第%d章小节: %s", chapter.id, section.heading)
        return self.llm.chat(_WRITER_SYSTEM, user_prompt, temperature=0.35, max_tokens=8192)

    def _build_section_base_prompt(self, state: BookState) -> str:
        chapter = state.get_current_chapter()
        part = state.get_current_part()
        if not chapter or not part:
            return ""
        style_prompt = self._build_style_prompt(state.style)
        ref_prompt = self._build_references_prompt(state)
        covered = state.get_covered_topics(exclude_chapter_id=chapter.id)
        dedup_prompt = (
            f"\n## 其他章节已覆盖内容（本节勿重复展开，如需提及请一句带过并指向对应章节）\n{covered}"
            if covered
            else ""
        )
        return f"""# 章节信息
- 篇: {part.name}
- 章节: 第{chapter.id}章 {chapter.title}
- 概述: {chapter.summary}

# 全章高层大纲
{chapter.outline}

# 全章核心要点
{chr(10).join(f"- {p}" for p in chapter.key_points)}

{ref_prompt}

{_EVIDENCE_DISCIPLINE}
{dedup_prompt}

{style_prompt}"""

    def _write_from_blueprint(self, state: BookState, blueprint: ChapterBlueprint, base_prompt: str) -> str:
        """按章节蓝图逐小节写作，避免一次性长文过短或截断。"""
        chapter = state.get_current_chapter()
        if chapter is None:
            return ""
        dossier = chapter.research_dossier.model_dump(mode="python") if chapter.research_dossier else {}
        sections: list[str] = [f"# 第{chapter.id}章 {chapter.title}"]
        previous_brief = ""
        for section in blueprint.sections:
            section_markdown = self._write_section(state, section, blueprint, dossier, base_prompt, previous_brief)
            sections.append(section_markdown.strip())
            previous_brief = section_markdown[:600].replace("\n", " ")
        return "\n\n".join(part for part in sections if part.strip())

    def _write_section(
            self,
            state: BookState,
            section: BlueprintSection,
            blueprint: ChapterBlueprint,
            dossier: dict[str, object],
            base_prompt: str,
            previous_brief: str,
    ) -> str:
        chapter = state.get_current_chapter()
        section_prompt = f"""请只撰写当前小节，不要输出整章。

# 全章写作上下文
{base_prompt}

# 出版级章节蓝图
{blueprint.model_dump(mode="python")}

# 研究资料包
{dossier}

{_EVIDENCE_DISCIPLINE}

# 当前小节任务
- 小节标题: {section.heading}
- 目标字数: {section.target_words}
- 小节目的: {section.purpose}
- 要点: {"；".join(section.key_points) if section.key_points else "按蓝图展开"}
- 需要证据: {"；".join(section.evidence_needed) if section.evidence_needed else "无特殊证据要求"}
- 必备元素: {"；".join(section.required_elements) if section.required_elements else "无特殊元素要求"}

# 小节级出版约束
- 如果使用虚构案例、设想场景、未来年份或工程数字，必须明确标注“假设场景/示意”，不得伪装成真实项目。
- 不要用 Markdown 图片、Mermaid、SVG、HTML 或 ASCII 图充当占位图；必须在本小节输出至少一个完整 `book-figure` 规格块，清晰描述图表类型、专业图例、元素、关系、图注和 HTML/SVG 渲染说明。
- 即使必备元素中没有显式写 `book-figure`，也要根据本小节内容选择合适的 architecture、sequence、flowchart、dataflow、pyramid、layered、topology、lifecycle、matrix 或 timeline 图表类型。
- 不要为了衔接后文而重复本章其他小节会展开的主体内容；本小节只完成当前编号的任务。

# 前一个小节摘要
{previous_brief or "这是本章第一个小节。"}

请输出该小节的 Markdown。必须使用合适的 ## 或 ### 标题，不要输出整章标题。"""
        self.logger.info("撰写第%d章小节: %s", chapter.id if chapter else 0, section.heading)
        return self.llm.chat(_WRITER_SYSTEM, section_prompt, temperature=0.75, max_tokens=8192)
