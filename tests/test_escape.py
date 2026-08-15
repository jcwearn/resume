"""LaTeX escaping.

The finalizer runs on every string reaching a template, so a bug here is a
malformed .tex at best and silently wrong output at worst -- and `make check`
would not catch either as long as the result still fits on two pages.
"""

import pytest

from render import _SPECIAL, _UNICODE, Raw, build_env, finalize, latex_escape


@pytest.mark.parametrize(("char", "expected"), sorted(_SPECIAL.items()))
def test_every_special_character_is_escaped(char, expected):
    assert latex_escape(char) == expected


@pytest.mark.parametrize(("char", "expected"), sorted(_UNICODE.items()))
def test_every_unicode_character_is_mapped(char, expected):
    assert latex_escape(char) == expected


def test_backslash_replacement_is_not_re_escaped():
    """`\\` becomes `\\textbackslash{}`, whose own braces must survive intact.

    The two substitutions are separate passes over the string for exactly this
    reason. A single combined pass, or reordering them, would turn the braces
    this replacement introduces into `\\{\\}`.
    """
    assert latex_escape("\\") == r"\textbackslash{}"
    assert latex_escape("a\\b") == r"a\textbackslash{}b"


def test_special_pass_runs_before_unicode_pass():
    """An en-dash next to an ampersand: both maps apply, neither corrupts the other."""
    assert latex_escape("Jun 2024 – Jul 2026 & on") == r"Jun 2024 -- Jul 2026 \& on"


def test_non_breaking_space_becomes_a_tie():
    assert latex_escape("10 MB") == "10~MB"


def test_unmapped_text_passes_through():
    assert (
        latex_escape("plain ASCII, punctuation: ok!") == "plain ASCII, punctuation: ok!"
    )


def test_finalize_escapes_plain_strings():
    assert finalize("100% & rising") == r"100\% \& rising"


def test_finalize_leaves_raw_alone():
    """Raw is the opt-out for fields that hold real LaTeX or a URL."""
    url = Raw(r"https://example.com/a_b?c=1&d=2")
    assert finalize(url) == r"https://example.com/a_b?c=1&d=2"


def test_finalize_returns_raw_as_plain_str():
    """Jinja concatenates the result, so it must not stay a Raw and re-opt-out."""
    assert type(finalize(Raw("x"))) is str


@pytest.mark.parametrize("value", [None, 3, 2.5, True, ["a"], {"b": 1}])
def test_finalize_passes_non_strings_through_unchanged(value):
    assert finalize(value) is value


def test_raw_filter_is_registered_on_the_environment():
    assert build_env().filters["raw"] is Raw


def test_raw_filter_survives_a_render():
    """End to end: the filter has to defeat the finalizer, not just exist."""
    template = build_env().from_string(r"\VAR{ value | raw }")
    assert template.render(value="a_b & c") == "a_b & c"


def test_unfiltered_value_is_escaped_in_a_render():
    template = build_env().from_string(r"\VAR{ value }")
    assert template.render(value="a_b & c") == r"a\_b \& c"
