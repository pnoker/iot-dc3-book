"""
命令行接口：Typer 命令定义与分发。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypeVar

import typer

from core.log import get_logger, setup_logging
from core.workflow import BookProject

if TYPE_CHECKING:
    from collections.abc import Callable

    from core.state import BookState, ChapterContent, ChapterPlan, SectionContent, SectionPlan

app = typer.Typer(
    help="mi-book-writer: 多 Agent 书籍写作系统",
    no_args_is_help=True,
    add_completion=False,
)
kb_app = typer.Typer(help="知识库索引管理", add_completion=False)
outline_app = typer.Typer(help="大纲生成、导出、批准", add_completion=False)
write_app = typer.Typer(help="小节级写作与断点恢复", add_completion=False)
app.add_typer(kb_app, name="kb")
app.add_typer(outline_app, name="outline")
app.add_typer(write_app, name="write")

ResultT = TypeVar("ResultT")

ConfigOption = Annotated[str, typer.Option("--config", help="配置目录路径")]
ThreadIdOption = Annotated[str, typer.Option("--thread-id", help="任务线程 ID")]
LogLevelOption = Annotated[str, typer.Option("--log-level", help="日志级别")]
LogFileOption = Annotated[str | None, typer.Option("--log-file", help="日志文件路径")]
LogMaxBytesOption = Annotated[int, typer.Option("--log-max-bytes", help="单个日志文件最大字节数")]
LogBackupCountOption = Annotated[int, typer.Option("--log-backup-count", help="保留的历史日志文件数量")]


@app.callback(invoke_without_command=True)
def callback(
        ctx: typer.Context,
        config: ConfigOption = "config",
        thread_id: ThreadIdOption = "book-1",
        log_level: LogLevelOption = "INFO",
        log_file: LogFileOption = None,
        log_max_bytes: LogMaxBytesOption = 10 * 1024 * 1024,
        log_backup_count: LogBackupCountOption = 10,
) -> None:
    """保存全局选项。"""
    ctx.obj = {
        "config": config,
        "thread_id": thread_id,
        "log_level": log_level,
        "log_file": log_file,
        "log_max_bytes": log_max_bytes,
        "log_backup_count": log_backup_count,
    }


def _execute_project(ctx: typer.Context, action: Callable[[BookProject, str], ResultT]) -> ResultT:
    options = ctx.obj or {}
    setup_logging(
        level=str(options.get("log_level", "INFO")),
        log_file=options.get("log_file"),
        log_max_bytes=int(options.get("log_max_bytes", 10 * 1024 * 1024)),
        log_backup_count=int(options.get("log_backup_count", 10)),
    )
    logger = get_logger("main")

    config_path = Path(str(options.get("config", "config")))
    thread_id = str(options.get("thread_id", "book-1"))
    if not config_path.is_dir():
        raise typer.BadParameter(f"配置目录不存在: {config_path}", param_hint="--config")

    logger.info("=" * 60)
    logger.info("📚 mi-book-writer: 分阶段出版工作流")
    logger.info("=" * 60)

    try:
        project = BookProject(str(config_path))
        result = action(project, thread_id)
        logger.info("=" * 60)
        logger.info("✅ 执行完成")
        logger.info("=" * 60)
        return result
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，已保留最近一次小节级 checkpoint。")
        raise typer.Exit(code=0) from None
    except Exception as exc:
        logger.exception("❌ 执行失败")
        raise typer.Exit(code=1) from exc


@kb_app.command("status")
def kb_status(ctx: typer.Context) -> None:
    """查看知识库索引健康状态。"""

    def show(project: BookProject, _thread_id: str) -> None:
        typer.echo(json.dumps(project.kb_status(), ensure_ascii=False, indent=2))

    _execute_project(ctx, show)


@kb_app.command("build")
def kb_build(
        ctx: typer.Context,
        rebuild: Annotated[bool, typer.Option("--rebuild", help="清空现有索引后全量重建")] = False,
) -> None:
    """增量构建知识库；只有传 --rebuild 才全量重建。"""

    def build(project: BookProject, _thread_id: str) -> None:
        typer.echo(json.dumps(project.kb_build(rebuild=rebuild), ensure_ascii=False, indent=2))

    _execute_project(ctx, build)


@outline_app.command("status")
def outline_status(ctx: typer.Context) -> None:
    """查看 current/approved 大纲状态。"""

    def show(project: BookProject, _thread_id: str) -> None:
        typer.echo(json.dumps(project.outline_status(), ensure_ascii=False, indent=2))

    _execute_project(ctx, show)


@outline_app.command("generate")
def outline_generate(
        ctx: typer.Context,
        force: Annotated[bool, typer.Option("--force", help="覆盖 .data/outlines/current.json")] = False,
) -> None:
    """生成全书大纲和三级写作单元。"""

    def generate(project: BookProject, _thread_id: str) -> None:
        state = project.outline_generate(force=force)
        get_logger("main").info(
            "✅ 大纲已生成: %d 章，%d 个三级小节",
            len(state.get_all_chapters_flat()),
            len(state.get_all_sections_flat()),
        )

    _execute_project(ctx, generate)


@outline_app.command("approve")
def outline_approve(
        ctx: typer.Context,
        source: Annotated[str | None, typer.Option("--source", help="指定要批准的大纲 JSON；默认 current.json")] = None,
) -> None:
    """批准大纲；写作阶段只读取 approved.json。"""

    def approve(project: BookProject, _thread_id: str) -> None:
        state = project.outline_approve(source)
        get_logger("main").info(
            "✅ 大纲已批准: %d 章，%d 个三级小节",
            len(state.get_all_chapters_flat()),
            len(state.get_all_sections_flat()),
        )

    _execute_project(ctx, approve)


@outline_app.command("export")
def outline_export(
        ctx: typer.Context,
        file: Annotated[str, typer.Option("--file", help="导出文件路径")],
        approved: Annotated[bool, typer.Option("--approved", help="导出 approved.json；默认导出 current.json")] = False,
) -> None:
    """导出大纲 JSON 供人工审稿。"""

    def export(project: BookProject, _thread_id: str) -> None:
        source = project.outline_approved_path if approved else project.outline_current_path
        target = Path(file)
        if not source.exists():
            raise FileNotFoundError(f"大纲不存在: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        get_logger("main").info("✅ 大纲已导出: %s", target)

    _execute_project(ctx, export)


@write_app.command("start")
def write_start(
        ctx: typer.Context,
        fresh: Annotated[bool, typer.Option("--fresh", help="覆盖当前小节级写作 checkpoint")] = False,
) -> None:
    """基于 approved outline 创建小节级写作 checkpoint。"""

    def start(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.write_start(thread_id, fresh=fresh), ensure_ascii=False, indent=2))

    _execute_project(ctx, start)


@write_app.command("status")
def write_status(ctx: typer.Context) -> None:
    """查看小节级写作进度。"""

    def show(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.write_status(thread_id), ensure_ascii=False, indent=2))

    _execute_project(ctx, show)


@write_app.command("audit")
def write_audit(ctx: typer.Context) -> None:
    """诊断 checkpoint、稿件漂移、失败原因和出版审计问题。"""

    def audit(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.write_audit(thread_id), ensure_ascii=False, indent=2))

    _execute_project(ctx, audit)


@write_app.command("contents")
def write_contents(ctx: typer.Context) -> None:
    """查看小节级目录和完成状态。"""

    def show(project: BookProject, thread_id: str) -> None:
        state = project.load_write_checkpoint_with_workers(thread_id)
        typer.echo(_format_write_contents(state))

    _execute_project(ctx, show)


@write_app.command("resume")
def write_resume(
        ctx: typer.Context,
        target: Annotated[str, typer.Argument(help="写作目标：current、all、1、1.1 或 1.1.1")] = "current",
) -> None:
    """按指定章节、二级节、三级小节或全书继续写作。"""

    def resume_project(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.write_resume(thread_id, target=target), ensure_ascii=False, indent=2))

    _execute_project(ctx, resume_project)


@write_app.command("section")
def write_section(
        ctx: typer.Context,
        target: Annotated[str, typer.Argument(help="章节/二级节/三级小节编号，例如 1、1.1、1.1.1")],
) -> None:
    """查看小节级 checkpoint 中的章节、二级节或三级小节正文。"""

    def show(project: BookProject, thread_id: str) -> None:
        state = project.load_write_checkpoint_with_workers(thread_id)
        typer.echo(_render_write_target(state, target))

    _execute_project(ctx, show)


def _format_write_contents(state: BookState) -> str:
    lines = [
        "目录进度",
        "状态说明：",
        "  小节审校：✅ 通过｜❌ 未通过｜🟡 待审校｜⬜ 待写作",
        "  章节质量门：✅ 通过｜❌ 未通过｜🟡 审核中｜⬜ 待合稿｜📘 已合稿",
        _write_contents_summary(state),
        "",
    ]
    current_section_id = state.current_section_id
    for part in state.parts:
        lines.append(f"{part.prefix}、{part.name}")
        for chapter in part.chapters:
            written_count = sum(1 for section in chapter.sections if state.get_section_content(section.id) is not None)
            assembled = "📘 已合稿" if state.get_chapter_content(chapter.id) is not None else "⬜ 未合稿"
            chapter_badge = _chapter_status_badge(state, chapter)
            lines.append(f"  第{chapter.id}章 {chapter.title}")
            lines.append(f"    章节质量门：{chapter_badge}｜合稿：{assembled}｜小节：{written_count}/{len(chapter.sections)}")
            if chapter.status == "quality_failed" and (chapter_content := state.get_chapter_content(chapter.id)) is not None:
                lines.append(f"    质量原因：{_feedback_summary(_chapter_feedback_text(chapter_content), limit=220)}")
            for section_group_id, group_title, sections in _group_chapter_sections(chapter):
                lines.append(f"    {section_group_id} {group_title}")
                for section in sections:
                    section_content = state.get_section_content(section.id)
                    status_note = _section_status_badge(section, section_content)
                    failure_note = _section_failure_note(section, section_content)
                    current = " ← 当前" if section.id == current_section_id else ""
                    lines.append(f"      小节审校：{status_note}｜{section.id} {section.title}{failure_note}{current}")
    return "\n".join(lines).rstrip()


def _write_contents_summary(state: BookState) -> str:
    sections = state.get_all_sections_flat()
    chapters = state.get_all_chapters_flat()
    reviewed = sum(1 for section in sections if section.status == "reviewed")
    failed = sum(1 for section in sections if section.status == "review_failed")
    waiting_review = sum(
        1
        for section in sections
        if state.get_section_content(section.id) is not None and section.status not in {"reviewed", "review_failed"}
    )
    missing = sum(1 for section in sections if state.get_section_content(section.id) is None)
    approved_chapters = sum(1 for chapter in chapters if chapter.status == "approved")
    failed_chapters = sum(1 for chapter in chapters if chapter.status == "quality_failed")
    assembled_chapters = sum(1 for chapter in chapters if state.get_chapter_content(chapter.id) is not None)
    checking_chapters = max(assembled_chapters - approved_chapters - failed_chapters, 0)
    missing_chapters = len(chapters) - assembled_chapters
    return (
        f"总览：\n"
        f"  小节审校：已写 {len(state.section_contents)}/{len(sections)}｜✅ 通过 {reviewed}｜❌ 未通过 {failed}｜"
        f"🟡 待审校 {waiting_review}｜⬜ 待写作 {missing}\n"
        f"  章节质量门：已合稿 {assembled_chapters}/{len(chapters)}｜✅ 通过 {approved_chapters}｜"
        f"❌ 未通过 {failed_chapters}｜🟡 审核中 {checking_chapters}｜⬜ 待合稿 {missing_chapters}"
    )


def _chapter_status_badge(state: BookState, chapter: ChapterPlan) -> str:
    if chapter.status == "approved":
        return "✅ 通过"
    if chapter.status == "quality_failed":
        return "❌ 未通过"
    if state.get_chapter_content(chapter.id) is not None:
        return "🟡 审核中"
    return "⬜ 待合稿"


def _section_status_badge(section: SectionPlan, content: SectionContent | None) -> str:
    if section.status == "reviewed":
        return "✅ 通过"
    if section.status == "review_failed":
        return "❌ 未通过"
    if content is not None:
        return "🟡 待审校"
    return "⬜ 待写作"


def _section_failure_note(section: SectionPlan, content: SectionContent | None) -> str:
    if section.status != "review_failed" or content is None:
        return ""
    feedback = content.revision_feedback or content.review_feedback
    return f"｜原因：{_feedback_summary(feedback, limit=140)}"


def _group_chapter_sections(chapter: ChapterPlan) -> list[tuple[str, str, list[SectionPlan]]]:
    groups: list[tuple[str, str, list[SectionPlan]]] = []
    group_index: dict[str, int] = {}
    for section in chapter.sections:
        group_id = section.id.rsplit(".", 1)[0]
        group_title = section.parent_title or "未命名节"
        if group_id not in group_index:
            group_index[group_id] = len(groups)
            groups.append((group_id, group_title, []))
        groups[group_index[group_id]][2].append(section)
    return groups


def _render_write_target(state: BookState, target: str) -> str:
    normalized = target.strip()
    if not re.fullmatch(r"\d+(?:\.\d+){0,2}", normalized):
        raise ValueError(f"编号格式无效: {target}，请使用 1、1.1 或 1.1.1")
    parts = normalized.split(".")
    if len(parts) == 3:
        section_content = state.get_section_content(normalized)
        if section_content is None:
            raise ValueError(f"三级小节尚无正文: {normalized}")
        section = state.get_section_plan(normalized)
        return _render_section_with_status(section_content, section)
    chapter_id = int(parts[0])
    chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"章节不存在: {chapter_id}")
    if len(parts) == 1:
        chapter_content = state.get_chapter_content(chapter_id)
        if chapter_content is not None and chapter_content.markdown.strip():
            return _render_chapter_with_status(state, chapter, chapter_content)
        section_contents = state.get_chapter_section_contents(chapter_id)
        if not section_contents:
            raise ValueError(f"第{chapter_id}章尚无正文")
        return "\n\n".join(
            [
                _chapter_status_block(chapter, chapter_content),
                _chapter_section_status_block(state, chapter),
                f"# 第{chapter.id}章 {chapter.title}",
                *(
                    _render_section_with_status(item, state.get_section_plan(item.section_id)).strip()
                    for item in section_contents
                ),
            ]
        )

    prefix = f"{normalized}."
    section_contents = [
        section_content
        for section in chapter.sections
        if section.id.startswith(prefix)
        if (section_content := state.get_section_content(section.id)) is not None
    ]
    if not section_contents:
        raise ValueError(f"二级节尚无正文: {normalized}")
    return "\n\n".join(
        _render_section_with_status(item, state.get_section_plan(item.section_id)).strip() for item in section_contents
    )


def _render_chapter_with_status(state: BookState, chapter: ChapterPlan, content: ChapterContent) -> str:
    return "\n\n".join(
        [_chapter_status_block(chapter, content), _chapter_section_status_block(state, chapter), content.markdown.strip()]
    ).strip()


def _render_section_with_status(content: SectionContent, section: SectionPlan | None) -> str:
    return "\n\n".join([_section_status_block(content, section), content.markdown.strip()]).strip()


def _chapter_status_block(chapter: ChapterPlan, content: ChapterContent | None) -> str:
    lines = ["<!-- write-status", "scope: chapter", f"id: {chapter.id}", f"status: {chapter.status}"]
    if content is not None:
        lines.append(f"revision_count: {content.revision_count}")
        if chapter.status == "quality_failed":
            lines.append("quality_failed: true")
            lines.append(f"feedback: {_feedback_summary(_chapter_feedback_text(content))}")
    lines.append("-->")
    return "\n".join(lines)


def _chapter_section_status_block(state: BookState, chapter: ChapterPlan) -> str:
    lines = ["<!-- section-status"]
    for section in chapter.sections:
        content = state.get_section_content(section.id)
        line = f"{section.id}: {section.status}"
        if section.status == "review_failed" and content is not None:
            line = f"{line}; feedback: {_feedback_summary(content.revision_feedback or content.review_feedback)}"
        lines.append(line)
    lines.append("-->")
    return "\n".join(lines)


def _section_status_block(content: SectionContent, section: SectionPlan | None) -> str:
    status = section.status if section is not None else "unknown"
    lines = ["<!-- write-status", "scope: section", f"id: {content.section_id}", f"status: {status}"]
    lines.append(f"revision_count: {content.revision_count}")
    if status == "review_failed":
        lines.append("review_failed: true")
        lines.append(f"feedback: {_feedback_summary(content.revision_feedback or content.review_feedback)}")
    lines.append("-->")
    return "\n".join(lines)


def _chapter_feedback_text(content: ChapterContent) -> str:
    return "\n\n".join(
        item
        for item in [
            content.publication_feedback,
            content.fact_feedback,
            content.citation_feedback,
            content.style_feedback,
            content.review_feedback,
            content.revision_feedback,
        ]
        if item
    )


def _feedback_summary(feedback: str, *, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", feedback).strip()
    if not text:
        return "无反馈详情"
    if issue_summary := _feedback_issue_summary(text):
        text = issue_summary
    return text if len(text) <= limit else f"{text[:limit]}..."


def _feedback_issue_summary(text: str) -> str:
    issues: list[dict[str, object]] = []
    for payload in _feedback_json_payloads(text):
        if not isinstance(payload, dict):
            continue
        payload_issues = payload.get("issues")
        if isinstance(payload_issues, list):
            issues.extend(issue for issue in payload_issues if isinstance(issue, dict))
    if not issues:
        return ""
    grouped_messages: dict[str, list[str]] = {}
    grouped_counts: dict[str, int] = {}
    for issue in issues:
        code = str(issue.get("code") or issue.get("type") or "").strip()
        message = str(issue.get("message") or issue.get("detail") or "").strip()
        label = code or _trim_feedback_text(message, 72) or "issue"
        grouped_counts[label] = grouped_counts.get(label, 0) + 1
        if code and message:
            grouped_messages.setdefault(label, [])
            if message not in grouped_messages[label]:
                grouped_messages[label].append(message)
        else:
            grouped_messages.setdefault(label, [])
    summaries = []
    for label, messages in list(grouped_messages.items())[:3]:
        count = grouped_counts[label]
        count_note = f" ×{count}" if count > 1 else ""
        if messages:
            summaries.append(f"{label}{count_note}：{_trim_feedback_text(messages[0], 72)}")
        else:
            summaries.append(f"{label}{count_note}")
    remaining_groups = len(grouped_messages) - len(summaries)
    if remaining_groups > 0:
        summaries.append(f"另有 {remaining_groups} 类")
    return "；".join(summaries)


def _trim_feedback_text(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def _feedback_json_payloads(text: str) -> list[object]:
    decoder = json.JSONDecoder()
    payloads = []
    cursor = 0
    while cursor < len(text):
        start = text.find("{", cursor)
        if start == -1:
            break
        try:
            payload, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        payloads.append(payload)
        cursor = start + end
    return payloads


def _chapter_status_label(status: str) -> str:
    return {
        "pending": "待写作",
        "researched": "已研究",
        "written": "已合稿",
        "fact_checked": "已事实核查",
        "styled": "已风格校验",
        "reviewed": "已审校",
        "approved": "质量通过",
        "quality_failed": "质量未通过",
    }.get(status, status)


def _section_status_label(status: str) -> str:
    return {
        "pending": "待写作",
        "written": "待审校",
        "assembled": "已合稿",
        "reviewed": "审校通过",
        "review_failed": "审校未通过",
    }.get(status, status)


@write_app.command("patch-section")
def write_patch_section(
        ctx: typer.Context,
        section_id: Annotated[str, typer.Option("--section-id", help="三级小节编号，例如 1.1.1")],
        file: Annotated[str, typer.Option("--file", help="Markdown 文件路径")],
) -> None:
    """用本地 Markdown 覆盖指定三级小节，并重新合成所在章节。"""

    def patch(project: BookProject, thread_id: str) -> None:
        project.patch_section(thread_id, section_id, Path(file).read_text(encoding="utf-8"))
        get_logger("main").info("✅ 三级小节已应用人工补丁: %s", section_id)

    _execute_project(ctx, patch)


@write_app.command("recover-manuscript")
def write_recover_manuscript(ctx: typer.Context) -> None:
    """把现有 manuscript 草稿显式导入小节级 checkpoint。"""

    def recover(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.recover_manuscript(thread_id), ensure_ascii=False, indent=2))

    _execute_project(ctx, recover)


@write_app.command("export")
def write_export(
        ctx: typer.Context,
        target: Annotated[str, typer.Argument(help="导出目标：markdown、word 或 all")] = "all",
) -> None:
    """导出出版稿 Markdown、Word 或全部格式。"""

    def export(project: BookProject, thread_id: str) -> None:
        result = project.write_export(thread_id, target=target)
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        get_logger("main").info("✅ 输出已生成: %s", result.get("output_dir"))

    _execute_project(ctx, export)


def main(argv: list[str] | None = None) -> None:
    """Typer 脚本入口。"""
    app(args=argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    main()
