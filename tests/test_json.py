"""out/resume.json -- the payload jacksonwearn.com renders its resume page from.

Nothing downstream of this file is in this repo, so a shape change here breaks
the website silently. `make check` builds the JSON but only ever checks that the
PDFs fit on two pages.
"""

import json

from render import ROOT, build_context, render_json

COMMITTED = ROOT / "out" / "resume.json"


def load(tmp_path, variant="default"):
    return json.loads(
        render_json(variant, tmp_path / "resume.json").read_text(encoding="utf-8")
    )


def test_top_level_keys_are_the_documented_six(tmp_path):
    assert set(load(tmp_path)) == {
        "variant",
        "profile",
        "experience",
        "projects",
        "skills",
        "education",
    }


def test_the_internal_sort_key_is_stripped(tmp_path):
    """_sort is a tuple used to order entries here; it means nothing to a consumer."""
    for entry in load(tmp_path)["experience"]:
        assert "_sort" not in entry


def test_other_variants_summaries_are_stripped(tmp_path):
    """summary is already resolved, so shipping the rest invites picking the wrong one."""
    assert "summary_variants" not in load(tmp_path)["profile"]


def test_the_resolved_summary_survives(tmp_path):
    assert load(tmp_path)["profile"]["summary"]


def test_raw_start_and_end_are_kept_alongside_the_formatted_range(tmp_path):
    """So a consumer can sort or reformat without parsing "Jun 2024 – Jul 2026"."""
    for entry in load(tmp_path)["experience"]:
        assert {"start", "end", "dates"} <= set(entry)


def test_json_text_is_not_latex_escaped(tmp_path):
    """Escaping belongs to the LaTeX finalizer; a JSON consumer wants the original."""
    text = (ROOT / "out" / "resume.json").read_text(encoding="utf-8")
    assert r"\textbackslash" not in text
    assert r"\%" not in text


def test_only_the_default_variant_is_published(tmp_path):
    assert load(tmp_path)["variant"] == "default"


def test_bullets_match_the_latex_context_exactly(tmp_path):
    """The PDF and the website must not drift: both come from build_context."""
    payload = load(tmp_path)
    context = build_context("default")

    from_json = [[b["text"] for b in e["bullets"]] for e in payload["experience"]]
    from_context = [[b["text"] for b in e["bullets"]] for e in context["experience"]]
    assert from_json == from_context


def test_output_is_byte_identical_to_the_committed_file(tmp_path):
    """A golden test, and safe to assert because publish.yaml keeps out/ current.

    It fails in exactly two situations, both of which you want to know about:
    content changed without a rebuild, or render_json's shape changed and the
    website's consumer has not been told.
    """
    generated = render_json("default", tmp_path / "resume.json").read_text(
        encoding="utf-8"
    )
    assert generated == COMMITTED.read_text(encoding="utf-8")


def test_generation_is_deterministic(tmp_path):
    first = render_json("default", tmp_path / "a.json").read_text(encoding="utf-8")
    second = render_json("default", tmp_path / "b.json").read_text(encoding="utf-8")
    assert first == second


def test_the_target_directory_is_created(tmp_path):
    target = render_json("default", tmp_path / "nested" / "deeper" / "resume.json")
    assert target.exists()
