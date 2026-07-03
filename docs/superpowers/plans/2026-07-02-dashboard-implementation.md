# Dashboard Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a professional local Web Dashboard for observing, controlling, and previewing the multi-agent book-writing workflow.

**Architecture:** Add a `FastAPI` adapter layer under `api/` that reuses existing `BookWriterGraph`, checkpoint, logs, RAG state, and output files. Add a Vue 3 + Vite + TypeScript
frontend under `web/` that consumes the API and renders overview, chapter preview, logs, and metrics without moving writing logic into the frontend.

**Tech Stack:** Python, FastAPI, uvicorn, Pydantic, pytest, Vue 3, Vite, TypeScript, Naive UI, ECharts, markdown-it.

---

## File Structure

- Create `api/__init__.py`: API package marker.
- Create `api/models.py`: Pydantic DTOs for dashboard responses and command requests.
- Create `api/log_reader.py`: Safe log tailing, parsing, filtering, and secret masking.
- Create `api/services.py`: Dashboard service that reads config, graph status, state, output files, RAG status, and metrics.
- Create `api/app.py`: FastAPI app factory and route registration.
- Modify `pyproject.toml`: add backend runtime dependencies `fastapi` and `uvicorn`.
- Modify `README.md`: add dashboard run instructions.
- Create `tests/test_api_log_reader.py`: tests for log filtering and masking.
- Create `tests/test_api_services.py`: tests for output path safety and DTO aggregation.
- Create `tests/test_api_app.py`: tests for status/logs/output routes.
- Create `web/package.json`: frontend scripts and dependencies.
- Create `web/index.html`, `web/vite.config.ts`, `web/tsconfig*.json`: Vite setup.
- Create `web/src/main.ts`, `web/src/App.vue`: app bootstrap and shell.
- Create `web/src/api/client.ts`: fetch wrappers.
- Create `web/src/pages/*.vue`: overview, chapters, logs, metrics, settings.
- Create `web/src/styles/main.css`: dashboard styling.

## Tasks

### Task 1: Backend log reader

**Files:**

- Create `api/log_reader.py`
- Test `tests/test_api_log_reader.py`

- [ ] Write tests for `mask_secrets`, `parse_log_line`, and `read_logs`.
- [ ] Verify the tests fail because `api.log_reader` does not exist.
- [ ] Implement secret masking, structured parsing, tail limit, and filters.
- [ ] Run `uv run pytest tests/test_api_log_reader.py -v`.

### Task 2: Backend service layer

**Files:**

- Create `api/models.py`
- Create `api/services.py`
- Test `tests/test_api_services.py`

- [ ] Write tests for output path traversal rejection.
- [ ] Write tests for chapter tree aggregation from a `BookState` fixture.
- [ ] Write tests for metrics aggregation from log events.
- [ ] Implement models and services with dependency injection-friendly constructors.
- [ ] Run `uv run pytest tests/test_api_services.py -v`.

### Task 3: FastAPI routes

**Files:**

- Create `api/app.py`
- Modify `pyproject.toml`
- Test `tests/test_api_app.py`

- [ ] Add dependencies `fastapi` and `uvicorn`.
- [ ] Write route tests using `fastapi.testclient.TestClient`.
- [ ] Implement `GET /api/status`, `/api/chapters`, `/api/logs`, `/api/output/files`, `/api/output/file`, `/api/metrics`, `/api/rag/status`.
- [ ] Add `WS /api/events` with periodic snapshots and log tail.
- [ ] Run `uv run pytest tests/test_api_app.py -v`.

### Task 4: CLI entry for dashboard

**Files:**

- Modify `cli.py`
- Modify `README.md`
- Test `tests/test_cli.py`

- [ ] Add a `dashboard` command that starts uvicorn on `127.0.0.1` by default.
- [ ] Add CLI help test for the dashboard command.
- [ ] Document `uv run python main.py dashboard`.
- [ ] Run `uv run pytest tests/test_cli.py -v`.

### Task 5: Frontend scaffold

**Files:**

- Create `web/package.json`
- Create `web/index.html`
- Create `web/vite.config.ts`
- Create `web/tsconfig.json`
- Create `web/tsconfig.node.json`
- Create `web/src/main.ts`
- Create `web/src/App.vue`
- Create `web/src/styles/main.css`

- [ ] Create Vue 3 + Vite + TypeScript setup.
- [ ] Add Naive UI, ECharts, markdown-it dependencies.
- [ ] Add scripts `dev`, `build`, `typecheck`.
- [ ] Run `cd web && pnpm install && pnpm build`.

### Task 6: Frontend API and pages

**Files:**

- Create `web/src/api/client.ts`
- Create `web/src/pages/OverviewPage.vue`
- Create `web/src/pages/ChaptersPage.vue`
- Create `web/src/pages/LogsPage.vue`
- Create `web/src/pages/MetricsPage.vue`
- Create `web/src/pages/SettingsPage.vue`
- Modify `web/src/App.vue`

- [ ] Implement typed API client.
- [ ] Implement overview cards, progress, RAG health, current chapter.
- [ ] Implement chapter tree and Markdown preview.
- [ ] Implement logs filtering UI.
- [ ] Implement metrics charts.
- [ ] Implement settings read-only page.
- [ ] Run `cd web && pnpm build`.

### Task 7: Verification and documentation

**Files:**

- Modify `README.md`

- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run mypy --python-version 3.14 core agents graph api cli.py main.py`.
- [ ] Run `cd web && pnpm build`.
- [ ] Confirm no secrets are displayed in tests or docs.
- [ ] Commit implementation.
