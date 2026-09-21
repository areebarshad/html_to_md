"""
Tests for data: URI image handling — extraction, inlining, and fallback.
"""
from __future__ import annotations

import base64
import os
import re

import pytest

from html_to_md import convert, ConversionConfig


# ---------------------------------------------------------------------------
# Minimal 1×1 transparent PNG (67 bytes)
# ---------------------------------------------------------------------------
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_PNG_B64 = base64.b64encode(_PNG_BYTES).decode()
_PNG_DATA_URI = f"data:image/png;base64,{_PNG_B64}"


def _img_html(alt: str = "Figure 1.1", src: str = _PNG_DATA_URI, title: str = "") -> str:
    t = f' title="{title}"' if title else ""
    return f'<p><img src="{src}" alt="{alt}"{t}></p>'


# ---------------------------------------------------------------------------
# Default behaviour (no asset_dir, keep_data_urls=False)
# ---------------------------------------------------------------------------

class TestDefaultBehaviour:
    def test_data_uri_replaced_with_placeholder(self):
        md = convert(_img_html())
        assert "[image:" in md
        assert "data:" not in md

    def test_placeholder_contains_alt_text(self):
        md = convert(_img_html(alt="My Figure"))
        assert "My Figure" in md

    def test_normal_src_passes_through(self):
        md = convert(_img_html(src="https://example.com/img.png"))
        assert "https://example.com/img.png" in md
        assert "![" in md


# ---------------------------------------------------------------------------
# keep_data_urls=True (inline mode)
# ---------------------------------------------------------------------------

class TestInlineMode:
    def test_data_uri_kept_inline(self):
        cfg = ConversionConfig(keep_data_urls=True)
        md = convert(_img_html(), config=cfg)
        assert "data:image/png;base64," in md
        assert "![" in md


# ---------------------------------------------------------------------------
# Asset extraction
# ---------------------------------------------------------------------------

class TestAssetExtraction:
    def test_file_written_to_asset_dir(self, tmp_path):
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        convert(_img_html(alt="test-fig"), config=cfg)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].suffix == ".png"

    def test_written_file_contents_match(self, tmp_path):
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        convert(_img_html(), config=cfg)
        written = list(tmp_path.iterdir())[0]
        assert written.read_bytes() == _PNG_BYTES

    def test_markdown_link_points_to_file(self, tmp_path):
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        md = convert(_img_html(alt="test-fig"), config=cfg)
        assert "![" in md
        assert "data:" not in md
        # Link should reference something under the asset dir name
        link_match = re.search(r"!\[.*?\]\((.*?)\)", md)
        assert link_match is not None
        href = link_match.group(1)
        assert ".png" in href

    def test_alt_text_used_in_filename_slug(self, tmp_path):
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        convert(_img_html(alt="Deterministic relationship"), config=cfg)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        # slug should contain recognisable words from alt
        assert "deterministic" in files[0].name or "relationship" in files[0].name

    def test_custom_asset_url_prefix(self, tmp_path):
        cfg = ConversionConfig(
            asset_dir=str(tmp_path),
            asset_url_prefix="./media",
        )
        md = convert(_img_html(), config=cfg)
        assert "./media/" in md

    def test_stable_filename_on_reruns(self, tmp_path):
        """Two conversions of the same image produce the same filename."""
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        md1 = convert(_img_html(), config=cfg)
        md2 = convert(_img_html(), config=cfg)
        link1 = re.search(r"!\[.*?\]\((.*?)\)", md1).group(1)
        link2 = re.search(r"!\[.*?\]\((.*?)\)", md2).group(1)
        assert os.path.basename(link1) == os.path.basename(link2)

    def test_multiple_images_each_extracted(self, tmp_path):
        html = (
            f'<p><img src="{_PNG_DATA_URI}" alt="Fig 1"></p>'
            f'<p><img src="{_PNG_DATA_URI}" alt="Fig 2"></p>'
        )
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        md = convert(html, config=cfg)
        links = re.findall(r"!\[.*?\]\((.*?)\)", md)
        assert len(links) == 2

    def test_asset_dir_created_if_missing(self, tmp_path):
        new_dir = tmp_path / "nested" / "assets"
        cfg = ConversionConfig(asset_dir=str(new_dir))
        convert(_img_html(), config=cfg)
        assert new_dir.exists()

    def test_no_files_written_when_no_data_uri(self, tmp_path):
        html = '<p><img src="https://example.com/img.png" alt="external"></p>'
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        convert(html, config=cfg)
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Malformed data URI
# ---------------------------------------------------------------------------

class TestMalformedDataUri:
    def test_bad_base64_falls_back_to_placeholder(self):
        html = '<p><img src="data:image/png;base64,NOT_VALID_BASE64!!!" alt="broken"></p>'
        cfg = ConversionConfig(asset_dir="/tmp/nowhere")
        # Must not raise; must produce a placeholder
        md = convert(html, config=cfg)
        assert "[image:" in md or "broken" in md

    def test_missing_comma_falls_back(self):
        html = '<p><img src="data:image/png;base64" alt="missing comma"></p>'
        cfg = ConversionConfig(asset_dir="/tmp/nowhere")
        md = convert(html, config=cfg)
        # Should not crash
        assert "missing comma" in md or "[image:" in md


# ---------------------------------------------------------------------------
# Title attribute preserved
# ---------------------------------------------------------------------------

class TestTitlePreservation:
    def test_title_preserved_with_normal_src(self):
        html = '<p><img src="https://example.com/img.png" alt="alt" title="my title"></p>'
        md = convert(html)
        assert '"my title"' in md

    def test_title_preserved_after_extraction(self, tmp_path):
        html = f'<p><img src="{_PNG_DATA_URI}" alt="fig" title="Fig caption"></p>'
        cfg = ConversionConfig(asset_dir=str(tmp_path))
        md = convert(html, config=cfg)
        assert '"Fig caption"' in md
