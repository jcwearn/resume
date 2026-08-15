"""Variant filtering.

This is the logic that decides what a tailored resume actually says, and it is
invisible in the PDF: drop the wrong bullet and the build is still two pages and
still green. The emphasis-within-a-tier invariant in particular is asserted by a
comment in `select_bullets` and by nothing else.
"""

import pytest

from render import apply_variant, select_bullets


def bullet(text, priority=None, tags=None):
    entry = {"text": text}
    if priority is not None:
        entry["priority"] = priority
    if tags is not None:
        entry["tags"] = tags
    return entry


def texts(bullets):
    return [b["text"] for b in bullets]


# --------------------------------------------------------------------------
# max_priority
# --------------------------------------------------------------------------


def test_bullets_above_max_priority_are_dropped():
    bullets = [bullet("keep", 1), bullet("drop", 3)]
    assert texts(select_bullets(bullets, {"max_priority": 2}, None)) == ["keep"]


def test_a_bullet_at_exactly_max_priority_is_kept():
    assert texts(select_bullets([bullet("edge", 2)], {"max_priority": 2}, None)) == [
        "edge"
    ]


def test_priority_defaults_to_two_when_absent():
    """An unmarked bullet is a priority-2 bullet, so max_priority 1 drops it."""
    assert select_bullets([bullet("unmarked")], {"max_priority": 1}, None) == []
    assert texts(select_bullets([bullet("unmarked")], {"max_priority": 2}, None)) == [
        "unmarked"
    ]


def test_max_priority_defaults_to_two_when_the_variant_omits_it():
    bullets = [bullet("keep", 2), bullet("drop", 3)]
    assert texts(select_bullets(bullets, {}, None)) == ["keep"]


# --------------------------------------------------------------------------
# exclude_tags
# --------------------------------------------------------------------------


def test_a_bullet_sharing_any_excluded_tag_is_dropped():
    bullets = [
        bullet("keep", tags=["backend"]),
        bullet("drop", tags=["frontend", "backend"]),
    ]
    assert texts(select_bullets(bullets, {"exclude_tags": ["frontend"]}, None)) == [
        "keep"
    ]


def test_an_untagged_bullet_survives_exclusion():
    assert texts(
        select_bullets([bullet("plain")], {"exclude_tags": ["frontend"]}, None)
    ) == ["plain"]


def test_an_empty_exclude_list_drops_nothing():
    """variants/backend.yaml ships `exclude_tags: []`, which YAML loads as a list."""
    bullets = [bullet("a", tags=["frontend"])]
    assert texts(select_bullets(bullets, {"exclude_tags": []}, None)) == ["a"]


def test_a_null_exclude_list_drops_nothing():
    bullets = [bullet("a", tags=["frontend"])]
    assert texts(select_bullets(bullets, {"exclude_tags": None}, None)) == ["a"]


# --------------------------------------------------------------------------
# emphasize
# --------------------------------------------------------------------------


def test_emphasis_reorders_within_a_tier():
    bullets = [bullet("plain", 2), bullet("emphasised", 2, tags=["backend"])]
    ordered = select_bullets(bullets, {"emphasize": ["backend"]}, None)
    assert texts(ordered) == ["emphasised", "plain"]


def test_emphasis_never_floats_a_bullet_across_a_tier():
    """The documented invariant: priority dominates, emphasis only breaks ties.

    Without it a variant could promote a minor tagged bullet above the work that
    carries the role -- which is the whole reason priority is the first sort key.
    """
    bullets = [
        bullet("carries the role", 1),
        bullet("minor but tagged", 2, tags=["backend"]),
    ]
    ordered = select_bullets(bullets, {"emphasize": ["backend"]}, None)
    assert texts(ordered) == ["carries the role", "minor but tagged"]


def test_earlier_emphasize_tags_outrank_later_ones():
    bullets = [
        bullet("data", 2, tags=["data"]),
        bullet("backend", 2, tags=["backend"]),
    ]
    ordered = select_bullets(bullets, {"emphasize": ["backend", "api", "data"]}, None)
    assert texts(ordered) == ["backend", "data"]


def test_a_bullet_matching_several_tags_takes_its_best_rank():
    bullets = [
        bullet("api only", 2, tags=["api"]),
        bullet("data and backend", 2, tags=["data", "backend"]),
    ]
    ordered = select_bullets(bullets, {"emphasize": ["backend", "api", "data"]}, None)
    assert texts(ordered) == ["data and backend", "api only"]


def test_the_sort_is_stable_for_equally_ranked_bullets():
    """Bullets matching on both keys keep their authored order."""
    bullets = [
        bullet("first", 2, tags=["backend"]),
        bullet("second", 2, tags=["backend"]),
        bullet("third", 2, tags=["backend"]),
    ]
    ordered = select_bullets(bullets, {"emphasize": ["backend"]}, None)
    assert texts(ordered) == ["first", "second", "third"]


def test_authored_order_is_untouched_without_emphasis():
    bullets = [bullet("b", 2, tags=["backend"]), bullet("a", 2)]
    assert texts(select_bullets(bullets, {}, None)) == ["b", "a"]


# --------------------------------------------------------------------------
# cap, and the interaction that matters
# --------------------------------------------------------------------------


def test_cap_truncates():
    bullets = [bullet("a"), bullet("b"), bullet("c")]
    assert texts(select_bullets(bullets, {}, 2)) == ["a", "b"]


def test_cap_larger_than_the_list_is_harmless():
    assert texts(select_bullets([bullet("a")], {}, 10)) == ["a"]


def test_no_cap_keeps_everything():
    bullets = [bullet("a"), bullet("b")]
    assert texts(select_bullets(bullets, {}, None)) == ["a", "b"]


def test_emphasis_decides_what_survives_the_cap():
    """backend.yaml's stated design: frontend bullets aren't excluded, they fall off."""
    bullets = [
        bullet("frontend work", 2, tags=["frontend"]),
        bullet("backend work", 2, tags=["backend"]),
    ]
    kept = select_bullets(bullets, {"emphasize": ["backend"]}, 1)
    assert texts(kept) == ["backend work"]


# --------------------------------------------------------------------------
# Degenerate input
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bullets", [None, []])
def test_missing_bullets_yield_an_empty_list(bullets):
    """A role or the projects block may simply have none."""
    assert select_bullets(bullets, {}, None) == []


def test_a_bullet_without_text_is_a_hard_error():
    with pytest.raises(SystemExit):
        select_bullets([{"tags": ["backend"]}], {}, None)


def test_the_error_fires_even_for_a_bullet_that_would_be_filtered_out():
    """Validation before filtering, so a typo in a low-priority bullet still fails."""
    with pytest.raises(SystemExit):
        select_bullets([{"priority": 3}], {"max_priority": 1}, None)


# --------------------------------------------------------------------------
# apply_variant
# --------------------------------------------------------------------------


def test_apply_variant_filters_every_role_and_the_projects_block():
    experience = [
        {"company": "A", "bullets": [bullet("keep", 1), bullet("drop", 3)]},
        {"company": "B", "bullets": [bullet("also keep", 1)]},
    ]
    projects = {"bullets": [bullet("proj keep", 1), bullet("proj drop", 3)]}

    apply_variant(experience, projects, {"max_priority": 2})

    assert texts(experience[0]["bullets"]) == ["keep"]
    assert texts(experience[1]["bullets"]) == ["also keep"]
    assert texts(projects["bullets"]) == ["proj keep"]


def test_apply_variant_honours_a_per_entry_max_bullets():
    """The cap is the entry's, not the variant's -- each role sets its own."""
    experience = [{"max_bullets": 1, "bullets": [bullet("a"), bullet("b")]}]
    projects = {"bullets": [bullet("x"), bullet("y")]}

    apply_variant(experience, projects, {})

    assert texts(experience[0]["bullets"]) == ["a"]
    assert texts(projects["bullets"]) == ["x", "y"]


def test_apply_variant_copes_with_a_role_that_has_no_bullets():
    experience = [{"company": "A"}]
    projects = {}

    apply_variant(experience, projects, {})

    assert experience[0]["bullets"] == []
    assert projects["bullets"] == []
