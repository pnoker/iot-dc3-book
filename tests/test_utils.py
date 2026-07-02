"""core.utils 单元测试"""

import pytest

from core.utils import parse_json_from_llm, truncate


def test_parse_json_codeblock():
    response = '```json\n{"key": "value"}\n```'
    result = parse_json_from_llm(response)
    assert result == {"key": "value"}


def test_parse_json_raw():
    response = '{"key": "value"}'
    result = parse_json_from_llm(response)
    assert result == {"key": "value"}


def test_parse_json_with_text():
    response = 'Here is the result:\n{"key": "value"}\nDone.'
    result = parse_json_from_llm(response)
    assert result == {"key": "value"}


def test_parse_json_invalid():
    with pytest.raises(ValueError, match="无法从 LLM 响应中解析 JSON"):
        parse_json_from_llm("this is not json at all")


def test_truncate_short():
    assert truncate("hello", 10) == "hello"


def test_truncate_long():
    result = truncate("hello world this is long", 10)
    assert len(result) == 10
    assert result.endswith("...")
