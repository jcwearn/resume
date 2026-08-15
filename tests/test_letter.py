"""Cover letters.

Letters live under gitignored private/, so CI never renders one and a break here
would surface at the worst possible moment -- while writing an application.
"""

import pytest
import yaml

from render import (
    DEFAULT_CLOSING,
    DEFAULT_SALUTATION,
    build_letter_context,
    render_letter,
)

MINIMAL = {
    "company": "Acme Corp",
    "role": "Staff Software Engineer",
    "paragraphs": ["First paragraph.", "Second paragraph."],
}


def write_letter(tmp_path, data, name="acme"):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_a_minimal_letter_loads(tmp_path):
    context = build_letter_context(write_letter(tmp_path, MINIMAL))
    assert context["letter"]["company"] == "Acme Corp"
    assert context["letter"]["paragraphs"] == MINIMAL["paragraphs"]


def test_the_profile_is_merged_in(tmp_path):
    """Name, location, email and links come from profile.yaml, never the letter,
    so a letter's header cannot drift from the resume's."""
    context = build_letter_context(write_letter(tmp_path, MINIMAL))
    assert context["profile"]["name"]


def test_a_missing_file_is_a_hard_error(tmp_path):
    with pytest.raises(SystemExit):
        build_letter_context(tmp_path / "nope.yaml")


@pytest.mark.parametrize("field", ["company", "role", "paragraphs"])
def test_each_required_field_is_enforced(tmp_path, field):
    data = {k: v for k, v in MINIMAL.items() if k != field}
    with pytest.raises(SystemExit):
        build_letter_context(write_letter(tmp_path, data))


def test_empty_paragraphs_are_rejected(tmp_path):
    """Present but empty is its own case: the field exists, the letter has no body."""
    with pytest.raises(SystemExit):
        build_letter_context(write_letter(tmp_path, {**MINIMAL, "paragraphs": []}))


def test_an_empty_file_is_rejected(tmp_path):
    path = tmp_path / "blank.yaml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit):
        build_letter_context(path)


def test_the_slug_becomes_the_default_name(tmp_path):
    letter = build_letter_context(write_letter(tmp_path, MINIMAL, name="acme-corp"))[
        "letter"
    ]
    assert letter["name"] == "acme-corp"


def test_salutation_and_closing_have_defaults(tmp_path):
    letter = build_letter_context(write_letter(tmp_path, MINIMAL))["letter"]
    assert letter["salutation"] == DEFAULT_SALUTATION
    assert letter["closing"] == DEFAULT_CLOSING
    assert letter["date"] is None


def test_explicit_values_beat_the_defaults(tmp_path):
    data = {
        **MINIMAL,
        "salutation": "Dear Alex",
        "closing": "Best",
        "date": "2026-08-15",
    }
    letter = build_letter_context(write_letter(tmp_path, data))["letter"]
    assert letter["salutation"] == "Dear Alex"
    assert letter["closing"] == "Best"
    assert letter["date"] == "2026-08-15"


def test_render_letter_writes_a_tex_named_for_the_slug(tmp_path):
    source = write_letter(tmp_path, MINIMAL, name="acme")
    out_dir = tmp_path / "build"
    target = render_letter(source, out_dir)
    assert target == out_dir / "letter-acme.tex"
    assert target.read_text(encoding="utf-8").strip()


def test_render_letter_copies_the_class_beside_the_tex(tmp_path):
    render_letter(write_letter(tmp_path, MINIMAL), tmp_path / "build")
    assert (tmp_path / "build" / "resume.cls").exists()


def test_letter_prose_is_latex_escaped(tmp_path):
    data = {**MINIMAL, "paragraphs": ["Grew revenue 40% & shipped a_b."]}
    tex = render_letter(write_letter(tmp_path, data), tmp_path / "build").read_text(
        encoding="utf-8"
    )
    assert r"40\% \& shipped a\_b." in tex
