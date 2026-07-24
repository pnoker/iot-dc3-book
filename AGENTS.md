# Repository Guidelines

## Project Structure & Module Organization

- `core/` contains infrastructure for configuration, state, RAG, workflow orchestration, quality checks, and exports. Markdown/Jinja templates live in `core/templates/`.
- `agents/` contains one module per writing or review role, generally implemented as a `BaseAgent` subclass.
- `cli.py` defines the Typer command tree; `main.py` is the executable entry point installed as `book-writer`.
- `config/*.yaml` defines book metadata, models, references, writing rules, quality gates, and output settings.
- `tests/` mirrors production behavior with `test_*.py` modules. Reference material belongs in `references/` or `research/`; visual sources belong in `assets/`.
- `.data/` stores checkpoints and intermediate manuscript state, while `output/` stores rendered deliverables. Review generated diffs carefully and avoid unrelated churn.

## Build, Test, and Development Commands

- `uv sync --extra dev` installs Python 3.13 dependencies and development tools from `uv.lock`.
- `uv run python main.py --help` lists the CLI; for example, `uv run python main.py write status` inspects writing progress.
- `uv run pytest` runs the complete suite. Pass a file or node ID for focused checks, such as `uv run pytest tests/test_state.py::test_fn`.
- `uv run ruff check .` runs linting; `uv run ruff format --check .` verifies formatting.
- `uv run mypy core agents` performs strict type checking. `uv build` creates distributable artifacts through Hatchling.

## Coding Style & Naming Conventions

Use four-space indentation, LF endings, double quotes, and a 120-column target. Ruff enforces import ordering, modern Python syntax, naming, and common bug patterns. Use `snake_case` for functions/modules, `PascalCase` for classes and Pydantic models, and descriptive constants in `UPPER_SNAKE_CASE`. Keep agent responsibilities isolated and preserve the typed `AppConfig`/`BookState` data flow.

## Testing Guidelines

Pytest discovers `tests/test_*.py`; name test functions `test_<behavior>`. Add a focused regression test before fixing a bug, then run that test and the full suite. No coverage threshold is configured, but new branches and error paths should be exercised. Mock external LLM, network, and filesystem boundaries where existing tests do.

## Commit & Pull Request Guidelines

History primarily uses short imperative prefixes such as `feat:`, `fix:`, `polish:`, `docs:`, and `chore:`. Keep each commit scoped to one concern. Pull requests should explain the user-visible impact, list validation commands, link relevant issues, and call out configuration or generated-output changes. Include before/after images for cover or figure updates, and never commit `.env` secrets or API keys.
