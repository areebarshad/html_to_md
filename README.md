# html-to-md

Production-grade HTML to [CommonMark](https://spec.commonmark.org/) Markdown converter.

## Features

- Full-page conversion with automatic content extraction (strips `<nav>`, `<header>`, `<footer>`, `<script>`, `<style>`, etc.)
- Auto-detects `<main>` / `<article>` / `[role='main']` as the primary content area
- Configurable CSS selector for main content
- GFM pipe tables with alignment
- Fenced code blocks with language detection (`language-*`, `lang-*`, `data-lang`)
- Inline code spans with backtick escaping
- Images with alt text and title
- Footnotes → `[^n]` reference-style definitions
- Inline and reference-style links
- ATX and setext headings
- Nested lists, blockquotes, definition lists, `<details>`, `<figure>`
- Optional line wrapping
- Thread-safe: one `Converter` instance handles concurrent calls

## Installation

```bash
pip install html-to-md
```

With the faster `lxml` parser (recommended):

```bash
pip install html-to-md[lxml]
```

## Quick start

```python
from html_to_md import convert

md = convert(open("page.html").read())
print(md)
```

## Full control

```python
from html_to_md import Converter, ConversionConfig

cfg = ConversionConfig(
    main_content_selector="article.post",
    heading_style="setext",
    wrap_width=80,
    link_style="reference",
    image_base_url="https://cdn.example.com",
)

converter = Converter(config=cfg)
md = converter.convert(html_string)
```

## CLI

```bash
# From file
html2md page.html -o page.md

# From stdin
curl https://example.com | html2md --selector article

# Options
html2md --help
```

## Configuration reference

| Option | Type | Default | Description |
|---|---|---|---|
| `strip_selectors` | list[str] | (nav, footer, …) | CSS selectors stripped before conversion |
| `main_content_selector` | str \| None | None | CSS selector for main content node |
| `auto_detect_content` | bool | True | Auto-detect `<main>` / `<article>` |
| `heading_style` | `"atx"` \| `"setext"` | `"atx"` | Heading format |
| `link_style` | `"inline"` \| `"reference"` | `"inline"` | Link format |
| `image_base_url` | str \| None | None | Base URL for relative image src |
| `link_base_url` | str \| None | None | Base URL for relative href |
| `keep_data_urls` | bool | False | Preserve `data:` URI images |
| `fenced_code_char` | `"\`"` \| `"~"` | `"\`"` | Fence character |
| `wrap_width` | int | 0 | Wrap at N columns (0 = off) |
| `strip_html_comments` | bool | True | Remove HTML comments |

## Development

```bash
pip install -e ".[dev]"
pytest
pytest --cov
```

## License

MIT
