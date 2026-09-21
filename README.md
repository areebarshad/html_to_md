<h1 align="center">
  <br>
  html-to-md
  <br>
</h1>

<p align="center">
  <strong>Production-grade HTML → <a href="https://spec.commonmark.org/">CommonMark</a> Markdown converter</strong><br>
  Handles real-world pages — tables, code, footnotes, XML — with a clean, configurable API.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/CommonMark-strict-green?style=flat-square" alt="CommonMark">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="MIT license">
  <img src="https://img.shields.io/badge/tests-168%20passed-brightgreen?style=flat-square" alt="168 tests">
</p>

---

## ✨ Features

| | |
|---|---|
| 📄 **Full-page extraction** | Auto-strips `<nav>`, `<header>`, `<footer>`, `<script>`, `<style>` and more |
| 🔍 **Smart content detection** | Finds `<main>`, `<article>`, `[role='main']` automatically |
| 📊 **GFM pipe tables** | Aligned columns, ragged-row tolerance |
| 💻 **Fenced code blocks** | Language auto-detected from `language-*`, `lang-*`, `data-lang` |
| 🖼️ **Images** | `![alt](src "title")` inline style, optional base URL rewriting |
| 🔗 **Links** | Inline or reference-style, with base URL support |
| 📝 **Footnotes** | `[^n]` reference-style definitions at document end |
| 🏷️ **Headings** | ATX (`#`) or setext (underline) style |
| 📋 **Rich elements** | Nested lists, blockquotes, definition lists, `<details>`, `<figure>` |
| 🧮 **MathML → LaTeX** | Inline `$...$` and display `$$...$$` with annotation fast-path |
| 🖼️ **Image extraction** | Decodes `data:` URI images to sidecar files, emits relative links |
| 🧩 **XML support** | Auto-detects XML documents and uses the dedicated parser |
| 🔄 **Thread-safe** | One `Converter` handles concurrent calls without shared state |

---

## 📦 Installation

```bash
pip install html-to-md
```

> **Recommended** — install with the faster `lxml` parser and XML support:

```bash
pip install html-to-md[lxml]
```

**Requirements:** Python 3.9+, `beautifulsoup4 >= 4.12`

---

## 🚀 Quick Start

### One-liner

```python
from html_to_md import convert

md = convert(open("page.html").read())
print(md)
```

### From a file path

```python
from html_to_md import Converter

converter = Converter()
md = converter.convert_file("page.html")
```

### From a URL (fetch yourself, convert here)

```python
import urllib.request
from html_to_md import convert

with urllib.request.urlopen("https://example.com") as r:
    md = convert(r.read())
```

---

## ⚙️ Full API

### `Converter` class

```python
from html_to_md import Converter, ConversionConfig

cfg = ConversionConfig(
    main_content_selector="article.post",   # target only this element
    heading_style="setext",                  # or "atx" (default)
    wrap_width=80,                           # wrap at 80 columns (0 = off)
    link_style="reference",                  # or "inline" (default)
    image_base_url="https://cdn.example.com",
)

converter = Converter(config=cfg)
md = converter.convert(html_string)
```

### `convert()` convenience function

```python
from html_to_md import convert, ConversionConfig

md = convert(
    html_string,
    config=ConversionConfig(wrap_width=80),
    parser="lxml",          # or "html.parser", "html5lib", "xml"
)
```

### MathML / equations

`html-to-md` converts `<math>` elements to LaTeX notation by default.

**Annotation fast-path** — MathJax and LaTeXML pages embed a `<annotation encoding="application/x-tex">` inside `<semantics>`.  When present, that string is used verbatim (always more accurate than structural reconstruction).

**Structural walk** — for all other MathML, the converter walks `mi`, `mn`, `mo`, `mfrac`, `msub`, `msup`, `mover`, `munderover`, `mtable`, `mfenced` and more, mapping Unicode operators to LaTeX commands.

```python
from html_to_md import convert, ConversionConfig

# Default: inline → $...$, display → $$...$$
md = convert(html_with_mathml)

# Custom delimiters (e.g. for MathJax \( \) / \[ \] style)
cfg = ConversionConfig(
    math_inline_delimiters=(r"\(", r"\)"),
    math_block_delimiters=(r"\[", r"\]"),
)
md = convert(html_with_mathml, config=cfg)

# Keep raw MathML (CommonMark HTML pass-through)
cfg = ConversionConfig(math_style="raw")

# Drop all math (legacy behaviour)
cfg = ConversionConfig(math_style="strip")
```

### Embedded images (data: URIs)

HTML pages from tools like Jupyter or lecture exporters often embed images as `data:` URIs.  By default these are replaced with `[image: alt]` placeholders.  Use `asset_dir` to extract them to files instead:

```python
from html_to_md import Converter, ConversionConfig

cfg = ConversionConfig(
    asset_dir="./assets",          # created automatically if missing
    asset_url_prefix="./assets",   # used in the Markdown link (defaults to asset_dir)
)
md = Converter(config=cfg).convert_file("lecture.html")
# Images extracted to ./assets/figure-1-1-abc12345.png etc.
# Markdown contains: ![Figure 1.1](./assets/figure-1-1-abc12345.png)
```

To keep data URIs inline instead:

```python
cfg = ConversionConfig(keep_data_urls=True)
```

### XML documents

`html-to-md` automatically detects XML input (via `<?xml …>` declaration or
`xmlns` attributes) and routes it through `lxml`'s XML parser when available —
no configuration needed.

```python
from html_to_md import convert

xml = b"""<?xml version="1.0"?>
<doc xmlns="http://example.com/ns">
  <section><title>Hello</title><p>World</p></section>
</doc>"""

md = convert(xml)   # uses xml parser automatically
```

To force the XML parser explicitly:

```python
converter = Converter(parser="xml")   # requires lxml
```

---

## 🖥️ CLI

```bash
# Convert a local file
html2md page.html -o page.md

# Pipe from stdin
curl https://example.com | html2md --selector article

# Target a specific content block
html2md page.html --selector "div.post-body" -o post.md

# Setext headings + 80-column wrap
html2md page.html --heading-style setext --wrap 80

# Extract embedded images to an assets/ directory
html2md lecture.html --assets ./assets -o lecture.md

# Use \( \) / \[ \] math delimiters instead of $ $$
html2md page.html --math latex    # default
html2md page.html --math raw      # preserve MathML verbatim
html2md page.html --math strip    # drop all math

# All options
html2md --help
```

---

## 🔧 Configuration Reference

| Option | Type | Default | Description |
|---|---|---|---|
| `strip_selectors` | `list[str]` | nav, footer, script… | CSS selectors removed before conversion |
| `main_content_selector` | `str \| None` | `None` | Target only this element |
| `auto_detect_content` | `bool` | `True` | Auto-find `<main>` / `<article>` |
| `heading_style` | `"atx" \| "setext"` | `"atx"` | ATX (`#`) or setext (underline) headings |
| `link_style` | `"inline" \| "reference"` | `"inline"` | Link format |
| `image_base_url` | `str \| None` | `None` | Prepend to relative image `src` values |
| `link_base_url` | `str \| None` | `None` | Prepend to relative `href` values |
| `keep_data_urls` | `bool` | `False` | Preserve `data:` URI images inline |
| `asset_dir` | `str \| None` | `None` | Extract `data:` URI images to this directory |
| `asset_url_prefix` | `str \| None` | `None` | URL prefix for extracted image links (defaults to `asset_dir`) |
| `math_style` | `"latex" \| "raw" \| "strip"` | `"latex"` | MathML rendering: LaTeX delimiters, raw HTML, or drop |
| `math_inline_delimiters` | `tuple[str, str]` | `("$", "$")` | Open/close delimiters for inline math |
| `math_block_delimiters` | `tuple[str, str]` | `("$$", "$$")` | Open/close delimiters for display math |
| `code_language_classes` | `list[str]` | `["language-", "lang-", "highlight-"]` | Prefixes stripped from `<code class>` |
| `fenced_code_char` | `"\`" \| "~"` | `` ` `` | Fence character for code blocks |
| `wrap_width` | `int` | `0` | Wrap output at N columns (0 = off) |
| `strip_html_comments` | `bool` | `True` | Remove `<!-- … -->` from output |
| `newlines_between_blocks` | `int` | `2` | Blank lines between block elements |

---

## 🛠️ Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage report
pytest --cov=html_to_md --cov-report=term-missing
```

## Author

Areeb Arshad | Data Science, Statistics, and Mathematics @ Virginia Tech 

## 📄 License

MIT
