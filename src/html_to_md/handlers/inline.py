from __future__ import annotations

import re
import urllib.parse
from typing import TYPE_CHECKING

from bs4 import NavigableString, Tag

if TYPE_CHECKING:
    from .._walker import Walker


_ESCAPE_RE = re.compile(r'([\\`*_{}\[\]()#+\-.!])')


def escape_markdown(text: str) -> str:
    """Escape CommonMark special characters in plain text."""
    return _ESCAPE_RE.sub(r'\\\1', text)


def handle_text(node: NavigableString, walker: Walker) -> str:
    text = str(node)
    if walker.in_preformatted:
        return text
    # Collapse whitespace; preserve single spaces
    text = re.sub(r'[ \t\r\n]+', ' ', text)
    if walker.in_code_span:
        return text
    return escape_markdown(text)


def handle_strong(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    if not inner.strip():
        return inner
    return f"**{inner}**"


def handle_em(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    if not inner.strip():
        return inner
    return f"*{inner}*"


def handle_del(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    if not inner.strip():
        return inner
    return f"~~{inner}~~"


def handle_code_span(node: Tag, walker: Walker) -> str:
    walker.in_code_span = True
    text = walker.convert_children(node)
    walker.in_code_span = False
    if '`' in text:
        fence = '``'
        if text.startswith('`') or text.endswith('`'):
            text = f' {text} '
    else:
        fence = '`'
    return f"{fence}{text}{fence}"


def handle_a(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    href = node.get('href', '')
    title = node.get('title', '')

    if not href:
        return inner

    href = _resolve_url(str(href), walker.config.link_base_url)

    if walker.config.link_style == 'reference':
        ref_id = walker.register_link_ref(str(href), str(title))
        return f'[{inner}][{ref_id}]'

    title_part = f' "{_escape_title(str(title))}"' if title else ''
    return f'[{inner}]({href}{title_part})'


def handle_img(node: Tag, walker: Walker) -> str:
    alt = node.get('alt', '')
    src = str(node.get('src', ''))
    title = node.get('title', '')

    if src.startswith('data:') and not walker.config.keep_data_urls:
        src = ''

    if not src:
        return f'[image: {escape_markdown(str(alt))}]'

    src = _resolve_url(src, walker.config.image_base_url)
    title_part = f' "{_escape_title(str(title))}"' if title else ''
    return f'![{escape_markdown(str(alt))}]({src}{title_part})'


def handle_br(node: Tag, walker: Walker) -> str:
    return '  \n' if not walker.in_preformatted else '\n'


def handle_sup(node: Tag, walker: Walker) -> str:
    # Footnote anchors are handled upstream; plain <sup> → superscript text
    inner = walker.convert_children(node)
    return f'<sup>{inner}</sup>'


def handle_sub(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    return f'<sub>{inner}</sub>'


def handle_abbr(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node)
    title = node.get('title', '')
    if title:
        return f'{inner} ({escape_markdown(str(title))})'
    return inner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_url(url: str, base: str | None) -> str:
    if base and url and not urllib.parse.urlsplit(url).scheme:
        return urllib.parse.urljoin(base, url)
    return url


def _escape_title(title: str) -> str:
    return title.replace('"', '\\"')
