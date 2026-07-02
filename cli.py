"""
命令行接口：Typer 命令定义与分发。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypeVar

import typer
import uvicorn

from core.log import get_logger, setup_logging
from graph import BookWriterGraph

if TYPE_CHECKING:
    from collections.abc import Callable
    from logging import Logger

app = typer.Typer(
    help="mi-book-writer: 多 Agent 书籍写作系统",
    no_args_is_help=False,
    add_completion=False,
)

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
    """保存全局选项；无子命令时执行 run。"""
    ctx.obj = {
        "config": config,
        "thread_id": thread_id,
        "log_level": log_level,
        "log_file": log_file,
        "log_max_bytes": log_max_bytes,
        "log_backup_count": log_backup_count,
    }
    if ctx.invoked_subcommand is None:
        _execute(ctx, lambda writer, selected_thread_id: writer.run(thread_id=selected_thread_id, fresh=False))


def _execute(ctx: typer.Context, action: Callable[[BookWriterGraph, str], ResultT]) -> ResultT:
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
    logger.info("📚 mi-book-writer: 多 Agent 书籍写作系统")
    logger.info("=" * 60)

    try:
        writer = BookWriterGraph(str(config_path))
        result = action(writer, thread_id)
        logger.info("=" * 60)
        logger.info("✅ 执行完成")
        logger.info("=" * 60)
        return result
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，已保留最近一次 checkpoint。下次运行使用 resume 恢复。")
        raise typer.Exit(code=0) from None
    except Exception as exc:
        logger.exception("❌ 执行失败")
        raise typer.Exit(code=1) from exc


@app.command()
def run(
    ctx: typer.Context,
    fresh: Annotated[bool, typer.Option("--fresh", help="忽略并清除同 thread-id 的旧 checkpoint 后重跑")] = False,
) -> None:
    """执行写书流程；默认自动续跑未完成 checkpoint。"""
    _execute(ctx, lambda writer, thread_id: writer.run(thread_id=thread_id, fresh=fresh))


@app.command()
def resume(ctx: typer.Context) -> None:
    """从 checkpoint 继续执行。"""
    logger = get_logger("main")
    _execute(ctx, lambda writer, thread_id: _resume(writer, thread_id, logger))


def _resume(writer: BookWriterGraph, thread_id: str, logger: Logger) -> dict[str, object]:
    logger.info("🔄 从断点恢复...")
    return writer.resume(thread_id=thread_id)


@app.command()
def status(ctx: typer.Context) -> None:
    """查看 checkpoint、当前章节和 RAG 健康状态。"""

    def show_status(writer: BookWriterGraph, thread_id: str) -> None:
        typer.echo(json.dumps(writer.get_status(thread_id), ensure_ascii=False, indent=2))

    _execute(ctx, show_status)


@app.command("export-state")
def export_state(
    ctx: typer.Context,
    file: Annotated[str, typer.Option("--file", help="导出文件路径")],
) -> None:
    """导出 checkpoint 状态 JSON。"""

    def export(writer: BookWriterGraph, thread_id: str) -> None:
        writer.export_state(thread_id, file)
        get_logger("main").info("✅ 状态已导出: %s", file)

    _execute(ctx, export)


@app.command("patch-chapter")
def patch_chapter(
    ctx: typer.Context,
    chapter_id: Annotated[int, typer.Option("--chapter-id", help="章节 ID")],
    file: Annotated[str, typer.Option("--file", help="Markdown 文件路径")],
    regenerate_output: Annotated[bool, typer.Option("--regenerate-output", help="补丁后立即重新生成 output")] = False,
) -> None:
    """用本地 Markdown 覆盖指定章节正文。"""

    def patch(writer: BookWriterGraph, thread_id: str) -> None:
        markdown = Path(file).read_text(encoding="utf-8")
        writer.patch_chapter(thread_id, chapter_id, markdown)
        logger = get_logger("main")
        logger.info("✅ 第%d章已应用人工补丁", chapter_id)
        if regenerate_output:
            writer.regenerate_output(thread_id)

    _execute(ctx, patch)


@app.command("revise-chapter")
def revise_chapter(
    ctx: typer.Context,
    chapter_id: Annotated[int, typer.Option("--chapter-id", help="章节 ID")],
    feedback: Annotated[str | None, typer.Option("--feedback", help="修订反馈文本")] = None,
    feedback_file: Annotated[str | None, typer.Option("--feedback-file", help="修订反馈文件")] = None,
    regenerate_output: Annotated[bool, typer.Option("--regenerate-output", help="修订后立即重新生成 output")] = False,
) -> None:
    """对指定章节执行一次 LLM 局部修订。"""
    if bool(feedback) == bool(feedback_file):
        raise typer.BadParameter("必须且只能提供 --feedback 或 --feedback-file")

    def revise(writer: BookWriterGraph, thread_id: str) -> None:
        selected_feedback = feedback if feedback is not None else Path(str(feedback_file)).read_text(encoding="utf-8")
        writer.revise_chapter(thread_id, chapter_id, selected_feedback)
        logger = get_logger("main")
        logger.info("✅ 第%d章已完成局部 LLM 修订", chapter_id)
        if regenerate_output:
            writer.regenerate_output(thread_id)

    _execute(ctx, revise)


@app.command("regenerate-output")
def regenerate_output(ctx: typer.Context) -> None:
    """仅根据 checkpoint 重新生成 output。"""

    def regenerate(writer: BookWriterGraph, thread_id: str) -> None:
        output_dir = writer.regenerate_output(thread_id)
        get_logger("main").info("✅ 输出已重新生成: %s", output_dir)

    _execute(ctx, regenerate)


@app.command()
def reset(
    ctx: typer.Context,
    yes: Annotated[bool, typer.Option("--yes", help="确认执行删除")] = False,
) -> None:
    """删除指定 thread-id 的 checkpoint。"""
    if not yes:
        raise typer.BadParameter("reset 会删除 checkpoint，请添加 --yes 确认")
    _execute(ctx, lambda writer, thread_id: writer.reset_thread(thread_id))


@app.command()
def dashboard(
    host: Annotated[str, typer.Option("--host", help="Dashboard 监听地址")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Dashboard 监听端口")] = 18080,
    reload: Annotated[bool, typer.Option("--reload", help="开发模式自动重载")] = False,
) -> None:
    """启动本地 Web Dashboard。"""
    uvicorn.run("api.app:app", host=host, port=port, reload=reload)


def main(argv: list[str] | None = None) -> None:
    """Typer 脚本入口。"""
    app(args=argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    main()
