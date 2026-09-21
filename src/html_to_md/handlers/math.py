"""
MathML → LaTeX translator.

Strategy:
1. If a ``<semantics>`` child carries an ``<annotation encoding="application/x-tex">``
   (or ``application/x-latex``), that string is used verbatim — MathJax/LaTeXML pages
   always carry this and it is always better than anything we can reconstruct.
2. Otherwise, walk the MathML element tree recursively and produce LaTeX from structure.

Inline ``<math>`` → ``$...$``; display ``<math display="block">`` → ``$$...$$``
on its own block paragraph.  The delimiters are read from ``ConversionConfig``.
"""
from __future__ import annotations

import re
import string
from typing import TYPE_CHECKING

from bs4 import NavigableString, Tag

if TYPE_CHECKING:
    from .._walker import Walker


# ---------------------------------------------------------------------------
# Unicode → LaTeX command table
# ---------------------------------------------------------------------------

# Operators and relation symbols
_OP_MAP: dict[str, str] = {
    # Greek lower-case
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\epsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "π": r"\pi",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    # Greek upper-case
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "Θ": r"\Theta",
    "Λ": r"\Lambda",
    "Ξ": r"\Xi",
    "Π": r"\Pi",
    "Σ": r"\Sigma",
    "Υ": r"\Upsilon",
    "Φ": r"\Phi",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
    # Variant Greek
    "ϵ": r"\varepsilon",
    "ϑ": r"\vartheta",
    "ϕ": r"\varphi",
    "ϱ": r"\varrho",
    "ς": r"\varsigma",
    # Arrows
    "→": r"\to",
    "←": r"\leftarrow",
    "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow",
    "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow",
    "↦": r"\mapsto",
    "↑": r"\uparrow",
    "↓": r"\downarrow",
    # Binary operators
    "±": r"\pm",
    "∓": r"\mp",
    "×": r"\times",
    "÷": r"\div",
    "⋅": r"\cdot",
    "∘": r"\circ",
    "⊕": r"\oplus",
    "⊗": r"\otimes",
    "⊂": r"\subset",
    "⊃": r"\supset",
    "⊆": r"\subseteq",
    "⊇": r"\supseteq",
    "∩": r"\cap",
    "∪": r"\cup",
    # Relations
    "≤": r"\leq",
    "≥": r"\geq",
    "≠": r"\neq",
    "≈": r"\approx",
    "≡": r"\equiv",
    "∼": r"\sim",
    "∝": r"\propto",
    "∈": r"\in",
    "∉": r"\notin",
    "∋": r"\ni",
    # Large operators
    "∑": r"\sum",
    "∏": r"\prod",
    "∫": r"\int",
    "∮": r"\oint",
    "∂": r"\partial",
    "∇": r"\nabla",
    # Misc
    "∞": r"\infty",
    "∅": r"\emptyset",
    "√": r"\sqrt",
    "…": r"\ldots",
    "⋯": r"\cdots",
    "⋮": r"\vdots",
    "⋱": r"\ddots",
    "′": r"'",
    "″": r"''",
    "‾": r"\overline",   # used as accent in mover
    # Accent chars that appear as <mo> children of <mover>/<munder>
    "^": r"\hat",
    "~": r"\tilde",
    "→": r"\vec",        # duplicate key; last wins — arrow-over is \vec
    "⃗": r"\vec",   # COMBINING RIGHT ARROW ABOVE
    "˜": r"\tilde", # SMALL TILDE
    "ˆ": r"\hat",   # MODIFIER LETTER CIRCUMFLEX
    # Fences
    "(": "(",
    ")": ")",
    "[": "[",
    "]": "]",
    "{": r"\{",
    "}": r"\}",
    "|": r"|",
    "‖": r"\|",
    "⌈": r"\lceil",
    "⌉": r"\rceil",
    "⌊": r"\lfloor",
    "⌋": r"\rfloor",
    "〈": r"\langle",
    "〉": r"\rangle",
    "⟨": r"\langle",
    "⟩": r"\rangle",
}

# Accents applied via \hat{x}, \bar{x} etc. — keyed by the <mo> text in an mover
_ACCENT_MAP: dict[str, str] = {
    "^": r"\hat",
    "˜": r"\tilde",
    "~": r"\tilde",
    "‾": r"\bar",
    "¯": r"\bar",
    "̅": r"\bar",   # COMBINING OVERLINE
    "→": r"\vec",
    "⃗": r"\vec",
    "→": r"\vec",
    "˙": r"\dot",
    "¨": r"\ddot",
    "˘": r"\breve",
    "ˇ": r"\check",
    "˚": r"\mathring",
    "̂": r"\hat",   # COMBINING CIRCUMFLEX
    "̃": r"\tilde", # COMBINING TILDE
    # also handle multi-char accent operators from MathML
    "&#x5E;": r"\hat",
    "&#x7E;": r"\tilde",
}

# Named operators emitted by <mo> that should map to LaTeX \operatorname or macro
_NAMED_OPS: dict[str, str] = {
    "sin": r"\sin",
    "cos": r"\cos",
    "tan": r"\tan",
    "sec": r"\sec",
    "csc": r"\csc",
    "cot": r"\cot",
    "arcsin": r"\arcsin",
    "arccos": r"\arccos",
    "arctan": r"\arctan",
    "sinh": r"\sinh",
    "cosh": r"\cosh",
    "tanh": r"\tanh",
    "log": r"\log",
    "ln": r"\ln",
    "exp": r"\exp",
    "det": r"\det",
    "dim": r"\dim",
    "ker": r"\ker",
    "lim": r"\lim",
    "sup": r"\sup",
    "inf": r"\inf",
    "max": r"\max",
    "min": r"\min",
    "gcd": r"\gcd",
    "Cov": r"\operatorname{Cov}",
    "Var": r"\operatorname{Var}",
    "E": r"\operatorname{E}",
    "Pr": r"\Pr",
    "iid": r"\overset{\text{iid}}{\sim}",
    "indep": r"\overset{\text{indep}}{\sim}",
}

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def handle_math(node: Tag, walker: "Walker") -> str:
    """Convert a ``<math>`` element to a LaTeX-delimited string."""
    cfg = walker.config

    if cfg.math_style == "strip":
        return ""

    if cfg.math_style == "raw":
        return str(node)

    # --- latex mode ---
    is_display = _is_display(node)
    latex = _math_to_latex(node)

    open_d, close_d = cfg.math_block_delimiters if is_display else cfg.math_inline_delimiters

    if is_display:
        return f"\n\n{open_d}{latex}{close_d}\n\n"
    else:
        return f"{open_d}{latex}{close_d}"


# ---------------------------------------------------------------------------
# Display detection
# ---------------------------------------------------------------------------

def _is_display(node: Tag) -> bool:
    """Return True if this is a display (block) math element."""
    display_attr = node.get("display", "")
    if isinstance(display_attr, list):
        display_attr = " ".join(display_attr)
    if display_attr == "block":
        return True

    # MathJax / pandoc convention: wrapper element with class "math display"
    classes = node.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    if "display" in classes:
        return True

    # Check parent element for display hints
    parent = node.parent
    if parent and isinstance(parent, Tag):
        parent_classes = parent.get("class", [])
        if isinstance(parent_classes, str):
            parent_classes = parent_classes.split()
        if "math-display" in parent_classes or "display-math" in parent_classes:
            return True

    return False


# ---------------------------------------------------------------------------
# Top-level MathML → LaTeX converter
# ---------------------------------------------------------------------------

def _math_to_latex(node: Tag) -> str:
    """
    Convert a ``<math>`` element (or any MathML subtree) to a LaTeX string.

    First tries the annotation fast path; falls back to structural walk.
    """
    # Fast path: prefer embedded LaTeX annotation
    annotation = _find_annotation(node)
    if annotation is not None:
        return annotation.strip()

    # Structural walk
    return _tex(node).strip()


def _find_annotation(node: Tag) -> str | None:
    """
    Look for ``<annotation encoding="application/x-tex">`` inside a
    ``<semantics>`` element and return its text content, or None.
    """
    for enc in ("application/x-tex", "application/x-latex", "TeX", "LaTeX"):
        ann = node.find("annotation", attrs={"encoding": enc})
        if ann and isinstance(ann, Tag):
            return ann.get_text()
    return None


# ---------------------------------------------------------------------------
# Recursive MathML element walker
# ---------------------------------------------------------------------------

def _tex(node: Tag | NavigableString | None) -> str:
    """Recursively convert a MathML node to LaTeX."""
    if node is None:
        return ""

    if isinstance(node, NavigableString):
        text = str(node)
        # Skip pure whitespace NavigableStrings — they're formatting artefacts
        # inside the MathML source, not mathematical content.
        if text.strip() == "":
            return ""
        return _map_text(text)

    if not isinstance(node, Tag):
        return ""

    name = node.name or ""

    # Strip namespace prefix (e.g. "m:mi" → "mi")
    if ":" in name:
        name = name.split(":", 1)[1]

    # Leaf text elements
    if name in ("mi", "mn", "mtext", "ms"):
        return _tex_leaf(node, name)

    if name == "mo":
        return _tex_mo(node)

    if name == "mspace":
        width = node.get("width", "")
        if "em" in str(width):
            try:
                w = float(str(width).replace("em", ""))
                if w <= 0.16:
                    return r"\, "
                elif w <= 0.33:
                    return r"\; "
                else:
                    return r"\quad "
            except ValueError:
                pass
        return r"\, "

    # Grouping
    if name in ("mrow", "math", "semantics"):
        # For semantics, skip annotation elements
        children = [c for c in node.children
                    if not (isinstance(c, Tag) and c.name in ("annotation", "annotation-xml"))]
        return "".join(_tex(c) for c in children)

    # Style / presentation wrappers — pass through
    if name in ("mstyle", "mpadded", "merror", "mphantom", "menclose"):
        return _tex_children(node)

    # Fractions
    if name == "mfrac":
        children = _element_children(node)
        if len(children) >= 2:
            num = _tex(children[0])
            den = _tex(children[1])
            linethickness = node.get("linethickness", "")
            if linethickness in ("0", "0pt", "0em"):
                # Binomial coefficient style (no line)
                return r"\binom{" + num + r"}{" + den + r"}"
            return r"\frac{" + num + r"}{" + den + r"}"
        return _tex_children(node)

    # Square root / nth root
    if name == "msqrt":
        inner = _tex_children(node)
        return r"\sqrt{" + inner + r"}"

    if name == "mroot":
        children = _element_children(node)
        if len(children) >= 2:
            base = _tex(children[0])
            idx = _tex(children[1])
            return r"\sqrt[" + idx + r"]{" + base + r"}"
        return r"\sqrt{" + _tex_children(node) + r"}"

    # Sub / sup / subsup
    if name == "msub":
        children = _element_children(node)
        if len(children) >= 2:
            base = _brace(_tex(children[0]))
            sub = _brace(_tex(children[1]))
            return base + "_{" + sub.strip("{}") + "}"
        return _tex_children(node)

    if name == "msup":
        children = _element_children(node)
        if len(children) >= 2:
            base = _brace(_tex(children[0]))
            sup = _brace(_tex(children[1]))
            return base + "^{" + sup.strip("{}") + "}"
        return _tex_children(node)

    if name == "msubsup":
        children = _element_children(node)
        if len(children) >= 3:
            base = _brace(_tex(children[0]))
            sub = _tex(children[1])
            sup = _tex(children[2])
            return base + "_{" + sub + "}^{" + sup + "}"
        return _tex_children(node)

    # Over / under / underover
    if name == "mover":
        children = _element_children(node)
        if len(children) >= 2:
            base = _tex(children[0])
            accent_node = children[1]
            accent_text = accent_node.get_text() if isinstance(accent_node, Tag) else str(accent_node)
            accent_text = accent_text.strip()
            cmd = _ACCENT_MAP.get(accent_text)
            if cmd:
                return cmd + "{" + base + "}"
            # Not a known accent — use \overset
            over = _tex(accent_node)
            return r"\overset{" + over + r"}{" + base + r"}"
        return _tex_children(node)

    if name == "munder":
        children = _element_children(node)
        if len(children) >= 2:
            base = _tex(children[0])
            under = _tex(children[1])
            # Common case: \underbrace, \underline
            base_text = base.strip()
            if base_text in (r"\sum", r"\prod", r"\int", r"\lim", r"\max", r"\min",
                             r"\sup", r"\inf"):
                return base + r"_{" + under + r"}"
            return r"\underset{" + under + r"}{" + base + r"}"
        return _tex_children(node)

    if name == "munderover":
        children = _element_children(node)
        if len(children) >= 3:
            base = _tex(children[0])
            under = _tex(children[1])
            over = _tex(children[2])
            base_text = base.strip()
            if base_text in (r"\sum", r"\prod", r"\int", r"\lim"):
                return base + r"_{" + under + r"}^{" + over + r"}"
            return r"\overset{" + over + r"}{\underset{" + under + r"}{" + base + r"}}"
        return _tex_children(node)

    # Fences / delimiters
    if name == "mfenced":
        open_fence = str(node.get("open", "("))
        close_fence = str(node.get("close", ")"))
        sep = str(node.get("separators", ","))
        # Filter out <mo> children that are just the separator (e.g. redundant
        # explicit <mo>,</mo> inside mfenced — the separators attr handles those).
        sep_chars = set(sep) | {",", ";", "|"}
        children = [
            c for c in _element_children(node)
            if not (isinstance(c, Tag)
                    and (c.name or "").lstrip(":").endswith("mo")
                    and c.get_text().strip() in sep_chars)
        ]
        parts = []
        for i, child in enumerate(children):
            parts.append(_tex(child))
            if i < len(children) - 1 and sep:
                sep_char = sep[min(i, len(sep) - 1)]
                parts.append(sep_char + " ")
        inner = "".join(parts)
        open_latex = _fence_latex(open_fence)
        close_latex = _fence_latex(close_fence)
        return r"\left" + open_latex + inner + r"\right" + close_latex

    # Tables (arrays)
    if name == "mtable":
        return _tex_table(node)

    if name in ("mtr", "mlabeledtr"):
        # Handled inside _tex_table; skip if encountered standalone
        return _tex_children(node)

    if name == "mtd":
        return _tex_children(node)

    # Multiscripts (pre-sub/sup) — basic support
    if name == "mmultiscripts":
        children = _element_children(node)
        if children:
            base = _tex(children[0])
            scripts = "".join(_tex(c) for c in children[1:])
            return base + scripts
        return ""

    # Phantom / none
    if name in ("mphantom", "none"):
        return ""

    # Fallback: recurse
    return _tex_children(node)


# ---------------------------------------------------------------------------
# Leaf-element helpers
# ---------------------------------------------------------------------------

def _tex_leaf(node: Tag, name: str) -> str:
    """Handle mi / mn / mtext / ms leaves."""
    raw = node.get_text()
    if name == "mtext":
        # Preserve as \text{...}
        return r"\text{" + raw + r"}"
    if name == "ms":
        # String literal — treat as \text
        return r"\text{``" + raw + r"''}"
    if name == "mi":
        # Single letter: italic by default (fine in LaTeX math mode).
        # Multi-letter: treat as operator name if known, else \mathrm.
        mapped = _OP_MAP.get(raw)
        if mapped:
            return mapped
        if len(raw) > 1:
            named = _NAMED_OPS.get(raw)
            if named:
                return named
            # Multi-letter identifier → \mathrm
            return r"\mathrm{" + raw + r"}"
        # Check if mathvariant is "normal" (i.e. upright)
        variant = str(node.get("mathvariant", ""))
        if variant in ("normal", "bold", "bold-italic"):
            if variant == "bold":
                return r"\mathbf{" + raw + r"}"
            return r"\mathrm{" + raw + r"}"
        return _map_text(raw)
    if name == "mn":
        return raw
    return _map_text(raw)


def _tex_mo(node: Tag) -> str:
    """Handle <mo> operator elements."""
    raw = node.get_text().strip()
    # Named operators
    named = _NAMED_OPS.get(raw)
    if named:
        return named + " "
    # Unicode map
    mapped = _OP_MAP.get(raw)
    if mapped:
        # Add spacing around multi-char LaTeX commands (relation/binary operators)
        # so the following token is not absorbed into the command name.
        if mapped.startswith("\\") and len(mapped) > 2:
            return " " + mapped + " "
        return mapped
    # Stretchy or invisible operators
    if raw in ("⁡", "⁢", "⁣", "⁤"):  # invisible operators
        return ""
    # Fallback: return as-is with light escaping
    return _map_text(raw)


def _map_text(text: str) -> str:
    """Map individual characters through the operator table; return LaTeX."""
    result = []
    for ch in text:
        mapped = _OP_MAP.get(ch)
        if mapped:
            result.append(mapped)
        elif ch in string.ascii_letters or ch in string.digits:
            result.append(ch)
        elif ch == " ":
            result.append(r"\,")
        else:
            # Escape special LaTeX characters
            if ch in r"_^&%$#{}~\|":
                result.append("\\" + ch)
            else:
                result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# Table helper
# ---------------------------------------------------------------------------

def _tex_table(node: Tag) -> str:
    """Convert <mtable> to a LaTeX array environment."""
    rows = []
    for tr in node.find_all(re.compile(r"^m(labeled)?tr$"), recursive=False):
        cells = []
        for td in tr.find_all("mtd", recursive=False):
            cells.append(_tex(td))
        rows.append(" & ".join(cells))
    body = r" \\ ".join(rows)
    return r"\begin{array}{" + "c" * _max_cols(node) + r"}" + body + r"\end{array}"


def _max_cols(table: Tag) -> int:
    max_c = 0
    for tr in table.find_all(re.compile(r"^m(labeled)?tr$"), recursive=False):
        n = len(tr.find_all("mtd", recursive=False))
        if n > max_c:
            max_c = n
    return max(max_c, 1)


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _tex_children(node: Tag) -> str:
    return "".join(_tex(c) for c in node.children)


def _element_children(node: Tag) -> list[Tag]:
    """Return direct Tag children only (skip NavigableStrings)."""
    return [c for c in node.children if isinstance(c, Tag)]


def _brace(s: str) -> str:
    """Wrap in braces only if multi-character."""
    s = s.strip()
    if len(s) == 1:
        return s
    return "{" + s + "}"


def _fence_latex(fence: str) -> str:
    """Map a fence character to its LaTeX \\left/\\right argument."""
    mapping = {
        "(": "(",
        ")": ")",
        "[": "[",
        "]": "]",
        "{": r"\{",
        "}": r"\}",
        "|": r"|",
        "‖": r"\|",
        "⌈": r"\lceil",
        "⌉": r"\rceil",
        "⌊": r"\lfloor",
        "⌋": r"\rfloor",
        "〈": r"\langle",
        "〉": r"\rangle",
        "⟨": r"\langle",
        "⟩": r"\rangle",
        "": ".",   # empty → \left. (invisible delimiter)
    }
    return mapping.get(fence, fence)
