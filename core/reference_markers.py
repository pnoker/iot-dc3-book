"""出版前内部资料标记审计与转换。"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal

from core.state import BookState, EvidenceNote, ResearchDossier
from core.wordcount import count_words

ReferenceCleanMode = Literal["remove", "footnote", "endnote"]

_REFERENCE_MARK_RE = re.compile(
    r"(?P<full>（\s*资料\s*[：:]\s*(?P<inner_cn>[^）]+?)\s*）|\(\s*资料\s*[：:]\s*(?P<inner_ascii>[^)]+?)\s*\))"
)
_REFERENCE_ID_RE = re.compile(r"\[(?P<kind>[SW])(\s*)(?P<number>\d+)\]", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceMarker:
    """正文中的一个内部资料标记。"""

    chapter_id: int
    section_id: str
    marker: str
    reference_ids: list[str]
    missing_ids: list[str]
    context: str


@dataclass(frozen=True)
class ReferenceChapterAudit:
    """单章内部资料标记审计结果。"""

    chapter_id: int
    title: str
    marker_count: int
    reference_count: int
    missing_count: int
    unique_reference_ids: list[str]
    missing_reference_ids: list[str]
    available_reference_ids: list[str]
    markers: list[ReferenceMarker]


@dataclass(frozen=True)
class ReferenceAuditResult:
    """全书内部资料标记审计结果。"""

    chapter_count: int
    marker_count: int
    reference_count: int
    missing_count: int
    chapters: list[ReferenceChapterAudit]

    def to_dict(self) -> dict[str, object]:
        return {
            "chapter_count": self.chapter_count,
            "marker_count": self.marker_count,
            "reference_count": self.reference_count,
            "missing_count": self.missing_count,
            "pass": self.missing_count == 0,
            "chapters": [
                {
                    **asdict(chapter),
                    "markers": [asdict(marker) for marker in chapter.markers],
                }
                for chapter in self.chapters
            ],
        }


@dataclass(frozen=True)
class ReferenceCleanChange:
    """单个内容对象的引用转换结果。"""

    path_hint: str
    before_markers: int
    after_markers: int


@dataclass(frozen=True)
class ReferenceCleanResult:
    """内部资料标记转换结果。"""

    mode: ReferenceCleanMode
    changed_files: list[str]
    marker_count_before: int
    marker_count_after: int
    footnote_count: int
    endnote_count: int
    missing_count: int
    changes: list[ReferenceCleanChange]

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "changed_count": len(self.changed_files),
            "changed_files": self.changed_files,
            "marker_count_before": self.marker_count_before,
            "marker_count_after": self.marker_count_after,
            "footnote_count": self.footnote_count,
            "endnote_count": self.endnote_count,
            "missing_count": self.missing_count,
            "changes": [asdict(change) for change in self.changes],
        }


def audit_reference_markers(state: BookState) -> ReferenceAuditResult:
    """审计章节合稿中的 `[S]/[W]` 内部资料标记。"""
    chapters: list[ReferenceChapterAudit] = []
    for chapter in state.get_all_chapters_flat():
        content = state.get_chapter_content(chapter.id)
        if content is None:
            continue
        dossier = chapter.research_dossier
        available_ids = _available_reference_ids(dossier)
        markers = list(_iter_reference_markers(content.markdown, chapter_id=chapter.id, available_ids=available_ids))
        unique_ids = sorted({ref_id for marker in markers for ref_id in marker.reference_ids}, key=_reference_sort_key)
        missing_ids = sorted({ref_id for marker in markers for ref_id in marker.missing_ids}, key=_reference_sort_key)
        chapters.append(
            ReferenceChapterAudit(
                chapter_id=chapter.id,
                title=chapter.title,
                marker_count=len(markers),
                reference_count=sum(len(marker.reference_ids) for marker in markers),
                missing_count=sum(len(marker.missing_ids) for marker in markers),
                unique_reference_ids=unique_ids,
                missing_reference_ids=missing_ids,
                available_reference_ids=sorted(available_ids, key=_reference_sort_key),
                markers=markers,
            )
        )
    return ReferenceAuditResult(
        chapter_count=len(chapters),
        marker_count=sum(chapter.marker_count for chapter in chapters),
        reference_count=sum(chapter.reference_count for chapter in chapters),
        missing_count=sum(chapter.missing_count for chapter in chapters),
        chapters=chapters,
    )


def clean_reference_markers(state: BookState, *, mode: ReferenceCleanMode) -> ReferenceCleanResult:
    """把章节与小节正文中的内部资料标记移除或转换为出版形式。"""
    if mode not in {"remove", "footnote", "endnote"}:
        raise ValueError("引用清理模式无效，请使用 remove、footnote 或 endnote")

    chapter_dossiers = {chapter.id: chapter.research_dossier for chapter in state.get_all_chapters_flat()}
    changed_files: list[str] = []
    changes: list[ReferenceCleanChange] = []
    marker_count_before = 0
    marker_count_after = 0
    footnote_count = 0
    endnote_count = 0

    for content in state.section_contents:
        dossier = chapter_dossiers.get(content.chapter_id)
        transformed = transform_reference_markers(content.markdown, dossier=dossier, mode=mode)
        marker_count_before += transformed.before_markers
        marker_count_after += transformed.after_markers
        footnote_count += transformed.footnote_count
        endnote_count += transformed.endnote_count
        if transformed.markdown != content.markdown:
            content.markdown = transformed.markdown
            content.word_count = count_words(content.markdown)
            path_hint = f"chapter-{content.chapter_id:02d}/{content.section_id}.md"
            changed_files.append(path_hint)
            changes.append(
                ReferenceCleanChange(
                    path_hint=path_hint,
                    before_markers=transformed.before_markers,
                    after_markers=transformed.after_markers,
                )
            )

    for chapter_content in state.chapters:
        dossier = chapter_dossiers.get(chapter_content.chapter_id)
        transformed = transform_reference_markers(chapter_content.markdown, dossier=dossier, mode=mode)
        marker_count_before += transformed.before_markers
        marker_count_after += transformed.after_markers
        footnote_count += transformed.footnote_count
        endnote_count += transformed.endnote_count
        if transformed.markdown != chapter_content.markdown:
            chapter_content.markdown = transformed.markdown
            chapter_content.word_count = count_words(chapter_content.markdown)
            path_hint = f"chapter-{chapter_content.chapter_id:02d}/chapter.md"
            changed_files.append(path_hint)
            changes.append(
                ReferenceCleanChange(
                    path_hint=path_hint,
                    before_markers=transformed.before_markers,
                    after_markers=transformed.after_markers,
                )
            )

    audit = audit_reference_markers(state)
    return ReferenceCleanResult(
        mode=mode,
        changed_files=changed_files,
        marker_count_before=marker_count_before,
        marker_count_after=marker_count_after,
        footnote_count=footnote_count,
        endnote_count=endnote_count,
        missing_count=audit.missing_count,
        changes=changes,
    )


@dataclass(frozen=True)
class _TransformedMarkdown:
    markdown: str
    before_markers: int
    after_markers: int
    footnote_count: int
    endnote_count: int


def transform_reference_markers(
        markdown: str,
        *,
        dossier: ResearchDossier | None,
        mode: ReferenceCleanMode,
) -> _TransformedMarkdown:
    """转换单段 Markdown 中的内部资料标记。"""
    matches = list(_REFERENCE_MARK_RE.finditer(markdown))
    if not matches:
        return _TransformedMarkdown(markdown, 0, 0, 0, 0)

    available = _evidence_by_id(dossier)
    endnotes: list[str] = []
    footnotes: list[str] = []
    footnote_numbers: dict[str, int] = {}
    endnote_numbers: dict[str, int] = {}

    def replacement(match: re.Match[str]) -> str:
        ids = _normalize_reference_ids(match.group("inner_cn") or match.group("inner_ascii") or "")
        if mode == "remove":
            return ""
        if mode == "footnote":
            parts: list[str] = []
            for ref_id in ids:
                number = footnote_numbers.get(ref_id)
                if number is None:
                    number = len(footnotes) + 1
                    footnote_numbers[ref_id] = number
                    footnotes.append(_format_footnote(number, ref_id, available.get(ref_id)))
                parts.append(f"[^{number}]")
            return "".join(parts)
        parts = []
        for ref_id in ids:
            number = endnote_numbers.get(ref_id)
            if number is None:
                number = len(endnotes) + 1
                endnote_numbers[ref_id] = number
                endnotes.append(_format_endnote(number, ref_id, available.get(ref_id)))
            parts.append(f"[{number}]")
        return "".join(parts)

    body = _REFERENCE_MARK_RE.sub(replacement, markdown)
    if mode == "footnote" and footnotes:
        body = _append_reference_notes(body, "参考注释", footnotes)
    if mode == "endnote" and endnotes:
        body = _append_reference_notes(body, "参考文献说明", endnotes)
    return _TransformedMarkdown(
        body,
        before_markers=len(matches),
        after_markers=len(_REFERENCE_MARK_RE.findall(body)),
        footnote_count=len(footnotes),
        endnote_count=len(endnotes),
    )


def _iter_reference_markers(markdown: str, *, chapter_id: int, available_ids: set[str]) -> list[ReferenceMarker]:
    markers: list[ReferenceMarker] = []
    for match in _REFERENCE_MARK_RE.finditer(markdown):
        inner = match.group("inner_cn") or match.group("inner_ascii") or ""
        reference_ids = _normalize_reference_ids(inner)
        missing_ids = [ref_id for ref_id in reference_ids if ref_id not in available_ids]
        markers.append(
            ReferenceMarker(
                chapter_id=chapter_id,
                section_id=_section_id_for_offset(markdown, match.start()),
                marker=match.group("full"),
                reference_ids=reference_ids,
                missing_ids=missing_ids,
                context=_context(markdown, match.start(), match.end()),
            )
        )
    return markers


def _normalize_reference_ids(text: str) -> list[str]:
    ids: list[str] = []
    for match in _REFERENCE_ID_RE.finditer(text):
        ref_id = f"{match.group('kind').upper()}{int(match.group('number'))}"
        if ref_id not in ids:
            ids.append(ref_id)
    return ids


def _available_reference_ids(dossier: ResearchDossier | None) -> set[str]:
    return set(_evidence_by_id(dossier))


def _evidence_by_id(dossier: ResearchDossier | None) -> dict[str, EvidenceNote]:
    if dossier is None:
        return {}
    return {note.id.upper(): note for note in dossier.evidence_notes}


def _format_footnote(number: int, ref_id: str, note: EvidenceNote | None) -> str:
    if note is None:
        return f"[^{number}]: {ref_id}：未在当前章节研究资料包中找到对应来源。"
    locator = f"，{note.locator}" if note.locator else ""
    excerpt = _compact_excerpt(note.excerpt)
    return f"[^{number}]: {ref_id}：{note.source}{locator}。{excerpt}"


def _format_endnote(number: int, ref_id: str, note: EvidenceNote | None) -> str:
    if note is None:
        return f"{number}. {ref_id}：未在当前章节研究资料包中找到对应来源。"
    locator = f"，{note.locator}" if note.locator else ""
    excerpt = _compact_excerpt(note.excerpt)
    return f"{number}. {ref_id}：{note.source}{locator}。{excerpt}"


def _append_reference_notes(markdown: str, title: str, notes: list[str]) -> str:
    stripped = markdown.rstrip()
    return f"{stripped}\n\n#### {title}\n\n" + "\n".join(notes) + "\n"


def _compact_excerpt(text: str, *, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit].rstrip() + ("…" if len(compact) > limit else "")


def _context(markdown: str, start: int, end: int, *, radius: int = 48) -> str:
    left = max(0, start - radius)
    right = min(len(markdown), end + radius)
    return re.sub(r"\s+", " ", markdown[left:right]).strip()


def _section_id_for_offset(markdown: str, offset: int) -> str:
    section_id = ""
    for match in re.finditer(r"^#{2,6}\s+((?:\d+\.){2}\d+)\b", markdown, flags=re.MULTILINE):
        if match.start() > offset:
            break
        section_id = match.group(1)
    return section_id


def _reference_sort_key(ref_id: str) -> tuple[str, int]:
    match = re.fullmatch(r"([SW])(\d+)", ref_id.upper())
    if match is None:
        return ref_id, 0
    return match.group(1), int(match.group(2))
