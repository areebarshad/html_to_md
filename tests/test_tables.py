"""Tests for HTML table conversion."""
from __future__ import annotations

import pytest
from html_to_md import Converter, ConversionConfig


def c(html: str) -> str:
    cfg = ConversionConfig(auto_detect_content=False, strip_selectors=[])
    return Converter(config=cfg).convert(f'<body>{html}</body>')


def table_rows(md: str) -> list[list[str]]:
    """Parse pipe-table rows from Markdown output, skipping separator row."""
    rows = []
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        # Skip separator rows (only dashes and colons)
        if all(set(c.replace(':', '').replace('-', '').replace(' ', '')) == set() for c in cells):
            continue
        rows.append(cells)
    return rows


class TestBasicTable:
    SIMPLE = '''
    <table>
      <thead><tr><th>A</th><th>B</th></tr></thead>
      <tbody><tr><td>1</td><td>2</td></tr></tbody>
    </table>
    '''

    def test_produces_pipe_table(self):
        result = c(self.SIMPLE)
        assert '|' in result

    def test_header_present(self):
        result = c(self.SIMPLE)
        rows = table_rows(result)
        assert rows[0] == ['A', 'B']

    def test_data_row_present(self):
        result = c(self.SIMPLE)
        rows = table_rows(result)
        assert rows[1] == ['1', '2']

    def test_separator_row_present(self):
        result = c(self.SIMPLE)
        sep_lines = [l for l in result.splitlines() if '---' in l and '|' in l]
        assert sep_lines


class TestTableAlignment:
    ALIGNED = '''
    <table>
      <thead>
        <tr>
          <th align="left">Left</th>
          <th align="right">Right</th>
          <th align="center">Center</th>
        </tr>
      </thead>
      <tbody><tr><td>L</td><td>R</td><td>C</td></tr></tbody>
    </table>
    '''

    def test_left_alignment_marker(self):
        result = c(self.ALIGNED)
        assert ':---' in result

    def test_right_alignment_marker(self):
        result = c(self.ALIGNED)
        assert '---:' in result

    def test_center_alignment_marker(self):
        result = c(self.ALIGNED)
        assert ':---:' in result or ':--:' in result


class TestTableEdgeCases:
    def test_pipe_in_cell_escaped(self):
        result = c('<table><tr><td>a | b</td></tr></table>')
        assert r'a \| b' in result

    def test_ragged_table(self):
        html = '''
        <table>
          <tr><td>1</td><td>2</td><td>3</td></tr>
          <tr><td>A</td></tr>
        </table>
        '''
        result = c(html)
        rows = table_rows(result)
        # All rows should have the same column count
        col_counts = {len(r) for r in rows}
        assert len(col_counts) == 1

    def test_empty_table(self):
        result = c('<table></table>')
        assert result.strip() == ''

    def test_colspan(self):
        html = '<table><tr><td colspan="2">wide</td></tr><tr><td>a</td><td>b</td></tr></table>'
        result = c(html)
        assert 'wide' in result
        rows = table_rows(result)
        # colspan row should have 2 cells (wide + placeholder)
        assert len(rows[0]) == 2

    def test_fixture_table(self, tmp_path):
        from pathlib import Path
        fixture = Path(__file__).parent / 'fixtures' / 'table.html'
        html = fixture.read_text(encoding='utf-8')
        cfg = ConversionConfig()
        result = Converter(config=cfg).convert(html)
        assert 'Widget' in result
        assert r'Doohickey \| special' in result
