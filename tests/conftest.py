from __future__ import annotations

import os
from pathlib import Path

import pytest

from html_to_md import Converter, ConversionConfig, convert

FIXTURES = Path(__file__).parent / 'fixtures'


def fixture_path(name: str) -> Path:
    return FIXTURES / name


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding='utf-8')


@pytest.fixture
def default_converter() -> Converter:
    return Converter()


@pytest.fixture
def fragment_converter() -> Converter:
    """Converter with auto-detect disabled — suitable for HTML fragments."""
    return Converter(config=ConversionConfig(auto_detect_content=False, strip_selectors=[]))


def md_lines(md: str) -> list[str]:
    """Non-empty stripped lines from Markdown output."""
    return [l.rstrip() for l in md.splitlines() if l.strip()]
