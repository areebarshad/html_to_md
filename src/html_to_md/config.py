from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Tuple


@dataclass
class ConversionConfig:
    """Controls every aspect of the HTML-to-Markdown conversion."""

    # --- Content extraction ---
    strip_selectors: Sequence[str] = field(
        default_factory=lambda: [
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "aside",
            "[role='navigation']",
            "[role='banner']",
            "[role='contentinfo']",
            ".ad",
            ".advertisement",
            ".sidebar",
            ".cookie-banner",
        ]
    )
    """CSS selectors / tag names removed before conversion."""

    main_content_selector: str | None = None
    """
    If set, only the first element matching this CSS selector is converted.
    Example: ``"article"`` or ``"div.post-body"``.
    When *None* the entire ``<body>`` is used (after stripping unwanted elements).
    """

    auto_detect_content: bool = True
    """
    When *True* and ``main_content_selector`` is *None*, the converter
    attempts to find the primary content element by checking for
    ``<main>``, ``<article>``, or ``[role='main']`` before falling back
    to ``<body>``.
    """

    # --- Heading style ---
    heading_style: str = "atx"
    """``"atx"`` (``# Heading``) or ``"setext"`` (underline style, h1/h2 only)."""

    # --- Link / image options ---
    link_style: str = "inline"
    """``"inline"`` → ``[text](url)`` or ``"reference"`` → ``[text][ref]`` blocks."""

    image_base_url: str | None = None
    """Base URL prepended to relative image ``src`` values."""

    link_base_url: str | None = None
    """Base URL prepended to relative ``href`` values."""

    keep_data_urls: bool = False
    """When *False*, ``data:`` URI images are replaced with a placeholder."""

    asset_dir: str | None = None
    """
    Directory where extracted ``data:`` URI images are written.
    When set, base64 image data is decoded and saved to this directory;
    the Markdown references the file by a relative path.
    When *None*, ``data:`` URIs fall back to ``keep_data_urls`` behaviour.
    """

    asset_url_prefix: str | None = None
    """
    URL prefix written into the Markdown ``![alt](prefix/file.png)`` link.
    Defaults to ``asset_dir`` when *None*.
    Useful when the assets directory is served at a different path.
    """

    # --- Code blocks ---
    code_language_classes: Sequence[str] = field(
        default_factory=lambda: ["language-", "lang-", "highlight-"]
    )
    """Prefixes stripped from ``<code class="...">`` to obtain the language tag."""

    fenced_code_char: str = "`"
    """Character used for fenced code blocks: ``'`'`` or ``'~'``."""

    # --- Math ---
    math_style: str = "latex"
    """
    How ``<math>`` elements are rendered.

    ``"latex"``
        MathML is translated to LaTeX delimiters: inline ``$...$``,
        display ``$$...$$``.  An ``<annotation encoding="application/x-tex">``
        child is used verbatim when present.
    ``"raw"``
        The ``<math>`` element is emitted verbatim as an HTML block
        (CommonMark raw-HTML pass-through).
    ``"strip"``
        The ``<math>`` element and all its children are dropped (legacy
        behaviour).
    """

    math_inline_delimiters: Tuple[str, str] = ("$", "$")
    """Open/close delimiters for inline math.  Default ``("$", "$")``."""

    math_block_delimiters: Tuple[str, str] = ("$$", "$$")
    """Open/close delimiters for display/block math.  Default ``("$$", "$$")``."""

    # --- Tables ---
    table_column_separator: str = " | "
    """String used between pipe-table columns."""

    table_missing_cell: str = ""
    """Placeholder for missing cells in ragged tables."""

    # --- Footnotes ---
    footnote_selectors: Sequence[str] = field(
        default_factory=lambda: [
            "sup > a[href^='#']",
            "a[href^='#fn']",
            "a[href^='#footnote']",
        ]
    )
    """CSS selectors that identify inline footnote anchors."""

    # --- Whitespace / output ---
    newlines_between_blocks: int = 2
    """Blank lines between top-level block elements."""

    wrap_width: int = 0
    """Line-wrap column. ``0`` disables wrapping."""

    strip_html_comments: bool = True
    """Remove ``<!-- ... -->`` from output."""

    def validate(self) -> None:
        if self.heading_style not in ("atx", "setext"):
            raise ValueError(f"heading_style must be 'atx' or 'setext', got {self.heading_style!r}")
        if self.link_style not in ("inline", "reference"):
            raise ValueError(f"link_style must be 'inline' or 'reference', got {self.link_style!r}")
        if self.fenced_code_char not in ("`", "~"):
            raise ValueError(f"fenced_code_char must be '`' or '~', got {self.fenced_code_char!r}")
        if self.newlines_between_blocks < 1:
            raise ValueError("newlines_between_blocks must be >= 1")
        if self.math_style not in ("latex", "raw", "strip"):
            raise ValueError(f"math_style must be 'latex', 'raw', or 'strip', got {self.math_style!r}")
        if len(self.math_inline_delimiters) != 2:
            raise ValueError("math_inline_delimiters must be a 2-tuple of (open, close)")
        if len(self.math_block_delimiters) != 2:
            raise ValueError("math_block_delimiters must be a 2-tuple of (open, close)")


DEFAULT_CONFIG = ConversionConfig()
