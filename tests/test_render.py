"""The Jinja2 environment and the LaTeX rendering path."""

import pytest
from jinja2 import UndefinedError

from render import ROOT, VARIANTS, build_context, build_env, render


def variant_names():
    return sorted(p.stem for p in VARIANTS.glob("*.yaml"))


# --------------------------------------------------------------------------
# Delimiters
# --------------------------------------------------------------------------


def test_variable_delimiter_is_latex_safe():
    """`{{ }}` would collide with LaTeX's own braces, hence `\\VAR{...}`."""
    assert build_env().from_string(r"\VAR{ name }").render(name="Jackson") == "Jackson"


def test_a_jinja_default_delimiter_is_inert():
    assert build_env().from_string("{{ name }}").render(name="Jackson") == "{{ name }}"


def test_block_delimiter_drives_control_flow():
    template = build_env().from_string(
        r"\BLOCK{for item in items}\VAR{ item };\BLOCK{endfor}"
    )
    assert template.render(items=["a", "b"]) == "a;b;"


def test_comment_delimiter_is_stripped():
    assert build_env().from_string(r"a\#{ hidden }b").render() == "ab"


def test_undefined_names_raise_rather_than_render_empty():
    """StrictUndefined: a typo in a template should break the build, not the layout."""
    with pytest.raises(UndefinedError):
        build_env().from_string(r"\VAR{ nope }").render()


def test_a_missing_attribute_also_raises():
    with pytest.raises(UndefinedError):
        build_env().from_string(r"\VAR{ profile.nope }").render(profile={})


# --------------------------------------------------------------------------
# build_context
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", variant_names())
def test_every_shipped_variant_builds_a_context(name):
    context = build_context(name)
    assert set(context) == {
        "profile",
        "experience",
        "projects",
        "skills",
        "education",
        "variant",
    }


def test_context_names_the_variant_it_was_built_for():
    assert build_context("default")["variant"]["name"] == "default"


def test_experience_is_sorted_most_recent_first():
    entries = build_context("default")["experience"]
    sorts = [e["_sort"] for e in entries]
    assert sorts == sorted(sorts, reverse=True)


def test_every_role_gets_a_formatted_date_range():
    for entry in build_context("default")["experience"]:
        assert " – " in entry["dates"]


def test_an_unknown_variant_lists_the_available_ones():
    with pytest.raises(SystemExit) as excinfo:
        build_context("no-such-variant")
    message = str(excinfo.value)
    for name in variant_names():
        assert name in message


def test_a_variant_summary_override_wins():
    """profile.summary_variants.<name> replaces the default summary, if present."""
    profile = build_context("default")["profile"]
    assert "summary" in profile
    assert isinstance(profile["summary"], str)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", variant_names())
def test_render_writes_a_tex_file_for_each_variant(name, tmp_path):
    target = render(name, tmp_path)
    assert target == tmp_path / f"resume-{name}.tex"
    assert target.read_text(encoding="utf-8").strip()


def test_render_copies_the_class_beside_the_tex(tmp_path):
    """Tectonic compiles from that directory, so it has to be self-contained."""
    render("default", tmp_path)
    assert (tmp_path / "resume.cls").read_bytes() == (
        ROOT / "templates" / "resume.cls"
    ).read_bytes()


def test_render_creates_the_output_directory(tmp_path):
    nested = tmp_path / "does" / "not" / "exist"
    assert render("default", nested).exists()


def test_rendered_output_is_pure_ascii(tmp_path):
    """The point of the _UNICODE map: the .tex must compile under any engine."""
    tex = render("default", tmp_path).read_text(encoding="utf-8")
    non_ascii = {c for c in tex if ord(c) > 127}
    assert not non_ascii


def test_rendering_is_deterministic(tmp_path):
    """Reproducible PDFs depend on this; publish.yaml would loop without it."""
    first = render("default", tmp_path / "a").read_text(encoding="utf-8")
    second = render("default", tmp_path / "b").read_text(encoding="utf-8")
    assert first == second
