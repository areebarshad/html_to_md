"""
html_to_md
~~~~~~~~~~
Production-grade HTML to CommonMark Markdown converter.

Quick start::

    from html_to_md import convert

    md = convert("<h1>Hello</h1><p>World</p>")

For full control::

    from html_to_md import Converter, ConversionConfig

    cfg = ConversionConfig(heading_style="setext", wrap_width=80)
    converter = Converter(config=cfg)
    md = converter.convert(html_string)
"""

from .config import ConversionConfig, DEFAULT_CONFIG
from .converter import Converter, convert

__all__ = [
    "convert",
    "Converter",
    "ConversionConfig",
    "DEFAULT_CONFIG",
]

__version__ = "0.1.0"
