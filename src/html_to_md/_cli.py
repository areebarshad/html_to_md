from __future__ import annotations

import argparse
import sys

from .config import ConversionConfig
from .converter import Converter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='html2md',
        description='Convert HTML to CommonMark Markdown.',
    )
    parser.add_argument(
        'input',
        nargs='?',
        metavar='FILE',
        help='HTML file to read (default: stdin)',
    )
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Write Markdown to FILE instead of stdout',
    )
    parser.add_argument(
        '--selector',
        metavar='CSS',
        help='CSS selector for main content (e.g. "article")',
    )
    parser.add_argument(
        '--no-auto-detect',
        action='store_true',
        help='Disable automatic content detection',
    )
    parser.add_argument(
        '--heading-style',
        choices=['atx', 'setext'],
        default='atx',
        metavar='STYLE',
        help='Heading style: atx (default) or setext',
    )
    parser.add_argument(
        '--wrap',
        type=int,
        default=0,
        metavar='N',
        help='Wrap output at N columns (0 = no wrap)',
    )
    parser.add_argument(
        '--base-url',
        metavar='URL',
        help='Base URL for resolving relative links and images',
    )
    parser.add_argument(
        '--parser',
        default=None,
        metavar='NAME',
        help='BeautifulSoup parser: lxml (default if installed), html.parser, html5lib',
    )

    args = parser.parse_args(argv)

    config = ConversionConfig(
        main_content_selector=args.selector,
        auto_detect_content=not args.no_auto_detect,
        heading_style=args.heading_style,
        wrap_width=args.wrap,
        link_base_url=args.base_url,
        image_base_url=args.base_url,
    )

    converter = Converter(config=config, parser=args.parser)

    if args.input:
        md = converter.convert_file(args.input)
    else:
        html = sys.stdin.read()
        md = converter.convert(html)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(md)
    else:
        sys.stdout.write(md)

    return 0


if __name__ == '__main__':
    sys.exit(main())
