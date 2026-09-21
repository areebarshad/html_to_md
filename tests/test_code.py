"""Tests for code block and inline code conversion."""
from __future__ import annotations

import pytest
from html_to_md import Converter, ConversionConfig


def c(html: str, **kwargs) -> str:
    cfg = ConversionConfig(auto_detect_content=False, strip_selectors=[], **kwargs)
    return Converter(config=cfg).convert(f'<body>{html}</body>')


class TestLanguageDetection:
    @pytest.mark.parametrize('cls,expected_lang', [
        ('language-python', 'python'),
        ('lang-javascript', 'javascript'),
        ('highlight-ruby', 'ruby'),
    ])
    def test_prefix_stripping(self, cls, expected_lang):
        result = c(f'<pre><code class="{cls}">x</code></pre>')
        assert f'```{expected_lang}' in result

    def test_data_lang_attribute(self):
        result = c('<pre><code data-lang="go">x</code></pre>')
        assert '```go' in result

    def test_no_language(self):
        result = c('<pre><code>no lang</code></pre>')
        assert '```\n' in result

    def test_multiple_classes_picks_first_match(self):
        result = c('<pre><code class="foo language-py bar">x</code></pre>')
        assert '```py' in result


class TestFencedBlocks:
    def test_backtick_fence_default(self):
        result = c('<pre><code>x</code></pre>')
        assert '```' in result

    def test_tilde_fence(self):
        result = c('<pre><code>x</code></pre>', fenced_code_char='~')
        assert '~~~' in result

    def test_content_with_triple_backtick_uses_longer_fence(self):
        result = c('<pre><code>```nested```</code></pre>')
        # fence must be longer than any run inside
        assert '````' in result

    def test_code_is_verbatim_no_escaping(self):
        result = c('<pre><code class="language-md"># heading\n**bold**</code></pre>')
        assert '# heading' in result
        assert '**bold**' in result
        assert r'\#' not in result


class TestInlineCode:
    def test_backtick_wrapper(self):
        result = c('<p><code>x = 1</code></p>')
        assert '`x = 1`' in result

    def test_special_chars_not_escaped(self):
        result = c('<p><code>a * b</code></p>')
        assert '`a * b`' in result
        assert r'\*' not in result


class TestFixtureCodeBlocks:
    def test_fixture(self):
        from pathlib import Path
        fixture = Path(__file__).parent / 'fixtures' / 'code_blocks.html'
        html = fixture.read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '```python' in result
        assert '```bash' in result
        assert 'def greet' in result
