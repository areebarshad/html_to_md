from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup

try:
    from bs4 import XMLParsedAsHTMLWarning as _XMLWarn
except ImportError:  # bs4 < 4.11
    _XMLWarn = None  # type: ignore[assignment,misc]

from .config import ConversionConfig, DEFAULT_CONFIG
from .extractor import extract_content
from ._walker import Walker

# Matches <?xml …> declarations or root elements with xmlns attributes.
_XML_SNIFF = re.compile(
    rb'^\s*<\?xml[\s>]|<[A-Za-z][^>]*\sxmlns[=:]',
    re.MULTILINE,
)

# XHTML documents declare themselves via their DOCTYPE.  They are valid XML
# but browsers (and lxml's HTML parser) handle them fine as HTML, while
# lxml's strict XML parser can silently drop the <body> when namespace
# resolution fails, leaving only the Doctype string as output.
_XHTML_DOCTYPE_RE = re.compile(
    rb'<!DOCTYPE\s+html\b[^>]*?(?:XHTML|xhtml)',
    re.DOTALL | re.IGNORECASE,
)


def _looks_like_xml(html: str | bytes) -> bool:
    sample = html[:2048].encode('utf-8', errors='replace') if isinstance(html, str) else html[:2048]
    if _XHTML_DOCTYPE_RE.search(sample):
        return False  # XHTML is better handled by the HTML parser
    return bool(_XML_SNIFF.search(sample))


def _lxml_available() -> bool:
    try:
        import lxml  # noqa: F401
        return True
    except ImportError:
        return False


def _make_soup(html: str | bytes, parser: str) -> BeautifulSoup:
    # Use the dedicated XML parser for XML documents when lxml is present.
    if _looks_like_xml(html) and _lxml_available():
        return BeautifulSoup(html, features='xml')

    # Silence the XMLParsedAsHTMLWarning for edge-case XML fed to an HTML parser.
    if _XMLWarn is not None:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=_XMLWarn)
            return BeautifulSoup(html, parser)

    return BeautifulSoup(html, parser)


def _choose_parser() -> str:
    if _lxml_available():
        return 'lxml'
    return 'html.parser'


class Converter:
    """
    Thread-safe HTML-to-Markdown converter.

    Each call to :meth:`convert` creates a fresh :class:`Walker` instance,
    so a single :class:`Converter` can safely be reused across threads.

    Parameters
    ----------
    config:
        Conversion settings. Defaults to :data:`~html_to_md.config.DEFAULT_CONFIG`.
    parser:
        BeautifulSoup parser backend. Auto-detects ``lxml`` when installed,
        falls back to ``"html.parser"``. Pass ``"html5lib"`` for maximum
        HTML5 compatibility (requires the ``html5lib`` package).
    """

    def __init__(
        self,
        config: ConversionConfig | None = None,
        parser: str | None = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG
        self.config.validate()
        self.parser = parser or _choose_parser()

    def convert(self, html: str | bytes) -> str:
        """
        Convert *html* to Markdown and return the result as a string.

        Parameters
        ----------
        html:
            Full HTML document or fragment. Both ``str`` and ``bytes``
            (UTF-8 or with a charset meta tag) are accepted.

        Returns
        -------
        str
            CommonMark-compliant Markdown.
        """
        soup = _make_soup(html, self.parser)
        root = extract_content(soup, self.config)
        walker = Walker(self.config)
        return walker.convert(root)

    def convert_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read *path* and convert its HTML contents to Markdown."""
        with open(path, encoding=encoding) as fh:
            return self.convert(fh.read())


def convert(
    html: str | bytes,
    *,
    config: ConversionConfig | None = None,
    parser: str | None = None,
) -> str:
    """
    Module-level convenience function.

    Equivalent to ``Converter(config, parser).convert(html)``.
    """
    return Converter(config=config, parser=parser).convert(html)
