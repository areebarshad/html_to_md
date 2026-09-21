"""Integration tests for the Converter class and module-level convert()."""
from __future__ import annotations

from pathlib import Path

import pytest

from html_to_md import Converter, ConversionConfig, convert

FIXTURES = Path(__file__).parent / 'fixtures'


class TestModuleLevelConvert:
    def test_returns_string(self):
        result = convert('<p>Hello</p>')
        assert isinstance(result, str)

    def test_basic_paragraph(self):
        result = convert('<p>Hello world</p>')
        assert 'Hello world' in result

    def test_accepts_bytes(self):
        result = convert(b'<p>bytes</p>')
        assert 'bytes' in result

    def test_trailing_newline(self):
        result = convert('<p>text</p>')
        assert result.endswith('\n')

    def test_no_double_blank_lines(self):
        result = convert('<p>a</p><p>b</p><p>c</p>')
        assert '\n\n\n' not in result


class TestConverterReuse:
    def test_same_converter_multiple_calls(self):
        conv = Converter()
        r1 = conv.convert('<h1>First</h1>')
        r2 = conv.convert('<h1>Second</h1>')
        assert 'First' in r1
        assert 'Second' in r2
        assert 'First' not in r2  # state not leaked between calls


class TestConfigValidation:
    def test_invalid_heading_style_raises(self):
        with pytest.raises(ValueError, match='heading_style'):
            ConversionConfig(heading_style='bad').validate()

    def test_invalid_link_style_raises(self):
        with pytest.raises(ValueError, match='link_style'):
            ConversionConfig(link_style='bad').validate()

    def test_invalid_fence_char_raises(self):
        with pytest.raises(ValueError, match='fenced_code_char'):
            ConversionConfig(fenced_code_char='x').validate()


class TestSimplePageFixture:
    def test_main_content_extracted(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert 'Main Article' in result

    def test_nav_not_in_output(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert 'Site Header' not in result

    def test_footer_not_in_output(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert 'Footer content' not in result

    def test_inline_elements_converted(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '**paragraph**' in result
        assert '*emphasis*' in result
        assert '`inline code`' in result

    def test_image_converted(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '![A photo](photo.jpg "Photo title")' in result

    def test_link_with_title(self):
        html = (FIXTURES / 'simple_page.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '[link](https://example.com "Example")' in result


class TestListsFixture:
    def test_fixture(self):
        html = (FIXTURES / 'lists.html').read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '- Alpha' in result
        assert '1. First' in result
        assert '**HTML**' in result
        assert 'HyperText Markup Language' in result


class TestConvertFile:
    def test_convert_file(self, tmp_path):
        p = tmp_path / 'page.html'
        p.write_text('<main><p>From file</p></main>', encoding='utf-8')
        result = Converter().convert_file(str(p))
        assert 'From file' in result


class TestWrapWidth:
    def test_long_line_wrapped(self):
        long_p = '<p>' + 'word ' * 30 + '</p>'
        result = convert(long_p, config=ConversionConfig(wrap_width=60))
        for line in result.splitlines():
            assert len(line) <= 65  # some slack for edge words


class TestOutputCleanness:
    def test_no_ai_mentions_in_output(self):
        result = convert('<p>Hello</p>')
        forbidden = ['claude', 'anthropic', 'openai', 'llm', 'chatgpt']
        lower = result.lower()
        for word in forbidden:
            assert word not in lower
