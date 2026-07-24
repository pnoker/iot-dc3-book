"""出版级技术图表设计 Agent。"""

from __future__ import annotations

import contextlib
import json
import re
import signal
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree

from agents.base import BaseAgent
from core.figures import FigureDesign, FigureSpec, render_figure_blueprint_svg, render_figure_skill_svg
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
    return f"""你是出版级技术图表设计师。根据中文图表 brief 设计定制 SVG 主体，供书籍印刷使用。

以下是必须遵循的设计系统规范（来自项目 architecture-diagram 技能）：

{design_system}

硬性输出要求：
1. 只输出 JSON object，唯一字段为 `body_svg`；字段值必须是完整的 `<g data-layout="..."></g>`。
2. `body_svg` 不得包含 `<svg>`、`<defs>`、`<style>`、`<script>`、外部图片、联网字体或任何解释文字。
3. 图表将嵌入统一的 1800×900 白底出版画布；标题区 `y < 110`、页脚 `y > 775` 已被占用。
4. 只在 `x=80..1720`、`y=125..750` 内绘图，主体尽量覆盖 `x=120..1680`、`y=145..720`。
5. 只使用 `rect/circle/ellipse/line/path/polygon/polyline/text/tspan/g`，字体由外层继承。
6. 忠实综合 brief 的 layout、elements、relationships、components、connections、regions 与 render_notes；自动升级字段可能有关系残片，关系文字绝不能当节点。
7. 节点使用短标签，说明放进节点副文或简短 callout；禁止占位标签、省略号、重阴影、大色块和长段落。
8. 图例和图注由外层统一绘制，`body_svg` 不要重复绘制独立图例或图注。"""


class FigureDesignerAgent(BaseAgent):
    """为 `book-figure` 生成定制主体并套用统一出版画布。"""

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
        """让 LLM 生成定制 SVG 主体；失败时回退到本地语义蓝图。"""
        if self._consecutive_failures >= self.circuit_breaker_failures:
            if not self._circuit_open_logged:
                self.logger.warning("AI 图表主体连续失败 %d 次，本进程后续图表直接使用本地语义蓝图。", self._consecutive_failures)
                self._circuit_open_logged = True
            return self._fallback_design(spec, palette)
        retry_feedback = feedback
        last_error: Exception | None = None
        for attempt in range(self.polish_rounds + 1):
            try:
                body_svg = self._request_svg_body(spec, feedback=retry_feedback)
                svg = render_figure_skill_svg(spec, palette=palette, body_svg=body_svg)
                self._consecutive_failures = 0
                return FigureDesign(svg=svg, html="", notes="AI 定制主体 + architecture-diagram 统一画布")
            except Exception as exc:
                last_error = exc
                if attempt < self.polish_rounds:
                    retry_feedback = (
                        f"{feedback}\n\n上一轮生成未通过本地校验：{exc}。"
                        "请保留图表语义并重新输出更简洁、完整、合法的 SVG 主体。"
                    ).strip()
        self._consecutive_failures += 1
        self.logger.warning("AI 图表主体生成失败，使用本地语义蓝图兜底: %s", last_error)
        return self._fallback_design(spec, palette)

    def _request_svg_body(self, spec: FigureSpec, *, feedback: str) -> str:
        with _hard_timeout(self.timeout_seconds + 2.0):
            payload = self.llm.chat_json(
                self._system_prompt,
                _build_svg_body_prompt(spec, feedback=feedback),
                temperature=0.18,
                max_tokens=self.max_tokens,
                timeout=self.timeout_seconds,
                retry_attempts=self.retry_attempts,
                json_retry_attempts=self.json_retry_attempts,
            )
        return _normalize_svg_body(payload.get("body_svg"))

    def _fallback_design(self, spec: FigureSpec, palette: dict[str, str]) -> FigureDesign:
        """LLM 不可用时，用本地语义蓝图渲染 SVG，HTML 交给管线的模板外壳包裹。"""
        blueprint = _fallback_blueprint(spec)
        svg = render_figure_blueprint_svg(spec, palette=palette, blueprint=blueprint)
        return FigureDesign(svg=svg, html="", notes="本地语义蓝图兜底")


def _build_svg_body_prompt(spec: FigureSpec, *, feedback: str) -> str:
    return f"""请为下面的图表规格绘制定制 SVG 主体。

## 图表规格
{json.dumps(_spec_payload(spec), ensure_ascii=False, indent=2)}

## 上一轮校验反馈
{feedback or "无"}

绘图要求：
- 先按 layout/render_notes 选择正确视觉语法：时序图用真实参与者泳道，市场格局用坐标轴/象限与气泡，分层图用职责层，流程图用分支，协议报文用字段带，数据对比用表格或图表；不要机械画空卡片链。
- 主结论一眼可读，布局紧凑但不拥挤；节点包含短标题和必要说明，必要时加入边界、阶段条带或关键说明。
- 白色卡片、`rx=8~12`、`stroke-width=1.5~2`；所有矩形（包括表头、条带、柱形）只能使用白色或浅填充 `#EFF6FF/#ECFDF5/#F5F3FF/#FFF7ED/#FEF2F2/#FFFBEB/#F8FAFC`，禁止深色表头与饱和色块。
- 语义描边：蓝 `#2563EB`=核心平台/主链路，青 `#0F766E`=设备/边缘，紫 `#7C3AED`=数据，橙 `#F97316`=AI，红 `#DC2626`=安全/风险，琥珀 `#D97706`=云/外部，灰 `#64748B/#94A3B8/#E2E8F0`=次要边界。
- 正文 `#0F172A`，次文 `#64748B`；组件标题 15–18px，说明 10–13px，禁止小于 10px。
- 连线先于卡片绘制；主链路使用 `marker-end="url(#bp-arrow-primary)"`，次要/回路使用 `marker-end="url(#bp-arrow)"`；不得自定义 marker 或重复画箭头三角形。
- 架构图、分层图和数据流图只用水平/垂直正交折线；箭头起终点落在卡片边缘，不得深入卡片内部，也不得穿过第三方卡片。
- 双向流拆成两条间距清晰的平行路径；多对一连接使用目标卡片上的不同锚点，禁止多条线汇聚到同一点。
- 非父子区域边界互不覆盖，卡片完整位于所属区域内；连线标签放在线旁的不透明白底小标签内，不压卡片或区域边界。
- 时序消息严格按 brief 顺序自上而下，返回消息使用虚线，自调用画回环。
- 坐标/象限图标清轴名与方向，不伪造数值；比较图保持列对齐；所有信息必须来自 brief。
- 不要绘制独立图例和图注，外层会统一补齐。
- `body_svg` 保持精简，不写 XML 注释，不重复元素，总长度控制在 12000 字符以内；不要输出 `<defs>`。

现在只输出 `{{"body_svg":"<g data-layout=...>...</g>"}}`。"""


def _normalize_html(content: str) -> str:
    """去掉可能的 Markdown 代码围栏，截取 HTML 或 SVG 文档主体。"""
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
        svg_match = re.search(r"<svg\b.*?</svg>", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if svg_match is None:
            raise RuntimeError("HTML/SVG 缺少完整文档结构")
        svg = svg_match.group(0).strip()
        return f"<!doctype html><html><body>{svg}</body></html>"
    return cleaned[start:end + len("</html>")].strip()


def _normalize_svg_body(value: object) -> str:
    body = str(value or "").strip()
    fence_match = re.fullmatch(r"```(?:svg|xml)?\s*(.*?)\s*```", body, re.DOTALL | re.I)
    if fence_match:
        body = fence_match.group(1).strip()
    match = re.search(r"<g\b.*</g>", body, flags=re.DOTALL | re.IGNORECASE)
    if match is None:
        raise RuntimeError("AI 图表响应缺少完整 <g> 主体")
    body = match.group(0).strip()
    body = re.sub(
        r'''\smarker-(?:start|mid|end)=["']url\(#(?!bp-arrow(?:-primary)?\b)[^)]+\)["']''',
        "",
        body,
        flags=re.I,
    )
    if len(body) < 600:
        raise RuntimeError("AI 图表主体过短，疑似占位图")
    if not re.search(r"<g\b[^>]*\bdata-layout=", body, flags=re.I):
        raise RuntimeError("AI 图表主体缺少 data-layout")
    if re.search(r">\s*(?:节点\d+|container|service|user)\s*<|\.\.\.|…", body, flags=re.I):
        raise RuntimeError("AI 图表主体包含占位词或省略号")

    try:
        root = ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
    except ElementTree.ParseError as exc:
        raise RuntimeError(f"AI 图表主体 XML 无效: {exc}") from exc
    allowed_tags = {"svg", "g", "rect", "circle", "ellipse", "line", "path", "polygon", "polyline", "text", "tspan"}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag not in allowed_tags:
            raise RuntimeError(f"AI 图表主体包含不允许的 SVG 标签: {tag}")
        for key, raw in element.attrib.items():
            attr = key.rsplit("}", 1)[-1].lower()
            text = str(raw)
            if attr in {"href", "style"} or re.search(r"(?:javascript:|data:|https?://|@import)", text, flags=re.I):
                raise RuntimeError(f"AI 图表主体包含不安全属性: {attr}")
            if tag == "rect" and attr == "fill":
                allowed_rect_fills = {
                    "#FFFFFF", "#FFF", "WHITE", "NONE", "TRANSPARENT",
                    "#EFF6FF", "#ECFDF5", "#F5F3FF", "#FFF7ED",
                    "#FEF2F2", "#FFFBEB", "#F8FAFC",
                    "#DBEAFE", "#D1FAE5", "#EDE9FE", "#FFEDD5",
                    "#FEE2E2", "#FEF3C7", "#F1F5F9", "#E2E8F0",
                    "#F0F4F8", "#ECEFF1",
                }
                if text.upper() not in allowed_rect_fills:
                    raise RuntimeError(f"AI 图表矩形使用非浅色填充: {text}")
            if attr == "font-size":
                number = re.search(r"\d+(?:\.\d+)?", text)
                if number and float(number.group(0)) < 10:
                    raise RuntimeError("AI 图表主体字号小于 10px")
    return body


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
    if spec.figure_type == "sequence":
        sequence_blueprint = _sequence_fallback_blueprint(spec)
        if sequence_blueprint is not None:
            return sequence_blueprint

    nodes = []
    source_components = spec.components or []
    if spec.elements:
        source_components = [
            {"id": f"n{index}", "label": item, "group": "", "priority": "normal"}
            for index, item in enumerate(spec.elements[:10], start=1)
        ]
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


def _sequence_fallback_blueprint(spec: FigureSpec) -> dict[str, Any] | None:
    actors: list[str] = []
    actor_roles: dict[str, str] = {}
    messages: list[tuple[int, str, str, str]] = []
    for step, element in enumerate(spec.elements[:12], start=1):
        subject, detail = _split_sequence_element(element)
        if "→" not in subject:
            actor = _sequence_actor_name(subject)
            if actor:
                _append_unique(actors, actor)
                if detail and actor not in actor_roles:
                    actor_roles[actor] = _compact_role(detail)
            continue
        source_text, target_text = subject.split("→", 1)
        source = _sequence_actor_name(source_text)
        target = _sequence_actor_name(target_text)
        if not source or not target:
            continue
        _append_unique(actors, source)
        _append_unique(actors, target)
        messages.append((step, source, target, _compact_label(detail or "消息传递").rstrip("。；;")))
    if len(actors) < 2 or not messages:
        return None

    actor_ids = {actor: f"actor-{index}" for index, actor in enumerate(actors[:6], start=1)}
    chain_steps = _sequence_chain_steps(spec.relationships)
    nodes = [
        {
            "id": actor_ids[actor],
            "label": actor,
            "group": "",
            "role": actor_roles.get(actor, ""),
            "emphasis": "primary" if index == 1 else "normal",
            "shape": "card",
        }
        for index, actor in enumerate(actors[:6], start=1)
    ]
    edges = [
        {
            "from": actor_ids[source],
            "to": actor_ids[target],
            "label": label,
            "style": "dashed" if step in chain_steps else "solid",
            "direction": "left-to-right",
        }
        for step, source, target, label in messages[:10]
        if source in actor_ids and target in actor_ids
    ]
    return {
        "layout": "sequence",
        "title": spec.title,
        "subtitle": spec.audience_takeaway or spec.purpose,
        "groups": [],
        "nodes": nodes,
        "edges": edges,
        "callouts": [_compact_label(item) for item in spec.callouts[:2] if item],
        "legend": spec.legend[:3],
        "design_notes": "本地语义蓝图兜底，按参与者归一化时序消息",
    }


def _split_sequence_element(value: str) -> tuple[str, str]:
    text = str(value).strip()
    for separator in ["：", ":"]:
        if separator in text:
            subject, detail = text.split(separator, 1)
            return subject.strip(), detail.strip()
    return text, ""


def _sequence_actor_name(value: str) -> str:
    text = re.sub(r"[（(].*?[）)]", "", str(value)).strip()
    text = re.sub(r"(?:内部|外部)$", "", text).strip()
    return text[:16]


def _sequence_chain_steps(relationships: list[str]) -> set[int]:
    steps: set[int] = set()
    for relationship in relationships:
        match = re.search(r"步骤([^为。；;]+)为链上", relationship)
        if match is None:
            continue
        steps.update(int(value) for value in re.findall(r"\d+", match.group(1)))
    return steps


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


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
