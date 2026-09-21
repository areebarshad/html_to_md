"""Tests for inline element conversion."""
from __future__ import annotations

import pytest
from conftest import md_lines
from html_to_md import convert, ConversionConfig, Converter


def c(html: str, **kwargs) -> str:
    """Convert a fragment with no stripping."""
    cfg = ConversionConfig(auto_detect_content=False, strip_selectors=[], **kwargs)
    return Converter(config=cfg).convert(f'<body>{html}</body>')


class TestStrong:
    def test_b_tag(self):
        assert '**bold**' in c('<p><b>bold</b></p>')

    def test_strong_tag(self):
        assert '**strong**' in c('<p><strong>strong</strong></p>')

    def test_empty_strong(self):
        result = c('<p><strong></strong></p>')
        assert '****' not in result


class TestEmphasis:
    def test_em_tag(self):
        assert '*italic*' in c('<p><em>italic</em></p>')

    def test_i_tag(self):
        assert '*italic*' in c('<p><i>italic</i></p>')


class TestStrikethrough:
    def test_del_tag(self):
        assert '~~deleted~~' in c('<p><del>deleted</del></p>')

    def test_s_tag(self):
        assert '~~struck~~' in c('<p><s>struck</s></p>')


class TestCodeSpan:
    def test_basic(self):
        assert '`code`' in c('<p><code>code</code></p>')

    def test_backtick_in_content(self):
        result = c('<p><code>`tick`</code></p>')
        assert '``' in result

    def test_no_markdown_escape_inside_code(self):
        result = c('<p><code>*not bold*</code></p>')
        assert '\\*' not in result


class TestLinks:
    def test_inline_link(self):
        result = c('<a href="https://example.com">Example</a>')
        assert '[Example](https://example.com)' in result

    def test_link_with_title(self):
        result = c('<a href="https://x.com" title="X">X site</a>')
        assert '[X site](https://x.com "X")' in result

    def test_empty_href(self):
        result = c('<a href="">No href</a>')
        assert 'No href' in result
        assert '[]()' not in result

    def test_reference_style(self):
        result = c('<a href="https://example.com">click</a>', link_style='reference')
        assert '[click][1]' in result
        assert '[1]: https://example.com' in result

    def test_relative_url_with_base(self):
        result = c(
            '<a href="/page">Page</a>',
            link_base_url='https://example.com',
        )
        assert 'https://example.com/page' in result


class TestImages:
    def test_basic_image(self):
        result = c('<img src="pic.png" alt="A pic">')
        assert '![A pic](pic.png)' in result

    def test_image_with_title(self):
        result = c('<img src="pic.png" alt="alt" title="Title">')
        assert '![alt](pic.png "Title")' in result

    def test_data_url_stripped(self):
        result = c('<img src="data:image/png;base64,abc" alt="data">')
        assert 'data:' not in result
        assert 'data' in result

    def test_data_url_kept_when_configured(self):
        result = c('<img src="data:image/png;base64,abc" alt="d">', keep_data_urls=True)
        assert 'data:image/png;base64,abc' in result

    def test_relative_src_with_base(self):
        result = c('<img src="/img/x.png" alt="x">', image_base_url='https://cdn.example.com')
        assert 'https://cdn.example.com/img/x.png' in result


class TestLineBreak:
    def test_br(self):
        result = c('<p>line1<br>line2</p>')
        assert '  \n' in result


class TestEscaping:
    def test_asterisk_escaped(self):
        result = c('<p>* not a list</p>')
        assert r'\*' in result

    def test_hash_escaped(self):
        result = c('<p># not a heading</p>')
        assert r'\#' in result

    def test_pipe_not_escaped_in_paragraph(self):
        # | is only special inside GFM tables; no escaping needed in body text
        result = c('<p>a | b</p>')
        assert 'a | b' in result
