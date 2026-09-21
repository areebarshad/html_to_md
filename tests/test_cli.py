"""Tests for the html2md CLI."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from html_to_md._cli import main

FIXTURES = Path(__file__).parent / 'fixtures'


def run_cli(*args, stdin: str = '') -> tuple[int, str]:
    """Run the CLI with the given arguments and return (exit_code, stdout)."""
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    sys.stdin = io.StringIO(stdin)
    captured = io.StringIO()
    sys.stdout = captured
    try:
        code = main(list(args))
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
    return code, captured.getvalue()


class TestCLIBasic:
    def test_stdin_to_stdout(self):
        code, out = run_cli(stdin='<p>Hello CLI</p>')
        assert code == 0
        assert 'Hello CLI' in out

    def test_file_input(self):
        fixture = str(FIXTURES / 'simple_page.html')
        code, out = run_cli(fixture)
        assert code == 0
        assert 'Main Article' in out

    def test_output_file(self, tmp_path):
        out_file = str(tmp_path / 'out.md')
        fixture = str(FIXTURES / 'simple_page.html')
        code, _ = run_cli(fixture, '-o', out_file)
        assert code == 0
        content = Path(out_file).read_text(encoding='utf-8')
        assert 'Main Article' in content


class TestCLIOptions:
    def test_selector_option(self):
        code, out = run_cli('--selector', 'main', stdin='<main><p>main</p></main><aside>side</aside>')
        assert 'main' in out
        assert 'side' not in out

    def test_heading_style_setext(self):
        code, out = run_cli('--heading-style', 'setext', stdin='<h1>Title</h1>')
        assert code == 0
        lines = [l for l in out.splitlines() if l.strip()]
        assert any(set(l) == {'='} for l in lines)

    def test_wrap_option(self):
        long = '<p>' + 'word ' * 40 + '</p>'
        code, out = run_cli('--wrap', '60', stdin=long)
        assert code == 0
        for line in out.splitlines():
            assert len(line) <= 65
