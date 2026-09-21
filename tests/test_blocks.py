"""Tests for block-level element conversion."""
from __future__ import annotations

import pytest
from conftest import md_lines
from html_to_md import Converter, ConversionConfig


def c(html: str, **kwargs) -> str:
    cfg = ConversionConfig(auto_detect_content=False, strip_selectors=[], **kwargs)
    return Converter(config=cfg).convert(f'<body>{html}</body>')


class TestHeadings:
    @pytest.mark.parametrize('level', range(1, 7))
    def test_atx_headings(self, level):
        result = c(f'<h{level}>Heading {level}</h{level}>')
        prefix = '#' * level
        assert f'{prefix} Heading {level}' in result

    def test_setext_h1(self):
        result = c('<h1>Title</h1>', heading_style='setext')
        lines = md_lines(result)
        assert 'Title' in lines
        assert any(set(l) == {'='} for l in lines)

    def test_setext_h2(self):
        result = c('<h2>Subtitle</h2>', heading_style='setext')
        lines = md_lines(result)
        assert 'Subtitle' in lines
        assert any(set(l) == {'-'} for l in lines)

    def test_setext_h3_falls_back_to_atx(self):
        result = c('<h3>Deep</h3>', heading_style='setext')
        assert '### Deep' in result


class TestParagraph:
    def test_basic(self):
        result = c('<p>Hello world</p>')
        assert 'Hello world' in result

    def test_blank_lines_between(self):
        result = c('<p>One</p><p>Two</p>')
        assert result.count('\n\n') >= 1
        assert 'One' in result
        assert 'Two' in result

    def test_empty_paragraph_ignored(self):
        result = c('<p></p>')
        assert result.strip() == ''


class TestBlockquote:
    def test_basic(self):
        result = c('<blockquote><p>Quote</p></blockquote>')
        assert '> Quote' in result

    def test_multiline(self):
        result = c('<blockquote><p>Line 1</p><p>Line 2</p></blockquote>')
        assert '> Line 1' in result
        assert '> Line 2' in result


class TestLists:
    def test_unordered(self):
        result = c('<ul><li>A</li><li>B</li><li>C</li></ul>')
        assert '- A' in result
        assert '- B' in result
        assert '- C' in result

    def test_ordered(self):
        result = c('<ol><li>First</li><li>Second</li></ol>')
        assert '1. First' in result
        assert '2. Second' in result

    def test_nested_ul(self):
        result = c('<ul><li>Top<ul><li>Nested</li></ul></li></ul>')
        assert '- Top' in result
        assert '- Nested' in result
        # Nested item should be indented
        lines = result.splitlines()
        nested_lines = [l for l in lines if 'Nested' in l]
        assert nested_lines
        assert nested_lines[0].startswith('    ')

    def test_definition_list(self):
        result = c('<dl><dt>Term</dt><dd>Definition</dd></dl>')
        assert '**Term**' in result
        assert 'Definition' in result


class TestHorizontalRule:
    def test_hr(self):
        result = c('<hr>')
        assert '---' in result


class TestCodeBlock:
    def test_pre_without_code(self):
        result = c('<pre>raw\nverbatim\n</pre>')
        assert '```' in result or '~~~' in result
        assert 'raw' in result

    def test_pre_code_python(self):
        result = c('<pre><code class="language-python">x = 1</code></pre>')
        assert '```python' in result
        assert 'x = 1' in result

    def test_pre_code_no_language(self):
        result = c('<pre><code>plain</code></pre>')
        assert '```\n' in result or '```' in result
        assert 'plain' in result
