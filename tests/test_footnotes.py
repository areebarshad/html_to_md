"""Tests for footnote conversion."""
from __future__ import annotations

import pytest
from html_to_md import Converter, ConversionConfig


def c(html: str) -> str:
    cfg = ConversionConfig(auto_detect_content=False, strip_selectors=[])
    return Converter(config=cfg).convert(f'<body>{html}</body>')


class TestFootnoteAnchors:
    def test_sup_anchor_becomes_reference(self):
        result = c('<p>Text<sup><a href="#fn-1">1</a></sup></p>')
        assert '[^1]' in result

    def test_duplicate_anchor_reuses_number(self):
        result = c(
            '<p>A<sup><a href="#fn-1">1</a></sup> and again<sup><a href="#fn-1">1</a></sup></p>'
        )
        assert result.count('[^1]') == 2

    def test_multiple_footnotes_numbered_in_order(self):
        result = c(
            '<p>'
            '<sup><a href="#fn-1">1</a></sup>'
            '<sup><a href="#fn-2">2</a></sup>'
            '</p>'
        )
        assert '[^1]' in result
        assert '[^2]' in result


class TestFootnoteDefinitions:
    def test_definitions_appended(self):
        html = '''
        <p>Text<sup><a href="#fn-1">1</a></sup></p>
        <section class="footnotes">
          <ol>
            <li id="fn-1">Footnote body. <a href="#fnref-1">↩</a></li>
          </ol>
        </section>
        '''
        result = c(html)
        assert '[^1]: Footnote body.' in result

    def test_back_links_stripped_from_definitions(self):
        html = '''
        <p>Text<sup><a href="#fn-1">1</a></sup></p>
        <section class="footnotes">
          <ol><li id="fn-1">Body. <a href="#fnref-1" class="footnote-backref">↩</a></li></ol>
        </section>
        '''
        result = c(html)
        assert '↩' not in result


class TestFixtureFootnotes:
    def test_fixture(self):
        from pathlib import Path
        fixture = Path(__file__).parent / 'fixtures' / 'footnotes.html'
        html = fixture.read_text(encoding='utf-8')
        result = Converter().convert(html)
        assert '[^1]' in result
        assert '[^2]' in result
        assert '[^1]: This is the first footnote.' in result
        assert '[^2]: This is the second footnote.' in result
        # First footnote referenced twice in body (also appears once in the definition line)
        assert result.count('[^1]') == 3  # 2 inline + 1 in "[^1]: ..." definition
