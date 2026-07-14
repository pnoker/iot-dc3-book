"""出版级技术图表设计 Agent。"""

from __future__ import annotations

import contextlib
import json
import re
import signal
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agents.base import BaseAgent
from core.figures import FigureDesign, FigureSpec, render_figure_blueprint_svg
from core.llm_client import LLMClient

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import FrameType

# 技能文件缺失时的内置设计系统兜底，保证管线永不因缺文件而崩。
_FALLBACK_DESIGN_SYSTEM = """浅色出版印刷主题：
- 背景 #F8FAFC，主体卡片白底 #FFFFFF 圆角，极淡网格 #E2E8F0。
- 语义配色（浅填充+饱和描边+深色文字 #0F172A）：蓝 #2563EB=核心平台/主链路；青绿 #0F766E=边缘/接入；紫 #7C3AED=数据/存储；橙 #F97316=AI/智能；红 #DC2626=安全/风险；琥珀 #D97706=云/外部；灰 #94A3B8=外部依赖。
- 中文字体栈：'PingFang SC','Microsoft YaHei','Noto Sans SC',Arial,sans-serif；标题 22-28px，组件名 13-15px，副标签 10-12px。
- 圆角矩形 rx=10，1.5px 描边；连线先画落在盒子后，箭头用 marker；图例放主体之外，图注置底。
- 每张图只表达一个主结论，主链路高亮，边界/层级/时序/决策关系一眼可读。"""

_SKILL_DESIGN_SYSTEM_START = "## Design System"
_SKILL_DESIGN_SYSTEM_END = "## Output"


def _load_design_system(skill_dir: Path | None) -> str:
    """从项目内 architecture-diagram 技能提取「设计系统」章节；缺失则用内置兜底。"""
    if skill_dir is None:
        return _FALLBACK_DESIGN_SYSTEM
    skill_file = Path(skill_dir) / "SKILL.md"
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK_DESIGN_SYSTEM
    start = text.find(_SKILL_DESIGN_SYSTEM_START)
    if start < 0:
        return _FALLBACK_DESIGN_SYSTEM
    end = text.find(_SKILL_DESIGN_SYSTEM_END, start)
    section = text[start:] if end < 0 else text[start:end]
    section = section.strip()
    return section or _FALLBACK_DESIGN_SYSTEM


def _build_system_prompt(design_system: str) -> str:
    return f"""你是出版级技术图表设计师。根据给定的中文图表 brief，直接输出一份完整的 self-contained HTML 文件，主体是浅色主题的 inline SVG 架构图，供书籍印刷使用。

以下是必须遵循的设计系统规范（来自项目 architecture-diagram 技能）：

{design_system}

硬性输出要求：
1. 只输出 HTML 源码本身，从 `<!doctype html>` 开始、到 `</html>` 结束；不要 Markdown 代码围栏，不要任何解释或前后缀文字。
2. 全部内联：内联 CSS + 内联 SVG，禁止联网加载字体、禁止引用外部图片、禁止任何 `<script>` 标签。
3. 浅色背景（#F8FAFC 页面、白底卡片），使用规定的中文字体栈与语义配色。
4. 忠实表达 brief 的 components（节点）、connections（连线）、regions（边界）；elements、relationships 只作语义补充；禁止虚构事实、数据、标准或来源。
5. 节点用短标签（不超过 14 个汉字），解释性文字放入信息卡或图注，禁止 `节点1/节点2/最右侧/container/service/user` 这类占位标签。
6. 图必须完整可读：所有节点有标签、连线有明确指向、主链路高亮、图例置于主体之外、底部给出出版级中文图注。
7. connections 必须连接真实节点，绝不能把「数据流/控制流」这类关系名当成节点画成方块。
8. 入书画布固定为横向 `width="1200" height="760" viewBox="0 0 1200 760"`，禁止输出竖版、方图、超长网页或正文说明卡片。"""


class FigureDesignerAgent(BaseAgent):
    """为 `book-figure` 直接生成出版级浅色 HTML 图表。"""

    def __init__(
            self,
            llm: LLMClient,
            *,
            polish_rounds: int = 0,
            timeout_seconds: float = 60.0,
            max_tokens: int = 8192,
            retry_attempts: int = 1,
            json_retry_attempts: int = 1,
            circuit_breaker_failures: int = 3,
            skill_dir: Path | None = None,
    ) -> None:
        super().__init__(llm)
        if polish_rounds < 0:
            raise ValueError("polish_rounds 不能小于 0")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须大于 0")
        if max_tokens <= 0:
            raise ValueError("max_tokens 必须大于 0")
        if retry_attempts <= 0:
            raise ValueError("retry_attempts 必须大于 0")
        if json_retry_attempts <= 0:
            raise ValueError("json_retry_attempts 必须大于 0")
        if circuit_breaker_failures <= 0:
            raise ValueError("circuit_breaker_failures 必须大于 0")
        self.polish_rounds = polish_rounds
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.retry_attempts = retry_attempts
        self.json_retry_attempts = json_retry_attempts
        self.circuit_breaker_failures = circuit_breaker_failures
        self.skill_dir = Path(skill_dir) if skill_dir is not None else None
        self._design_system = _load_design_system(self.skill_dir)
        self._system_prompt = _build_system_prompt(self._design_system)
        self._consecutive_failures = 0
        self._circuit_open_logged = False

    def design(self, spec: FigureSpec, *, palette: dict[str, str], feedback: str = "") -> FigureDesign:
        """让 LLM 直接生成完整浅色 HTML；失败时回退到本地语义蓝图渲染。"""
        if self._consecutive_failures >= self.circuit_breaker_failures:
            if not self._circuit_open_logged:
                self.logger.warning("AI 图表 HTML 连续失败 %d 次，本进程后续图表直接使用本地语义蓝图。", self._consecutive_failures)
                self._circuit_open_logged = True
            return self._fallback_design(spec, palette)
        try:
            html = self._request_html(spec, feedback=feedback)
            svg = _extract_svg(html)
            self._consecutive_failures = 0
            return FigureDesign(svg=svg, html=html, notes="AI 直出浅色 HTML")
        except Exception as exc:
            self._consecutive_failures += 1
            self.logger.warning("AI 图表 HTML 生成失败，使用本地语义蓝图兜底: %s", exc)
            return self._fallback_design(spec, palette)

    def _request_html(self, spec: FigureSpec, *, feedback: str) -> str:
        with _hard_timeout(self.timeout_seconds + 2.0):
            content = self.llm.chat(
                self._system_prompt,
                _build_html_prompt(spec, feedback=feedback),
                temperature=0.25,
                max_tokens=self.max_tokens,
                timeout=self.timeout_seconds,
                retry_attempts=self.retry_attempts,
            )
        html = _normalize_html(content)
        _validate_html_document(html)
        return html

    def _fallback_design(self, spec: FigureSpec, palette: dict[str, str]) -> FigureDesign:
        """LLM 不可用时，用本地语义蓝图渲染 SVG，HTML 交给管线的模板外壳包裹。"""
        blueprint = _fallback_blueprint(spec)
        svg = render_figure_blueprint_svg(spec, palette=palette, blueprint=blueprint)
        return FigureDesign(svg=svg, html="", notes="本地语义蓝图兜底")


def _build_html_prompt(spec: FigureSpec, *, feedback: str) -> str:
    return f"""请把下面的图表规格绘制成一份完整的浅色 HTML 架构图。

## 图表规格
{json.dumps(_spec_payload(spec), ensure_ascii=False, indent=2)}

## 上一轮校验反馈
{feedback or "无"}

画布与比例要求：内联 SVG 必须固定为 `width="1200" height="760" viewBox="0 0 1200 760"`；图形主体控制在 24px 安全边距内；不要在 SVG 下方追加说明卡片或长文本区。

现在直接输出完整 HTML（从 <!doctype html> 到 </html>），不要解释。"""


def _normalize_html(content: str) -> str:
    """去掉可能的 Markdown 代码围栏，截取 HTML 文档主体。"""
    cleaned = content.strip()
    fence_match = re.fullmatch(r"```(?:html)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.I)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    lower = cleaned.lower()
    start = lower.find("<!doctype")
    if start < 0:
        start = lower.find("<html")
    end = lower.rfind("</html>")
    if start < 0 or end < 0:
        raise RuntimeError("HTML 缺少 <html>...</html> 结构")
    return cleaned[start:end + len("</html>")].strip()


def _validate_html_document(html_text: str) -> None:
    if len(html_text) < 800:
        raise RuntimeError("HTML 内容过短，疑似占位图")
    lower = html_text.lower()
    if "<svg" not in lower:
        raise RuntimeError("HTML 缺少内联 SVG")
    if "</svg>" not in lower:
        raise RuntimeError("SVG 未闭合，疑似响应被截断")
    if "<script" in lower:
        raise RuntimeError("HTML 不允许包含 <script>")


def _extract_svg(html_text: str) -> str:
    match = re.search(r"<svg\b.*?</svg>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if match is None:
        raise RuntimeError("HTML 中未找到内联 SVG")
    return match.group(0).strip()


@contextlib.contextmanager
def _hard_timeout(seconds: float) -> Iterator[None]:
    if threading.current_thread() is not threading.main_thread() or not hasattr(signal, "setitimer"):
        yield
        return
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def raise_timeout(_signum: int, _frame: FrameType | None) -> None:
        raise TimeoutError(f"AI 图表 HTML 生成超过硬超时 {seconds:.1f}s")

    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


def _fallback_blueprint(spec: FigureSpec) -> dict[str, Any]:
    nodes = []
    source_components = spec.components or []
    if not source_components:
        source_components = [
            {"id": f"n{index}", "label": _compact_label(item), "subtitle": _compact_role(item), "group": "", "priority": "normal"}
            for index, item in enumerate((spec.elements or [spec.title])[:10], start=1)
        ]
    for index, item in enumerate(source_components[:10], start=1):
        source_label = _compact_label(spec.elements[index - 1]) if index <= len(spec.elements) else ""
        label = str(item.get("label") or source_label or item.get("id") or spec.title)
        role = str(item.get("subtitle") or item.get("role") or "")
        nodes.append(
            {
                "id": str(item.get("id") or f"n{index}"),
                "label": _compact_label(label),
                "group": str(item.get("group") or ""),
                "role": _compact_role(role),
                "emphasis": str(item.get("priority") or item.get("emphasis") or "normal"),
                "shape": str(item.get("shape") or ""),
            }
        )
    edges = []
    for item in spec.connections[:8]:
        edges.append(
            {
                "from": str(item.get("from") or ""),
                "to": str(item.get("to") or ""),
                "label": _compact_label(str(item.get("label") or "主链路")),
                "style": str(item.get("style") or "solid"),
                "direction": str(item.get("direction") or ""),
            }
        )
    if not edges:
        for index in range(max(0, min(len(nodes) - 1, 8))):
            label = spec.relationships[index % len(spec.relationships)] if spec.relationships else "主链路"
            edges.append({"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "label": _compact_label(label), "style": "solid"})
    return {
        "layout": spec.figure_type,
        "title": spec.title,
        "subtitle": spec.audience_takeaway or spec.purpose,
        "groups": spec.regions[:4],
        "nodes": nodes,
        "edges": edges,
        "callouts": [_compact_label(item) for item in (spec.callouts or [item for item in [spec.visual_focus, spec.audience_takeaway] if item] or spec.relationships)[:3] if item],
        "legend": spec.legend[:4],
        "design_notes": "本地语义蓝图兜底，本地出版级渲染",
    }


def _compact_label(value: str) -> str:
    text = str(value).replace("“", "‘").replace("”", "’").strip()
    if "：" in text or ":" in text:
        separator = "：" if "：" in text else ":"
        prefix, suffix = text.split(separator, 1)
        prefix = prefix.strip()
        suffix = suffix.strip()
        quoted = _first_quoted(suffix)
        if _is_generic_label(prefix) or "决策" in prefix or "判断" in prefix:
            text = quoted or _first_clause(suffix)
        else:
            text = prefix if len(prefix) <= 18 else _first_clause(suffix)
    text = _clean_generic_references(text)
    return text[:36].rstrip() + ("…" if len(text) > 36 else "")


def _compact_role(value: str) -> str:
    text = str(value).replace("“", "‘").replace("”", "’").strip()
    if "：" in text or ":" in text:
        separator = "：" if "：" in text else ":"
        text = text.split(separator, 1)[1].strip()
    for separator in ["——", "--", "—", "；", ";", "。"]:
        if separator in text:
            text = text.split(separator, 1)[1].strip()
            break
    text = text.strip(" ，。；;：:、")
    text = _clean_generic_references(text)
    return text[:34].rstrip() + ("…" if len(text) > 34 else "")


def _clean_generic_references(value: str) -> str:
    text = re.sub(r"(?:进入|转入|指向|到)?(?:节点|决策节点|判断节点|处理节点)\d+", "进入下一判断", value)
    text = re.sub(r"最右侧(?:路径)?", "推荐路径", text)
    return text.strip(" ，。；;：:、")


def _first_quoted(value: str) -> str:
    for left, right in [("‘", "’"), ("'", "'"), ('"', '"')]:
        if left in value and right in value.split(left, 1)[1]:
            return value.split(left, 1)[1].split(right, 1)[0].strip()
    return ""


def _first_clause(value: str) -> str:
    text = value.strip(" ，。；;：:—-、")
    for separator in ["——", "--", "—", "；", ";", "。", "，"]:
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    return text.strip(" ，。；;：:—-、")


def _is_generic_label(value: str) -> bool:
    text = value.strip()
    return text in {"最右侧", "左侧", "右侧"} or text.startswith(("节点", "决策节点", "判断节点", "处理节点", "计算节点", "执行节点"))


def _spec_payload(spec: FigureSpec) -> dict[str, object]:
    return {
        "chapter_id": spec.chapter_id,
        "section_id": spec.section_id,
        "occurrence": spec.occurrence,
        "id": spec.figure_id,
        "type": spec.figure_type,
        "title": spec.title,
        "purpose": spec.purpose,
        "layout": spec.layout,
        "elements": spec.elements,
        "relationships": spec.relationships,
        "legend": spec.legend,
        "caption": spec.caption,
        "render_notes": spec.render_notes,
        "audience_takeaway": spec.audience_takeaway,
        "visual_focus": spec.visual_focus,
        "design_level": spec.design_level,
        "components": spec.components,
        "connections": spec.connections,
        "regions": spec.regions,
        "callouts": spec.callouts,
        "visual_constraints": spec.visual_constraints,
    }
