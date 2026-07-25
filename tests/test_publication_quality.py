from __future__ import annotations

import pytest

from core.quality_rules import ensure_book_releasable, evaluate_chapter_quality
from core.state import BookState, ChapterContent, ChapterPlan, PartPlan, QualitySettings, SectionContent, SectionPlan
from core.state_validation import is_complete_book_state, require_complete_book_state


def _state(content: ChapterContent | None = None) -> BookState:
    state = BookState(
        parts=[PartPlan(name="基础篇", prefix="一", chapters=[ChapterPlan(id=1, title="概述")])],
        quality=QualitySettings(
            enabled=True,
            mode="release",
            min_words_per_chapter=100,
            target_words_per_chapter=150,
            min_heading_count=3,
            min_figures_or_tables=1,
            require_summary=True,
            require_exercises=True,
            min_exercise_count=3,
            require_existing_local_images=True,
            forbid_placeholder_images=True,
            forbid_unsourced_statistics=True,
            forbid_unresolved_final_review=True,
        ),
    )
    if content is not None:
        state.chapters.append(content)
    return state


def test_publication_quality_fails_short_chapter_and_missing_assets() -> None:
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 第1章 概述\n\n据行业调查，超过六成项目延期。")
    report = evaluate_chapter_quality(_state(content), content)

    assert report.pass_ is False
    codes = {issue.code for issue in report.issues}
    assert "word_count.too_short" in codes
    assert "asset.missing_figure_or_table" in codes
    assert "fact.unsourced_statistics" in codes


def test_publication_quality_fails_when_chapter_exceeds_target_limit() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n" + "内容" * 100,
    )
    state = _state(content)
    state.writing.default_chapter_target_words = 150
    state.quality.max_words_over_target_ratio = 1.2

    report = evaluate_chapter_quality(state, content)

    codes = {issue.code for issue in report.issues}
    assert "word_count.too_long" in codes


def test_publication_quality_flags_unsourced_precise_hard_facts() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n2023年，某城市平台将端到端时延稳定控制在50ms，相关市场规模达到100亿元。",
    )

    report = evaluate_chapter_quality(_state(content), content)

    codes = {issue.code for issue in report.issues}
    assert "fact.unsourced_hard_fact" in codes


def test_publication_quality_locates_unsourced_hard_facts_to_section() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n### 1.1.1 小节一\n\n工程背景。\n\n### 1.1.2 小节二\n\n2023年，平台将端到端时延稳定控制在50ms。",
    )
    state = _state(content)
    state.parts[0].chapters[0].sections = [
        SectionPlan(id="1.1.1", chapter_id=1, title="小节一", heading="1.1.1 小节一"),
        SectionPlan(id="1.1.2", chapter_id=1, title="小节二", heading="1.1.2 小节二"),
    ]
    state.section_contents = [
        SectionContent(section_id="1.1.1", chapter_id=1, title="小节一", markdown="### 1.1.1 小节一\n\n工程背景。"),
        SectionContent(
            section_id="1.1.2",
            chapter_id=1,
            title="小节二",
            markdown="### 1.1.2 小节二\n\n2023年，平台将端到端时延稳定控制在50ms。",
        ),
    ]

    report = evaluate_chapter_quality(state, content)
    issue = next(issue for issue in report.issues if issue.code == "fact.unsourced_hard_fact")

    assert issue.scope == "section"
    assert issue.section_id == "1.1.2"
    assert issue.section_title == "小节二"
    assert '"section_id": "1.1.2"' in report.to_feedback()


def test_publication_quality_allows_sourced_or_hypothetical_hard_facts() -> None:
    sourced = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n2023年，相关标准进入新阶段。（资料：[S1]）",
    )
    hypothetical = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="# 第1章 概述\n\n在假设场景中，网关每10秒采集一次数据，用于说明采集周期对链路压力的影响。",
    )

    sourced_codes = {issue.code for issue in evaluate_chapter_quality(_state(sourced), sourced).issues}
    hypothetical_codes = {issue.code for issue in evaluate_chapter_quality(_state(hypothetical), hypothetical).issues}

    assert "fact.unsourced_hard_fact" not in sourced_codes
    assert "fact.unsourced_hard_fact" not in hypothetical_codes


def test_publication_quality_allows_illustrative_progress_percentage() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown=(
            "# 第1章 概述\n\n"
            "- **固件包写入**：平台通过块传输写入镜像。\n"
            "- **状态反馈**：平台可以获得例如‘升级中 20%’、‘校验失败’等进度状态。"
        ),
    )

    codes = {issue.code for issue in evaluate_chapter_quality(_state(content), content).issues}

    assert "fact.unsourced_statistics" not in codes


def test_publication_quality_ignores_hard_facts_inside_fenced_blocks() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown="""# 第1章 概述

图表和配置块中的数字用于渲染或示例，不是正文事实断言。

```book-figure
id: "fig-01-01"
type: "flowchart"
title: "图1-1 测试流程"
purpose: "说明测试流程。"
layout: "宽100%，图例透明度20%。"
elements:
  - "步骤A"
relationships:
  - "步骤A持续30秒后进入步骤B"
legend:
  - "蓝色=步骤"
caption: "图1-1 展示测试流程。"
render_notes: "HTML/SVG 统一绘制。"
```

```yaml
interval: 5秒
timeout: 50ms
```
""",
    )

    codes = {issue.code for issue in evaluate_chapter_quality(_state(content), content).issues}

    assert "fact.unsourced_statistics" not in codes
    assert "fact.unsourced_hard_fact" not in codes


def test_publication_quality_honors_hypothetical_heading_scope() -> None:
    content = ChapterContent(
        chapter_id=1,
        title="概述",
        markdown=(
            "# 第1章 概述\n\n"
            "#### 假设场景：温室选型\n\n"
            "温度控制需在±1°C以内，湿度需在±5% RH以内。\n\n"
            "#### 真实项目结论\n\n"
            "数据显示，60%的设备需要提前更换。"
        ),
    )

    report = evaluate_chapter_quality(_state(content), content)
    issue = next(issue for issue in report.issues if issue.code == "fact.unsourced_statistics")

    assert "60%" in issue.message
    assert "±5%" not in issue.message


def test_publication_quality_accepts_structured_chapter(tmp_path) -> None:
    image = tmp_path / "figure.png"
    image.write_bytes(b"png")
    markdown = f"""# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。这里避免无来源统计，只讨论可验证的工程判断。

![图1-1 架构图]({image})

## 本章小结
本章总结核心概念、工程判断和实践路径，帮助读者建立稳定的知识结构。

## 思考与练习
1. 解释核心概念。
2. 设计一个小型方案。
3. 分析一个工程风险。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    report = evaluate_chapter_quality(_state(content), content, base_dir=tmp_path)

    assert report.pass_ is True


def test_publication_quality_counts_book_figure_spec_as_figure() -> None:
    markdown = """# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。

```book-figure
id: "fig-01-01"
type: "architecture"
title: "图1-1 平台分层架构"
purpose: "说明平台层次与职责边界。"
layout: "自下而上分层。"
elements:
  - "设备层"
relationships:
  - "设备层连接平台层"
legend:
  - "蓝色=核心平台服务"
caption: "图1-1 展示平台分层架构。"
render_notes: "HTML/SVG 统一绘制。"
```

## 本章小结
本章总结核心概念、工程判断和实践路径，帮助读者建立稳定的知识结构。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    state = _state(content)
    state.quality.min_words_per_chapter = 20
    state.quality.min_heading_count = 2
    state.quality.require_exercises = False
    state.quality.require_existing_local_images = True

    report = evaluate_chapter_quality(state, content)

    assert report.pass_ is True
    assert report.statistics["figure_or_table_count"] == 1


def test_publication_quality_accepts_engineering_closure_without_textbook_summary() -> None:
    markdown = """# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。

```book-figure
id: "fig-01-01"
type: "architecture"
title: "图1-1 平台分层架构"
purpose: "说明平台层次与职责边界。"
layout: "自下而上分层。"
elements:
  - "设备层"
relationships:
  - "设备层连接平台层"
legend:
  - "蓝色=核心平台服务"
caption: "图1-1 展示平台分层架构。"
render_notes: "HTML/SVG 统一绘制。"
```

### 1.2.1 工程检查表：上线前必须确认的边界
这一节不是课后总结，而是把前面的工程判断收束成上线前需要确认的系统边界、风险承担方式和团队协作约定。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    state = _state(content)
    state.quality.min_words_per_chapter = 20
    state.quality.min_heading_count = 2
    state.quality.require_exercises = False
    state.quality.require_existing_local_images = False

    report = evaluate_chapter_quality(state, content)

    codes = {issue.code for issue in report.issues}
    assert "structure.missing_closure" not in codes


def test_publication_quality_rejects_incomplete_book_figure_spec() -> None:
    markdown = """# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。

```book-figure
id: "fig-01-01"
type: "flowchart"
title: "图1-1 数据处理流程"
caption: "图1-1 展示处理流程。"
```

## 本章小结
本章总结核心概念、工程判断和实践路径，帮助读者建立稳定的知识结构。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    state = _state(content)
    state.quality.min_words_per_chapter = 20
    state.quality.min_heading_count = 2

    report = evaluate_chapter_quality(state, content)

    codes = {issue.code for issue in report.issues}
    assert "asset.invalid_book_figure" in codes


def test_publication_quality_rejects_unsupported_book_figure_type() -> None:
    markdown = """# 第1章 概述

## 1.1 工程问题
这是一个足够长的段落，用来解释工程背景、技术约束、系统边界、风险来源、实践方法和读者需要掌握的核心能力。

```book-figure
id: "fig-01-01"
type: "layered-architecture"
title: "图1-1 分层架构"
purpose: "说明平台层次与职责边界。"
layout: "自下而上分层。"
elements:
  - "设备层"
relationships:
  - "设备层连接平台层"
legend:
  - "蓝色=核心平台服务"
caption: "图1-1 展示平台分层架构。"
render_notes: "HTML/SVG 统一绘制。"
```

## 本章小结
本章总结核心概念、工程判断和实践路径，帮助读者建立稳定的知识结构。
"""
    content = ChapterContent(chapter_id=1, title="概述", markdown=markdown)
    state = _state(content)
    state.style.illustrations = {"allowed_types": ["layered"], "marker": "book-figure"}
    state.quality.min_words_per_chapter = 20
    state.quality.min_heading_count = 2

    report = evaluate_chapter_quality(state, content)

    invalid_issue = next(issue for issue in report.issues if issue.code == "asset.invalid_book_figure")
    assert "不支持 type: layered-architecture" in invalid_issue.message


def test_publication_quality_requires_book_figure_per_section() -> None:
    state = BookState(
        parts=[
            PartPlan(
                name="基础篇",
                prefix="一",
                chapters=[
                    ChapterPlan(
                        id=1,
                        title="概述",
                        sections=[
                            SectionPlan(id="1.1.1", chapter_id=1, title="小节一", heading="1.1.1 小节一"),
                            SectionPlan(id="1.1.2", chapter_id=1, title="小节二", heading="1.1.2 小节二"),
                        ],
                    )
                ],
            )
        ],
        quality=QualitySettings(
            enabled=True,
            min_words_per_chapter=1,
            min_heading_count=1,
            min_figures_or_tables=0,
            min_figures_per_section=1,
            require_summary=False,
            require_exercises=False,
            require_existing_local_images=False,
            forbid_placeholder_images=False,
            forbid_unsourced_statistics=False,
        ),
        section_contents=[
            SectionContent(
                section_id="1.1.1",
                chapter_id=1,
                title="小节一",
                markdown="""### 1.1.1 小节一

正文。

```book-figure
id: "fig-01-01"
type: "flowchart"
title: "图1-1 流程"
purpose: "说明流程。"
layout: "从左到右。"
elements:
  - "步骤A"
relationships:
  - "步骤A到步骤B"
legend:
  - "蓝色=步骤"
caption: "图1-1 展示流程。"
render_notes: "HTML/SVG 统一绘制。"
```
""",
            ),
            SectionContent(section_id="1.1.2", chapter_id=1, title="小节二", markdown="### 1.1.2 小节二\n\n正文。"),
        ],
    )
    content = ChapterContent(chapter_id=1, title="概述", markdown="# 第1章 概述\n\n正文。")

    report = evaluate_chapter_quality(state, content)

    codes = {issue.code for issue in report.issues}
    assert "asset.section_missing_book_figure" in codes
    assert "1.1.2 小节二" in report.to_feedback()


def test_release_state_requires_publication_approval() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))
    state.current_phase = "completed"

    assert is_complete_book_state(state) is False
    with pytest.raises(RuntimeError, match="未通过出版级终审"):
        require_complete_book_state(state)
    with pytest.raises(RuntimeError, match="publication_approved"):
        ensure_book_releasable(state)


def test_release_rechecks_chapter_quality_even_when_approved() -> None:
    state = _state(ChapterContent(chapter_id=1, title="概述", markdown="# 正文"))
    state.current_phase = "completed"
    state.publication_approved = True

    with pytest.raises(RuntimeError, match="质量复检失败"):
        ensure_book_releasable(state)
