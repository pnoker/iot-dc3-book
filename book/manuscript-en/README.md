# English Manuscript (manuscript-en)

English final-copy sources for the site's `/en/` locale. The tree mirrors
`book/manuscript/` one-to-one; `scripts/build_web.py` picks up whatever is
translated — untranslated chapters simply stay Chinese-only. Edit a file,
rerun `pnpm web` (or `pnpm dev`), and the site reflects it immediately.

## Conventions

- One file per H2 section, same filenames as the Chinese tree: `chapter-XX/X.Y.md`.
  Optional `chapter-XX/_intro.md` holds the chapter introduction (text between the
  chapter heading and the first H2).
- Same frontmatter key: `section: "1.1 ..."`. Section headings keep the numeric stem:
  `## 1.1 The Evolution and Limits of Industrial Software`; sub-headings `### 1.1.1 ...`.
- Figures are referenced by a language-neutral anchor on its own line — identical in
  both language trees:

  ```
  @[fig-01-01]
  ```

  Do NOT write captions in the manuscript. The figure registry
  (`book/figures/chapter-XX/{fig-id}.yaml`) holds `caption.zh` / `caption.en` and
  in-figure label translations (`labels.en`) for every figure; the page renders the
  inline, light/dark-themed SVG with the caption for the current language.
- Keep the Chinese argumentative structure and paragraph order — translation, not
  rewriting. Terminology follows appendix A of the Chinese edition
  (e.g. 物模型 → thing model, 位号值 → point value, 设备影子 → device shadow).
- Prefer established English terms for standards and products (SCADA, MES, OPC UA,
  Spring AI, MCP); spell out an abbreviation on first use in each chapter.

## Translating a figure's in-artwork labels

Run `uv run python scripts/extract_figure_i18n.py fig-XX-YY --write` to add a
`labels.en` stub to that figure's registry entry, fill in the translations, and the
`/en/` pages render English-labeled SVGs on the next build. Figures without a
mapping fall back to Chinese labels, and the build prints an audit warning. Keep
in-figure English compact — SVG text boxes are sized for the shorter Chinese strings.

## Progress

| Unit | Status |
|---|---|
| Preface — About the Author / Foreword / How to Read | ✅ translated |
| Appendix | ✅ translated |
| Ch. 1–14 sections (83 files + 3 chapter intros) | ✅ translated (~250k words) |
| Figure in-artwork labels (200 figures, ~5,900 strings) | ✅ translated (`labels.en` in each figure registry) |
| Figure captions (`caption.en`) | ✅ translated |

Full English edition is live at `/en/`. Revisions to the Chinese manuscript should
be mirrored here section by section — the shared conventions live in
`TRANSLATION_CONTRACT.md` (same directory).
