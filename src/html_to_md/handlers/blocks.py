from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    from .._walker import Walker

_SETEXT_CHARS = {1: '=', 2: '-'}


def handle_heading(node: Tag, walker: Walker, level: int) -> str:
    inner = walker.convert_children(node).strip()
    if not inner:
        return ''

    if walker.config.heading_style == 'setext' and level <= 2:
        char = _SETEXT_CHARS[level]
        underline = char * max(len(inner), 3)
        return f'\n\n{inner}\n{underline}\n\n'

    hashes = '#' * level
    return f'\n\n{hashes} {inner}\n\n'


def handle_p(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node).strip()
    if not inner:
        return ''
    return f'\n\n{inner}\n\n'


def handle_blockquote(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node).strip()
    if not inner:
        return ''
    quoted = '\n'.join(f'> {line}' for line in inner.splitlines())
    return f'\n\n{quoted}\n\n'


def handle_ul(node: Tag, walker: Walker, ordered: bool = False) -> str:
    walker.list_depth += 1
    walker.ordered_list_counters.append(0)
    items = _collect_list_items(node, walker, ordered)
    walker.list_depth -= 1
    walker.ordered_list_counters.pop()
    indent = '    ' * (walker.list_depth)
    result = '\n'.join(f'{indent}{item}' for item in items)
    if walker.list_depth == 0:
        return f'\n\n{result}\n\n'
    return f'\n{result}'


def handle_ol(node: Tag, walker: Walker) -> str:
    return handle_ul(node, walker, ordered=True)


def _collect_list_items(node: Tag, walker: Walker, ordered: bool) -> list[str]:
    items: list[str] = []
    counter = 1
    for child in node.children:
        if not isinstance(child, Tag):
            continue
        if child.name == 'li':
            if ordered:
                prefix = f'{counter}. '
                counter += 1
            else:
                prefix = '- '
            content = walker.convert_children(child).strip()
            # Handle multi-line list items — indent continuation lines
            lines = content.splitlines()
            if lines:
                first = f'{prefix}{lines[0]}'
                rest = [f'    {l}' for l in lines[1:]]
                items.append('\n'.join([first] + rest))
    return items


def handle_dl(node: Tag, walker: Walker) -> str:
    parts: list[str] = []
    for child in node.children:
        if not isinstance(child, Tag):
            continue
        if child.name == 'dt':
            term = walker.convert_children(child).strip()
            parts.append(f'**{term}**')
        elif child.name == 'dd':
            definition = walker.convert_children(child).strip()
            parts.append(f':   {definition}')
    return '\n\n' + '\n'.join(parts) + '\n\n'


def handle_hr(node: Tag, walker: Walker) -> str:
    return '\n\n---\n\n'


def handle_div(node: Tag, walker: Walker) -> str:
    inner = walker.convert_children(node).strip()
    if not inner:
        return ''
    return f'\n\n{inner}\n\n'


def handle_pre(node: Tag, walker: Walker) -> str:
    # Delegated to code handler when <pre><code> — handled in code.py
    # This handles bare <pre> (non-code verbatim blocks)
    walker.in_preformatted = True
    inner = node.get_text()
    walker.in_preformatted = False
    fence = walker.config.fenced_code_char * 3
    return f'\n\n{fence}\n{inner}\n{fence}\n\n'


def handle_details(node: Tag, walker: Walker) -> str:
    summary_tag = node.find('summary')
    if summary_tag and isinstance(summary_tag, Tag):
        summary_tag.decompose()
        summary_text = walker.convert_children(summary_tag).strip() if summary_tag else ''
    else:
        summary_text = 'Details'
    inner = walker.convert_children(node).strip()
    lines = [f'> **{summary_text}**'] + [f'> {l}' for l in inner.splitlines()]
    return '\n\n' + '\n'.join(lines) + '\n\n'


def handle_figure(node: Tag, walker: Walker) -> str:
    figcaption = node.find('figcaption')
    caption = ''
    if figcaption and isinstance(figcaption, Tag):
        caption = walker.convert_children(figcaption).strip()
        figcaption.decompose()
    inner = walker.convert_children(node).strip()
    if caption:
        return f'\n\n{inner}\n\n*{caption}*\n\n'
    return f'\n\n{inner}\n\n'
