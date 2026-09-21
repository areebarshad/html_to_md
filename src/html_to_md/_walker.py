from __future__ import annotations

import re
from typing import Callable

from bs4 import NavigableString, Tag

from .config import ConversionConfig
from .handlers import blocks, code, inline, tables
from .handlers import math as math_handler
from .handlers.footnotes import FootnoteRegistry, handle_footnote_anchor, try_collect_footnote_definitions


class Walker:
    """
    Recursive DOM walker that converts a BeautifulSoup tree to Markdown.

    State attributes are modified in-place during traversal and reset
    after each nested call returns, so the walker is NOT thread-safe.
    """

    def __init__(self, config: ConversionConfig) -> None:
        self.config = config
        self.in_preformatted = False
        self.in_code_span = False
        self.list_depth = 0
        self.ordered_list_counters: list[int] = []
        self.footnotes = FootnoteRegistry()
        self._link_refs: dict[str, tuple[str, str]] = {}  # ref_id → (url, title)
        self._link_ref_counter = 0
        # Pending asset extractions: list of (relative_url_path, raw_bytes, content_type)
        self._pending_assets: list[tuple[str, bytes, str]] = []
        self._asset_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, root: Tag) -> str:
        try_collect_footnote_definitions(root, self)
        md = self.convert_children(root)
        md = self._post_process(md)
        if self.config.link_style == 'reference':
            md += self._render_link_refs()
        if self.footnotes:
            md += self.footnotes.render_definitions()
        self._flush_assets()
        return md

    def register_asset(self, data: bytes, content_type: str, alt: str) -> str:
        """
        Register a decoded data-URI payload for later disk write.

        Returns the relative URL path that should be used in the Markdown link.
        """
        import hashlib

        ext = _content_type_to_ext(content_type)
        slug = _slugify(alt)[:40] or "image"
        # Use a short content hash so re-runs are stable and collisions vanish.
        digest = hashlib.sha1(data).hexdigest()[:8]
        filename = f"{slug}-{digest}{ext}"

        asset_url_prefix = self.config.asset_url_prefix or self.config.asset_dir or "assets"
        # Normalise to forward slashes for the Markdown link
        prefix = asset_url_prefix.rstrip("/\\").replace("\\", "/")
        url_path = f"{prefix}/{filename}"

        self._pending_assets.append((filename, data, content_type))
        return url_path

    def _flush_assets(self) -> None:
        """Write collected asset files to disk if asset_dir is configured."""
        if not self._pending_assets or not self.config.asset_dir:
            return
        import os
        os.makedirs(self.config.asset_dir, exist_ok=True)
        for filename, data, _ in self._pending_assets:
            dest = os.path.join(self.config.asset_dir, filename)
            with open(dest, "wb") as fh:
                fh.write(data)
        self._pending_assets.clear()

    def convert_children(self, node: Tag) -> str:
        parts: list[str] = []
        for child in node.children:
            parts.append(self._dispatch(child))
        return ''.join(parts)

    # ------------------------------------------------------------------
    # Dispatch table
    # ------------------------------------------------------------------

    def _dispatch(self, node) -> str:
        if isinstance(node, NavigableString):
            return inline.handle_text(node, self)

        if not isinstance(node, Tag):
            return ''

        name = node.name

        # ---- Pre / code blocks ----------------------------------------
        if name == 'pre':
            if node.find('code'):
                return code.handle_pre_code(node, self)
            return blocks.handle_pre(node, self)

        if name == 'code' and not self.in_preformatted:
            return inline.handle_code_span(node, self)

        # ---- Headings -------------------------------------------------
        if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return blocks.handle_heading(node, self, int(name[1]))

        # ---- Block elements -------------------------------------------
        if name == 'p':
            return blocks.handle_p(node, self)
        if name == 'blockquote':
            return blocks.handle_blockquote(node, self)
        if name == 'ul':
            return blocks.handle_ul(node, self)
        if name == 'ol':
            return blocks.handle_ol(node, self)
        if name in ('dl',):
            return blocks.handle_dl(node, self)
        if name == 'hr':
            return blocks.handle_hr(node, self)
        if name in ('div', 'section', 'article', 'main', 'body'):
            return blocks.handle_div(node, self)
        if name == 'details':
            return blocks.handle_details(node, self)
        if name == 'figure':
            return blocks.handle_figure(node, self)

        # ---- Table ----------------------------------------------------
        if name == 'table':
            return tables.handle_table(node, self)

        # Skip table structure tags (handled inside handle_table)
        if name in ('thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'colgroup', 'col', 'caption'):
            return self.convert_children(node)

        # ---- Inline elements ------------------------------------------
        if name in ('strong', 'b'):
            return inline.handle_strong(node, self)
        if name in ('em', 'i'):
            return inline.handle_em(node, self)
        if name in ('del', 's', 'strike'):
            return inline.handle_del(node, self)
        if name == 'br':
            return inline.handle_br(node, self)
        if name == 'sup':
            return self._handle_sup(node)
        if name == 'sub':
            return inline.handle_sub(node, self)
        if name == 'abbr':
            return inline.handle_abbr(node, self)
        if name == 'img':
            return inline.handle_img(node, self)
        if name == 'a':
            return self._handle_a(node)

        # ---- Math -----------------------------------------------------
        if name == 'math':
            return math_handler.handle_math(node, self)

        # ---- Semantic / pass-through ----------------------------------
        if name in ('span', 'label', 'time', 'mark', 'cite', 'q',
                    'li', 'dt', 'dd', 'figcaption', 'summary',
                    'address', 'bdi', 'bdo', 'data', 'dfn', 'kbd',
                    'rp', 'rt', 'ruby', 'samp', 'small', 'u', 'var', 'wbr'):
            return self.convert_children(node)

        # ---- Skip non-content tags ------------------------------------
        if name in ('head', 'meta', 'link', 'title', 'base',
                    'script', 'style', 'noscript', 'template',
                    'object', 'embed', 'param', 'map', 'area',
                    'audio', 'video', 'source', 'track',
                    'input', 'button', 'select', 'option', 'optgroup',
                    'textarea', 'form', 'fieldset', 'legend',
                    'datalist', 'output', 'progress', 'meter',
                    'canvas', 'svg',
                    '[document]'):
            return ''

        # Fallback: recurse into unknown tags
        return self.convert_children(node)

    # ------------------------------------------------------------------
    # Footnote / link-ref helpers
    # ------------------------------------------------------------------

    def _handle_sup(self, node: Tag) -> str:
        """Check for footnote anchor inside <sup>."""
        anchor = node.find('a')
        if anchor and isinstance(anchor, Tag):
            href = str(anchor.get('href', ''))
            if href.startswith('#'):
                return handle_footnote_anchor(anchor, self)
        return inline.handle_sup(node, self)

    def _handle_a(self, node: Tag) -> str:
        """Check for footnote anchor pattern on <a> directly."""
        href = str(node.get('href', ''))
        is_footnote = any(
            _css_match(node, sel)
            for sel in self.config.footnote_selectors
        )
        if is_footnote and href.startswith('#'):
            return handle_footnote_anchor(node, self)
        return inline.handle_a(node, self)

    def register_link_ref(self, url: str, title: str) -> str:
        key = (url, title)
        for ref_id, stored in self._link_refs.items():
            if stored == key:
                return ref_id
        self._link_ref_counter += 1
        ref_id = str(self._link_ref_counter)
        self._link_refs[ref_id] = key
        return ref_id

    def _render_link_refs(self) -> str:
        if not self._link_refs:
            return ''
        lines = []
        for ref_id, (url, title) in self._link_refs.items():
            title_part = f' "{title}"' if title else ''
            lines.append(f'[{ref_id}]: {url}{title_part}')
        return '\n\n' + '\n'.join(lines) + '\n'

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _post_process(self, md: str) -> str:
        # Collapse runs of 3+ blank lines to exactly 2
        md = re.sub(r'\n{3,}', '\n\n', md)
        # Strip leading/trailing whitespace
        md = md.strip()
        if md:
            md += '\n'
        if self.config.wrap_width > 0:
            md = _wrap_text(md, self.config.wrap_width)
        return md


# ---------------------------------------------------------------------------
# Tiny CSS selector helper for the cases where bs4.Tag.matches() is unavailable
# ---------------------------------------------------------------------------

def _css_match(node: Tag, selector: str) -> bool:
    try:
        # Use the node's parent as search context; select returns all matches
        parent = node.parent
        if parent is None:
            return False
        return node in parent.select(selector)
    except Exception:
        return False


def _wrap_text(text: str, width: int) -> str:
    import textwrap
    lines = []
    for line in text.splitlines():
        if len(line) <= width or line.startswith(('    ', '\t', '|', '>', '#', '`', '-', '*', '+', '$$', '\\[')):
            lines.append(line)
        else:
            lines.extend(textwrap.wrap(line, width))
    return '\n'.join(lines) + '\n'


_EXT_MAP: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


def _content_type_to_ext(content_type: str) -> str:
    """Return a file extension for a MIME type, defaulting to .bin."""
    base = content_type.split(";")[0].strip().lower()
    return _EXT_MAP.get(base, ".bin")


def _slugify(text: str) -> str:
    """Convert arbitrary text to a safe filename slug."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")
