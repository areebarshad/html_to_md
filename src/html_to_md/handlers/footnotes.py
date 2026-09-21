from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    from .._walker import Walker


class FootnoteRegistry:
    """
    Two-phase footnote handling:
    1. Pre-scan collects definition text keyed by href.
    2. During DOM traversal, anchors are numbered in order of first appearance.
    3. render_definitions() emits ``[^n]: text`` in numeric order.
    """

    def __init__(self) -> None:
        self._href_to_text: dict[str, str] = {}  # href → raw text
        self._href_to_num: dict[str, int] = {}   # href → assigned number
        self._counter = 0

    def pre_register_definition(self, href: str, text: str) -> None:
        """Record definition text for a footnote href before traversal."""
        self._href_to_text[href] = text

    def register_anchor(self, href: str) -> int:
        """Assign (or retrieve) the footnote number for *href*."""
        if href not in self._href_to_num:
            self._counter += 1
            self._href_to_num[href] = self._counter
        return self._href_to_num[href]

    def render_definitions(self) -> str:
        """Return the footnote definitions block, or empty string if none."""
        pairs = [
            (num, self._href_to_text.get(href, ''))
            for href, num in self._href_to_num.items()
            if self._href_to_text.get(href)
        ]
        if not pairs:
            return ''
        lines = [f'[^{num}]: {text}' for num, text in sorted(pairs)]
        return '\n\n' + '\n'.join(lines) + '\n'

    def __bool__(self) -> bool:
        return bool(self._href_to_num)


def handle_footnote_anchor(node: Tag, walker: Walker) -> str:
    """
    Convert an inline footnote anchor (``<sup><a href="#fn-1">1</a></sup>``)
    to ``[^1]`` syntax and register the reference.
    """
    href = str(node.get('href', ''))
    if not href.startswith('#'):
        from .inline import handle_a
        return handle_a(node, walker)

    num = walker.footnotes.register_anchor(href)
    return f'[^{num}]'


# Selectors that identify footnote definition containers to extract from the DOM
_DEFINITION_CONTAINER_SELECTORS = [
    'section.footnotes',
    '.footnotes',
    '#footnotes',
    'div.footnote',
    'ol.footnotes',
]

_DEFINITION_ITEM_SELECTORS = [
    'li[id^="fn"]',
    'li[id^="footnote"]',
    'div[id^="fn"]',
    'p[id^="fn"]',
]


def try_collect_footnote_definitions(root: Tag, walker: Walker) -> None:
    """
    Pre-scan for footnote definition elements, register their text, then
    *remove them from the DOM* so they are not rendered as ordinary lists.
    """
    seen_ids: set[str] = set()

    # First try whole container sections (extract + collect items inside)
    for container_sel in _DEFINITION_CONTAINER_SELECTORS:
        for container in list(root.select(container_sel)):
            if not isinstance(container, Tag):
                continue
            for item in container.find_all('li'):
                if not isinstance(item, Tag):
                    continue
                item_id = item.get('id', '')
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(str(item_id))
                _collect_item(item, '#' + str(item_id), walker)
            container.decompose()

    # Also sweep any remaining individual items not inside a container
    for item_sel in _DEFINITION_ITEM_SELECTORS:
        for item in list(root.select(item_sel)):
            if not isinstance(item, Tag):
                continue
            item_id = str(item.get('id', ''))
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            _collect_item(item, '#' + item_id, walker)
            item.decompose()


def _collect_item(item: Tag, href: str, walker: Walker) -> None:
    # Strip back-link anchors before extracting text
    for back_link in item.select('a[href^="#fnref"], a.footnote-backref'):
        back_link.decompose()
    text = item.get_text(separator=' ').strip()
    text = re.sub(r'\s+', ' ', text)
    if text:
        walker.footnotes.pre_register_definition(href, text)
