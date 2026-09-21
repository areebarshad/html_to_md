from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    from .._walker import Walker


def detect_language(code_tag: Tag, config) -> str:
    """
    Extract a language identifier from <code class="language-python"> etc.
    Returns empty string when no language is detected.
    """
    classes = code_tag.get('class') or []
    if isinstance(classes, str):
        classes = classes.split()

    for cls in classes:
        for prefix in config.code_language_classes:
            if cls.startswith(prefix):
                lang = cls[len(prefix):]
                if lang:
                    return lang

    # Also check data-lang attribute (used by some syntax highlighters)
    data_lang = code_tag.get('data-lang') or code_tag.get('data-language')
    if data_lang:
        return str(data_lang).strip()

    return ''


def handle_pre_code(pre_tag: Tag, walker: Walker) -> str:
    """
    Handle ``<pre><code ...>`` blocks — the standard HTML fenced-code pattern.
    Returns a fenced code block with optional language tag.
    """
    code_tag = pre_tag.find('code')
    if code_tag is None or not isinstance(code_tag, Tag):
        # Bare <pre> without <code> child
        walker.in_preformatted = True
        text = pre_tag.get_text()
        walker.in_preformatted = False
        return _fence(text, '', walker)

    lang = detect_language(code_tag, walker.config)
    walker.in_preformatted = True
    text = code_tag.get_text()
    walker.in_preformatted = False

    return _fence(text, lang, walker)


def _fence(text: str, lang: str, walker: Walker) -> str:
    char = walker.config.fenced_code_char
    # If the code itself contains the fence char sequences, use a longer fence
    fence_len = 3
    import re
    pattern = re.compile(rf'{re.escape(char)}{{3,}}')
    for match in pattern.finditer(text):
        fence_len = max(fence_len, len(match.group()) + 1)

    fence = char * fence_len
    # Ensure text ends with newline
    if text and not text.endswith('\n'):
        text += '\n'
    return f'\n\n{fence}{lang}\n{text}{fence}\n\n'
