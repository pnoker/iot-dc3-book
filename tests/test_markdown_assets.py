from __future__ import annotations

from core.markdown_assets import find_invalid_book_figures


def test_book_figure_required_fields_accept_json_keys() -> None:
    markdown = '''```book-figure
{
  "id": "fig-01-01",
  "type": "layered",
  "title": "图1-1 平台分层架构",
  "purpose": "说明平台层次与职责边界。",
  "layout": "自下而上分层。",
  "elements": ["设备层", "平台层"],
  "relationships": ["设备层连接平台层"],
  "legend": ["蓝色=核心平台服务"],
  "caption": "图1-1 展示平台分层架构。",
  "render_notes": "HTML/SVG 统一绘制。"
}
```'''

    assert find_invalid_book_figures(markdown) == []
