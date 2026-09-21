from __future__ import annotations

from bs4 import BeautifulSoup

from .config import ConversionConfig, DEFAULT_CONFIG
from .extractor import extract_content
from ._walker import Walker


def _make_soup(html: str | bytes, parser: str) -> BeautifulSoup:
    return BeautifulSoup(html, parser)


def _choose_parser() -> str:
    try:
        import lxml  # noqa: F401
        return 'lxml'
    except ImportError:
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
