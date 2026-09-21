"""
Tests for MathML → LaTeX conversion.

Covers the constructs named in the regression-analysis lecture report:
  - inline vs display detection
  - annotation fast-path
  - mi / mn / mo leaf elements
  - mfrac (fractions)
  - msub / msup / msubsup
  - mover (accents: hat, bar)
  - munderover (sum with limits)
  - nested expressions (OLS estimators)
  - math_style "raw" and "strip"
  - no backslash-doubling in output
  - display-math lines survive wrap_width
"""
from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from html_to_md import convert, ConversionConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mk(mathml: str, display: bool = False) -> str:
    """Wrap MathML snippet in a <math> element and a minimal HTML document."""
    disp = ' display="block"' if display else ''
    return f"<p><math{disp}>{mathml}</math></p>"


def _conv(html: str, **cfg_kwargs) -> str:
    cfg = ConversionConfig(**cfg_kwargs)
    return convert(html, config=cfg)


# ---------------------------------------------------------------------------
# Display detection
# ---------------------------------------------------------------------------

class TestDisplayDetection:
    def test_inline_wraps_in_single_dollar(self):
        md = _conv(_mk("<mi>x</mi>"))
        assert "$x$" in md

    def test_display_block_attr_wraps_in_double_dollar(self):
        md = _conv(_mk("<mi>x</mi>", display=True))
        assert "$$x$$" in md

    def test_display_class_convention(self):
        """class="math display" is a common MathJax/pandoc convention."""
        html = '<p><math class="math display"><mi>x</mi></math></p>'
        md = _conv(html)
        assert "$$x$$" in md

    def test_inline_class_convention(self):
        html = '<p><math class="math inline"><mi>x</mi></math></p>'
        md = _conv(html)
        assert "$x$" in md


# ---------------------------------------------------------------------------
# Annotation fast-path
# ---------------------------------------------------------------------------

class TestAnnotationFastPath:
    def test_semantics_annotation_used_verbatim(self):
        mathml = (
            "<semantics>"
            "<mrow><mi>Y</mi></mrow>"
            '<annotation encoding="application/x-tex">Y = f(X)</annotation>'
            "</semantics>"
        )
        md = _conv(_mk(mathml))
        assert "Y = f(X)" in md

    def test_latex_encoding_also_accepted(self):
        mathml = (
            "<semantics>"
            "<mrow><mi>Y</mi></mrow>"
            '<annotation encoding="application/x-latex">\\alpha + \\beta</annotation>'
            "</semantics>"
        )
        md = _conv(_mk(mathml))
        assert r"\alpha + \beta" in md

    def test_annotation_takes_priority_over_tree_walk(self):
        """Even if the tree would give different output, annotation wins."""
        mathml = (
            "<semantics>"
            "<mrow><mi>WRONG</mi></mrow>"
            '<annotation encoding="application/x-tex">CORRECT</annotation>'
            "</semantics>"
        )
        md = _conv(_mk(mathml))
        assert "CORRECT" in md
        assert "WRONG" not in md


# ---------------------------------------------------------------------------
# Leaf elements
# ---------------------------------------------------------------------------

class TestLeafElements:
    def test_mi_single_letter(self):
        md = _conv(_mk("<mi>x</mi>"))
        assert "$x$" in md

    def test_mi_greek_unicode(self):
        md = _conv(_mk("<mi>β</mi>"))
        assert r"\beta" in md

    def test_mi_varepsilon(self):
        md = _conv(_mk("<mi>ϵ</mi>"))
        assert r"\varepsilon" in md

    def test_mn_number(self):
        md = _conv(_mk("<mn>42</mn>"))
        assert "$42$" in md

    def test_mo_sum_operator(self):
        md = _conv(_mk("<mo>∑</mo>"))
        assert r"\sum" in md

    def test_mo_partial_derivative(self):
        md = _conv(_mk("<mo>∂</mo>"))
        assert r"\partial" in md

    def test_mtext_becomes_text_command(self):
        md = _conv(_mk("<mtext>iid</mtext>"))
        assert r"\text{iid}" in md


# ---------------------------------------------------------------------------
# Fractions
# ---------------------------------------------------------------------------

class TestFractions:
    def test_simple_fraction(self):
        """SSE/n → \\frac{SSE}{n}"""
        mathml = (
            "<mfrac>"
            "<mi>SSE</mi>"
            "<mi>n</mi>"
            "</mfrac>"
        )
        md = _conv(_mk(mathml))
        assert r"\frac" in md
        assert "SSE" in md
        assert "n" in md

    def test_nested_fraction(self):
        """\\frac{\\sum ...}{\\sum ...}"""
        mathml = (
            "<mfrac>"
            "<mrow><mo>∑</mo><mi>a</mi></mrow>"
            "<mrow><mo>∑</mo><mi>b</mi></mrow>"
            "</mfrac>"
        )
        md = _conv(_mk(mathml))
        assert r"\frac" in md
        assert r"\sum" in md


# ---------------------------------------------------------------------------
# Sub / sup
# ---------------------------------------------------------------------------

class TestSubSup:
    def test_msub(self):
        """Y_i"""
        mathml = "<msub><mi>Y</mi><mi>i</mi></msub>"
        md = _conv(_mk(mathml))
        assert "Y" in md
        assert "_{i}" in md or "_i" in md

    def test_msup(self):
        """X^2"""
        mathml = "<msup><mi>X</mi><mn>2</mn></msup>"
        md = _conv(_mk(mathml))
        assert "X" in md
        assert "^{2}" in md or "^2" in md

    def test_msubsup(self):
        """\\sum_{i=1}^{n}"""
        mathml = (
            "<msubsup>"
            "<mo>∑</mo>"
            "<mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow>"
            "<mi>n</mi>"
            "</msubsup>"
        )
        md = _conv(_mk(mathml))
        assert r"\sum" in md
        assert "_{" in md
        assert "}^{" in md or "^{" in md


# ---------------------------------------------------------------------------
# Accents (mover)
# ---------------------------------------------------------------------------

class TestAccents:
    def test_hat_over_beta(self):
        """\\hat{\\beta}"""
        mathml = (
            "<mover accent='true'>"
            "<mi>β</mi>"
            "<mo>^</mo>"
            "</mover>"
        )
        md = _conv(_mk(mathml))
        assert r"\hat" in md
        assert r"\beta" in md

    def test_bar_over_X(self):
        """\\bar{X}"""
        mathml = (
            "<mover accent='true'>"
            "<mi>X</mi>"
            "<mo>‾</mo>"
            "</mover>"
        )
        md = _conv(_mk(mathml))
        assert r"\bar" in md
        assert "X" in md

    def test_bar_with_overline_char(self):
        """Also common: ¯ (macron) as accent."""
        mathml = (
            "<mover accent='true'>"
            "<mi>Y</mi>"
            "<mo>¯</mo>"
            "</mover>"
        )
        md = _conv(_mk(mathml))
        assert r"\bar" in md


# ---------------------------------------------------------------------------
# Sum with limits (munderover)
# ---------------------------------------------------------------------------

class TestUnderOver:
    def test_sum_with_limits(self):
        """\\sum_{i=1}^{n}"""
        mathml = (
            "<munderover>"
            "<mo>∑</mo>"
            "<mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow>"
            "<mi>n</mi>"
            "</munderover>"
        )
        md = _conv(_mk(mathml))
        assert r"\sum" in md
        assert "_{" in md
        assert "}^{" in md or "^{" in md

    def test_integral_with_limits(self):
        mathml = (
            "<munderover>"
            "<mo>∫</mo>"
            "<mn>0</mn>"
            "<mo>∞</mo>"
            "</munderover>"
        )
        md = _conv(_mk(mathml))
        assert r"\int" in md
        assert r"\infty" in md


# ---------------------------------------------------------------------------
# Full equations from the lecture (structural walk — no annotation)
# ---------------------------------------------------------------------------

class TestLectureEquations:
    def test_linear_model(self):
        """Y_i = β_0 + β_1 X_i + ε_i"""
        mathml = (
            "<mrow>"
            "<msub><mi>Y</mi><mi>i</mi></msub>"
            "<mo>=</mo>"
            "<msub><mi>β</mi><mn>0</mn></msub>"
            "<mo>+</mo>"
            "<msub><mi>β</mi><mn>1</mn></msub>"
            "<msub><mi>X</mi><mi>i</mi></msub>"
            "<mo>+</mo>"
            "<msub><mi>ϵ</mi><mi>i</mi></msub>"
            "</mrow>"
        )
        md = _conv(_mk(mathml))
        assert r"\beta" in md
        assert r"\varepsilon" in md or r"\epsilon" in md

    def test_ols_beta1_hat(self):
        """
        \\hat{\\beta}_1 = \\frac{\\sum (X_i - \\bar{X})(Y_i - \\bar{Y})}
                                {\\sum (X_i - \\bar{X})^2}
        """
        mathml = (
            "<mrow>"
            "<msub>"
            "  <mover accent='true'><mi>β</mi><mo>^</mo></mover>"
            "  <mn>1</mn>"
            "</msub>"
            "<mo>=</mo>"
            "<mfrac>"
            "  <mrow><mo>∑</mo><mo>(</mo><msub><mi>X</mi><mi>i</mi></msub><mo>−</mo>"
            "         <mover accent='true'><mi>X</mi><mo>‾</mo></mover><mo>)</mo></mrow>"
            "  <mrow><mo>∑</mo><msup>"
            "         <mrow><mo>(</mo><msub><mi>X</mi><mi>i</mi></msub>"
            "         <mo>−</mo><mover accent='true'><mi>X</mi><mo>‾</mo></mover><mo>)</mo></mrow>"
            "         <mn>2</mn></msup></mrow>"
            "</mfrac>"
            "</mrow>"
        )
        md = _conv(_mk(mathml))
        assert r"\hat" in md
        assert r"\beta" in md
        assert r"\frac" in md
        assert r"\sum" in md
        assert r"\bar" in md

    def test_mse(self):
        """MSE = SSE / (n-2)"""
        mathml = (
            "<mrow>"
            "<mi>MSE</mi>"
            "<mo>=</mo>"
            "<mfrac><mi>SSE</mi><mrow><mi>n</mi><mo>−</mo><mn>2</mn></mrow></mfrac>"
            "</mrow>"
        )
        md = _conv(_mk(mathml))
        assert r"\frac" in md
        assert "SSE" in md

    def test_conditional_expectation(self):
        """E(Y | X)"""
        mathml = (
            "<mrow>"
            "<mi>E</mi>"
            "<mfenced open='(' close=')'>"
            "  <mrow><mi>Y</mi><mo>∣</mo><mi>X</mi></mrow>"
            "</mfenced>"
            "</mrow>"
        )
        md = _conv(_mk(mathml))
        assert "E" in md
        assert "Y" in md
        assert "X" in md


# ---------------------------------------------------------------------------
# math_style options
# ---------------------------------------------------------------------------

class TestMathStyle:
    def test_strip_drops_math(self):
        md = _conv(_mk("<mi>x</mi>"), math_style="strip")
        # No dollar signs
        assert "$" not in md

    def test_raw_emits_math_tag(self):
        md = _conv(_mk("<mi>x</mi>"), math_style="raw")
        assert "<math" in md

    def test_latex_default(self):
        md = _conv(_mk("<mi>x</mi>"))
        assert "$x$" in md


# ---------------------------------------------------------------------------
# No backslash doubling
# ---------------------------------------------------------------------------

class TestNoDoubleEscape:
    def test_backslash_not_doubled(self):
        mathml = "<mi>β</mi>"
        md = _conv(_mk(mathml))
        # Should contain \beta, NOT \\beta
        assert r"\beta" in md
        assert r"\\beta" not in md

    def test_frac_not_doubled(self):
        mathml = "<mfrac><mn>1</mn><mn>2</mn></mfrac>"
        md = _conv(_mk(mathml))
        assert r"\frac" in md
        assert r"\\frac" not in md


# ---------------------------------------------------------------------------
# Display-math lines survive wrap_width
# ---------------------------------------------------------------------------

class TestWrapProtection:
    def test_display_math_not_broken_by_wrap(self):
        long_mathml = "<mrow>" + "<mi>x</mi><mo>+</mo>" * 20 + "<mi>y</mi></mrow>"
        md = _conv(_mk(long_mathml, display=True), wrap_width=40)
        # The $$ delimiters must still be on their own lines
        lines = md.splitlines()
        assert any(line.strip().startswith("$$") for line in lines)


# ---------------------------------------------------------------------------
# Custom delimiters
# ---------------------------------------------------------------------------

class TestCustomDelimiters:
    def test_custom_inline_delimiters(self):
        cfg = ConversionConfig(
            math_inline_delimiters=(r"\(", r"\)"),
            math_block_delimiters=(r"\[", r"\]"),
        )
        md = convert(_mk("<mi>x</mi>"), config=cfg)
        assert r"\(x\)" in md

    def test_custom_block_delimiters(self):
        cfg = ConversionConfig(
            math_inline_delimiters=(r"\(", r"\)"),
            math_block_delimiters=(r"\[", r"\]"),
        )
        md = convert(_mk("<mi>x</mi>", display=True), config=cfg)
        assert r"\[x\]" in md
