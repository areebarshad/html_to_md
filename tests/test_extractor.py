"""Tests for content extraction logic."""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from html_to_md import ConversionConfig
from html_to_md.extractor import extract_content


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'html.parser')


class TestStripElements:
    def test_script_stripped(self):
        soup = make_soup('<body><script>alert(1)</script><p>keep</p></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.find('script') is None

    def test_style_stripped(self):
        soup = make_soup('<body><style>body{}</style><p>keep</p></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.find('style') is None

    def test_nav_stripped(self):
        soup = make_soup('<body><nav>Menu</nav><main><p>Content</p></main></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.find('nav') is None

    def test_footer_stripped(self):
        soup = make_soup('<body><main><p>ok</p></main><footer>Footer</footer></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.find('footer') is None

    def test_custom_selector_stripped(self):
        cfg = ConversionConfig(strip_selectors=['.ads'])
        soup = make_soup('<body><div class="ads">Ad</div><p>Content</p></body>')
        root = extract_content(soup, cfg)
        assert root.find(class_='ads') is None


class TestAutoDetect:
    def test_prefers_main(self):
        soup = make_soup('<body><main id="m"><p>main</p></main><aside>side</aside></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.get('id') == 'm'

    def test_falls_back_to_article(self):
        soup = make_soup('<body><article id="a"><p>text</p></article></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.get('id') == 'a'

    def test_falls_back_to_body(self):
        soup = make_soup('<body><p>just body</p></body>')
        root = extract_content(soup, ConversionConfig())
        assert root.name == 'body'

    def test_auto_detect_disabled(self):
        cfg = ConversionConfig(auto_detect_content=False)
        soup = make_soup('<body><main><p>main</p></main></body>')
        root = extract_content(soup, cfg)
        assert root.name == 'body'


class TestMainContentSelector:
    def test_explicit_selector(self):
        cfg = ConversionConfig(main_content_selector='div.content')
        soup = make_soup('<body><div class="content" id="c"><p>ok</p></div></body>')
        root = extract_content(soup, cfg)
        assert root.get('id') == 'c'

    def test_missing_selector_raises(self):
        cfg = ConversionConfig(main_content_selector='div.missing')
        soup = make_soup('<body><p>no match</p></body>')
        with pytest.raises(ValueError, match='matched nothing'):
            extract_content(soup, cfg)


class TestCommentStripping:
    def test_comments_removed(self):
        soup = make_soup('<body><!-- hidden --><p>visible</p></body>')
        root = extract_content(soup, ConversionConfig(strip_html_comments=True))
        assert 'hidden' not in str(root)

    def test_comments_kept_when_disabled(self):
        soup = make_soup('<body><!-- kept --><p>visible</p></body>')
        root = extract_content(soup, ConversionConfig(strip_html_comments=False))
        assert 'kept' in str(root)
