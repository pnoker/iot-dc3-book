"""book-builder CLI —— 纯手工写稿 + 自动组装成书。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from book_builder.config import load_config
from book_builder.figures import collect_figure_assets
from book_builder.log import get_logger, setup_logging
from book_builder.manuscript import load_manuscript
from book_builder.markdown import generate_markdown_output
from book_builder.pdf import generate_pdf_output

app = typer.Typer(help="book-builder: 纯手工写稿 + 自动组装成书", no_args_is_help=True)

logger = get_logger("cli")


@app.command()
def build(
    config_dir: Annotated[str, typer.Option("--config", help="配置目录路径")] = "book/config",
    output_dir: Annotated[str, typer.Option("--output", help="输出目录")] = "./output",
    manuscript_dir: Annotated[str, typer.Option("--manuscript", help="手稿目录")] = "book/manuscript",
    figures_dir: Annotated[str, typer.Option("--figures-dir", help="图表资产目录")] = "book/figures",
    skip_figures: Annotated[bool, typer.Option("--skip-figures", help="跳过图表资产收集")] = False,
    log_level: Annotated[str, typer.Option("--log-level", help="日志级别")] = "INFO",
) -> None:
    """从手稿 Markdown 和图表资产组装出版稿。

    读取 book/config/ 下的 YAML 配置和 book/manuscript/ 下的手稿文件，
    收集图表资产，生成层级化 Markdown 输出和单文件 book.md。
    """
    setup_logging(level=log_level)
    cfg = load_config(config_dir)
    assert cfg.parts, "配置中缺少篇章结构"

    # 1) 读取手稿
    chapters = load_manuscript(cfg.parts, manuscript_dir)
    chapter_count = len(chapters)
    total = sum(len(p.chapters) for p in cfg.parts)
    logger.info("手稿读取: %d/%d 章", chapter_count, total)

    # 2) 收集图表资产
    figure_assets = None
    if not skip_figures:
        figure_result = collect_figure_assets(
            chapters,
            f"{output_dir}/figures",
            source_figures_dir=figures_dir,
            illustration_config=cfg.style.illustrations.model_dump(),
        )
        figure_assets = figure_result.assets
        if figure_result.missing:
            logger.warning("图表缺失 %d 个（book-figure 原始块保留在输出中）", len(figure_result.missing))
        logger.info("图表资产: %d 个已收集", len(figure_assets))

    # 3) 生成 Markdown
    cover_html = Path(config_dir).parent / "assets" / "cover.html"
    result = generate_markdown_output(
        chapters, cfg.parts, cfg, output_dir,
        figure_assets=figure_assets, cover_html=cover_html,
    )
    logger.info("✅ 构建完成: %s", result["output_dir"])
    logger.info("   book.md: %s", result["book_markdown"])


@app.command()
def pdf(
    config_dir: Annotated[str, typer.Option("--config", help="配置目录路径")] = "book/config",
    output_dir: Annotated[str, typer.Option("--output", help="输出目录")] = "./output",
    manuscript_dir: Annotated[str, typer.Option("--manuscript", help="手稿目录")] = "book/manuscript",
    figures_dir: Annotated[str, typer.Option("--figures-dir", help="图表资产目录")] = "book/figures",
    css_file: Annotated[str | None, typer.Option("--css", help="PDF 样式 CSS 文件")] = None,
    chrome_bin: Annotated[str | None, typer.Option("--chrome", help="Chrome/Edge 可执行文件路径")] = None,
    skip_build: Annotated[bool, typer.Option("--skip-build", help="跳过 build，直接用已有 book.md")] = False,
    log_level: Annotated[str, typer.Option("--log-level", help="日志级别")] = "INFO",
) -> None:
    """从手稿组装并导出 PDF。

    先执行 build 组装手稿（除非 --skip-build），再通过 Pandoc + Chrome 生成 PDF。
    封面页面从 book/assets/cover.html 单独渲染并合并为首页。
    """
    setup_logging(level=log_level)
    cfg = load_config(config_dir)

    out = Path(output_dir)
    book_md = out / cfg.output.book_markdown
    cover_html = Path(config_dir).parent / "assets" / "cover.html"

    if not skip_build:
        chapters = load_manuscript(cfg.parts, manuscript_dir)
        figure_result = collect_figure_assets(
            chapters,
            f"{output_dir}/figures",
            source_figures_dir=figures_dir,
            illustration_config=cfg.style.illustrations.model_dump(),
        )
        # 不阻断：缺失图表时 book-figure 块保留在输出中
        generate_markdown_output(
            chapters, cfg.parts, cfg, str(out),
            figure_assets=figure_result.assets, cover_html=cover_html,
        )

    if not book_md.exists():
        typer.echo(f"错误: 缺少 {book_md}，请先执行 build")
        raise typer.Exit(1)

    resolved_css = css_file or str(Path(__file__).resolve().parent / "pdf_style.css")

    pdf_path = generate_pdf_output(
        book_md,
        out / "book.pdf",
        css_file=resolved_css if Path(resolved_css).exists() else None,
        chrome_bin=chrome_bin,
        pandoc_bin=cfg.output.pandoc_bin,
        cover_html=cover_html if cover_html.exists() else None,
    )
    if pdf_path:
        logger.info("✅ PDF 导出完成: %s", pdf_path)
    else:
        typer.echo("⚠️  PDF 未生成（缺少 Chrome/Edge），仅 Markdown 可用")


def main(argv: list[str] | None = None) -> None:
    """Typer 脚本入口。"""
    app(args=argv if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    main()
