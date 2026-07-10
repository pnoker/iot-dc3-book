"""全书出版前确定性审计。"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from core.originality import split_paragraphs
from core.state import BookState

Severity = Literal["blocker", "major", "minor"]

_TERM_DEFINITION_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9·]{2,24})（([A-Za-z][^），,；;]{1,80})）")


@dataclass(frozen=True)
class PublicationAuditIssue:
    """出版审计问题。"""

    code: str
    severity: Severity
    message: str
    suggestion: str = ""
    chapter_id: int | None = None
    section_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
        }
        if self.chapter_id is not None:
            payload["chapter_id"] = self.chapter_id
        if self.section_id is not None:
            payload["section_id"] = self.section_id
        return payload


def audit_publication_readiness(state: BookState) -> list[PublicationAuditIssue]:
    """返回全书发布前必须处理的确定性问题。"""
    issues: list[PublicationAuditIssue] = []
    _audit_chapter_and_section_completion(state, issues)
    _audit_unresolved_foreshadows(state, issues)
    _audit_duplicate_paragraphs(state, issues)
    _audit_terminology_consistency(state, issues)
    return issues


def summarize_publication_audit(state: BookState) -> dict[str, object]:
    """生成可写入 final_report 或诊断命令的出版审计摘要。"""
    issues = audit_publication_readiness(state)
    blocking = [issue for issue in issues if issue.severity in {"blocker", "major"}]
    revise_chapters = _revise_chapters_from_issues(issues)
    return {
        "pass": not blocking,
        "source": "deterministic_publication_audit",
        "issue_count": len(issues),
        "blocking_issue_count": len(blocking),
        "issues": [issue.to_dict() for issue in issues],
        "revise_chapters": revise_chapters,
        "summary": _audit_summary(issues),
    }


def audit_has_blocking_issues(report: dict[str, object]) -> bool:
    """判断审计报告是否存在会阻断出版通过的问题。"""
    return report.get("pass") is not True


def _audit_chapter_and_section_completion(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    chapter_contents = {content.chapter_id: content for content in state.chapters if content.markdown.strip()}
    section_contents = {content.section_id: content for content in state.section_contents if content.markdown.strip()}
    for chapter in state.get_all_chapters_flat():
        if chapter.id not in chapter_contents:
            issues.append(
                PublicationAuditIssue(
                    code="chapter.missing_content",
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章尚未合稿。",
                    suggestion=f"执行 `uv run python main.py write resume {chapter.id}` 完成该章。",
                )
            )
        elif chapter.status == "quality_failed":
            issues.append(
                PublicationAuditIssue(
                    code="chapter.quality_failed",
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章章节质量门未通过。",
                    suggestion=f"查看 `uv run python main.py write section {chapter.id}` 的反馈后修订。",
                )
            )
        elif chapter.status != "approved":
            issues.append(
                PublicationAuditIssue(
                    code="chapter.not_approved",
                    severity="major",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章状态为 {chapter.status}，尚未达到出版通过状态。",
                    suggestion=f"执行 `uv run python main.py write resume {chapter.id}` 重新进入章节质量门。",
                )
            )
        for section in chapter.sections:
            if section.id not in section_contents:
                issues.append(
                    PublicationAuditIssue(
                        code="section.missing_content",
                        severity="blocker",
                        chapter_id=chapter.id,
                        section_id=section.id,
                        message=f"三级小节 {section.id} 尚无正文。",
                        suggestion=f"执行 `uv run python main.py write resume {section.id}` 补写该小节。",
                    )
                )
            elif section.status == "review_failed":
                issues.append(
                    PublicationAuditIssue(
                        code="section.review_failed",
                        severity="blocker",
                        chapter_id=chapter.id,
                        section_id=section.id,
                        message=f"三级小节 {section.id} 小节审校未通过。",
                        suggestion=f"执行 `uv run python main.py write resume {section.id}` 自动重试，或人工修订后 `write patch-section`。",
                    )
                )
            elif section.status != "reviewed":
                issues.append(
                    PublicationAuditIssue(
                        code="section.not_reviewed",
                        severity="major",
                        chapter_id=chapter.id,
                        section_id=section.id,
                        message=f"三级小节 {section.id} 状态为 {section.status}，尚未审校通过。",
                        suggestion=f"执行 `uv run python main.py write resume {section.id}` 完成审校。",
                    )
                )


def _audit_unresolved_foreshadows(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    if not state.quality.forbid_unresolved_final_review:
        return
    for item in state.foreshadows:
        if item.status != "planted":
            continue
        issues.append(
            PublicationAuditIssue(
                code="foreshadow.unresolved",
                severity="blocker",
                chapter_id=item.planned_resolve_chapter,
                message=f"伏笔 {item.id} 尚未回收: {item.description}",
                suggestion=f"在第{item.planned_resolve_chapter}章自然回收该伏笔，或明确标记为 abandoned。",
            )
        )


def _audit_duplicate_paragraphs(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    by_paragraph: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for content in state.chapters:
        for paragraph in split_paragraphs(content.markdown):
            normalized = re.sub(r"\s+", "", paragraph)
            if len(normalized) < 160:
                continue
            by_paragraph[normalized].append((content.chapter_id, paragraph[:80].replace("\n", " ")))
    for occurrences in by_paragraph.values():
        chapter_ids = sorted({chapter_id for chapter_id, _excerpt in occurrences})
        if len(chapter_ids) <= 1:
            continue
        excerpt = occurrences[0][1]
        issues.append(
            PublicationAuditIssue(
                code="content.duplicate_paragraph",
                severity="major",
                chapter_id=chapter_ids[0],
                message=f"多章出现高度重复段落，涉及章节: {chapter_ids}，片段: {excerpt}...",
                suggestion="压缩重复论述；保留首次完整解释，后续章节只做一句引用或差异化展开。",
            )
        )
        if len([issue for issue in issues if issue.code == "content.duplicate_paragraph"]) >= 10:
            return


def _audit_terminology_consistency(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    translations: dict[str, set[str]] = defaultdict(set)
    first_chapter: dict[str, int] = {}
    for content in state.chapters:
        for term, english in _TERM_DEFINITION_RE.findall(content.markdown):
            normalized_english = re.sub(r"\s+", " ", english.strip()).lower()
            translations[term].add(normalized_english)
            first_chapter.setdefault(term, content.chapter_id)
    for term, english_names in translations.items():
        if len(english_names) <= 1:
            continue
        issues.append(
            PublicationAuditIssue(
                code="terminology.inconsistent_translation",
                severity="major",
                chapter_id=first_chapter.get(term),
                message=f"术语“{term}”存在多个英文释义: {sorted(english_names)}。",
                suggestion="统一全书术语表，首次出现给出标准英文，后续保持同一中文/英文口径。",
            )
        )


def _revise_chapters_from_issues(issues: list[PublicationAuditIssue]) -> list[dict[str, object]]:
    reasons: dict[int, list[str]] = defaultdict(list)
    for issue in issues:
        if issue.severity not in {"blocker", "major"} or issue.chapter_id is None:
            continue
        if issue.message not in reasons[issue.chapter_id]:
            reasons[issue.chapter_id].append(issue.message)
    return [
        {"chapter_id": chapter_id, "reason": "；".join(chapter_reasons[:3])}
        for chapter_id, chapter_reasons in sorted(reasons.items())
    ]


def _audit_summary(issues: list[PublicationAuditIssue]) -> str:
    if not issues:
        return "确定性出版审计通过。"
    counts: dict[str, int] = defaultdict(int)
    for issue in issues:
        counts[issue.severity] += 1
    return "确定性出版审计发现问题：" + "，".join(f"{severity}={count}" for severity, count in sorted(counts.items()))
