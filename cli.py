"""
命令行接口：参数解析与命令分发。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import Logger

from core.log import get_logger, setup_logging
from graph import BookWriterGraph


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="mi-book-writer: 多 Agent 书籍写作系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="config", help="配置目录或文件路径 (默认: config/)")
    parser.add_argument("--thread-id", default="book-1", help="任务线程 ID (默认: book-1)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    parser.add_argument("--log-file", default=None, help="日志文件路径 (可选)")
    parser.add_argument("--resume", action="store_true", help="兼容旧参数：等同于 resume 命令")

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="执行写书流程；默认自动续跑未完成 checkpoint")
    run_parser.add_argument("--fresh", action="store_true", help="忽略并清除同 thread-id 的旧 checkpoint 后重跑")

    subparsers.add_parser("resume", help="从 checkpoint 继续执行")
    subparsers.add_parser("status", help="查看 checkpoint、当前章节和 RAG 健康状态")

    export_parser = subparsers.add_parser("export-state", help="导出 checkpoint 状态 JSON")
    export_parser.add_argument("--file", required=True, help="导出文件路径")

    patch_parser = subparsers.add_parser("patch-chapter", help="用本地 Markdown 覆盖指定章节正文")
    patch_parser.add_argument("--chapter-id", type=int, required=True, help="章节 ID")
    patch_parser.add_argument("--file", required=True, help="Markdown 文件路径")
    patch_parser.add_argument("--regenerate-output", action="store_true", help="补丁后立即重新生成 output")

    revise_parser = subparsers.add_parser("revise-chapter", help="对指定章节执行一次 LLM 局部修订")
    revise_parser.add_argument("--chapter-id", type=int, required=True, help="章节 ID")
    feedback_group = revise_parser.add_mutually_exclusive_group(required=True)
    feedback_group.add_argument("--feedback", help="修订反馈文本")
    feedback_group.add_argument("--feedback-file", help="修订反馈文件")
    revise_parser.add_argument("--regenerate-output", action="store_true", help="修订后立即重新生成 output")

    subparsers.add_parser("regenerate-output", help="仅根据 checkpoint 重新生成 output")

    reset_parser = subparsers.add_parser("reset", help="删除指定 thread-id 的 checkpoint")
    reset_parser.add_argument("--yes", action="store_true", help="确认执行删除")

    args = parser.parse_args(argv)
    if args.command is None:
        args.command = "resume" if args.resume else "run"
        args.fresh = False
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    setup_logging(level=args.log_level, log_file=args.log_file)
    logger = get_logger("main")

    config_path = Path(args.config)
    if not config_path.exists() and not config_path.is_dir():
        logger.error("配置文件不存在: %s", config_path)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("📚 mi-book-writer: 多 Agent 书籍写作系统")
    logger.info("=" * 60)

    try:
        writer = BookWriterGraph(str(config_path))
        dispatch_command(args, writer, logger)

        logger.info("=" * 60)
        logger.info("✅ 执行完成")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.info("⏹️  用户中断，已保留最近一次 checkpoint。下次运行使用 resume 恢复。")
        sys.exit(0)
    except Exception:
        logger.exception("❌ 执行失败")
        sys.exit(1)


def dispatch_command(args: argparse.Namespace, writer: BookWriterGraph, logger: Logger) -> None:
    if args.command == "run":
        writer.run(thread_id=args.thread_id, fresh=getattr(args, "fresh", False))
    elif args.command == "resume":
        logger.info("🔄 从断点恢复...")
        writer.resume(thread_id=args.thread_id)
    elif args.command == "status":
        print(json.dumps(writer.get_status(args.thread_id), ensure_ascii=False, indent=2))
    elif args.command == "export-state":
        writer.export_state(args.thread_id, args.file)
        logger.info("✅ 状态已导出: %s", args.file)
    elif args.command == "patch-chapter":
        markdown = Path(args.file).read_text(encoding="utf-8")
        writer.patch_chapter(args.thread_id, args.chapter_id, markdown)
        logger.info("✅ 第%d章已应用人工补丁", args.chapter_id)
        if args.regenerate_output:
            writer.regenerate_output(args.thread_id)
    elif args.command == "revise-chapter":
        feedback = args.feedback or Path(args.feedback_file).read_text(encoding="utf-8")
        writer.revise_chapter(args.thread_id, args.chapter_id, feedback)
        logger.info("✅ 第%d章已完成局部 LLM 修订", args.chapter_id)
        if args.regenerate_output:
            writer.regenerate_output(args.thread_id)
    elif args.command == "regenerate-output":
        output_dir = writer.regenerate_output(args.thread_id)
        logger.info("✅ 输出已重新生成: %s", output_dir)
    elif args.command == "reset":
        if not args.yes:
            raise ValueError("reset 会删除 checkpoint，请添加 --yes 确认")
        writer.reset_thread(args.thread_id)
        logger.info("✅ 已删除 thread-id=%s 的 checkpoint", args.thread_id)
    else:
        raise ValueError(f"未知命令: {args.command}")
