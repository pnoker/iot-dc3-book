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

    from core.state import BookState, ChapterPlan, SectionPlan

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


@write_app.command("contents")
def write_contents(ctx: typer.Context) -> None:
    """查看小节级目录和完成状态。"""

    def show(project: BookProject, thread_id: str) -> None:
        state = project.load_write_checkpoint(thread_id)
        typer.echo(_format_write_contents(state))

    _execute_project(ctx, show)


@write_app.command("resume")
def write_resume(
        ctx: typer.Context,
        max_sections: Annotated[int, typer.Option("--max-sections", help="本次最多续写几个三级小节")] = 1,
) -> None:
    """从当前 1.1.1 级别断点继续写作。"""

    def resume_project(project: BookProject, thread_id: str) -> None:
        typer.echo(json.dumps(project.write_resume(thread_id, max_sections=max_sections), ensure_ascii=False, indent=2))

    _execute_project(ctx, resume_project)


@write_app.command("section")
def write_section(
        ctx: typer.Context,
        target: Annotated[str, typer.Argument(help="章节/二级节/三级小节编号，例如 1、1.1、1.1.1")],
) -> None:
    """查看小节级 checkpoint 中的章节、二级节或三级小节正文。"""

    def show(project: BookProject, thread_id: str) -> None:
        state = project.load_write_checkpoint(thread_id)
        typer.echo(_render_write_target(state, target))

    _execute_project(ctx, show)


def _format_write_contents(state: BookState) -> str:
    lines = ["目录"]
    current_section_id = state.current_section_id
    for part in state.parts:
        lines.append(f"{part.prefix}、{part.name}")
        for chapter in part.chapters:
            written_count = sum(1 for section in chapter.sections if state.get_section_content(section.id) is not None)
            assembled = "已合稿" if state.get_chapter_content(chapter.id) is not None else "未合稿"
            lines.append(f"  第{chapter.id}章 {chapter.title}（{written_count}/{len(chapter.sections)}，{assembled}）")
            for section_group_id, group_title, sections in _group_chapter_sections(chapter):
                lines.append(f"    {section_group_id} {group_title}")
                for section in sections:
                    done = "✓" if state.get_section_content(section.id) is not None else " "
                    current = " ← 当前" if section.id == current_section_id else ""
                    lines.append(f"      [{done}] {section.id} {section.title}{current}")
    return "\n".join(lines).rstrip()


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
        return section_content.markdown
    chapter_id = int(parts[0])
    chapter = next((item for item in state.get_all_chapters_flat() if item.id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"章节不存在: {chapter_id}")
    if len(parts) == 1:
        chapter_content = state.get_chapter_content(chapter_id)
        if chapter_content is not None and chapter_content.markdown.strip():
            return chapter_content.markdown
        section_contents = state.get_chapter_section_contents(chapter_id)
        if not section_contents:
            raise ValueError(f"第{chapter_id}章尚无正文")
        return "\n\n".join([f"# 第{chapter.id}章 {chapter.title}", *(item.markdown.strip() for item in section_contents)])

    prefix = f"{normalized}."
    section_contents = [
        section_content
        for section in chapter.sections
        if section.id.startswith(prefix)
        if (section_content := state.get_section_content(section.id)) is not None
    ]
    if not section_contents:
        raise ValueError(f"二级节尚无正文: {normalized}")
    return "\n\n".join(item.markdown.strip() for item in section_contents)


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


@write_app.command("export-output")
def write_export_output(ctx: typer.Context) -> None:
    """根据小节级 checkpoint 导出 output。"""

    def export(project: BookProject, thread_id: str) -> None:
        output_dir = project.write_export_output(thread_id)
        get_logger("main").info("✅ 输出已生成: %s", output_dir)

    _execute_project(ctx, export)


def main(argv: list[str] | None = None) -> None:
    """Typer 脚本入口。"""
    app(args=argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    main()
