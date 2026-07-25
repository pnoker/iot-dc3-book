"""全书出版前确定性审计。"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from core.chapter_structure import expected_chapter_heading_structure, extract_markdown_headings
from core.originality import split_paragraphs
from core.state import BookState

Severity = Literal["blocker", "major", "minor"]

_TERM_DEFINITION_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9·]{2,24})（([A-Za-z][^），,；;]{1,80})）")
_TERM_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9\-.·]*(?:[ /+][A-Za-z0-9][A-Za-z0-9\-.·]*)*$")
_TERM_HEAD_STOPWORDS = {"和", "或", "包含", "位于", "以", "并", "并入", "至", "至于", "字节"}


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
    _audit_chapter_heading_structure(state, issues)
    _audit_unresolved_foreshadows(state, issues)
    _audit_duplicate_paragraphs(state, issues)
    _audit_terminology_consistency(state, issues)
    _audit_claim_registry(state, issues)
    return issues


def _audit_claim_registry(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    """检查章节声明登记的最小完整性，避免 required_claims/evidence 漂移。"""
    for chapter in state.get_all_chapters_flat():
        blueprint = getattr(chapter, "blueprint", None)
        if blueprint is None:
            continue
        required = set(blueprint.required_claims or [])
        section_claim_ids: set[str] = set()
        for section in blueprint.sections:
            section_claim_ids.update(section.claim_ids or [])
        missing = sorted(required - section_claim_ids)
        if missing:
            issues.append(
                PublicationAuditIssue(
                    code="claim.orphaned",
                    severity="major",
                    message=f"第{chapter.id}章合同声明未在任何小节 claim_ids 中落地: {', '.join(missing)}",
                    suggestion="在对应小节的 claim_ids 中登记该 claim，或在 required_claims 中移除。",
                    chapter_id=chapter.id,
                )
            )
        dossier = getattr(chapter, "research_dossier", None)
        if dossier is None or not dossier.claims:
            continue
        evidence_ids = {note.id for note in dossier.evidence_notes}
        for claim in dossier.claims:
            if claim.claim_type in {"standard", "version", "performance", "metric", "case"} and not claim.evidence_ids:
                issues.append(
                    PublicationAuditIssue(
                        code="claim.missing_evidence",
                        severity="major",
                        message=f"第{chapter.id}章 claim {claim.id} 类型 {claim.claim_type} 缺少证据引用",
                        suggestion="在 ResearchDossier.evidence_notes 增加证据并写入 claim.evidence_ids。",
                        chapter_id=chapter.id,
                    )
                )
                continue
            unknown = sorted(set(claim.evidence_ids) - evidence_ids)
            if unknown:
                issues.append(
                    PublicationAuditIssue(
                        code="claim.invalid_evidence",
                        severity="major",
                        message=f"第{chapter.id}章 claim {claim.id} 引用未登记证据: {', '.join(unknown)}",
                        suggestion="补齐 EvidenceNote 或修正 claim.evidence_ids。",
                        chapter_id=chapter.id,
                    )
                )


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


def _audit_chapter_heading_structure(state: BookState, issues: list[PublicationAuditIssue]) -> None:
    chapter_contents = {content.chapter_id: content for content in state.chapters if content.markdown.strip()}
    for chapter in state.get_all_chapters_flat():
        content = chapter_contents.get(chapter.id)
        if content is None:
            continue
        try:
            expected = expected_chapter_heading_structure(chapter)
        except RuntimeError as exc:
            issues.append(
                PublicationAuditIssue(
                    code="chapter.heading.invalid_plan",
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章标题规划无效: {exc}",
                    suggestion="修复 SectionPlan 编号、顺序、parent_title 和标题契约后重新合稿。",
                )
            )
            continue

        headings = extract_markdown_headings(content.markdown)
        actual_h1 = [heading.title for heading in headings if heading.level == 1]
        actual_h2 = [heading.title for heading in headings if heading.level == 2]
        actual_h3 = [heading.title for heading in headings if heading.level == 3]
        h1_matches = actual_h1 == [expected.chapter_heading]
        h2_matches = actual_h2 == list(expected.parent_headings)
        h3_matches = actual_h3 == list(expected.section_headings)
        if not h1_matches:
            issues.append(
                PublicationAuditIssue(
                    code="chapter.heading.h1_mismatch",
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章 H1 与规划不一致: {actual_h1!r}。",
                    suggestion=f"重新合稿，H1 应为 `{expected.chapter_heading}`。",
                )
            )
        if not actual_h2 and expected.parent_headings:
            code = "chapter.heading.h2_missing"
            message = f"第{chapter.id}章缺少全部二级标题。"
        elif not h2_matches:
            code = "chapter.heading.h2_mismatch"
            message = f"第{chapter.id}章 H2 与规划不一致: {actual_h2!r}。"
        else:
            code = ""
            message = ""
        if code:
            issues.append(
                PublicationAuditIssue(
                    code=code,
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=message,
                    suggestion=f"重新合稿，H2 应依次为: {list(expected.parent_headings)!r}。",
                )
            )
        if not h3_matches:
            missing = [heading for heading in expected.section_headings if heading not in actual_h3]
            issue_code = "chapter.heading.h3_missing" if missing else "chapter.heading.h3_mismatch"
            issues.append(
                PublicationAuditIssue(
                    code=issue_code,
                    severity="blocker",
                    chapter_id=chapter.id,
                    message=f"第{chapter.id}章 H3 与规划不一致，缺失: {missing!r}，实际: {actual_h3!r}。",
                    suggestion="从权威 SectionContent 重新确定性合稿，不要人工维护章节标题骨架。",
                )
            )
        if h1_matches and h2_matches and h3_matches:
            actual_ordered = tuple(heading for heading in headings if heading.level <= 3)
            if actual_ordered != expected.ordered_headings:
                issues.append(
                    PublicationAuditIssue(
                        code="chapter.heading.skeleton_order",
                        severity="blocker",
                        chapter_id=chapter.id,
                        message=f"第{chapter.id}章 H1/H2/H3 标题齐全，但层级挂载或顺序与规划不一致。",
                        suggestion="从权威 SectionContent 重新确定性合稿，恢复 H1 → H2 → H3 的规划顺序。",
                    )
                )
        previous_level: int | None = None
        for heading in headings:
            if previous_level is not None and heading.level > previous_level + 1:
                issues.append(
                    PublicationAuditIssue(
                        code="chapter.heading.level_jump",
                        severity="blocker",
                        chapter_id=chapter.id,
                        message=(
                            f"第{chapter.id}章标题层级从 H{previous_level} 跳至 H{heading.level}: {heading.title}。"
                        ),
                        suggestion="重新合稿并确保标题层级按 H1/H2/H3/H4-H6 逐级展开。",
                    )
                )
                break
            previous_level = heading.level


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
            english = re.sub(r"\s+", " ", english.strip())
            if not english or len(english) > 40:
                continue
            if re.search(r"[一-鿿]", english):
                continue
            if term in _TERM_HEAD_STOPWORDS or any(term.startswith(word) for word in _TERM_HEAD_STOPWORDS):
                continue
            if not _TERM_TOKEN_RE.fullmatch(english):
                continue
            translations[term].add(english.lower())
            first_chapter.setdefault(term, content.chapter_id)
    for term, english_names in translations.items():
        canonical = _canonical_english_variants(english_names)
        if len(canonical) <= 1:
            continue
        issues.append(
            PublicationAuditIssue(
                code="terminology.inconsistent_translation",
                severity="major",
                chapter_id=first_chapter.get(term),
                message=f"术语“{term}”存在多个英文释义: {sorted(canonical)}。",
                suggestion="统一全书术语表，首次出现给出标准英文，后续保持同一中文/英文口径。",
            )
        )


def _canonical_english_variants(english_names: set[str]) -> set[str]:
    """把同一术语的“单复数/大小写”合并为同一释义，减少术语审计误报。"""
    normalized = {name.lower().strip() for name in english_names}
    canonical: set[str] = set()
    for name in normalized:
        singular = _singularize(name)
        if singular in normalized or _singularize(singular) in normalized:
            canonical.add(singular)
        else:
            canonical.add(name)
    return canonical


def _singularize(name: str) -> str:
    """粗略去复数：处理 -ies/-es/-s 三种常见形式。"""
    if name.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    if name.endswith("es") and len(name) > 2 and name[-3] in {"x", "s", "h", "z"}:
        return name[:-2]
    if name.endswith("s") and len(name) > 2 and not name.endswith("ss"):
        return name[:-1]
    return name


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
