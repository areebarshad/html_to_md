from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    from .._walker import Walker

_ALIGN_MAP = {
    'left': ':---',
    'right': '---:',
    'center': ':---:',
    'justify': '---',
}


def handle_table(node: Tag, walker: Walker) -> str:
    """Convert an HTML table to a GFM pipe table."""
    rows, alignments = _extract_rows(node, walker)
    if not rows:
        return ''

    # Normalize column count
    col_count = max(len(r) for r in rows)
    rows = [_pad_row(r, col_count, walker.config.table_missing_cell) for r in rows]

    # Determine column widths for pretty-printing
    col_widths = [
        max(len(rows[i][j]) for i in range(len(rows)))
        for j in range(col_count)
    ]
    # Ensure separator dashes meet alignment marker minimums
    col_widths = [max(w, 3) for w in col_widths]

    # Detect header row (first row when table has <thead> OR no explicit header)
    has_header = bool(node.find('thead')) or _first_row_is_th(node)
    if not has_header and rows:
        # Insert an empty header row so the table is valid CommonMark
        rows.insert(0, [''] * col_count)

    lines: list[str] = []
    for idx, row in enumerate(rows):
        padded = [cell.ljust(col_widths[j]) for j, cell in enumerate(row)]
        lines.append('| ' + ' | '.join(padded) + ' |')
        if idx == 0:
            sep_cells = [_separator(col_widths[j], alignments.get(j)) for j in range(col_count)]
            lines.append('| ' + ' | '.join(sep_cells) + ' |')

    return '\n\n' + '\n'.join(lines) + '\n\n'


def _extract_rows(table: Tag, walker: Walker) -> tuple[list[list[str]], dict[int, str]]:
    rows: list[list[str]] = []
    alignments: dict[int, str] = {}

    # Collect column alignments from <col> / <colgroup>
    for col_idx, col in enumerate(table.find_all('col')):
        if isinstance(col, Tag):
            align = col.get('align', '')
            if align and isinstance(align, str):
                alignments[col_idx] = align.lower()

    for tr in table.find_all('tr'):
        if not isinstance(tr, Tag):
            continue
        cells: list[str] = []
        for col_idx, cell in enumerate(tr.find_all(['td', 'th'])):
            if not isinstance(cell, Tag):
                continue
            # Pick up inline alignment
            align = cell.get('align', '')
            if align and isinstance(align, str) and col_idx not in alignments:
                alignments[col_idx] = align.lower()

            content = walker.convert_children(cell).strip()
            # Pipe characters inside cells must be escaped
            content = content.replace('|', '\\|')
            # Collapse newlines inside a cell
            content = ' '.join(content.splitlines())

            # Handle colspan: repeat cell
            colspan = _int_attr(cell, 'colspan', 1)
            cells.append(content)
            for _ in range(colspan - 1):
                cells.append(walker.config.table_missing_cell)

        if cells:
            rows.append(cells)

    return rows, alignments


def _pad_row(row: list[str], width: int, filler: str) -> list[str]:
    if len(row) >= width:
        return row[:width]
    return row + [filler] * (width - len(row))


def _separator(width: int, align: str | None) -> str:
    marker = _ALIGN_MAP.get(align or '', '---')
    # Pad marker to column width
    dashes_needed = width - (len(marker) - marker.count(':'))
    if align == 'center':
        dashes = '-' * max(dashes_needed, 1)
        return f':{dashes}:'
    elif align == 'left':
        dashes = '-' * max(width - 1, 3)
        return f':{dashes}'
    elif align == 'right':
        dashes = '-' * max(width - 1, 3)
        return f'{dashes}:'
    else:
        return '-' * max(width, 3)


def _first_row_is_th(table: Tag) -> bool:
    first_tr = table.find('tr')
    if not isinstance(first_tr, Tag):
        return False
    return bool(first_tr.find('th'))


def _int_attr(tag: Tag, attr: str, default: int) -> int:
    val = tag.get(attr, default)
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
