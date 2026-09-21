from __future__ import annotations

from bs4 import BeautifulSoup, Comment, Tag

from .config import ConversionConfig


def extract_content(soup: BeautifulSoup, config: ConversionConfig) -> Tag:
    """
    Return the Tag that should be converted, after removing unwanted elements.

    Order of operations:
    1. Remove HTML comments (if configured).
    2. Strip elements matching ``config.strip_selectors``.
    3. If ``config.main_content_selector`` is set, return the first match.
    4. If ``config.auto_detect_content`` is True, check for <main> / <article> /
       [role='main'].
    5. Fall back to <body> or the whole document root.
    """
    if config.strip_html_comments:
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

    _strip_elements(soup, config)

    if config.main_content_selector:
        node = soup.select_one(config.main_content_selector)
        if node is None:
            raise ValueError(
                f"main_content_selector {config.main_content_selector!r} matched nothing"
            )
        return node  # type: ignore[return-value]

    if config.auto_detect_content:
        for selector in ("main", "article", "[role='main']", "[role='document']"):
            node = soup.select_one(selector)
            if node is not None:
                return node  # type: ignore[return-value]

    body = soup.find("body")
    if body is not None:
        return body  # type: ignore[return-value]

    return soup  # type: ignore[return-value]


def _strip_elements(soup: BeautifulSoup, config: ConversionConfig) -> None:
    """Remove all elements matching any selector in ``config.strip_selectors``."""
    for selector in config.strip_selectors:
        for node in soup.select(selector):
            node.decompose()
