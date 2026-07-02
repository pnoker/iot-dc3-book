from __future__ import annotations

from main import parse_args


def test_default_command_is_run() -> None:
    args = parse_args([])

    assert args.command == "run"
    assert args.thread_id == "book-1"


def test_legacy_resume_flag_maps_to_resume_command() -> None:
    args = parse_args(["--resume", "--thread-id", "book-2"])

    assert args.command == "resume"
    assert args.thread_id == "book-2"


def test_status_command_parses_thread_id() -> None:
    args = parse_args(["--thread-id", "book-2", "status"])

    assert args.command == "status"
    assert args.thread_id == "book-2"


def test_patch_chapter_command_requires_chapter_and_file() -> None:
    args = parse_args(["patch-chapter", "--chapter-id", "7", "--file", "chapter.md"])

    assert args.command == "patch-chapter"
    assert args.chapter_id == 7
    assert args.file == "chapter.md"
